"""Focused source, identity, data-preservation and equipment-structure checks for the Centaur stage."""

import hashlib
import json
import struct

from wotlkconv.m2 import parse_m2, parse_skin

import centaur_race_pack as c
import centaur_racials as spells


def main():
    c.ownership()
    inventory = json.loads((c.WORK / 'inventory.json').read_text())
    assert inventory['complete'] and inventory['build'] == c.centaur_source.BUILD
    for asset in inventory['assets'].values():
        from pathlib import Path
        assert hashlib.sha256(Path(asset['path']).read_bytes()).hexdigest() == asset['sha256']
    for spec in c.SPECS:
        race, _, donor = spec
        manifest = c.p.load_manifest('centaur_' + spec[1])
        assert manifest['race_ids'] == [race] and manifest['legacy_mask_race'] == donor
        assert manifest['appearance']['supported_genders'] == [0, 1]
        assert manifest['appearance']['profiles']['1']['capacities'] == [16, 1, 14, 1, 1]
        for folder in ('client-dbc', 'server/dbc'):
            table = c.p.RawWdbc((c.STAGE / folder / 'ChrRaces.dbc').read_bytes())
            row = next(row for row in table.records if c.p._value(row, 0) == race)
            assert c.p._value(row, 16) == c.ranges(race)['CreatureDisplayInfo']['male']
            assert c.p._value(row, 20) == c.ranges(race)['CreatureDisplayInfo']['female']
            assert c.p._value(row, 52) == (0 if donor == 1 else 1)
    for sex, identifier in c.centaur_source.MODELS.items():
        root = c.STAGE / 'assets/custom/centaur'
        model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
        skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
        assert 0 < model.vertex_count < 65536 and len(model.bones) == 208
        assert max(skin.vertices) < model.vertex_count and max(skin.indices) < len(skin.vertices)
        assert all(struct.unpack_from('<H', row, 12)[0] <= 75 for row in skin.submeshes)
        assert sum(struct.unpack_from('<H', row, 10)[0] for row in skin.submeshes) == len(skin.indices)
        geosets = {struct.unpack_from('<H', row)[0] for row in skin.submeshes}
        assert not any(g // 100 in (5, 9, 11, 13) for g in geosets), 'No imported humanoid lower garments'
        assert 1801 not in geosets, 'Bare donor waist must not duplicate the fitted horse-back surface'
        assert {g for g in geosets if g // 100 == 18} == {1805}, 'Use the fitted four-leg belt bands'
        hoof_points = []
        for row in skin.submeshes:
            geoset = struct.unpack_from('<H', row)[0]
            first, count = struct.unpack_from('<2H', row, 4)
            points = [struct.unpack_from('<3f', model.vertices, skin.vertices[i] * 48)
                      for i in range(first, first + count)]
            if geoset == 2002:
                hoof_points.extend(points)
            elif geoset == 1:
                assert min(point[2] for point in points) >= .75, 'Clothing cannot cover fetlock fur'
        assert hoof_points and max(p[2] for p in hoof_points) < .22, 'Boots must cover only the hooves'
        assert {(p[0] > .35, p[1] > 0) for p in hoof_points} == {(a, b) for a in (False, True) for b in (False, True)}
        for row in skin.submeshes:
            first, count = struct.unpack_from('<2H', row, 4)
            palette = struct.unpack_from('<H', row, 12)[0]
            influences = struct.unpack_from('<H', row, 16)[0]
            for lookup in range(first, first + count):
                vertex = skin.vertices[lookup] * 48
                for slot in range(4):
                    if model.vertices[vertex + 12 + slot]:
                        assert slot < influences and skin.bones[lookup * 4 + slot] < palette
        for i in range(model.vertex_count):
            record = model.vertices[i * 48:(i + 1) * 48]
            assert sum(record[12:16]) == 255
            assert all(b < len(model.bones) for b, w in zip(record[16:20], record[12:16]) if w)
        report = json.loads((c.WORK / 'clothing-report.json').read_text())['models'][str(sex)]
        assert report['regions'] == list(range(8))
    for folder in ('client-dbc', 'server/dbc'):
        data = (c.STAGE / folder / 'Spell.dbc').read_bytes()
        spells.check(data)
        table = c.p.RawWdbc(data)
        for row in table.records:
            if c.p._value(row, 0) in {ability[0] for ability in spells.ABILITIES}:
                for field in c.p.SPELL_STRING_FIELDS:
                    offset = c.p._value(row, field * 4)
                    assert offset < len(table.strings), 'Spell string offset must be rebased for each destination'
                    assert b'\0' in table.strings[offset:]
    for malformed in (b'SFID', struct.pack('<4sI', b'TXID', 4)):
        try:
            c.centaur_source.references(malformed)
        except ValueError:
            continue
        raise AssertionError('Truncated source dependency accepted')
    print('PASS exact source hashes, both faction/gender contracts, equipment indices/weights/palettes, '
          'travel rows and truncated dependency rejection')


if __name__ == '__main__':
    main()
