"""Guard the actual Solosis repair against geometry loss and unsafe materials."""
from pathlib import Path
import json
import struct
import sys

M = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(M/'tools'))
from fix_solosis_materials import repair, verify, digest
D = M/'data/3d/model-fixes/solosis'
receipt = json.loads((D/'receipt.json').read_text())
for stem in ['0577_Solosis', '0577_Solosis_s']:
    old = (D/'before'/(stem+'.m2')).read_bytes()
    skin = (D/'before'/(stem+'00.skin')).read_bytes()
    fixed, fixed_skin = repair(stem, old, skin)
    assert fixed == (D/(stem+'.m2')).read_bytes()
    assert fixed_skin == (D/(stem+'00.skin')).read_bytes()
    for kind in ['geometry', 'material', 'missing_part']:
        md, sk = bytearray(fixed), bytearray(fixed_skin)
        if kind == 'geometry':
            _, offset = struct.unpack_from('<II', md, 0x3c)
            md[offset] ^= 1
        elif kind == 'material':
            _, offset = struct.unpack_from('<II', md, 0x70)
            struct.pack_into('<H', md, offset+4, 0)
        else:
            struct.pack_into('<I', sk, 28, 1)
        try:
            verify(old, skin, md, sk)
        except AssertionError:
            pass
        else:
            raise AssertionError('Mutation accepted: '+kind)
    try:
        repair(stem, old+b'changed', skin)
    except ValueError:
        pass
    else:
        raise AssertionError('Unknown source accepted')
for row in receipt['files']:
    assert digest((D/row['name']).read_bytes()) == row['after']
print('PASS both Solosis palettes: exact geometry/animation preservation, materials, complete sections, mutation rejection.')
