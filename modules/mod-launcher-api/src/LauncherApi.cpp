// mod-launcher-api: HTTP API for the Esteria launcher (account creation, character management, presence).
// HTTP threads only parse and authenticate; every game or database action is queued to the world thread.
#include "AccountMgr.h"
#include "ArenaTeamMgr.h"
#include "CalendarMgr.h"
#include "CharacterCache.h"
#include "Config.h"
#include "DBCStores.h"
#include "DatabaseEnv.h"
#include "GuildMgr.h"
#include "Log.h"
#include "ObjectAccessor.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "StringFormat.h"
#include "Util.h"
#include "World.h"
#include "WorldSessionMgr.h"
#include "../vendor/json.hpp"
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/beast.hpp>
#include <boost/beast/ssl.hpp>
#include <atomic>
#include <chrono>
#include <deque>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <random>
#include <regex>
#include <thread>
#include <unordered_map>

namespace
{
    namespace asio = boost::asio;
    namespace beast = boost::beast;
    namespace http = beast::http;
    using Json = nlohmann::json;
    using Clock = std::chrono::steady_clock;
    using Tcp = asio::ip::tcp;

    constexpr std::size_t MaxBody = 16 * 1024;
    constexpr uint32 MaxConnections = 32;
    constexpr uint32 MaxQueued = 64;

    struct Settings
    {
        bool enabled = false;
        std::string bind = "127.0.0.1";
        uint16 port = 8095;
        std::string cert;
        std::string key;
        bool registration = true;
        uint32 tokenHours = 168;
        bool charDelete = true;
        bool rename = true;
        bool customize = true;
        bool faction = true;
        bool race = true;
    };

    struct Reply
    {
        int status = 200;
        Json body = Json::object();
    };

    Reply Fail(int status, std::string const& code, std::string const& message)
    {
        return {status, {{"error", code}, {"message", message}}};
    }

    struct Presence
    {
        std::string name;
        uint8 level = 0;
        uint8 raceId = 0;
        uint8 classId = 0;
        std::string race;
        std::string cls;
        std::string zone;
        uint32 mapId = 0;
    };

    struct Token
    {
        uint32 account = 0;
        Clock::time_point expires;
    };

    struct Task
    {
        std::function<Reply()> run;
        std::promise<Reply> done;
    };

    std::string Hex(std::size_t bytes)
    {
        static std::random_device device;
        std::string out;
        char const* digits = "0123456789abcdef";
        for (std::size_t i = 0; i < bytes; ++i)
        {
            uint32 value = device() & 0xFF;
            out += digits[value >> 4];
            out += digits[value & 15];
        }
        return out;
    }

    char const* LocaleName(char const* const* names)
    {
        char const* value = names[sWorld->GetDefaultDbcLocale()];
        return value && *value ? value : names[0] ? names[0] : "";
    }

    class Api
    {
    public:
        static Api& Instance()
        {
            static Api api;
            return api;
        }

        void Configure()
        {
            Settings next;
            next.enabled = sConfigMgr->GetOption<bool>("LauncherApi.Enable", false);
            next.bind = sConfigMgr->GetOption<std::string>("LauncherApi.Bind", "127.0.0.1");
            next.port = sConfigMgr->GetOption<uint16>("LauncherApi.Port", 8095);
            next.cert = sConfigMgr->GetOption<std::string>("LauncherApi.Tls.Cert", "");
            next.key = sConfigMgr->GetOption<std::string>("LauncherApi.Tls.Key", "");
            next.registration = sConfigMgr->GetOption<bool>("LauncherApi.AllowRegistration", true);
            next.tokenHours = sConfigMgr->GetOption<uint32>("LauncherApi.TokenHours", 168);
            next.charDelete = sConfigMgr->GetOption<bool>("LauncherApi.Character.Delete", true);
            next.rename = sConfigMgr->GetOption<bool>("LauncherApi.Service.Rename", true);
            next.customize = sConfigMgr->GetOption<bool>("LauncherApi.Service.Customize", true);
            next.faction = sConfigMgr->GetOption<bool>("LauncherApi.Service.Faction", true);
            next.race = sConfigMgr->GetOption<bool>("LauncherApi.Service.Race", true);
            std::lock_guard lock(mutex_);
            settings_ = next; // shortcut: listener address/TLS changes need a restart; the rest applies on reload
        }

