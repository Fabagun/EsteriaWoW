#include "Creature.h"
#include "CreatureAI.h"
#include "DataMap.h"
#include "Group.h"
#include "GridNotifiers.h"
#include "GridNotifiersImpl.h"
#include "CellImpl.h"
#include "ObjectAccessor.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "ScriptedCreature.h"
#include "SlimeCentaurRacials.h"
#include "Spell.h"
#include "SpellAuraEffects.h"
#include "SpellAuras.h"
#include "SpellScript.h"
#include "SpellInfo.h"
#include "TemporarySummon.h"

using namespace SlimeCentaurRacials;

namespace
{
    bool IsSlime(Unit const* unit)
    {
        Player const* player = unit->ToPlayer();
        return player && player->getRace(true) == RACE_SLIME_GIANT_HORDE;
    }

    bool IsCentaur(Unit const* unit)
    {
        Player const* player = unit->ToPlayer();
        return player && player->getRace(true) == RACE_CENTAUR_ALLIANCE;
    }

    bool Moving(Player const* player)
    {
        return player->IsAlive() && !player->IsInCombat() && player->isMoving()
            && !player->IsInFlight() && !player->GetVehicle();
    }

    bool Running(Player const* player)
    {
        return Moving(player) && !player->IsWalking() && !player->IsFlying() && !player->IsInWater();
    }

    struct RunState final : DataMap::Base
    {
        uint32 elapsed = 0;
        uint32 pulse = 0;
    };

    bool Ready(Player* player)
    {
        RunState const* state = player->CustomData.Get<RunState>("CentaurPlainsrunner");
        return IsCentaur(player) && player->HasAura(WarbandPlainsrunner) && Running(player)
            && state && state->elapsed >= 8000;
    }

    template <typename Action>
    void NearbyParty(Player* player, Action action)
    {
        action(player);
        if (Group* group = player->GetGroup())
            for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
                if (Player* member = ref->GetSource())
                    if (member != player && player->IsInSameGroupWith(member) && member->IsAlive()
                        && player->IsWithinDistInMap(member, 30.0f) && player->IsWithinLOSInMap(member))
                        action(member);
    }
}

class slime_centaur_players : public PlayerScript
{
public:
    slime_centaur_players() : PlayerScript("slime_centaur_players",
        {PLAYERHOOK_ON_LOGIN, PLAYERHOOK_ON_UPDATE}) { }

    void OnPlayerLogin(Player* player) override
    {
        if (IsSlime(player))
            for (uint32 spell : {Bouncy, ToxicComposition, Reconstitution, SlimeTrail})
                player->learnSpell(spell);
        else if (IsCentaur(player))
            for (uint32 spell : {PolearmSpecialty, HighHorsepower, WarbandPlainsrunner, Warcry})
                player->learnSpell(spell);
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        if (Aura* aura = player->GetAura(PlainsrunnerSpeed))
        {
            Player* source = ObjectAccessor::FindPlayer(aura->GetCasterGUID());
            if (!Moving(player) || !source || !source->IsWithinDistInMap(player, 30.0f)
                || !source->IsInSameGroupWith(player) || !Ready(source))
                player->RemoveAurasDueToSpell(PlainsrunnerSpeed);
        }

        if (!IsCentaur(player))
            return;

        RunState* state = player->CustomData.GetDefault<RunState>("CentaurPlainsrunner");
        if (!Running(player))
        {
            state->elapsed = 0;
            state->pulse = 0;
            return;
        }

        state->elapsed = RunningTime(state->elapsed, diff, true);
        state->pulse += diff;
        if (state->elapsed < 8000 || state->pulse < 250 || !player->HasAura(WarbandPlainsrunner))
            return;

        state->pulse = 0;
        NearbyParty(player, [player](Player* member)
        {
            if (!Moving(member))
                return;
            int32 const amount = member->IsOutdoors() ? 10 : 5;
            if (AuraEffect const* current = member->GetAuraEffect(PlainsrunnerSpeed, EFFECT_0))
                if (current->GetAmount() != amount)
                    member->RemoveAurasDueToSpell(PlainsrunnerSpeed);
            player->CastCustomSpell(PlainsrunnerSpeed, SPELLVALUE_BASE_POINT0, amount, member, true);
        });
    }
};

