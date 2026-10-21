#include "Player.h"
#include "CentaurAppearance.h"
#include "Chat.h"
#include "CommandScript.h"
#include "ScriptMgr.h"
#include "Spell.h"
#include "SpellInfo.h"
#include "SpellAuraEffects.h"
#include "SpellScript.h"
#include "SlimeCentaurRacials.h"
#include "WorldSession.h"

#include <array>

namespace
{
    enum CentaurSpells : uint32
    {
        SPELL_CENTAUR_GALLOP = 111000,
        SPELL_CENTAUR_SWIFT_GALLOP = 111001,
        SPELL_CENTAUR_FLIGHT = 111002,
        SPELL_CENTAUR_SWIFT_FLIGHT = 111003
    };

    struct TravelAbility
    {
        uint32 spell;
        uint8 level;
        uint16 riding;
    };

    constexpr std::array<TravelAbility, 4> TravelAbilities =
    {{
        {SPELL_CENTAUR_GALLOP, 20, 75},
        {SPELL_CENTAUR_SWIFT_GALLOP, 40, 150},
        {SPELL_CENTAUR_FLIGHT, 60, 225},
        {SPELL_CENTAUR_SWIFT_FLIGHT, 70, 300}
    }};

    constexpr bool IsCentaur(uint8 race)
    {
        return race == RACE_CENTAUR_ALLIANCE;
    }

    static_assert(IsCentaur(RACE_CENTAUR_ALLIANCE) && !IsCentaur(RACE_CENTAUR_HORDE));
    static_assert(!IsCentaur(RACE_HUMAN) && !IsCentaur(RACE_SLIME_GIANT_HORDE));
    static_assert(GetPairedRaceForRace(RACE_CENTAUR_ALLIANCE) == RACE_NONE);
    static_assert(GetLegacyMaskRaceForRace(RACE_CENTAUR_HORDE) == RACE_ORC);
    static_assert(PLAYER_FLAGS_CENTAUR_HIDE_LEGS == CentaurAppearance::HideLegArmorFlag);

    void TeachTravel(Player* player)
    {
        if (!IsCentaur(player->getRace(true)))
            return;

        for (auto const& ability : TravelAbilities)
            if (player->GetLevel() >= ability.level && !player->HasSpell(ability.spell))
                player->learnSpell(ability.spell);
    }
}

class centaur_travel_player : public PlayerScript
{
public:
    centaur_travel_player() : PlayerScript("centaur_travel_player",
        {PLAYERHOOK_ON_LOGIN, PLAYERHOOK_ON_LEVEL_CHANGED}) { }

    void OnPlayerLogin(Player* player) override
    {
        TeachTravel(player);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        TeachTravel(player);
    }
};

class centaur_travel_spells : public AllSpellScript
{
public:
    centaur_travel_spells() : AllSpellScript("centaur_travel_spells", {ALLSPELLHOOK_ON_SPELL_CHECK_CAST}) { }

    void OnSpellCheckCast(Spell* spell, bool /*strict*/, SpellCastResult& result) override
    {
        Player* player = spell->GetCaster()->ToPlayer();
        if (!player || result != SPELL_CAST_OK)
            return;

        SpellInfo const* info = spell->GetSpellInfo();
        for (auto const& ability : TravelAbilities)
        {
            if (info->Id != ability.spell)
                continue;

            if (!IsCentaur(player->getRace(true)))
                result = SPELL_FAILED_SPELL_UNAVAILABLE;
            else if (player->GetLevel() < ability.level)
                result = SPELL_FAILED_LOWLEVEL;
            else if (player->GetBaseSkillValue(SKILL_RIDING) < ability.riding)
                result = SPELL_FAILED_MIN_SKILL;
            else if (ability.spell <= SPELL_CENTAUR_SWIFT_GALLOP &&
                (player->GetShapeshiftForm() != FORM_NONE || player->getTransForm()))
                result = SPELL_FAILED_NOT_SHAPESHIFT;

            return;
        }

        // Self-running racials retain normal mounted speed and cancellation rules without a rider model.
        if (IsCentaur(player->getRace(true)) && info->HasAura(SPELL_AURA_MOUNTED))
            result = SPELL_FAILED_SPELL_UNAVAILABLE;
    }
};

class spell_centaur_travel_passenger : public AuraScript
{
    PrepareAuraScript(spell_centaur_travel_passenger);

    void Apply(AuraEffect const* /*effect*/, AuraEffectHandleModes /*mode*/)
    {
        Player* player = GetTarget()->ToPlayer();
        if (player && IsCentaur(player->getRace(true)))
        {
            if (GetId() >= SPELL_CENTAUR_FLIGHT)
                player->CastCustomSpell(SlimeCentaurRacials::FlightPassenger, SPELLVALUE_BASE_POINT1,
                    SlimeCentaurRacials::FlightSpeed(player->GetBaseSkillValue(SKILL_RIDING)), player, true);
            else
                player->CastSpell(player, SlimeCentaurRacials::TravelPassenger, true);
        }
    }

    void Remove(AuraEffect const* /*effect*/, AuraEffectHandleModes /*mode*/)
    {
        GetTarget()->RemoveAurasDueToSpell(SlimeCentaurRacials::TravelPassenger);
        GetTarget()->RemoveAurasDueToSpell(SlimeCentaurRacials::FlightPassenger);
    }

    void Speed(AuraEffect const* effect, int32& amount, bool& /*canRecalculate*/)
    {
        if (effect->GetAuraType() == SPELL_AURA_MOD_INCREASE_MOUNTED_SPEED)
            if (Player* player = GetUnitOwner()->ToPlayer())
                amount = SlimeCentaurRacials::GroundSpeed(player->GetBaseSkillValue(SKILL_RIDING));
    }

    void Register() override
    {
        DoEffectCalcAmount += AuraEffectCalcAmountFn(spell_centaur_travel_passenger::Speed,
            EFFECT_ALL, SPELL_AURA_ANY);
        AfterEffectApply += AuraEffectApplyFn(spell_centaur_travel_passenger::Apply,
            EFFECT_0, SPELL_AURA_ANY, AURA_EFFECT_HANDLE_REAL);
        AfterEffectRemove += AuraEffectRemoveFn(spell_centaur_travel_passenger::Remove,
            EFFECT_0, SPELL_AURA_ANY, AURA_EFFECT_HANDLE_REAL);
    }
};

class centaur_appearance_commands : public CommandScript
{
public:
    centaur_appearance_commands() : CommandScript("centaur_appearance_commands") { }

    Acore::ChatCommands::ChatCommandTable GetCommands() const override
    {
        static Acore::ChatCommands::ChatCommandTable commands =
        {
            {"centaurlegs", HandleLegArmor, SEC_PLAYER, Acore::ChatCommands::Console::No}
        };
        return commands;
    }

    static bool HandleLegArmor(ChatHandler* handler, bool shown)
    {
        Player* player = handler->GetSession()->GetPlayer();
        if (!player || !IsCentaur(player->getRace(true)))
            return false;

        if (shown)
            player->RemovePlayerFlag(PLAYER_FLAGS_CENTAUR_HIDE_LEGS);
        else
            player->SetPlayerFlag(PLAYER_FLAGS_CENTAUR_HIDE_LEGS);

        player->SaveToDB(false, false);
        return true;
    }
};

void AddSC_centaur_travel()
{
    new centaur_travel_player();
    new centaur_travel_spells();
    new centaur_appearance_commands();
    RegisterSpellScript(spell_centaur_travel_passenger);
}
