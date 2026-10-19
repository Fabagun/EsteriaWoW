#include <windows.h>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>

template<class T>
T& At(void* object, unsigned offset)
{
    return *reinterpret_cast<T*>(static_cast<unsigned char*>(object) + offset);
}

int main(int argc, char** argv)
{
    assert(argc == 2);
    HMODULE library = LoadLibraryA(argv[1]);
    assert(library);
    auto mounted = reinterpret_cast<bool(__cdecl*)(void*)>(GetProcAddress(library, "EsteriaSelfMounted"));
    auto animate = reinterpret_cast<void(__cdecl*)(void*, unsigned*)>(
        GetProcAddress(library, "EsteriaSelfAnimation"));
    auto motion = reinterpret_cast<void(__cdecl*)(void*, unsigned*)>(
        GetProcAddress(library, "EsteriaSelfMotion"));
    assert(mounted && animate && motion);
    std::array<unsigned char, 0x1100> unit{};
    std::array<unsigned char, 0x400> fields{};
    std::array<unsigned char, 8> model{};
    At<unsigned>(unit.data(), 0x14) = 4;
    At<void*>(unit.data(), 0xD0) = fields.data();
    At<void*>(unit.data(), 0xB4) = model.data();
    fields[0x44] = 66;
    At<unsigned>(fields.data(), 0xF4) = 60070;
    At<unsigned>(fields.data(), 0xD4) = 0x08000000;
    assert(mounted(unit.data()) && !mounted(nullptr));
    unsigned const routes[][2] = {{0,618}, {4,620}, {5,622}, {143,624}, {11,630}, {12,632},
        {13,634}, {94,636}, {37,640}, {38,638}, {39,642}, {40,638}, {187,644}, {25,618}, {91,618}};
    for (auto const& route : routes)
    {
        unsigned args[] = {reinterpret_cast<unsigned>(model.data()), 0xffffffff, route[0], 1, 120, 0, 0};
        animate(unit.data(), args);
        assert(args[2] == route[1] && args[3] == 0 && args[4] == 120);
        unsigned request[] = {route[0], 1, 120, 0x3f800000};
        motion(unit.data(), request);
        assert(request[0] == route[1] && request[1] == 0 && request[2] == 120);
        motion(unit.data(), request);
        assert(request[0] == route[1] && request[1] == 0 && request[2] == 120);
    }
    // Dismount, female, another race, morph, ordinary mounts, NPCs, and accessory models must pass through.
    for (unsigned scenario = 0; scenario < 7; ++scenario)
    {
        auto savedFields = fields;
        auto savedUnit = unit;
        unsigned args[] = {reinterpret_cast<unsigned>(model.data()), 0xffffffff, 5, 1, 120, 0, 0};
        switch (scenario)
        {
            case 0: At<unsigned>(fields.data(), 0xD4) = 0; break;
            case 1: fields[0x46] = 1; break;
            case 2: fields[0x44] = 12; break;
            case 3: At<unsigned>(fields.data(), 0xF4) = 29422; break;
            case 4: At<unsigned>(fields.data(), 0xFC) = 123; break;
            case 5: At<unsigned>(unit.data(), 0x14) = 3; break;
            case 6: args[0] = 0; break;
        }
        if (scenario != 6)
            assert(!mounted(unit.data()));
        animate(unit.data(), args);
        assert(args[2] == 5 && args[3] == 1 && args[4] == 120);
        fields = savedFields;
        unit = savedUnit;
    }
    unsigned untouched[] = {reinterpret_cast<unsigned>(model.data()), 0xffffffff, 1, 1, 0, 0, 0};
    animate(unit.data(), untouched);
    assert(untouched[2] == 1 && untouched[3] == 1);
    animate(nullptr, untouched);
    animate(unit.data(), nullptr);
    std::puts("Running Wild native routes and isolation passed");
}
