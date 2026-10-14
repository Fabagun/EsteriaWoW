// Execute the patched x86 archive guards with a relocating native-resize fallback.
#include <windows.h>

#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>

namespace
{
    // Relocate the fixture together; low addresses may already belong to the CRT's process heap.
    constexpr unsigned Delta = 0x10000000;
    unsigned& Capacity() { return *reinterpret_cast<unsigned*>(Delta + 0x00B2FA38); }
    unsigned& Count() { return *reinterpret_cast<unsigned*>(Delta + 0x00B2FA3C); }
    unsigned*& Items() { return *reinterpret_cast<unsigned**>(Delta + 0x00B2FA40); }
    unsigned resizeCalls = 0;
    unsigned inputIndex = 0;
    unsigned inputEax = 0;
    void* invokeAddress = nullptr;
    unsigned frame[4] = {};
    unsigned observed[8] = {};
    unsigned flagsBefore = 0, flagsAfter = 0, stackBefore = 0, stackAfter = 0;

    void __stdcall Resize(unsigned table, unsigned capacity)
    {
        assert(table == Delta + 0x00B2FA38 && capacity > Capacity() && capacity % 64 == 0);
        assert(Count() == Capacity());
        auto replacement = static_cast<unsigned*>(HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, capacity * 4));
        assert(replacement);
        std::memcpy(replacement, Items(), Count() * 4);
        assert(HeapFree(GetProcessHeap(), 0, Items()));
        Items() = replacement;
        Capacity() = capacity;
        ++resizeCalls;
    }

    __declspec(naked) void ResizeEntry()
    {
        __asm
        {
            push dword ptr [esp + 4]
            push ecx
            call Resize
            ret 4
        }
    }

    __declspec(naked) void InvokeMachine()
    {
        __asm
        {
            pushfd
            pushad
            mov stackBefore, esp
            mov eax, inputEax
            mov ebx, 0x23456789
            mov ecx, 0x3456789A
            mov edx, 0x456789AB
            mov esi, 0x56789ABC
            mov edi, inputIndex
            lea ebp, frame
            stc
            pushfd
            pop flagsBefore
            call dword ptr [invokeAddress]
            mov observed[0], eax
            mov observed[4], ebx
            mov observed[8], ecx
            mov observed[12], edx
            mov observed[16], esi
            mov observed[20], edi
            mov observed[24], ebp
            pushfd
            pop flagsAfter
            mov stackAfter, esp
            popad
            popfd
            ret
        }
    }

    void Invoke(void* address, unsigned index, bool helper)
    {
        invokeAddress = address;
        inputIndex = index;
        inputEax = helper ? index : 0x12345678;
        frame[3] = index;
        InvokeMachine();
        assert(stackBefore == stackAfter && ((flagsBefore ^ flagsAfter) & 0xCD5) == 0);
        assert(observed[1] == 0x23456789 && observed[4] == 0x56789ABC);
        assert(observed[5] == index && observed[6] == reinterpret_cast<unsigned>(frame));
    }

    void Reset(unsigned count)
    {
        if (Items())
            assert(HeapFree(GetProcessHeap(), 0, Items()));
        Capacity() = 64;
        Count() = count;
        Items() = static_cast<unsigned*>(HeapAlloc(GetProcessHeap(), 0, 64 * 4));
        assert(Items());
        for (unsigned i = 0; i < 64; ++i)
            Items()[i] = 0xA5000000 + i;
        resizeCalls = 0;
    }

    void Map(unsigned address)
    {
        auto page = reinterpret_cast<void*>(address & ~65535u);
        auto allocation = VirtualAlloc(page, 65536, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        if (allocation != page)
            std::fprintf(stderr, "Mapping %p failed (%lu); test image base %p\n", page, GetLastError(),
                GetModuleHandleW(nullptr));
        assert(allocation == page);
    }
}

