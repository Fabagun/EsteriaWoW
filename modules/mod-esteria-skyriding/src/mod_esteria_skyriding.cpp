/*
 * Esteria Skyriding: server half (docs in the client repo, wowdecomp/docs/SKYRIDING_*.md).
 *
 * The client flies with the shared simulator (SkyridingPhysics.h) and sends its position in native movement packets.
 * This module decides who may skyride (capable client, dynamic style, eligible mount, flyable area), owns ability
 * charges and cooldowns, checks every airborne movement packet against the simulator's energy envelope, and tells
 * observers the rider's live speed so any client extrapolates the rider correctly.
 */

#include "BattlefieldMgr.h"
#include "Config.h"
#include "DBCStores.h"
#include "DatabaseEnv.h"
#include "Log.h"
#include "Map.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "SkyridingEnvelope.h"
#include "SkyridingWire.h"
#include "SpellAuraEffects.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "Timer.h"
#include "WorldPacket.h"
#include "WorldSession.h"
#include <cmath>
#include <unordered_map>

namespace
{
    using namespace Skyriding;
    namespace Wire = SkyridingWire;

    // Profile field names in wire order (Skyriding::Profile); each is "Skyriding.Physics.<name>" in the config.
    char const* const PhysicsNames[Profile::FieldCount] = {
        "Gravity", "DragLinear", "DragQuadratic", "OverspeedDrag", "MinGlideSpeed", "StallSpeed", "LiftEfficiency",
        "MaxAirSpeed", "MaxBoostSpeed", "TurnResponse", "TurnSpeedRef", "SurgeAccel", "SurgeSeconds", "WhirlAccel",
        "WhirlSeconds", "AscentImpulse", "LiftOffUp", "LiftOffForward", "FlapImpulse", "HaltFactor", "HaltSeconds",
        "HaltGravityScale", "ThrillSpeed"
    };

    struct Settings
    {
        bool enable = true;
        bool allFlyingMounts = true;
        bool validate = true;
        bool flyEverywhere = true;
        EnvelopeConfig envelope;
        Profile physics;
        ResourceRules rules;
    };

    Settings settings;
    std::unordered_map<uint32, bool> mountTable; // esteria_skyriding_mounts: spell_id -> enabled

    char const* const StateKey = "EsteriaSkyridingState";
    char const* const ActiveKey = "EsteriaSkyriding"; // present only while active; mod-anticheat skips such players
    constexpr uint32 UpdateMs = 250;
    constexpr uint32 AbilitiesPerSecond = 20;

    struct Rider : DataMap::Base
    {
        bool capable = false;
        Wire::Style style = Wire::Style::Dynamic;
        bool active = false;
        bool grantedFly = false;
        bool resourcesReady = false;
        Resources resources;
        uint32 sinceUpdate = 0;
        bool wasAirborne = false;
        uint8 lastRefusal = 255;

        Envelope envelope;
        Position lastGood;
        bool correctionPending = false;
        uint32 violations = 0;

        float sentSpeed = -1.0f;
        uint32 sentSpeedAt = 0;
        uint32 rateWindow = 0;
        uint32 rateCount = 0;
    };

    Rider* GetRider(Player* player) { return player->CustomData.Get<Rider>(StateKey); }

    void Send(Player* player, uint8 const* bytes, size_t size)
    {
        if (!size)
            return;
        WorldPacket data(SMSG_ESTERIA_SKYRIDE, size);
        data.append(bytes, size);
        player->SendDirectMessage(&data);
    }

    bool Airborne(Player* player) { return player->IsFlying(); }
    bool Thrill(Player* player, Rider const& rider) { return Airborne(player) && rider.envelope.speed >= settings.physics.thrillSpeed; }

    Wire::ResourceState ResourceStateOf(Player* player, Rider const& rider)
    {
        Wire::ResourceState state;
        state.profile = settings.rules.profile;
        state.charges = rider.resources.charges;
        state.maxCharges = settings.rules.maxCharges;
        state.nextChargeMs = rider.resources.NextChargeMs(settings.rules, Airborne(player), Thrill(player, rider));
        return state;
    }

    void SendResources(Player* player, Rider const& rider)
    {
        uint8 buffer[Wire::MaxServerSize];
        Send(player, buffer, Wire::Write(ResourceStateOf(player, rider), buffer, sizeof(buffer)));
    }

