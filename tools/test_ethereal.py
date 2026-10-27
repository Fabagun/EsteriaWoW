"""Offline source/data gates for the native Ethereal stage. Native execution is a separate build gate."""

from collections import Counter
import hashlib
import json
import re
import struct

import ethereal_race_pack as pack
import ethereal_source as source
from wotlkconv.m2 import parse_m2, parse_skin


def main():
    root, stage = source.WORK, pack.STAGE
    audit = json.loads((root / 'source-audit.json').read_text())
    assert audit['npc_mapping_verified'] and audit['build'] == source.BUILD
    inventory = json.loads((root / 'inventory.json').read_text())
    assert inventory['complete'] and inventory['scope'] == 'full' and inventory['build'] == source.BUILD
    for asset in inventory['assets'].values():
        raw = source.Path(asset['path']).read_bytes()
        assert len(raw) == asset['bytes'] and hashlib.sha256(raw).hexdigest() == asset['sha256']
    header = (source.NATIVE / 'Engine/Source/Retail/Ethereal.h').read_text()

    def numbers(name):
        return [int(value) for value in re.search(r'\b' + name + r'\[\]\s*=\s*\{([^}]+)\}', header)[1].split(',')
                if value.strip()]

    geosets = set(numbers('SourceGeosets'))
    assert len(geosets) == len(numbers('SourceGeosets')) == 27
    for name, identifier in (('ethereal_male', 5926159), ('ethereal_female', 6152557), ('dreadnaught', 6254042)):
        model = parse_m2((root / 'source' / f'{identifier}.m2').read_bytes())
        for skin_id, values in audit['models'][name]['skins'].items():
            skin = parse_skin((root / 'source' / f'{skin_id}.skin').read_bytes())
            original = [struct.unpack_from('<H', row)[0] for row in skin.submeshes]
            assert set(original) - {0} == (set() if name == 'dreadnaught' else geosets)
            assert original.count(0) == (4 if name == 'dreadnaught' else 6)
            assert len(skin.vertices) <= 65535 and max(skin.vertices) < model.vertex_count
            assert dict(Counter(map(str, original))) == values
        assert len(geosets) + 11 <= 64
    assert numbers('Bodies') == [5926159, 6152557, 6254042]
    palettes = {
        'MaleCloth': {6190257,6190260,6190261,6190262,6190263,6190264,6190900,6190902,6190903},
        'FemaleCloth': {6190261,6190900,6190901,6190902,6190903,6190904,6190905},
        'MaleBandages': {6190258,6190259}, 'FemaleBandages': {6190257,6190258,6190259},
        'EnergyColors': set(range(6190249,6190255)), 'ExtraColors': {6190255,6190256},
        'MechColors': set(range(6403194,6403200)), 'MechGlowColors': set(range(6435132,6435138))}
    for name, expected in palettes.items():
        assert set(numbers(name)) == expected
        for identifier in expected:
            assert (root / 'source' / f'{identifier}.blp').is_file()
    assert numbers('MaleCloth')[0] == 6190261 and numbers('FemaleCloth')[0] == 6190902
    assert numbers('MechColors')[0] == 6403197 and numbers('MechGlowColors')[0] == 6435135
    server_wire = pack.p.ROOT / 'src/server/shared/RetailLookWire.h'
    client_wire = source.NATIVE / 'Engine/Source/Retail/RetailLookWire.h'
    assert server_wire.read_bytes() == client_wire.read_bytes()
    assert 'MaxForm = 6' in server_wire.read_text()
    allocation = pack.p.load_json(pack.p.ALLOCATION_PATH)
    for spec in pack.SPECS:
        race, faction, donor = spec
        assert allocation['race_ids']['ethereal_' + faction] == [race]
        assert allocation['race_allocations']['ethereal_' + faction] == pack.ranges(race)
    for name in (*pack.shared.TABLES, 'Spell'):
        before = pack.p.RawWdbc((stage / 'baseline' / (name + '.dbc')).read_bytes())
        after = pack.p.RawWdbc((stage / 'client-dbc' / (name + '.dbc')).read_bytes())
        assert not (Counter(before.records) - Counter(after.records)), name
        assert after.strings.startswith(before.strings), name
        if name not in ('CharBaseInfo','CharacterFacialHairStyles'):
            assert len({pack.p._value(row,0) for row in after.records}) == len(after.records), name
    races = pack.p.RawWdbc((stage / 'client-dbc/ChrRaces.dbc').read_bytes())
    for race, faction, donor in pack.SPECS:
        row = next(row for row in races.records if pack.p._value(row,0) == race)
        assert pack.p._value(row,52) == donor - 1
        assert [pack.p._value(row, offset) for offset in (16,20)] == list(pack.ranges(race)['CreatureDisplayInfo'].values())
    spell_table = pack.p.RawWdbc((stage / 'client-dbc/Spell.dbc').read_bytes())
    spell = next(row for row in spell_table.records if pack.p._value(row,0) == pack.SPELL)
    index = pack.racial_data.field_index()
    visage = next(row for row in spell_table.records if pack.p._value(row,0) == 110685)
    for name in ('SpellVisualID_1', 'SpellVisualID_2'):
        assert pack.p._value(spell,index[name] * 4) == pack.p._value(visage,index[name] * 4)
    assert pack.p._value(spell,index['SpellVisualID_1'] * 4) != 0
    assert pack.p._value(spell,index['Effect_1'] * 4) == 3
    assert not pack.p._value(spell,index['Attributes'] * 4) & 0x10000000
    for name in (*pack.shared.SERVER_TABLES, 'Spell'):
        before = pack.p.RawWdbc((stage / 'baseline-server' / (name + '.dbc')).read_bytes())
        after = pack.p.RawWdbc((stage / 'server/dbc' / (name + '.dbc')).read_bytes())
        assert not (Counter(before.records) - Counter(after.records)), name
        assert after.strings.startswith(before.strings), name
    print(f'PASS {len(inventory["assets"])} original asset hashes; exact NPC graph; all 27 geoset IDs and core layers in every LOD;')
    print('PASS all material palettes, identical wire headers, faction models, saved-form capacity, dummy racial and preserved client/server rows')
    print('Native compile, fixture execution and in-game behavior have not been verified by these offline checks.')


if __name__ == '__main__':
    main()
