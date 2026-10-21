"""Check independent upper-leg belt bands, the clean cloak hem and inset mirrored chest UVs."""

from pathlib import Path
import struct

import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin

import centaur_deploy as deploy
import test_centaur_v6 as previous
from sethrak_equipment_repair import mesh_triangles

WORK = deploy.WORK / 'repair-v7'


def main(output_root=None):
    output_root = output_root or WORK
    previous.main(output_root)
    report = {}
    for identifier in (4036647, 4081379):
        root = deploy.pack.STAGE / 'assets/custom/centaur'
        model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
        skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
        belt = previous.points(model, skin, 1805)
        assert belt and not any(1801 <= struct.unpack_from('<H', r)[0] <= 1804 for r in skin.submeshes)
        quadrants = set()
        centers = set()
        for record in belt.values():
            x, y, z = struct.unpack_from('<3f', record)
            u, v = struct.unpack_from('<2f', record, 32)
            front = x > .35
            quadrants.add((front, y > 0))
            assert .25 < u < .5 and .375 < v < .625 and z > 1.0
            if abs(u - .375) < .008 and abs(y) > .20:
                centers.add((front, y > 0))
        for ordinal, row in enumerate(skin.submeshes):
            if struct.unpack_from('<H', row)[0] != 1805:
                continue
            for batch in skin.batches:
                if struct.unpack_from('<H', batch, 4)[0] == ordinal:
                    texture = model.texture_combos[struct.unpack_from('<H', batch, 16)[0]]
                    assert model.textures[texture]['type'] == 15, 'Belt must not sample the pants/chest composition'
            for tri in mesh_triangles(skin, row):
                u = [struct.unpack_from('<f', model.vertices, i * 48 + 32)[0] for i in tri]
                assert max(u) - min(u) < .126, 'Belt seam triangles must not cross the UV wrap'
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    if u[a] <= .375 <= u[b] and u[a] != u[b]:
                        t = (.375 - u[a]) / (u[b] - u[a])
                        p, q = [np.array(struct.unpack_from('<3f', model.vertices, tri[i] * 48)) for i in (a, b)]
                        point = p + (q - p) * t
                        if abs(point[1]) > .20:
                            centers.add((point[0] > .35, point[1] > 0))
        assert len(quadrants) == 4 and centers == quadrants, 'Every leg needs an outward-facing belt center'
        for geoset in range(1502, 1511):
            cape = previous.points(model, skin, geoset)
            assert len(cape) == 17 * 25, 'Cloak must be one regular surface without folded duplicate layers'
            hem = [r for r in cape.values() if abs(struct.unpack_from('<f', r, 36)[0] - .993) < 1e-5]
            assert len(hem) == 17
            hem.sort(key=lambda r: struct.unpack_from('<f', r, 4)[0])
            positions = [np.array(struct.unpack_from('<3f', r)) for r in hem]
            assert all(p[0] > -.55 for p in positions), 'Move the hem away from the tail/rump'
            assert max(p[0] for p in positions) - min(p[0] for p in positions) < .055
            assert all(np.linalg.norm(a - b) < .11 for a, b in zip(positions, positions[1:])), 'Hem has a spike'
            assert all(a[1] < b[1] for a, b in zip(positions, positions[1:])), 'Hem folds back on itself'
        body = previous.points(model, skin, 1)
        chest = [r for r in body.values() if struct.unpack_from('<f', r, 8)[0] > 2.14
                 and abs(struct.unpack_from('<f', r, 4)[0]) < .20
                 and struct.unpack_from('<f', r, 32)[0] > .25]
        assert chest
        assert all(.25 + 6 / 2048 - 1e-6 <= struct.unpack_from('<f', r, 32)[0]
                   <= .5 - 6 / 2048 + 1e-6 for r in chest), 'Chest center samples outside the safe atlas interior'
        report[str(identifier)] = {'four_outward_belt_centers': True, 'belt_material': 15,
            'cape_vertices_per_style': 425, 'clean_hem': True, 'chest_uv_inset_pixels': 6}
    deploy.pack.json_save(output_root / 'regional-validation.json', report)
    print('PASS four-leg belt material/centers, clean forward cloak hem and chest atlas-edge guards for both sexes')


if __name__ == '__main__':
    main()