        void Start()
        {
            Settings s = Current();
            if (!s.enabled)
                return;
            try
            {
                if (!s.cert.empty())
                {
                    tls_ = std::make_unique<asio::ssl::context>(asio::ssl::context::tls_server);
                    tls_->use_certificate_chain_file(s.cert);
                    tls_->use_private_key_file(s.key, asio::ssl::context::pem);
                }
                acceptor_ = std::make_unique<Tcp::acceptor>(io_, Tcp::endpoint(asio::ip::make_address(s.bind), s.port));
            }
            catch (std::exception const& error)
            {
                LOG_ERROR("module.launcherapi", "Could not start the launcher API: {}", error.what());
                tls_.reset();
                acceptor_.reset();
                return;
            }
            running_ = true;
            listener_ = std::thread([this] { Accept(); });
            LOG_INFO("module.launcherapi", "Launcher API listening on {}:{} ({})", s.bind, s.port, tls_ ? "TLS" : "plain HTTP");
        }

        void Stop()
        {
            running_ = false;
            if (acceptor_)
            {
                boost::system::error_code ignored;
                acceptor_->close(ignored);
            }
            if (listener_.joinable())
                listener_.join();
            for (int i = 0; i < 60 && active_ > 0; ++i)
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            std::deque<Task> pending;
            {
                std::lock_guard lock(mutex_);
                pending.swap(tasks_);
            }
            for (auto& task : pending)
                task.done.set_value(Fail(503, "shutdown", "Server is shutting down."));
        }

        // World thread: run queued API work.
        void Pump()
        {
            for (int budget = 8; budget > 0; --budget)
            {
                Task task;
                {
                    std::lock_guard lock(mutex_);
                    if (tasks_.empty())
                        return;
                    task = std::move(tasks_.front());
                    tasks_.pop_front();
                }
                try
                {
                    task.done.set_value(task.run());
                }
                catch (std::exception const& error)
                {
                    LOG_ERROR("module.launcherapi", "Launcher API task failed: {}", error.what());
                    task.done.set_value(Fail(500, "internal", "Internal error."));
                }
            }
        }

        void Track(Player* player)
        {
            Presence p;
            p.name = player->GetName();
            p.level = player->GetLevel();
            p.raceId = player->getRace();
            p.classId = player->getClass();
            p.mapId = player->GetMapId();
            if (ChrRacesEntry const* race = sChrRacesStore.LookupEntry(p.raceId))
                p.race = LocaleName(race->name);
            if (ChrClassesEntry const* cls = sChrClassesStore.LookupEntry(p.classId))
                p.cls = LocaleName(cls->name);
            if (AreaTableEntry const* area = sAreaTableStore.LookupEntry(player->GetZoneId()))
                p.zone = LocaleName(area->area_name);
            std::lock_guard lock(mutex_);
            online_[player->GetSession()->GetAccountId()] = std::move(p);
        }

        void Untrack(Player* player)
        {
            std::lock_guard lock(mutex_);
            online_.erase(player->GetSession()->GetAccountId());
        }

    private:
        Settings Current()
        {
            std::lock_guard lock(mutex_);
            return settings_;
        }

        void Accept()
        {
            while (running_)
            {
                Tcp::socket socket(io_);
                boost::system::error_code error;
                acceptor_->accept(socket, error);
                if (error)
                {
                    if (!running_)
                        return;
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                    continue;
                }
                if (active_ >= MaxConnections)
                    continue; // socket closes
                ++active_;
                std::thread([this, s = std::move(socket)]() mutable
                {
                    try
                    {
                        Connection(std::move(s));
                    }
                    catch (std::exception const&)
                    {
                    }
                    --active_;
                }).detach();
            }
        }