    // Native SMSG_SPLINE_SET_FLIGHT_SPEED to everyone who sees the rider (not the rider): their clients extrapolate
    // along the rider's facing at this speed between heartbeats.
    void SendObserverSpeed(Player* player, float speed)
    {
        WorldPacket data(SMSG_SPLINE_SET_FLIGHT_SPEED, 8 + 4);
        data << player->GetPackGUID();
        data << speed;
        player->SendMessageToSet(&data, false);
    }

    uint32 MountSpell(Player* player)
    {
        Unit::AuraEffectList const& mounts = player->GetAuraEffectsByType(SPELL_AURA_MOUNTED);
        return mounts.empty() ? 0 : mounts.front()->GetId();
    }

    // The flight speed often sits in a second aura the mount spell triggers (scaling mounts), so look at the player.
    bool EligibleMount(Player* player, uint32 spell)
    {
        auto row = mountTable.find(spell);
        if (row != mountTable.end())
            return row->second;
        return settings.allFlyingMounts && player->HasAuraType(SPELL_AURA_MOD_INCREASE_MOUNTED_FLIGHT_SPEED);
    }

    // The same rules a flying mount obeys (SpellInfo::CheckLocation, Spell::CheckCast), never in instances.
    bool FlyableHere(Player* player, uint32 spell)
    {
        if (player->GetMap()->Instanceable())
            return false;
        AreaTableEntry const* area = sAreaTableStore.LookupEntry(player->GetAreaId());
        if (!area)
            area = sAreaTableStore.LookupEntry(player->GetZoneId());
        if (!area || !area->IsFlyable() || (area->flags & AREA_FLAG_NO_FLY_ZONE))
            return false;
        if (Battlefield* field = sBattlefieldMgr->GetBattlefieldToZoneId(player->GetZoneId()))
            if (!field->CanFlyIn())
                return false;
        SpellInfo const* info = sSpellMgr->GetSpellInfo(spell);
        return info && player->canFlyInZone(player->GetMapId(), player->GetZoneId(), info);
    }

    // Why the rider may not skyride right now, or 0 when it may.
    uint8 Refusal(Player* player, Rider const& rider)
    {
        if (!settings.enable)
            return uint8(Wire::EndReason::Disabled);
        if (rider.style != Wire::Style::Dynamic)
            return uint8(Wire::EndReason::Style);
        if (!player->IsAlive())
            return uint8(Wire::EndReason::Death);
        if (player->GetVehicle() || player->IsInFlight() || player->GetTransport())
            return uint8(Wire::EndReason::Vehicle);
        uint32 spell = MountSpell(player);
        if (!spell || !EligibleMount(player, spell))
            return uint8(Wire::EndReason::Dismount);
        if (!FlyableHere(player, spell))
            return uint8(Wire::EndReason::Area);
        return 0;
    }

    void ResetEnvelope(Rider& rider)
    {
        rider.envelope.Reset();
        rider.correctionPending = false;
    }

    void Begin(Player* player, Rider& rider)
    {
        rider.active = true;
        player->CustomData.Set(ActiveKey, new DataMap::Base());
        if (!player->HasAuraType(SPELL_AURA_FLY))
        {
            player->SetCanFly(true);
            rider.grantedFly = true;
        }
        if (!rider.resourcesReady)
        {
            rider.resources.Reset(settings.rules);
            rider.resourcesReady = true;
        }
        ResetEnvelope(rider);
        rider.envelope.credit = 0.0f;
        rider.wasAirborne = Airborne(player);

        Wire::Begin begin;
        begin.resources = ResourceStateOf(player, rider);
        begin.physics = settings.physics;
        uint8 buffer[Wire::MaxServerSize];
        Send(player, buffer, Wire::Write(begin, buffer, sizeof(buffer)));
    }

    void End(Player* player, Rider& rider, uint8 reason)
    {
        if (!rider.active)
            return;
        rider.active = false;
        player->CustomData.Erase(ActiveKey);
        if (rider.grantedFly && !player->HasAuraType(SPELL_AURA_FLY))
            player->SetCanFly(false);
        rider.grantedFly = false;
        ResetEnvelope(rider);
        SendObserverSpeed(player, player->GetSpeed(MOVE_FLIGHT));
        rider.sentSpeed = -1.0f;

        uint8 buffer[Wire::MaxServerSize];
        Send(player, buffer, Wire::WriteEnd(Wire::EndReason(reason), buffer, sizeof(buffer)));
    }

    void Refresh(Player* player, Rider& rider)
    {
        uint8 refusal = Refusal(player, rider);
        if (refusal != rider.lastRefusal)
        {
            rider.lastRefusal = refusal;
            LOG_INFO("module", "Skyriding: {} {} (mount spell {}, area {})", player->GetName(),
                refusal ? "may not skyride, reason" : "may skyride", refusal, MountSpell(player), player->GetAreaId());
        }
        if (!refusal && !rider.active)
            Begin(player, rider);
        else if (refusal && rider.active)
            End(player, rider, refusal);
    }

