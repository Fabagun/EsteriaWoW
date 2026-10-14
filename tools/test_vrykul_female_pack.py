"""Check the staged race identities, donor dependency closure and existing-data preservation."""

import struct
from pathlib import Path
from wotlkconv.m2 import parse_m2, parse_skin
import vrykul_female_pack as v


def check():
    v.check()
    p = v.p
    storm = v.o.Storm(p.DLL_DEFAULT)
    handle = storm.open_archive(v.STAGE/'client'/v.ASSET)
    try:
        names = {name.casefold(): name for name, *_ in storm.list_files(handle)}
        payload = storm.read(handle, v.MODEL)
        original = (v.SOURCE/'Character/Vrykul/Female/VrykulPCFemale.m2').read_bytes()
        reference = {v.MODEL: original, v.SHARED_EFFECT: b''}
        v.isolate_effect(reference)
        repaired, _ = v.separate_bone_track_arrays(reference[v.MODEL])
        # Historical stages predate the proven native-reader alias repair.
        assert payload in (reference[v.MODEL], repaired)
        assert storm.read(handle, v.PRIVATE_EFFECT) == v.SOURCE.joinpath(
            *v.p.PureWindowsPath(v.SHARED_EFFECT).parts).read_bytes()
        model = parse_m2(payload)
        for seq in model.sequences:
            if not seq['flags'] & (0x20 | 0x40):
                name = f'{v.MODEL[:-3]}{seq["id"]:04d}-{seq["variation_index"]:02d}.anim'
                assert name.casefold() in names, name
        for level in range(4):
            parse_skin(storm.read(handle, v.MODEL[:-3]+f'{level:02d}.skin'))
        section_data = (v.STAGE/'tables/CharSections.dbc').read_bytes()
        sections = p.RawWdbc(section_data)
        for race in (56, 57):
            for row in p._table_rows_for_race(section_data, 'CharSections', race):
                if p._value(row, 8) != 1:
                    continue
                for field in (4, 5, 6):
                    offset = p._value(row, field*4)
                    if offset:
                        key = p._string(sections.strings, offset).decode()
                        assert key.casefold() in names, key
        assert sum(name.endswith('_vrf.m2') for name in names) == 340
    finally:
        storm.dll.SFileCloseArchive(handle)
    races = p.RawWdbc((v.STAGE/'tables/ChrRaces.dbc').read_bytes())
    alliance = next(r for r in races.records if p._value(r, 0) == 61)
    assert (p._value(alliance, 8), p._value(alliance, 28), p._value(alliance, 52)) == (1, 7, 0)
    assert p._string(races.strings, p._value(alliance, 44)) == b'OgreAlliance'
    assert (p._value(alliance, 16), p._value(alliance, 20)) == (60053, 60054)
    for name in v.SERVER:
        old = p.RawWdbc((v.STAGE/'baseline-server'/(name+'.dbc')).read_bytes())
        new = p.RawWdbc((v.STAGE/'server'/(name+'.dbc')).read_bytes())
        for i, row in enumerate(old.records):
            expected = p._replace(row, 20, 4, v.DISPLAY_ID) if name == 'ChrRaces' \
                and p._value(row, 0) in (56, 57) else row
            assert new.records[i] == expected, (name, i)
        assert new.strings.startswith(old.strings)
    data = (v.STAGE/'EsteriaAppearance.bin').read_bytes()
    count = struct.unpack_from('<I', data, 8)[0]
    profiles = {struct.unpack_from('<2I', data, 12+i*(12+16*144)): data[12+i*(12+16*144):
                12+(i+1)*(12+16*144)] for i in range(count)}
    for race in (56, 57):
        record = profiles[(race, 1)]
        assert [struct.unpack_from('<I', record, 12+i*144+4)[0] for i in range(5)] == v.CAPACITIES
    source = p.ROOT/'src/server/shared/CreatureAppearance.h'
    assert 'return gender ? VrykulFemale : VrykulMale;' in source.read_text()
    print('Female assets, 340 helmets, faction/language, native profiles and server baselines verified')


if __name__ == '__main__':
    check()