        template <class Stream>
        void Exchange(Stream& stream, std::string const& ip)
        {
            beast::flat_buffer buffer;
            http::request_parser<http::string_body> parser;
            parser.body_limit(MaxBody);
            http::read(stream, buffer, parser);
            http::request<http::string_body> request = parser.release();
            Reply reply = Route(request, ip);
            http::response<http::string_body> response{static_cast<http::status>(reply.status), request.version()};
            response.set(http::field::content_type, "application/json");
            response.set(http::field::access_control_allow_origin, "*");
            response.set(http::field::access_control_allow_headers, "authorization, content-type");
            response.set(http::field::access_control_allow_methods, "GET, POST, OPTIONS");
            response.keep_alive(false);
            response.body() = reply.status == 204 ? std::string() : reply.body.dump();
            response.prepare_payload();
            http::write(stream, response);
        }

        void Connection(Tcp::socket socket)
        {
            boost::system::error_code ignored;
            std::string ip = socket.remote_endpoint(ignored).address().to_string();
            beast::tcp_stream plain(std::move(socket));
            plain.expires_after(std::chrono::seconds(10));
            if (tls_)
            {
                beast::ssl_stream<beast::tcp_stream> secure(std::move(plain), *tls_);
                secure.handshake(asio::ssl::stream_base::server);
                Exchange(secure, ip);
                secure.shutdown(ignored);
            }
            else
            {
                Exchange(plain, ip);
                plain.socket().shutdown(Tcp::socket::shutdown_send, ignored);
            }
        }

        // ---- routing -------------------------------------------------------------------------------------------

        Reply Route(http::request<http::string_body> const& request, std::string const& ip)
        {
            if (request.method() == http::verb::options)
                return {204, Json::object()};
            std::string target(request.target());
            target = target.substr(0, target.find('?'));
            static std::string const prefix = "/launcher/v1/";
            if (target.rfind(prefix, 0) != 0)
                return Fail(404, "not_found", "Unknown route.");
            std::string route = target.substr(prefix.size());
            while (!route.empty() && route.back() == '/')
                route.pop_back();
            bool get = request.method() == http::verb::get;
            bool post = request.method() == http::verb::post;

            Json body = Json::object();
            if (post && !request.body().empty())
            {
                body = Json::parse(request.body(), nullptr, false);
                if (!body.is_object())
                    return Fail(400, "bad_request", "Body must be a JSON object.");
            }

            Settings s = Current();
            if (get && route == "info")
                return {200, {{"name", "launcher-api"}, {"registration", s.registration},
                    {"services", {{"rename", s.rename}, {"customize", s.customize}, {"faction", s.faction}, {"race", s.race}}},
                    {"characterDelete", s.charDelete}}};
            if (post && route == "register")
                return Register(body, ip, s);
            if (post && route == "login")
                return Login(body, ip, s);

            std::string header(request[http::field::authorization]);
            uint32 account = Authenticate(header.rfind("Bearer ", 0) == 0 ? header.substr(7) : std::string());
            if (!account)
                return Fail(401, "unauthorized", "Sign in again.");

            if (post && route == "logout")
            {
                std::lock_guard lock(mutex_);
                tokens_.erase(header.substr(7));
                return {200, {{"ok", true}}};
            }
            if (get && route == "presence")
                return PresenceOf(account);

            // Everything below touches the game or databases, so it runs on the world thread.
            std::function<Reply()> work;
            if (get && route == "me")
                work = [account] { return Me(account); };
            else if (post && route == "password")
                work = [account, body] { return ChangePassword(account, body); };
            else if (post && route == "email")
                work = [account, body] { return ChangeEmail(account, body); };
            else if (get && route == "characters")
                work = [account] { return Characters(account); };
            else if (post && route.rfind("characters/", 0) == 0)
                work = CharacterAction(account, route.substr(11), body, s);
            if (!work)
                return Fail(404, "not_found", "Unknown route.");
            return OnWorld(std::move(work));
        }