int main(int argc, char** argv)
{
    assert(argc == 2);
    // Reserve the audited addresses before the large file buffer can occupy them.
    Map(Delta + 0x00400000);
    Map(Delta + 0x00B20000);
    Map(Delta + 0x00E00000);
    std::ifstream stream(argv[1], std::ios::binary);
    std::vector<char> image{std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
    assert(image.size() > 0x1000);
    auto dos = reinterpret_cast<IMAGE_DOS_HEADER*>(image.data());
    auto nt = reinterpret_cast<IMAGE_NT_HEADERS32*>(image.data() + dos->e_lfanew);
    assert(nt->FileHeader.Machine == IMAGE_FILE_MACHINE_I386 && nt->OptionalHeader.ImageBase == 0x00400000);
    auto sections = IMAGE_FIRST_SECTION(nt);
    unsigned helper = 0;
    for (unsigned i = 0; i < nt->FileHeader.NumberOfSections; ++i)
    {
        auto const& section = sections[i];
        if (std::memcmp(section.Name, ".empq", 5) == 0)
        {
            unsigned address = Delta + nt->OptionalHeader.ImageBase + section.VirtualAddress;
            assert(address >= Delta + 0x00E00000 && address + section.Misc.VirtualSize < Delta + 0x00E10000);
            std::memcpy(reinterpret_cast<void*>(address), image.data() + section.PointerToRawData,
                section.Misc.VirtualSize);
            unsigned relocated = 0;
            for (unsigned j = 0; j + 4 <= section.Misc.VirtualSize; ++j)
            {
                auto operand = reinterpret_cast<unsigned*>(address + j);
                if (*operand == 0x00B2FA38 || *operand == 0x00B2FA3C || *operand == 0x00B2FA40)
                {
                    *operand += Delta;
                    ++relocated;
                    j += 3;
                }
            }
            assert(relocated == 10);
            helper = address + 32;
        }
    }
    assert(helper);
    auto resize = reinterpret_cast<unsigned char*>(Delta + 0x004037F0);
    resize[0] = 0xE9;
    *reinterpret_cast<int*>(resize + 1) = reinterpret_cast<unsigned>(ResizeEntry) - (Delta + 0x004037F5);
    unsigned const sites[] = {0x00405E90, 0x00404963, 0x00405FD6, 0x00406040};
    for (unsigned site : sites)
    {
        unsigned length = site == sites[0] ? 5 : 6;
        auto code = reinterpret_cast<unsigned char*>(Delta + site);
        std::memcpy(code, image.data() + sections[0].PointerToRawData + site - 0x00401000, length);
        assert(code[0] == 0xE9);
        if (site == sites[3])
        {
            unsigned char const clear[] = {0xC7, 0x04, 0xBA, 0, 0, 0, 0, 0xC3};
            std::memcpy(code + length, clear, sizeof(clear));
        }
        else
            code[length] = 0xC3;
    }
    for (unsigned index : {0u, 63u, 64u, 67u, 127u, 128u, 191u, 192u, 300u})
        for (unsigned test = 0; test < 5; ++test)
        {
            Reset(43);
            Invoke(reinterpret_cast<void*>(test == 0 ? helper : Delta + sites[test - 1]), index, test == 0);
            assert(Count() == 43 && Capacity() > index && resizeCalls == (index >= 64 ? 1u : 0u));
            for (unsigned i = 0; i < 64; ++i)
                assert(Items()[i] == (test == 4 && i == index ? 0 : 0xA5000000 + i));
            assert(observed[0] == (test == 0 ? index : test == 1 ? reinterpret_cast<unsigned>(Items()) : 0x12345678));
            assert(observed[2] == (test == 2 ? reinterpret_cast<unsigned>(Items()) : 0x3456789A));
            assert(observed[3] == (test >= 3 ? reinterpret_cast<unsigned>(Items()) : 0x456789AB));
            if (test == 4)
                assert(Items()[index] == 0);
        }
    Reset(64);
    for (unsigned i = 64; i <= 300; ++i)
    {
        Invoke(reinterpret_cast<void*>(helper), i, true);
        Items()[i] = 0xA5000000 + i;
    }
    assert(Count() == 64 && Capacity() == 320 && resizeCalls == 4);
    for (unsigned i = 0; i <= 300; ++i)
        assert(Items()[i] == 0xA5000000 + i);
    assert(HeapFree(GetProcessHeap(), 0, Items()));
    std::puts("Archive capacity: PASS (all four write paths, boundary growth, register/flag/stack ABI, relocating fallback)");
}
