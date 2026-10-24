#include "BattlemonBattles.h"
#include "BattlemonNpcTrainers.h"
#include "BattlemonCenter.h"
#include "BattlemonMgr.h"
#include "Creature.h"
#include "CreatureScript.h"
#include "Player.h"
#include "ScriptedGossip.h"

class npc_battlemon_center : public CreatureScript
{
public:
    npc_battlemon_center() : CreatureScript("npc_battlemon_center") { }

    bool OnGossipHello(Player* player, Creature* creature) override
    {
        if (!sBattlemonMgr->ShouldHandle(player))
            return false;
        ClearGossipMenuFor(player);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Heal my Pokemon party.", GOSSIP_SENDER_MAIN,
            BattlemonCenter::Heal);
        AddGossipItemFor(player, GOSSIP_ICON_VENDOR, "Browse the Battlemon shop.", GOSSIP_SENDER_MAIN,
            BattlemonCenter::Shop);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Manage my Pokemon and moves.", GOSSIP_SENDER_MAIN,
            BattlemonCenter::Party);
        SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
        return true;
    }

    bool OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action) override
    {
        ClearGossipMenuFor(player);
        CloseGossipMenuFor(player);
        if (sender != GOSSIP_SENDER_MAIN || !creature->IsWithinDistInMap(player, INTERACTION_DISTANCE)
            || action < BattlemonCenter::Heal || action > BattlemonCenter::Party)
            return false;
        sBattlemonMgr->UseCenterService(player, action);
        return true;
    }
};

class npc_battlemon_trainer : public CreatureScript
{
public:
    npc_battlemon_trainer() : CreatureScript("npc_battlemon_trainer") { }

    bool OnGossipHello(Player* player, Creature* creature) override
    {
        if (!sBattlemonMgr->ShouldHandle(player) || !BattlemonNpcTrainers::Find(creature->GetEntry()))
            return false;
        ClearGossipMenuFor(player);
        AddGossipItemFor(player, GOSSIP_ICON_BATTLE, "Challenge this Pokemon Trainer.", GOSSIP_SENDER_MAIN, 1);
        AddGossipItemFor(player, GOSSIP_ICON_VENDOR, "Browse Pokemon supplies.", GOSSIP_SENDER_MAIN, 2);
        SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
        return true;
    }

    bool OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action) override
    {
        ClearGossipMenuFor(player);
        CloseGossipMenuFor(player);
        if (sender != GOSSIP_SENDER_MAIN || !creature->IsWithinDistInMap(player, INTERACTION_DISTANCE)
            || !BattlemonNpcTrainers::Find(creature->GetEntry()))
            return false;
        if (action == 1)
            BattlemonBattles::Instance().ChallengeTrainer(player, creature);
        else if (action == 2)
            sBattlemonMgr->UseCenterService(player, BattlemonCenter::Shop);
        return true;
    }
};

void AddSC_battlemon_center()
{
    new npc_battlemon_center();
    new npc_battlemon_trainer();
}