        Reply OnWorld(std::function<Reply()> work)
        {
            Task task{std::move(work), {}};
            std::future<Reply> future = task.done.get_future();
            {
                std::lock_guard lock(mutex_);
                if (!running_ || tasks_.size() >= MaxQueued)
                    return Fail(503, "busy", "Server busy; retry shortly.");
                tasks_.push_back(std::move(task));
            }
            if (future.wait_for(std::chrono::seconds(8)) != std::future_status::ready)
                return Fail(503, "busy", "Server busy; retry shortly.");
            return future.get();
        }

        // ---- sessions and throttling ---------------------------------------------------------------------------

        uint32 Authenticate(std::string const& token)
        {
            std::lock_guard lock(mutex_);
            auto found = tokens_.find(token);
            if (found == tokens_.end())
                return 0;
            if (found->second.expires < Clock::now())
            {
                tokens_.erase(found);
                return 0;
            }
            return found->second.account;
        }

        std::string Issue(uint32 account, uint32 hours)
        {
            std::string token = Hex(32);
            std::lock_guard lock(mutex_);
            auto now = Clock::now();
            for (auto it = tokens_.begin(); it != tokens_.end();)
                it = it->second.expires < now ? tokens_.erase(it) : std::next(it);
            tokens_[token] = {account, now + std::chrono::hours(hours ? hours : 1)};
            return token;
        }

        // Counts a hit against `key` and reports whether the caller is over `max` hits in `seconds`.
        bool Throttled(std::string const& key, std::size_t max, int seconds, bool record)
        {
            std::lock_guard lock(mutex_);
            auto now = Clock::now();
            auto& hits = hits_[key];
            while (!hits.empty() && now - hits.front() > std::chrono::seconds(seconds))
                hits.pop_front();
            bool over = hits.size() >= max;
            if (record && !over)
                hits.push_back(now);
            if (hits.empty())
                hits_.erase(key);
            return over;
        }

        // ---- handlers ------------------------------------------------------------------------------------------

        Reply Register(Json const& body, std::string const& ip, Settings const& s)
        {
            if (!s.registration)
                return Fail(403, "disabled", "Account creation is disabled on this server.");
            if (Throttled("reg:" + ip, 5, 3600, true))
                return Fail(429, "throttled", "Too many accounts created from this address; try again later.");
            std::string username = body.value("username", "");
            std::string password = body.value("password", "");
            std::string email = body.value("email", "");
            static std::regex const nameRule("^[A-Za-z0-9]{3,17}$");
            static std::regex const emailRule("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");
            if (!std::regex_match(username, nameRule))
                return Fail(400, "bad_username", "Account name must be 3-17 letters or digits.");
            if (password.size() < 6 || password.size() > MAX_PASS_STR)
                return Fail(400, "bad_password", "Password must be 6-16 characters.");
            if (email.size() > 120 || !std::regex_match(email, emailRule))
                return Fail(400, "bad_email", "Enter a valid email address.");
            return OnWorld([username, password, email]() -> Reply
            {
                switch (sAccountMgr->CreateAccount(username, password, email))
                {
                    case AOR_OK:
                        return {200, {{"ok", true}, {"username", username}}};
                    case AOR_NAME_ALREADY_EXIST:
                        return Fail(409, "name_taken", "That account name is already taken.");
                    default:
                        return Fail(400, "rejected", "The server rejected that account.");
                }
            });
        }

        Reply Login(Json const& body, std::string const& ip, Settings const& s)
        {
            if (Throttled("login:" + ip, 10, 600, false))
                return Fail(429, "throttled", "Too many failed sign-ins; try again in a few minutes.");
            std::string username = body.value("username", "");
            std::string password = body.value("password", "");
            Reply reply = OnWorld([username, password]() -> Reply
            {
                std::string upper = username;
                Utf8ToUpperOnlyLatin(upper);
                uint32 account = AccountMgr::GetId(upper);
                if (!account || !AccountMgr::CheckPassword(account, password))
                    return Fail(401, "bad_credentials", "Wrong account name or password.");
                return {200, {{"account", account}, {"username", upper}}};
            });
            if (reply.status != 200)
            {
                if (reply.status == 401)
                    Throttled("login:" + ip, 10, 600, true);
                return reply;
            }
            uint32 account = reply.body["account"].get<uint32>();
            reply.body.erase("account");
            reply.body["token"] = Issue(account, s.tokenHours);
            return reply;
        }

