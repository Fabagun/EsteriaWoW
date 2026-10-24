#include "BattlemonBattles.h"
#include "BattlemonMgr.h"
#include "Chat.h"
#include "ChatCommand.h"
#include "Group.h"
#include "Player.h"
#include "PlayerScript.h"
#include "ScriptMgr.h"
#include "WorldSession.h"

using namespace Acore::ChatCommands;

namespace
{
    bool IsMessage(uint32 language, std::string const& text)
    {
        return language == LANG_ADDON && text.compare(0, 4, "BMB\t") == 0;
    }
}

class BattlemonBattlesWorld final : public WorldScript
{
public:
    BattlemonBattlesWorld() : WorldScript("BattlemonBattlesWorld", {
        WORLDHOOK_ON_BEFORE_CONFIG_LOAD, WORLDHOOK_ON_UPDATE}) { }

    void OnBeforeConfigLoad(bool /*reload*/) override
    {
        BattlemonBattles::Instance().LoadConfig();
    }

    void OnUpdate(uint32 diff) override
    {
        BattlemonBattles::Instance().Update(diff);
    }
};

class BattlemonBattlesPlayer final : public PlayerScript
{
public:
    BattlemonBattlesPlayer() : PlayerScript("BattlemonBattlesPlayer", {
        PLAYERHOOK_ON_BEFORE_LOGOUT, PLAYERHOOK_ON_LOGOUT, PLAYERHOOK_ON_MAP_CHANGED,
        PLAYERHOOK_ON_BEFORE_SEND_CHAT_MESSAGE,
        PLAYERHOOK_CAN_PLAYER_USE_PRIVATE_CHAT, PLAYERHOOK_CAN_PLAYER_USE_GROUP_CHAT}) { }

    void OnPlayerBeforeLogout(Player* player) override
    {
        BattlemonBattles::Instance().Leave(player);
    }

    void OnPlayerLogout(Player* player) override
    {
        BattlemonBattles::Instance().Enqueue(player->GetGUID(), "", true);
    }

    void OnPlayerMapChanged(Player* player) override
    {
        BattlemonBattles::Instance().Enqueue(player->GetGUID(), "", true);
    }

    void OnPlayerBeforeSendChatMessage(Player* player, uint32& /*type*/, uint32& language,
        std::string& text) override
    {
        if (IsMessage(language, text))
            BattlemonBattles::Instance().Enqueue(player->GetGUID(), text.substr(4));
    }

    bool OnPlayerCanUseChat(Player* /*player*/, uint32 /*type*/, uint32 language,
        std::string& text, Player* /*receiver*/) override
    {
        return !IsMessage(language, text);
    }

    bool OnPlayerCanUseChat(Player* /*player*/, uint32 /*type*/, uint32 language,
        std::string& text, Group* /*group*/) override
    {
        return !IsMessage(language, text);
    }
};

class BattlemonBattlesCommands final : public CommandScript
{
public:
    BattlemonBattlesCommands() : CommandScript("BattlemonBattlesCommands") { }

    ChatCommandTable GetCommands() const override
    {
        static ChatCommandTable actions = {
            {"duel", Challenge, SEC_PLAYER, Console::No},
            {"accept", Accept, SEC_PLAYER, Console::No},
            {"decline", Decline, SEC_PLAYER, Console::No},
            {"forfeit", Forfeit, SEC_PLAYER, Console::No}
        };
        static ChatCommandTable commands = {{"bmb", actions}};
        return commands;
    }

    static bool Queue(ChatHandler* handler, char const* command)
    {
        if (handler->GetSession())
            BattlemonBattles::Instance().Enqueue(handler->GetSession()->GetPlayer()->GetGUID(), command);
        return true;
    }

    static bool Challenge(ChatHandler* handler) { return Queue(handler, "CHALLENGE"); }
    static bool Accept(ChatHandler* handler) { return Queue(handler, "ACCEPT"); }
    static bool Decline(ChatHandler* handler) { return Queue(handler, "DECLINE"); }
    static bool Forfeit(ChatHandler* handler) { return Queue(handler, "FORFEIT"); }
};

void AddSC_battlemon_battles()
{
    sBattlemonMgr->SetExtension(&BattlemonBattles::Instance());
    new BattlemonBattlesWorld();
    new BattlemonBattlesPlayer();
    new BattlemonBattlesCommands();
}