class slime_toxic_damage : public UnitScript
{
public:
    slime_toxic_damage() : UnitScript("slime_toxic_damage", true,
        {UNITHOOK_MODIFY_SPELL_DAMAGE_TAKEN, UNITHOOK_MODIFY_PERIODIC_DAMAGE_AURAS_TICK}) { }

    void ModifySpellDamageTaken(Unit* target, Unit* /*attacker*/, int32& damage,
        SpellInfo const* info) override
    {
        if (IsSlime(target) && target->HasAura(ToxicComposition) && info->Dispel == DISPEL_POISON)
            damage = CalculatePct(damage, 80);
    }

    void ModifyPeriodicDamageAurasTick(Unit* target, Unit* /*attacker*/, uint32& damage,
        SpellInfo const* info) override
    {
        if (IsSlime(target) && target->HasAura(ToxicComposition) && info->Dispel == DISPEL_POISON)
            damage = CalculatePct(damage, 80);
    }
};

class spell_slime_reconstitution : public AuraScript
{
    PrepareAuraScript(spell_slime_reconstitution);

    void Tick(AuraEffect const* /*effect*/)
    {
        Unit* target = GetTarget();
        if (IsSlime(target) && target->IsAlive() && !target->IsInCombat())
            target->ModifyHealth(std::max<uint32>(1, target->CountPctFromMaxHealth(1)));
    }

    void Register() override
    {
        OnEffectPeriodic += AuraEffectPeriodicFn(spell_slime_reconstitution::Tick,
            EFFECT_0, SPELL_AURA_PERIODIC_DUMMY);
    }
};

class spell_slime_trail : public AuraScript
{
    PrepareAuraScript(spell_slime_trail);

    void Spawn()
    {
        Unit* target = GetTarget();
        if (IsSlime(target) && target->IsAlive())
            if (TempSummon* slime = target->SummonCreature(SlimeCreature, target->GetPosition(),
                TEMPSUMMON_TIMED_DESPAWN, 6000))
            {
                slime->SetOwnerGUID(target->GetGUID());
                slime->SetFaction(target->GetFaction());
                slime->SetPvP(target->IsPvP());
                slime->SetLevel(target->GetLevel());
                slime->SetMaxHealth(std::max<uint32>(1, target->CountPctFromMaxHealth(5)));
                slime->SetHealth(slime->GetMaxHealth());
            }
    }

    void Apply(AuraEffect const* /*effect*/, AuraEffectHandleModes /*mode*/) { Spawn(); }

    void Tick(AuraEffect const* effect)
    {
        if (effect->GetTickNumber() < 6)
            Spawn();
    }

    void Register() override
    {
        AfterEffectApply += AuraEffectApplyFn(spell_slime_trail::Apply, EFFECT_0,
            SPELL_AURA_PERIODIC_DUMMY, AURA_EFFECT_HANDLE_REAL);
        OnEffectPeriodic += AuraEffectPeriodicFn(spell_slime_trail::Tick,
            EFFECT_0, SPELL_AURA_PERIODIC_DUMMY);
    }
};

struct npc_racial_sticky_slime : public ScriptedAI
{
    enum Events : uint32 { EVENT_SLIME_PULSE = 1 };
    EventMap events;

    explicit npc_racial_sticky_slime(Creature* creature) : ScriptedAI(creature)
    {
        me->SetCombatMovement(false);
        events.ScheduleEvent(EVENT_SLIME_PULSE, Milliseconds(1));
    }

