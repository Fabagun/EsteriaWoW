// Execute the staged x86 thunks against the real helper, with small stand-ins for stock continuations.
#include <windows.h>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>

constexpr unsigned TestDelta = 0x10000000; // Reserve a private test copy away from Windows' low-address mappings.

template<class T>
T& At(void* object, unsigned offset)
{
    return *reinterpret_cast<T*>(static_cast<unsigned char*>(object) + offset);
}

__declspec(naked) int __stdcall Mounted(void* /*unit*/)
{
    __asm
    {
        push ebp
        mov ebp, esp
        mov eax, [ebp + 8]
        mov edx, 0x106125C2
        jmp edx
    }
}

int main(int argc, char** argv)
{
    assert(argc == 3);
    for (unsigned original : {0x610000u, 0x730000u, 0xE00000u})
    {
        unsigned address = original + TestDelta;
        void* reserved = VirtualAlloc(reinterpret_cast<void*>(address), 0x10000,
            MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        if (reserved != reinterpret_cast<void*>(address))
        {
            MEMORY_BASIC_INFORMATION info{};
            VirtualQuery(reinterpret_cast<void*>(address), &info, sizeof(info));
            std::printf("Unavailable test address %x allocation %p type %lx\n",
                address, info.AllocationBase, info.Type);
            return 2;
        }
    }
    HMODULE library = LoadLibraryA(argv[1]);
    assert(library);
    std::ifstream input(argv[2], std::ios::binary);
    std::vector<char> file((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    assert(file.size() > 1024);
    auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(file.data());
    auto* nt = reinterpret_cast<IMAGE_NT_HEADERS32*>(file.data() + dos->e_lfanew);
    auto* sections = IMAGE_FIRST_SECTION(nt);
    unsigned imageBase = nt->OptionalHeader.ImageBase;
    auto raw = [&](unsigned rva) -> unsigned char*
    {
        for (unsigned i = 0; i < nt->FileHeader.NumberOfSections; ++i)
            if (rva >= sections[i].VirtualAddress
                && rva - sections[i].VirtualAddress < sections[i].SizeOfRawData)
                return reinterpret_cast<unsigned char*>(file.data()) + sections[i].PointerToRawData
                    + rva - sections[i].VirtualAddress;
        assert(false);
        return nullptr;
    };
    unsigned mapped = 0;
    for (unsigned i = 0; i < nt->FileHeader.NumberOfSections; ++i)
        if (std::memcmp(sections[i].Name, ".erwild", 7) == 0)
        {
            unsigned address = imageBase + sections[i].VirtualAddress + TestDelta;
            unsigned reserve = address & ~0xffffu;
            assert(reserve == 0xE00000 + TestDelta);
            std::memcpy(reinterpret_cast<void*>(address), raw(sections[i].VirtualAddress), sections[i].SizeOfRawData);
            // Relative branches remain byte-identical when caller/continuation move together.
            // Relocate only the three absolute IAT operands for this private test copy.
            unsigned calls = 0;
            auto* code = reinterpret_cast<unsigned char*>(address);
            for (unsigned offset = 0; offset + 6 <= sections[i].SizeOfRawData; ++offset)
                if (code[offset] == 0xff && code[offset + 1] == 0x15)
                {
                    unsigned& operand = At<unsigned>(code, offset + 2);
                    assert(operand >= 0xE04000 && operand < 0xE05000);
                    operand += TestDelta;
                    ++calls;
                }
            assert(calls == 3);
            mapped = address;
        }
    assert(mapped);
    auto* descriptor = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(
        raw(nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress));
    unsigned bound = 0;
    for (; descriptor->Name; ++descriptor)
    {
        if (std::strcmp(reinterpret_cast<char*>(raw(descriptor->Name)), "EsteriaAppearance.dll") != 0)
            continue;
        auto* names = reinterpret_cast<unsigned*>(raw(descriptor->OriginalFirstThunk));
        for (unsigned i = 0; names[i]; ++i)
        {
            auto* name = reinterpret_cast<char*>(raw(names[i]) + 2);
            if (std::strncmp(name, "EsteriaSelf", 11) != 0)
                continue;
            auto function = GetProcAddress(library, name);
            assert(function);
            At<unsigned>(reinterpret_cast<void*>(imageBase + descriptor->FirstThunk + TestDelta), i * 4)
                = reinterpret_cast<unsigned>(function);
            ++bound;
        }
    }
    assert(bound == 3);
    for (unsigned site : {0x6125C2u, 0x735820u, 0x737EF0u})
        std::memcpy(reinterpret_cast<void*>(site + TestDelta), raw(site - imageBase), 5);
    unsigned char const falseContinue[] = {0x0f,0x9f,0xc0,0x0f,0xb6,0xc0,0x5d,0xc2,4,0};
    unsigned char const trueContinue[] = {0xb8,1,0,0,0,0x5d,0xc2,4,0};
    unsigned char const animContinue[] = {0x8b,0x45,0x10,0xc9,0xc2,0x24,0};
    unsigned char const motionContinue[] = {0x8b,0x45,8,0x8b,0,0xc9,0xc2,0x18,0};
    std::memcpy(reinterpret_cast<void*>(0x6125C9 + TestDelta), falseContinue, sizeof(falseContinue));
    std::memcpy(reinterpret_cast<void*>(0x6125D7 + TestDelta), trueContinue, sizeof(trueContinue));
    std::memcpy(reinterpret_cast<void*>(0x735826 + TestDelta), animContinue, sizeof(animContinue));
    std::memcpy(reinterpret_cast<void*>(0x737EF6 + TestDelta), motionContinue, sizeof(motionContinue));
    FlushInstructionCache(GetCurrentProcess(), nullptr, 0);
    std::array<unsigned char, 0x1100> unit{};
    std::array<unsigned char, 0x400> fields{};
    std::array<unsigned char, 8> model{};
    At<unsigned>(unit.data(), 0x14) = 4;
    At<void*>(unit.data(), 0xD0) = fields.data();
    At<void*>(unit.data(), 0xB4) = model.data();
    fields[0x44] = 66;
    At<unsigned>(fields.data(), 0xF4) = 60070;
    At<unsigned>(fields.data(), 0xD4) = 0x08000000;
    using Animation = int(__thiscall*)(void*, unsigned, int, int, int, int, float, int, int, int);
    auto animate = reinterpret_cast<Animation>(0x735820 + TestDelta);
    using Motion = int(__thiscall*)(void*, unsigned*, int, int, int, int, int);
    auto motion = reinterpret_cast<Motion>(0x737EF0 + TestDelta);
    for (unsigned repeat = 0; repeat < 32; ++repeat)
    {
        assert(Mounted(unit.data()) == 1);
        assert(animate(unit.data(), reinterpret_cast<unsigned>(model.data()), -1, 5, -1, 0, 1.0, 1, 1, 0) == 622);
        unsigned request[] = {5, 1, 123, 0x3f800000};
        assert(motion(unit.data(), request, 622, 0, 0, 1, 1) == 622 && request[1] == 0 && request[2] == 123);
        fields[0x46] = 1;
        assert(Mounted(unit.data()) == 0);
        assert(animate(unit.data(), reinterpret_cast<unsigned>(model.data()), -1, 5, -1, 0, 1.0, 1, 1, 0) == 5);
        fields[0x46] = 0;
        At<unsigned>(fields.data(), 0xD4) = 0;
        assert(Mounted(unit.data()) == 0);
        At<unsigned>(unit.data(), 0x9C0) = 123;
        assert(Mounted(unit.data()) == 1); // Original compare still handles ordinary mounts.
        At<unsigned>(unit.data(), 0x9C0) = 0;
        At<unsigned>(fields.data(), 0xD4) = 0x08000000;
    }
    std::puts("Staged x86 thunks: PASS (imports, argument slots, branches, preserved stack, repeated calls)");
}
