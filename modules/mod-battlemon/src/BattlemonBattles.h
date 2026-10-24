#ifndef BATTLEMON_BATTLES_H
#define BATTLEMON_BATTLES_H

#include "BattlemonExtension.h"
#include "BattlemonTypes.h"
#include "Position.h"
#include "TaskScheduler.h"
#include <array>
#include <deque>
#include <mutex>
#include <unordered_map>
#include <unordered_set>

class Player;
class Creature;

class BattlemonBattles final : public BattlemonExtension
{
public:
    static BattlemonBattles& Instance();
    void LoadConfig();
    void Update(uint32 diff);
    void Enqueue(ObjectGuid player, std::string const& message, bool disconnect = false);
    bool IsReserved(ObjectGuid guid) const override;
    bool OnPacket(Player* player, std::string const& payload) override;
    bool IsPlaybackBusy(ObjectGuid guid) const override;
    void OnCatalogReload() override;
    void Leave(Player* player);
    void ChallengeTrainer(Player* player, Creature* trainer);

private:
    enum class ActionKind { None, Move, Switch, Struggle };
    struct Action
    {
        ActionKind kind = ActionKind::None;
        uint8 index = 0;
    };
    struct Duel
    {
        uint64 id = 0;
        ObjectGuid trainer = ObjectGuid::Empty;
        uint32 trainerEntry = 0;
        std::string trainerName;
        std::array<ObjectGuid, 2> players;
        std::array<std::vector<BattlemonBattler>, 2> teams;
        std::array<uint8, 2> active = {};
        std::array<Action, 2> actions;
        std::array<bool, 2> forced = {};
        std::array<bool, 2> bots = {};
        BattlemonEncounter field;
        uint32 revision = 1;
        uint64 deadline = 0;
        uint64 botAt = 0;
    };
    struct Invite
    {
        ObjectGuid from;
        uint64 expires = 0;
    };
    struct Scene
    {
        std::array<ObjectGuid, 2> actors;
        std::vector<ObjectGuid> effects;
        std::array<uint32, 2> displays = {};
        uint32 map = 0;
        uint32 instance = 0;
        Position origin;
        std::array<Position, 2> homes;
        std::array<ObjectGuid, 2> participants;
        std::array<uint32, 2> previousPhases = {};
        uint32 phase = 0;
        uint64 animationAt = 0;
        uint8 visualCast = 0;
        bool ending = false;
    };
    struct Input
    {
        ObjectGuid player;
        std::string message;
        bool disconnect = false;
        bool packet = false;
        bool deferred = false;
        ObjectGuid trainer = ObjectGuid::Empty;
    };

    BattlemonBattles();
    void Process(Input const& input);
    void Poll();
    void Challenge(Player* player);
    void Begin(Player* a, Player* b);
    void BeginTrainer(Player* player, Creature* trainer);
    bool DuelValid(Duel const& duel) const;
    void SubmitSide(Duel& duel, uint8 side, uint32 revision, Action action);
    void Submit(Player* player, uint32 revision, Action action);
    void Resolve(Duel& duel);
    void Publish(Duel& duel);
    void Finish(uint64 id, int winner, std::string const& reason);
    void CancelPlayer(ObjectGuid player);
    void BotChoose(Duel& duel, uint8 side);
    void Switch(Duel& duel, uint8 side, uint8 index);
    void Send(Player* player, std::string const& payload);
    void SendRaw(Player* player, std::string const& payload) const;
    uint64 PlaybackAt(ObjectGuid player) const;
    void SetPlayback(ObjectGuid player, uint64 until);
    void ClearPlayback(ObjectGuid player);
    void FlushPlayback();
    void Deliver(ObjectGuid player, std::string const& payload, uint64 at);
    void Broadcast(Duel const& duel, std::string const& payload);
    void ShowScene(Player* owner, BattlemonBattler const& a, BattlemonBattler const& b);
    void ClearScene(ObjectGuid owner);
    void EndScene(ObjectGuid owner);
    bool SceneValid(ObjectGuid owner) const;
    void Animate(ObjectGuid owner, uint8 side, std::string const& move);
    bool AnimateNative(ObjectGuid owner, uint8 side, std::string const& move);
    bool Eligible(Player* player) const;
    bool Near(Player* a, Player* b) const;
    bool PetMode(ObjectGuid guid) const;
    int Bench(Duel const& duel, uint8 side) const;
    static uint64 Now();

    bool _enabled = true;
    bool _allowClassic = true;
    bool _defaultPet = true;
    bool _duelsEnabled = true;
    bool _botsEnabled = true;
    bool _generateBots = true;
    bool _worldActors = true;
    bool _nativeSpellVisuals = true;
    uint8 _teamSize = 6;
    uint32 _turnSeconds = 45;
    uint32 _inviteSeconds = 30;
    uint32 _botThinkMs = 1500;
    uint32 _actorEntry = 60000;
    float _distance = 25.0f;
    uint64 _nextId = 1;
    TaskScheduler _scheduler;
    mutable std::mutex _queueMutex;
    struct Delivery
    {
        ObjectGuid player;
        std::string payload;
        uint64 at;
    };
    std::deque<Delivery> _deliveries;
    std::unordered_set<ObjectGuid> _timedPlayers;
    std::unordered_map<ObjectGuid, uint64> _playbackUntil;
    std::deque<Input> _inputs;
    std::unordered_set<ObjectGuid> _reserved;
    std::unordered_map<ObjectGuid, bool> _preferences;
    std::unordered_map<ObjectGuid, uint64> _lastCommand;
    std::unordered_map<ObjectGuid, Invite> _invites;
    std::unordered_map<ObjectGuid, uint64> _byPlayer;
    std::unordered_map<uint64, Duel> _duels;
    std::unordered_map<ObjectGuid, Scene> _scenes;
};

#endif
