"""Check Centaur repair boundaries, saved-choice compatibility and additive data changes."""

from collections import Counter
import struct

import centaur_deploy as deploy
import centaur_refine as repair
import test_centaur


def main():
    test_centaur.main()
    for name in repair.TABLES:
        before = deploy.pack.p.RawWdbc((repair.WORK / 'baseline-client' / (name + '.dbc')).read_bytes())
        after = deploy.pack.p.RawWdbc((repair.WORK / 'client-dbc' / (name + '.dbc')).read_bytes())
        assert not (Counter(before.records) - Counter(after.records)), name
        assert after.strings.startswith(before.strings), name
    for name in repair.SERVER_TABLES:
        before = deploy.pack.p.RawWdbc((repair.WORK / 'baseline-server' / (name + '.dbc')).read_bytes())
        after = deploy.pack.p.RawWdbc((repair.WORK / 'server' / (name + '.dbc')).read_bytes())
        assert not (Counter(before.records) - Counter(after.records)), name
    for race, faction, _ in deploy.pack.SPECS:
        manifest = deploy.pack.p.load_manifest('centaur_' + faction)
        for sex in (0, 1):
            capacities = manifest['appearance']['profiles'][str(sex)]['capacities']
            assert capacities == [16, 1, 14 if sex else 9, 1, 1 if sex else 8]
            table = deploy.pack.p.RawWdbc((repair.WORK / 'client-dbc/CharSections.dbc').read_bytes())
            hair = {deploy.pack.p._value(row, 32) for row in table.records
                    if [deploy.pack.p._value(row, n) for n in (4, 8, 12)] == [race, sex, 3]}
            assert hair == set(range(capacities[2]))
    for sex, identifier in deploy.pack.centaur_source.MODELS.items():
        from wotlkconv.m2 import parse_m2, parse_skin
        from wotlkconv.m2.skel import parse_skel
        root = deploy.pack.STAGE / 'assets/custom/centaur'
        model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
        skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
        # Shoulder clothing reaches the actual top of the authored arm, not the neck's clipping plane.
        skeleton = parse_skel((deploy.WORK / 'source' / ('4226281.skel' if sex else '4224620.skel')).read_bytes())
        assert all(skeleton.bones[skeleton.key_bone_lookup[key]]['parent_bone'] >= 0 for key in (0, 1))
        shell = []
        for row in skin.submeshes:
            if struct.unpack_from('<H', row)[0] != 1:
                continue
            first, count = struct.unpack_from('<2H', row, 4)
            shell.extend(struct.unpack_from('<3f', model.vertices, skin.vertices[i] * 48)
                         for i in range(first, first + count))
        assert any(abs(y) > .2 and z > 2.645 for x, y, z in shell), 'Shoulder cap was clipped at the neckline'
    print('PASS original records/skins preserved, complete facial ranges, fur/hoof policy and shoulder coverage')


if __name__ == '__main__':
    main()