        static Reply Me(uint32 account)
        {
            std::string name;
            AccountMgr::GetName(account, name);
            std::string email;
            if (QueryResult result = LoginDatabase.Query(Acore::StringFormat("SELECT email FROM account WHERE id = {}", account)))
                email = result->Fetch()[0].Get<std::string>();
            return {200, {{"username", name}, {"email", email}}};
        }

        static Reply ChangePassword(uint32 account, Json const& body)
        {
            std::string current = body.value("current", "");
            std::string next = body.value("new", "");
            if (next.size() < 6 || next.size() > MAX_PASS_STR)
                return Fail(400, "bad_password", "Password must be 6-16 characters.");
            if (!AccountMgr::CheckPassword(account, current))
                return Fail(401, "bad_credentials", "Current password is wrong.");
            if (AccountMgr::ChangePassword(account, next) != AOR_OK)
                return Fail(400, "rejected", "The server rejected that password.");
            return {200, {{"ok", true}}};
        }

        static Reply ChangeEmail(uint32 account, Json const& body)
        {
            std::string password = body.value("password", "");
            std::string email = body.value("email", "");
            static std::regex const emailRule("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");
            if (email.size() > 120 || !std::regex_match(email, emailRule))
                return Fail(400, "bad_email", "Enter a valid email address.");
            if (!AccountMgr::CheckPassword(account, password))
                return Fail(401, "bad_credentials", "Password is wrong.");
            if (AccountMgr::ChangeEmail(account, email) != AOR_OK)
                return Fail(400, "rejected", "The server rejected that email.");
            return {200, {{"ok", true}, {"email", email}}};
        }

        static Reply Characters(uint32 account)
        {
            Json live = Json::array();
            if (QueryResult result = CharacterDatabase.Query(Acore::StringFormat(
                "SELECT guid, name, race, class, gender, level, zone, map, online, at_login FROM characters "
                "WHERE account = {} ORDER BY guid", account)))
            {
                do
                {
                    Field* f = result->Fetch();
                    uint8 raceId = f[2].Get<uint8>();
                    uint8 classId = f[3].Get<uint8>();
                    ChrRacesEntry const* race = sChrRacesStore.LookupEntry(raceId);
                    ChrClassesEntry const* cls = sChrClassesStore.LookupEntry(classId);
                    AreaTableEntry const* area = sAreaTableStore.LookupEntry(f[6].Get<uint32>());
                    live.push_back({{"guid", f[0].Get<uint32>()}, {"name", f[1].Get<std::string>()},
                        {"raceId", raceId}, {"classId", classId}, {"gender", f[4].Get<uint8>()},
                        {"race", race ? LocaleName(race->name) : ""}, {"class", cls ? LocaleName(cls->name) : ""},
                        {"level", f[5].Get<uint8>()}, {"zone", area ? LocaleName(area->area_name) : ""},
                        {"online", f[8].Get<bool>()}, {"pendingService", f[9].Get<uint32>()}});
                } while (result->NextRow());
            }
            Json deleted = Json::array();
            if (QueryResult result = CharacterDatabase.Query(Acore::StringFormat(
                "SELECT guid, deleteInfos_Name, race, class, level, deleteDate FROM characters "
                "WHERE deleteInfos_Account = {} AND deleteDate IS NOT NULL ORDER BY deleteDate DESC", account)))
            {
                do
                {
                    Field* f = result->Fetch();
                    ChrRacesEntry const* race = sChrRacesStore.LookupEntry(f[2].Get<uint8>());
                    ChrClassesEntry const* cls = sChrClassesStore.LookupEntry(f[3].Get<uint8>());
                    deleted.push_back({{"guid", f[0].Get<uint32>()}, {"name", f[1].Get<std::string>()},
                        {"race", race ? LocaleName(race->name) : ""}, {"class", cls ? LocaleName(cls->name) : ""},
                        {"level", f[4].Get<uint8>()}, {"deletedAt", f[5].Get<uint32>()}});
                } while (result->NextRow());
            }
            return {200, {{"characters", live}, {"deleted", deleted}}};
        }

