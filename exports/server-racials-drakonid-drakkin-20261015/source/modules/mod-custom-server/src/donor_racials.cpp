/*
 * Keeps the donor race's racials off Drakkin and Drakonid.
 *
 * These races borrow Human (Alliance) or Orc (Horde) as their legacy race mask, so every
 * Human/Orc starting spell and racial skill line is offered to them. The exclusion tables
 * (`custom_race_start_spell_exclude`, `custom_race_start_skill_exclude`) cover the creation-time
 * lists, but a racial skill line also teaches its own spells through SkillLineAbility and can be
 * re-learned at login. Stripping the skill line and its spells after login is the one step that
 * holds whichever way they arrived.
 */

#include "Player.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"

#include <array>

namespace
{
    constexpr uint32 SkillHumanRacial = 754;
    constexpr uint32 SkillOrcRacial   = 125;

    // Every ability of the donor racial skill lines, from SkillLineAbility.dbc, plus the older
    // spell ids the starting-spell tables still list.
    constexpr std::array<uint32, 7> HumanRacialSpells =
    {
        20597, 20598, 20599, 20600, 20864, 58985, 59752
    };

    constexpr std::array<uint32, 10> OrcRacialSpells =
    {
        20572, 20573, 20574, 20575, 20576, 21563, 33697, 33702, 54562, 65222
    };

    template <std::size_t N>
    void StripRacials(Player* player, uint32 skill, std::array<uint32, N> const& spells)
    {
        if (player->HasSkill(skill))
            player->SetSkill(skill, 0, 0, 0);

        for (uint32 spellId : spells)
            if (player->HasSpell(spellId))
                player->removeSpell(spellId, SPEC_MASK_ALL, false);
    }
}

class custom_race_donor_racials : public PlayerScript
{
public:
    custom_race_donor_racials() : PlayerScript("custom_race_donor_racials", { PLAYERHOOK_ON_LOGIN }) { }

    void OnPlayerLogin(Player* player) override
    {
        switch (player->getRace(true))
        {
            case RACE_DRAKKIN_ALLIANCE:
            case RACE_DRAKONID_ALLIANCE:
                StripRacials(player, SkillHumanRacial, HumanRacialSpells);
                break;
            case RACE_DRAKKIN_HORDE:
            case RACE_DRAKONID_HORDE:
                StripRacials(player, SkillOrcRacial, OrcRacialSpells);
                break;
            default:
                break;
        }
    }
};

void AddSC_donor_racials()
{
    new custom_race_donor_racials();
}