    char const* const EnvelopeChecks[] = { "ok", "speed", "energy", "height", "hover" };

    // One airborne (flying or falling) movement packet of an active rider.
    void Validate(Player* player, Rider& rider, MovementInfo const& info)
    {
        Vec3 pos(info.pos.GetPositionX(), info.pos.GetPositionY(), info.pos.GetPositionZ());
        // First sample: allow ground speed plus a jump.
        EnvelopeResult result = rider.envelope.Check(pos, info.time, getMSTime(), player->GetSpeed(MOVE_RUN) + 8.0f,
            settings.physics, settings.envelope);
        if (result != EnvelopeResult::Ok)
        {
            ++rider.violations;
            LOG_INFO("module", "Skyriding: {} failed the {} check (speed {:.1f}, z {:.1f}), correction #{}", player->GetName(),
                EnvelopeChecks[uint8(result)], rider.envelope.speed, pos.z, rider.violations);
            rider.envelope.Reset();
            rider.correctionPending = true;
            return;
        }
        rider.lastGood = info.pos;

        uint32 now = getMSTime();
        float speed = rider.envelope.speed;
        if (std::fabs(speed - rider.sentSpeed) > 1.0f || getMSTimeDiff(rider.sentSpeedAt, now) > 1000)
        {
            SendObserverSpeed(player, std::max(speed, 1.0f));
            rider.sentSpeed = speed;
            rider.sentSpeedAt = now;
        }
    }

    void HandleAbility(Player* player, Rider& rider, Wire::Ability const& ability)
    {
        uint32 now = getMSTime();
        if (getMSTimeDiff(rider.rateWindow, now) >= 1000)
        {
            rider.rateWindow = now;
            rider.rateCount = 0;
        }
        if (++rider.rateCount > AbilitiesPerSecond)
            return;

        Wire::AbilityReply reply;
        reply.command = ability.command;
        reply.sequence = ability.sequence;
        if (!rider.active)
            reply.result = AbilityResult::Disabled;
        else
        {
            // Lift Off only needs "not flying yet". The others accept a falling rider too: a Flap can arrive in the
            // same server tick as the CMSG_MOVE_SET_FLY that started the flight, which the map thread handles later.
            bool airborne = ability.command == Command::LiftOff ? Airborne(player) : (Airborne(player) || player->IsFalling());
            reply.result = rider.resources.Use(ability.command, airborne, settings.rules);
        }

        if (reply.result == AbilityResult::Ok)
            rider.envelope.Grant(ability.command, settings.physics, settings.envelope, now);
        reply.cooldownMs = rider.resources.cooldownLeftMs[uint8(ability.command)];
        reply.resources = ResourceStateOf(player, rider);
        uint8 buffer[Wire::MaxServerSize];
        Send(player, buffer, Wire::Write(reply, buffer, sizeof(buffer)));
    }

    void LoadSettings()
    {
        settings = Settings();
        settings.enable = sConfigMgr->GetOption<bool>("Skyriding.Enable", true);
        settings.allFlyingMounts = sConfigMgr->GetOption<bool>("Skyriding.AllFlyingMounts", true);
        settings.validate = sConfigMgr->GetOption<bool>("Skyriding.Validate", true);
        settings.flyEverywhere = sConfigMgr->GetOption<bool>("Skyriding.FlyEverywhere", true);
        EnvelopeConfig& envelope = settings.envelope;
        envelope.driftPerSecond = sConfigMgr->GetOption<float>("Skyriding.Validate.DriftPerSecond", envelope.driftPerSecond);
        envelope.noise = sConfigMgr->GetOption<float>("Skyriding.Validate.Noise", envelope.noise);
        envelope.hoverMs = sConfigMgr->GetOption<uint32>("Skyriding.Validate.HoverMs", envelope.hoverMs);

        Profile defaults;
        for (uint32 i = 0; i < Profile::FieldCount; ++i)
            settings.physics.Fields()[i] = sConfigMgr->GetOption<float>(std::string("Skyriding.Physics.") + PhysicsNames[i],
                defaults.Fields()[i], false);
        if (!settings.physics.Valid())
        {
            LOG_ERROR("module", "Skyriding: Skyriding.Physics.* values are out of range, using the defaults");
            settings.physics = defaults;
        }

        ResourceRules& rules = settings.rules;
        rules.profile = sConfigMgr->GetOption<uint32>("Skyriding.ResourceProfile", 0) == 1 ? ResourceProfile::Vigor : ResourceProfile::Charges;
        rules.maxCharges = uint8(std::min<uint32>(20, sConfigMgr->GetOption<uint32>("Skyriding.MaxCharges", 6)));
        rules.regenMs = sConfigMgr->GetOption<uint32>("Skyriding.ChargeRegenMs", rules.regenMs);
        rules.thrillRegenMs = sConfigMgr->GetOption<uint32>("Skyriding.ThrillChargeRegenMs", rules.thrillRegenMs);
        rules.groundRegenMs = sConfigMgr->GetOption<uint32>("Skyriding.VigorGroundRegenMs", rules.groundRegenMs);
        rules.thrillVigorMs = sConfigMgr->GetOption<uint32>("Skyriding.VigorThrillRegenMs", rules.thrillVigorMs);
        rules.whirlCooldownMs = sConfigMgr->GetOption<uint32>("Skyriding.WhirlingSurgeCooldownMs", rules.whirlCooldownMs);
        rules.haltCooldownMs = sConfigMgr->GetOption<uint32>("Skyriding.AerialHaltCooldownMs", rules.haltCooldownMs);
        rules.flapCooldownMs = sConfigMgr->GetOption<uint32>("Skyriding.FlapCooldownMs", rules.flapCooldownMs);
    }