        // route: "<guid>/delete" | "<guid>/restore" | "<guid>/service"
        static std::function<Reply()> CharacterAction(uint32 account, std::string const& route, Json const& body, Settings const& s)
        {
            std::size_t slash = route.find('/');
            if (slash == std::string::npos || slash == 0 || slash > 10 || route.find_first_not_of("0123456789") < slash)
                return {};
            uint32 guid = static_cast<uint32>(std::stoul(route.substr(0, slash)));
            std::string action = route.substr(slash + 1);
            if (action == "delete")
                return [=] { return s.charDelete ? Delete(account, guid) : Fail(403, "disabled", "Character deletion is disabled."); };
            if (action == "restore")
                return [=] { return s.charDelete ? Restore(account, guid) : Fail(403, "disabled", "Character restore is disabled."); };
            if (action == "service")
                return [=] { return Service(account, guid, body.value("service", ""), s); };
            return {};
        }

        static bool InUse(uint32 guid)
        {
            return ObjectAccessor::FindConnectedPlayer(ObjectGuid::Create<HighGuid::Player>(guid)) ||
                sWorldSessionMgr->FindOfflineSessionForCharacterGUID(guid);
        }

        static bool Owns(uint32 account, uint32 guid)
        {
            CharacterCacheEntry const* data = sCharacterCache->GetCharacterCacheByGuid(ObjectGuid::Create<HighGuid::Player>(guid));
            return data && data->AccountId == account;
        }

        static Reply Delete(uint32 account, uint32 guid)
        {
            ObjectGuid object = ObjectGuid::Create<HighGuid::Player>(guid);
            if (!Owns(account, guid))
                return Fail(404, "not_found", "No such character on this account.");
            if (InUse(guid))
                return Fail(409, "online", "Log the character out of the game first.");
            if (sGuildMgr->GetGuildByLeader(object))
                return Fail(409, "guild_leader", "Hand over guild leadership before deleting this character.");
            if (sArenaTeamMgr->GetArenaTeamByCaptain(object))
                return Fail(409, "arena_captain", "Hand over your arena team before deleting this character.");
            sScriptMgr->OnPlayerDelete(object, account);
            sCalendarMgr->RemoveAllPlayerEventsAndInvites(object);
            Player::DeleteFromDB(guid, account, true, false);
            sWorld->UpdateRealmCharCount(account);
            LOG_INFO("module.launcherapi", "Account {} deleted character {} from the launcher", account, guid);
            return {200, {{"ok", true}}};
        }

        static Reply Restore(uint32 account, uint32 guid)
        {
            QueryResult deleted = CharacterDatabase.Query(Acore::StringFormat(
                "SELECT deleteInfos_Name FROM characters WHERE guid = {} AND deleteInfos_Account = {} AND deleteDate IS NOT NULL",
                guid, account));
            if (!deleted)
                return Fail(404, "not_found", "No such deleted character on this account.");
            std::string name = deleted->Fetch()[0].Get<std::string>();
            if (AccountMgr::GetCharactersCount(account) >= sWorld->getIntConfig(CONFIG_CHARACTERS_PER_ACCOUNT))
                return Fail(409, "full", "Your account has no free character slot.");
            if (sCharacterCache->GetCharacterGuidByName(name))
                return Fail(409, "name_taken", "Another character now uses that name.");
            CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_NAME_DATA);
            stmt->SetData(0, guid);
            PreparedQueryResult data = CharacterDatabase.Query(stmt);
            if (!data)
                return Fail(404, "not_found", "Character data is missing.");
            Field* f = data->Fetch();
            if (f[4].IsNull() || (f[4].Get<uint8>() != TEAM_ALLIANCE && f[4].Get<uint8>() != TEAM_HORDE))
                return Fail(409, "bad_team", "Character data is invalid; ask an administrator.");
            TeamId team = static_cast<TeamId>(f[4].Get<uint8>());
            stmt = CharacterDatabase.GetPreparedStatement(CHAR_UDP_RESTORE_DELETE_INFO);
            stmt->SetData(0, name);
            stmt->SetData(1, account);
            stmt->SetData(2, guid);
            CharacterDatabase.Execute(stmt);
            sCharacterCache->AddCharacterCacheEntry(ObjectGuid::Create<HighGuid::Player>(guid), account, name,
                f[2].Get<uint8>(), f[0].Get<uint8>(), f[1].Get<uint8>(), f[3].Get<uint8>(), team);
            sWorld->UpdateRealmCharCount(account);
            return {200, {{"ok", true}}};
        }

