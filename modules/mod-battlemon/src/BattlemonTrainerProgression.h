#pragma once

#include "Player.h"
#include <algorithm>
#include <array>
#include <atomic>

namespace BattlemonTrainerProgression
{
    inline std::atomic<bool> Enabled{false};
    constexpr uint16 Skill = 1900;
    constexpr uint32 JournalSpell = 931600;
    constexpr std::array<uint16, 6> RankCaps = {75, 150, 225, 300, 375, 450};
    constexpr std::array<char const*, 6> RankNames = {
        "Apprentice", "Journeyman", "Expert", "Artisan", "Master", "Grand Master"};

    inline uint32 LevelCap(Player const* player)
    {
        if (!Enabled || !player || !player->HasSkill(Skill))
            return 100;
        uint16 const value = player->GetPureSkillValue(Skill);
        if (value >= 450)
            return 100;
        if (value >= 375)
            return 80;
        if (value >= 300)
            return 70;
        if (value >= 225)
            return 60;
        if (value >= 150)
            return 40;
        if (value >= 75)
            return 30;
        return 20;
    }

    inline uint32 CombatLevel(Player const* player)
    {
        return std::min<uint32>(player->GetLevel(), LevelCap(player));
    }

    inline void AwardPractice(Player* player)
    {
        if (Enabled && player && player->HasSkill(Skill))
            player->UpdateSkill(Skill, 1);
    }
}