    // Every open-world area becomes flyable (AREA_FLAG_OUTLAND) and loses AREA_FLAG_NO_FLY_ZONE, for stock flight and
    // skyriding alike; instance maps keep their flags. The client extension patches its AreaTable the same way.
    void OpenAllAreasToFlight()
    {
        uint32 changed = 0;
        for (uint32 i = 0; i < sAreaTableStore.GetNumRows(); ++i)
        {
            AreaTableEntry const* area = sAreaTableStore.LookupEntry(i);
            MapEntry const* map = area ? sMapStore.LookupEntry(area->mapid) : nullptr;
            if (!map || map->Instanceable())
                continue;
            uint32 flags = (area->flags | AREA_FLAG_OUTLAND) & ~AREA_FLAG_NO_FLY_ZONE;
            if (flags != area->flags)
            {
                const_cast<AreaTableEntry*>(area)->flags = flags;
                ++changed;
            }
        }
        LOG_INFO("module", "Skyriding: flying opened in {} areas", changed);
    }

    void LoadMounts()
    {
        mountTable.clear();
        if (QueryResult result = WorldDatabase.Query("SELECT spell_id, enabled FROM esteria_skyriding_mounts"))
        {
            do
            {
                Field* fields = result->Fetch();
                mountTable[fields[0].Get<uint32>()] = fields[1].Get<uint8>() != 0;
            } while (result->NextRow());
        }
        LOG_INFO("module", "Skyriding: {} mount rows, all flying mounts {}", mountTable.size(), settings.allFlyingMounts ? "on" : "off");
    }
}

class SkyridingWorldScript : public WorldScript
{
public:
    SkyridingWorldScript() : WorldScript("SkyridingWorldScript", { WORLDHOOK_ON_AFTER_CONFIG_LOAD, WORLDHOOK_ON_STARTUP }) { }

    void OnAfterConfigLoad(bool reload) override
    {
        LoadSettings();
        if (reload)
            LoadMounts();
    }

    void OnStartup() override
    {
        LoadMounts();
        if (settings.flyEverywhere)
            OpenAllAreasToFlight();
    }
};

class SkyridingServerScript : public ServerScript
{
public:
    SkyridingServerScript() : ServerScript("SkyridingServerScript", { SERVERHOOK_CAN_PACKET_RECEIVE }) { }

