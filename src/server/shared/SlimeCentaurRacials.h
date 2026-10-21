#ifndef SLIME_CENTAUR_RACIALS_H
#define SLIME_CENTAUR_RACIALS_H

#include "Define.h"
#include <algorithm>

namespace SlimeCentaurRacials
{
    enum Spells : uint32
    {
        Bouncy = 111010,
        ToxicComposition = 111011,
        Reconstitution = 111012,
        SlimeTrail = 111013,
        StickySlime = 111014,
        PolearmSpecialty = 111020,
        HighHorsepower = 111021,
        WarbandPlainsrunner = 111022,
        PlainsrunnerSpeed = 111023,
        Warcry = 111024,
        WarcryDamage = 111025,
        TravelPassenger = 111026,
        FlightPassenger = 111027
    };

    constexpr uint32 SlimeCreature = 900720;
    constexpr uint32 PassengerVehicle = 900306;

    constexpr float BounceHeight(float drop)
    {
        return std::clamp(drop * 0.25f, 0.0f, 12.0f);
    }

    constexpr int32 GroundSpeed(uint16 riding) { return riding >= 150 ? 100 : 60; }
    constexpr int32 FlightSpeed(uint16 riding) { return riding >= 300 ? 280 : 150; }

    constexpr uint32 RunningTime(uint32 elapsed, uint32 diff, bool running)
    {
        return running ? std::min(elapsed + std::min(diff, 8000u), 8000u) : 0;
    }

    static_assert(BounceHeight(20.0f) == 5.0f);
    static_assert(BounceHeight(200.0f) == 12.0f);
    static_assert(BounceHeight(-10.0f) == 0.0f);
    static_assert(GroundSpeed(75) == 60 && GroundSpeed(150) == 100);
    static_assert(FlightSpeed(225) == 150 && FlightSpeed(300) == 280);
    static_assert(RunningTime(7999, 1, true) == 8000);
    static_assert(RunningTime(8000, 50, false) == 0);
    static_assert(RunningTime(8000, 0xFFFFFFFFu, true) == 8000);
}

#endif