    void UpdateAI(uint32 diff) override
    {
        Unit* owner = me->ToTempSummon() ? me->ToTempSummon()->GetSummonerUnit() : nullptr;
        if (!owner || !owner->IsAlive())
        {
            me->DespawnOrUnsummon();
            return;
        }
        events.Update(diff);
        if (events.ExecuteEvent() == EVENT_SLIME_PULSE)
        {
            std::list<Unit*> targets;
            Acore::AnyUnfriendlyUnitInObjectRangeCheck check(me, me, 3.0f);
            Acore::UnitListSearcher<Acore::AnyUnfriendlyUnitInObjectRangeCheck> searcher(me, targets, check);
            Cell::VisitObjects(me, searcher, 3.0f);
            for (Unit* target : targets)
                if (owner->IsValidAttackTarget(target))
                {
                    me->CastSpell(target, StickySlime, true);
                    if (!me->GetVictim())
                        AttackStart(target);
                }
            events.ScheduleEvent(EVENT_SLIME_PULSE, Milliseconds(250));
        }
        if (UpdateVictim())
            DoMeleeAttackIfReady();
    }
};

class spell_sticky_slime : public AuraScript
{
    PrepareAuraScript(spell_sticky_slime);

    void Tick(AuraEffect const* /*effect*/)
    {
        Unit* slime = GetCaster();
        if (!slime || !slime->IsAlive() || !slime->IsWithinDistInMap(GetTarget(), 3.0f))
            Remove();
    }

    void Register() override
    {
        OnEffectPeriodic += AuraEffectPeriodicFn(spell_sticky_slime::Tick,
            EFFECT_1, SPELL_AURA_PERIODIC_DUMMY);
    }
};

class spell_centaur_plainsrunner_speed : public AuraScript
{
    PrepareAuraScript(spell_centaur_plainsrunner_speed);

    void Update(AuraEffect const* /*effect*/, AuraEffectHandleModes /*mode*/)
    {
        for (UnitMoveType type : {MOVE_WALK, MOVE_RUN, MOVE_RUN_BACK, MOVE_SWIM, MOVE_SWIM_BACK,
            MOVE_FLIGHT, MOVE_FLIGHT_BACK})
            GetTarget()->UpdateSpeed(type, true);
    }

    void Register() override
    {
        AfterEffectApply += AuraEffectApplyFn(spell_centaur_plainsrunner_speed::Update, EFFECT_0,
            SPELL_AURA_DUMMY, AURA_EFFECT_HANDLE_CHANGE_AMOUNT_MASK);
        AfterEffectRemove += AuraEffectRemoveFn(spell_centaur_plainsrunner_speed::Update, EFFECT_0,
            SPELL_AURA_DUMMY, AURA_EFFECT_HANDLE_CHANGE_AMOUNT_MASK);
    }
};

class spell_centaur_warcry : public SpellScript
{
    PrepareSpellScript(spell_centaur_warcry);

    void Cry(SpellEffIndex /*index*/)
    {
        Player* player = GetCaster()->ToPlayer();
        if (!player || !IsCentaur(player))
            return;
        player->HandleEmoteCommand(EMOTE_ONESHOT_BATTLE_ROAR);
        NearbyParty(player, [player](Player* member)
        {
            int32 const amount = member == player ? 5 : 3;
            if (AuraEffect const* current = member->GetAuraEffect(WarcryDamage, EFFECT_0))
                if (current->GetAmount() > amount)
                    return;
            member->RemoveAurasDueToSpell(WarcryDamage);
            player->CastCustomSpell(WarcryDamage, SPELLVALUE_BASE_POINT0, amount, member, true);
        });
    }

    void Register() override
    {
        OnEffectHitTarget += SpellEffectFn(spell_centaur_warcry::Cry, EFFECT_0, SPELL_EFFECT_DUMMY);
    }
};

void AddSC_slime_centaur_racials()
{
    new slime_centaur_players();
    new slime_toxic_damage();
    RegisterSpellScript(spell_slime_reconstitution);
    RegisterSpellScript(spell_slime_trail);
    RegisterSpellScript(spell_sticky_slime);
    RegisterSpellScript(spell_centaur_warcry);
    RegisterSpellScript(spell_centaur_plainsrunner_speed);
    RegisterCreatureAI(npc_racial_sticky_slime);
}