    // ScriptMgr::CanPacketReceive dispatches the const overload.
    bool CanPacketReceive(WorldSession* session, WorldPacket const& packet) override
    {
        if (packet.GetOpcode() != CMSG_ESTERIA_SKYRIDE)
            return true;

        Player* player = session ? session->GetPlayer() : nullptr;
        size_t size = packet.size() - packet.rpos();
        if (!player || !player->IsInWorld() || !size || size > Wire::MaxClientSize)
        {
            LOG_INFO("module", "Skyriding: dropped a message ({} bytes, player {})", size,
                player ? (player->IsInWorld() ? "in world" : "not in world yet") : "none");
            return false;
        }

        Wire::Reader reader(packet.contents() + packet.rpos(), size);
        Wire::ClientMsg type;
        if (!Wire::ReadClientType(reader, type))
        {
            LOG_INFO("module", "Skyriding: {} sent an unknown message type", player->GetName());
            return false;
        }

        Rider* rider = player->CustomData.GetDefault<Rider>(StateKey);
        switch (type)
        {
            case Wire::ClientMsg::Hello:
            {
                Wire::Hello hello;
                if (!Wire::Read(reader, hello))
                {
                    LOG_INFO("module", "Skyriding: {} sent a malformed hello", player->GetName());
                    return false;
                }
                rider->capable = hello.version == Wire::Version;
                rider->style = hello.style;
                LOG_INFO("module", "Skyriding: hello from {} (version {}, style {})", player->GetName(), hello.version,
                    hello.style == Wire::Style::Steady ? "steady" : "dynamic");
                if (rider->capable)
                {
                    if (!rider->resourcesReady)
                    {
                        rider->resources.Reset(settings.rules);
                        rider->resourcesReady = true;
                    }
                    SendResources(player, *rider); // the client resends its hello until any reply arrives
                    Refresh(player, *rider);
                }
                break;
            }
            case Wire::ClientMsg::Ability:
            {
                Wire::Ability ability;
                if (rider->capable && Wire::Read(reader, ability))
                    HandleAbility(player, *rider, ability);
                break;
            }
            case Wire::ClientMsg::Style:
            {
                Wire::Style style;
                if (rider->capable && Wire::ReadStyle(reader, style))
                {
                    rider->style = style;
                    Refresh(player, *rider);
                }
                break;
            }
        }
        return false;
    }
};

class SkyridingPlayerScript : public PlayerScript
{
public:
    SkyridingPlayerScript() : PlayerScript("SkyridingPlayerScript", { PLAYERHOOK_ON_UPDATE, PLAYERHOOK_ON_BEFORE_TELEPORT, PLAYERHOOK_ON_MAP_CHANGED }) { }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        Rider* rider = GetRider(player);
        if (!rider || !rider->capable)
            return;

        if (rider->correctionPending && rider->active)
        {
            rider->correctionPending = false;
            Position const& good = rider->lastGood;
            player->NearTeleportTo(good.GetPositionX(), good.GetPositionY(), good.GetPositionZ(), player->GetOrientation());
            uint8 buffer[Wire::MaxServerSize];
            Send(player, buffer, Wire::WriteCorrection(buffer, sizeof(buffer)));
        }

        rider->sinceUpdate += diff;
        if (rider->sinceUpdate < UpdateMs)
            return;
        uint32 elapsed = rider->sinceUpdate;
        rider->sinceUpdate = 0;

        Refresh(player, *rider);
        if (!rider->active)
            return;
        bool airborne = Airborne(player);
        bool changed = rider->resources.Tick(elapsed, settings.rules, airborne, Thrill(player, *rider));
        if (changed || airborne != rider->wasAirborne)
            SendResources(player, *rider);
        rider->wasAirborne = airborne;
    }

    bool OnPlayerBeforeTeleport(Player* player, uint32 /*mapid*/, float /*x*/, float /*y*/, float /*z*/, float /*orientation*/,
        uint32 /*options*/, Unit* /*target*/) override
    {
        // The jump is not flight: start the envelope again from wherever the rider lands.
        if (Rider* rider = GetRider(player))
            rider->envelope.Reset();
        return true;
    }

    void OnPlayerMapChanged(Player* player) override
    {
        if (Rider* rider = GetRider(player))
        {
            End(player, *rider, uint8(Wire::EndReason::Teleport));
            Refresh(player, *rider);
        }
    }
};

class SkyridingMovementScript : public MovementHandlerScript
{
public:
    SkyridingMovementScript() : MovementHandlerScript("SkyridingMovementScript", { MOVEMENTHOOK_ON_PLAYER_MOVE }) { }

    void OnPlayerMove(Player* player, MovementInfo info, uint32 /*opcode*/) override
    {
        Rider* rider = GetRider(player);
        if (!rider || !rider->active || !settings.validate || rider->correctionPending)
            return;
        if (!info.HasMovementFlag(MovementFlags(MOVEMENTFLAG_FLYING | MOVEMENTFLAG_FALLING))
            || info.HasMovementFlag(MovementFlags(MOVEMENTFLAG_SWIMMING | MOVEMENTFLAG_ONTRANSPORT)))
        {
            rider->envelope.Reset();
            return;
        }
        Validate(player, *rider, info);
    }
};

void AddSC_esteria_skyriding()
{
    new SkyridingWorldScript();
    new SkyridingServerScript();
    new SkyridingPlayerScript();
    new SkyridingMovementScript();
}