        static Reply Service(uint32 account, uint32 guid, std::string const& service, Settings const& s)
        {
            uint32 flag = 0;
            if (service == "rename" && s.rename)
                flag = AT_LOGIN_RENAME;
            else if (service == "customize" && s.customize)
                flag = AT_LOGIN_CUSTOMIZE;
            else if (service == "faction" && s.faction)
                flag = AT_LOGIN_CHANGE_FACTION;
            else if (service == "race" && s.race)
                flag = AT_LOGIN_CHANGE_RACE;
            if (!flag)
                return Fail(400, "bad_service", "That service is unavailable.");
            if (!Owns(account, guid))
                return Fail(404, "not_found", "No such character on this account.");
            if (InUse(guid))
                return Fail(409, "online", "Log the character out of the game first.");
            CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_ADD_AT_LOGIN_FLAG);
            stmt->SetData(0, static_cast<uint16>(flag));
            stmt->SetData(1, guid);
            CharacterDatabase.Execute(stmt);
            return {200, {{"ok", true}, {"message", "Log in to that character in the game client to finish."}}};
        }

        Reply PresenceOf(uint32 account)
        {
            std::lock_guard lock(mutex_);
            auto found = online_.find(account);
            if (found == online_.end())
                return {200, {{"online", false}}};
            Presence const& p = found->second;
            return {200, {{"online", true}, {"character", {{"name", p.name}, {"level", p.level}, {"race", p.race},
                {"raceId", p.raceId}, {"class", p.cls}, {"classId", p.classId}, {"zone", p.zone}, {"map", p.mapId}}}}};
        }

        std::mutex mutex_;
        Settings settings_;
        std::unordered_map<std::string, Token> tokens_;
        std::unordered_map<std::string, std::deque<Clock::time_point>> hits_;
        std::unordered_map<uint32, Presence> online_;
        std::deque<Task> tasks_;
        asio::io_context io_;
        std::unique_ptr<asio::ssl::context> tls_;
        std::unique_ptr<Tcp::acceptor> acceptor_;
        std::thread listener_;
        std::atomic<bool> running_{false};
        std::atomic<uint32> active_{0};
    };

    class LauncherWorld final : public WorldScript
    {
    public:
        LauncherWorld() : WorldScript("LauncherApiWorld") { }
        void OnAfterConfigLoad(bool) override { Api::Instance().Configure(); }
        void OnStartup() override { Api::Instance().Start(); }
        void OnUpdate(uint32) override { Api::Instance().Pump(); }
        void OnShutdown() override { Api::Instance().Stop(); }
    };

    class LauncherPlayer final : public PlayerScript
    {
    public:
        LauncherPlayer() : PlayerScript("LauncherApiPlayer", {PLAYERHOOK_ON_LOGIN, PLAYERHOOK_ON_LOGOUT,
            PLAYERHOOK_ON_LEVEL_CHANGED, PLAYERHOOK_ON_UPDATE_ZONE}) { }
        void OnPlayerLogin(Player* player) override { Api::Instance().Track(player); }
        void OnPlayerLogout(Player* player) override { Api::Instance().Untrack(player); }
        void OnPlayerLevelChanged(Player* player, uint8) override { Api::Instance().Track(player); }
        void OnPlayerUpdateZone(Player* player, uint32, uint32) override { Api::Instance().Track(player); }
    };
}

void AddSC_launcher_api()
{
    new LauncherWorld();
    new LauncherPlayer();
}
