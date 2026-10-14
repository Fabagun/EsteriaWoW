// Run the actual WXL DLL against a synthetic Esteria image, including its x86 restriction thunk.
#include <windows.h>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "../../AzerothPlex/build/wxl-core/include/wxl/PluginApi.h"

namespace
{
    std::uintptr_t Address(std::uintptr_t preferred)
    {
        return reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr)) + preferred - 0x00400000;
    }

    template<class T>
    T& At(std::uintptr_t preferred)
    {
        return *reinterpret_cast<T*>(Address(preferred));
    }

    void __cdecl Log(int, char const*, char const*, ...) { }

    unsigned Restriction(void* thunk, unsigned race)
    {
        unsigned result;
        __asm
        {
            push edi
            mov edi, race
            call thunk
            mov result, eax
            pop edi
        }
        return result;
    }
}

int main(int argc, char** argv)
{
    assert(argc == 2);
    auto module = LoadLibraryA(argv[1]);
    assert(module);
    auto query = reinterpret_cast<WXL_QueryFn>(GetProcAddress(module, "WXL_Query"));
    auto load = reinterpret_cast<WXL_LoadFn>(GetProcAddress(module, "WXL_Load"));
    assert(query && load && query()->pluginVersion == 2);
    WXL_Api api{};
    api.structSize = sizeof(api);
    api.apiVersion = WXL_API_VERSION;
    api.Log = &Log;
    for (auto preferred : {0x00460000u, 0x004C0000u, 0x004D0000u, 0x004E0000u, 0x00DF0000u})
    {
        void* page = reinterpret_cast<void*>(Address(preferred));
        assert(VirtualAlloc(page, 65536, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE) == page);
    }
    constexpr std::array<unsigned, 8> references = {
        0x004E157D, 0x004E16A3, 0x004E15B5, 0x004E20EE,
        0x004E222A, 0x004E2127, 0x004E1E94, 0x004E1C3A,
    };
    std::memcpy(reinterpret_cast<void*>(Address(0x00DFE000)), "ESTERIA_CLIENT_FOUNDATION_V3", 29);
    for (auto site : references)
        At<unsigned>(site) = static_cast<unsigned>(Address(0x00DFE220));
    At<unsigned>(0x004CDA43) = static_cast<unsigned>(Address(0x00DFE400));
    At<unsigned>(0x004E1C34) = 0x100;
    At<unsigned>(0x004E1E9B) = 22;
    At<unsigned char>(0x00464C4F) = 0x64;
    constexpr unsigned char branch[] = {0x0F, 0x87, 0x3C, 0x01, 0, 0};
    std::memcpy(reinterpret_cast<void*>(Address(0x004DFAF0)), branch, sizeof(branch));
    unsigned original[64];
    for (unsigned i = 0; i < 64; ++i)
        At<unsigned>(0x00DFE220 + i * 4) = original[i] = 0xC0000000 + i;
    for (unsigned i = 1; i < 28; ++i)
        At<unsigned>(0x00DFE400 + i * 4) = 0xD0000000 + i;

    // Every fingerprint mismatch must refuse installation before any table or branch changes.
    for (auto site : references)
    {
        ++At<unsigned>(site);
        assert(load(&api) == 0);
        --At<unsigned>(site);
        assert(At<unsigned>(0x004E1C34) == 0x100);
        assert(std::memcmp(reinterpret_cast<void*>(Address(0x004DFAF0)), branch, sizeof(branch)) == 0);
    }
    At<unsigned char>(0x00DFE000) = 'X';
    assert(load(&api) == 0);
    At<unsigned char>(0x00DFE000) = 'E';
    At<unsigned char>(0x00464C4F) = 99;
    assert(load(&api) == 0);
    At<unsigned char>(0x00464C4F) = 100;
    constexpr unsigned char error[] = {0xB8, 0, 0, 0, 0, 0xC3};
    constexpr unsigned char success[] = {0xB8, 1, 0, 0, 0, 0xDD, 0xD8, 0xC3}; // Consume the thunk's fldz.
    std::memcpy(reinterpret_cast<void*>(Address(0x004DFC32)), error, sizeof(error));
    std::memcpy(reinterpret_cast<void*>(Address(0x004DFC18)), success, sizeof(success));

    assert(load(&api) == 1);
    auto* memory = reinterpret_cast<unsigned*>(At<unsigned>(references[0]));
    auto* names = reinterpret_cast<unsigned*>(At<unsigned>(0x004CDA43));
    for (auto site : references)
        assert(At<unsigned>(site) == reinterpret_cast<unsigned>(memory));
    assert(std::memcmp(memory, original, sizeof(original)) == 0);
    for (unsigned i = 64; i < 129 * 2; ++i)
        assert(memory[i] == 0);
    assert(names == memory + 129 * 2 && names[0] == 0);
    for (unsigned i = 1; i < 28; ++i)
        assert(names[i] == 0xD0000000 + i);
    for (unsigned i = 28; i < 129; ++i)
        assert(names[i] == names[28] && *reinterpret_cast<unsigned*>(names[i]) == 0);
    assert(At<unsigned>(0x004E1C34) == 129 * 2 * 4 && At<unsigned>(0x004E1E9B) == 129);
    assert(At<unsigned char>(0x00464C4F) == 100);
    auto target = Address(0x004DFAF0) + 6 + At<int>(0x004DFAF2);
    for (unsigned race : {12u, 63u, 64u, 127u, 128u})
        assert(Restriction(reinterpret_cast<void*>(target), race) == 1);
    for (unsigned race : {0u, 11u, 129u, 255u, 0xffffffffu})
        assert(Restriction(reinterpret_cast<void*>(target), race) == 0);
    assert(load(&api) == 1); // Re-entry must not allocate or redirect a second table.
    assert(At<unsigned>(references[0]) == reinterpret_cast<unsigned>(memory));
    std::puts("Race capacity: PASS (actual DLL, IDs through 128, both genders, names, fingerprints, character limit)");
}
