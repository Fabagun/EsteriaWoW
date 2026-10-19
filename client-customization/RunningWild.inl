// Build12340 Unit_C fields and SetAnimation arguments verified in the installed executable.
bool TarasekSelfMounted(void* unit)
{
    if (!unit || Field<unsigned>(unit, 0x14) != 4)
        return false;
    auto* fields = Field<unsigned char*>(unit, 0xD0);
    return fields && fields[0x44] == 66 && fields[0x46] == 0
        && Field<unsigned>(fields, 0xF4) == 60070 && Field<unsigned>(fields, 0xFC) == 0
        && (Field<unsigned>(fields, 0xD4) & 0x08000000) != 0;
}

extern "C" __declspec(dllexport) bool __cdecl EsteriaSelfMounted(void* unit)
{
    return TarasekSelfMounted(unit);
}

extern "C" __declspec(dllexport) void __cdecl EsteriaSelfAnimation(void* unit, unsigned* arguments)
{
    if (!arguments || !TarasekSelfMounted(unit)
        || reinterpret_cast<void*>(arguments[0]) != Field<void*>(unit, 0xB4))
        return;

    // Keep the player model, equipment, materials, and authored tracks. Only route animation requests.
    unsigned animation = arguments[2];
    switch (animation)
    {
        case 0: case 25: case 26: case 27: case 28: case 29: case 48: case 91:
            animation = 618; // MountSelfIdle
            break;
        case 4: animation = 620; break; // MountSelfWalk
        case 5: case 92: case 93: animation = 622; break; // MountSelfRun (no separate banked turns)
        case 143: animation = 624; break; // MountSelfSprint
        case 11: animation = 630; break; // MountSelfShuffleLeft
        case 12: animation = 632; break; // MountSelfShuffleRight
        case 13: animation = 634; break; // MountSelfWalkBackwards
        case 94: animation = 636; break; // MountSelfSpecial
        case 37: animation = 640; break; // MountSelfJumpStart
        case 38: case 40: animation = 638; break; // Jump loop also covers the missing authored fall.
        case 39: animation = 642; break; // MountSelfJumpEnd
        case 187: animation = 644; break; // MountSelfJumpLandRun
        default: return;
    }
    arguments[2] = animation;
    arguments[3] = 0; // Every selected authored MountSelf clip has variation zero.
}

extern "C" __declspec(dllexport) void __cdecl EsteriaSelfMotion(void* unit, unsigned* motion)
{
    if (!motion || !TarasekSelfMounted(unit))
        return;
    unsigned arguments[] = {reinterpret_cast<unsigned>(Field<void*>(unit, 0xB4)), 0xffffffff,
        motion[0], motion[1], 0};
    EsteriaSelfAnimation(unit, arguments);
    // Route before Unit_C compares desired/current IDs, so a loop is not restarted every update.
    motion[0] = arguments[2];
    motion[1] = arguments[3];
}

std::unordered_map<void*, bool> tarasekMountState;

void RefreshTarasekSelfMount(void* unit, void* character)
{
    bool active = TarasekSelfMounted(unit);
    auto found = tarasekMountState.find(character);
    if (found == tarasekMountState.end() && !active)
        return;
    if (found != tarasekMountState.end() && found->second == active)
        return;
    tarasekMountState[character] = active;
    Native<void(__thiscall*)(void*, unsigned, int)>(0x0073AC30)(unit, 0, -1);
}
