"""Verify actual installed correction bytes, exact source guards and all draw geometry."""
from pathlib import Path
import json,struct,sys
M=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(M/'tools'))
from fix_sunny_castform_materials import repair,digest
D=M/'data/3d/model-fixes/sunny-castform'
r=json.loads((D/'receipt.json').read_text())
for stem,proof in r['classification'].items():
    old=(D/'before'/(stem+'.m2')).read_bytes();skin=(D/'before'/(stem+'00.skin')).read_bytes()
    model,fixed_skin=repair(stem,old,skin,proof['solid'])
    assert model==(D/(stem+'.m2')).read_bytes() and fixed_skin==(D/(stem+'00.skin')).read_bytes()
    n,o=struct.unpack_from('<II',model,112);assert n==2 and struct.unpack_from('<4H',model,o)==(0,1,16,2)
    n,o=struct.unpack_from('<II',fixed_skin,28)
    sections=[struct.unpack_from('<10H7f',fixed_skin,o+i*48) for i in range(n)]
    assert n==2 and [s[4:6] for s in sections]==[(0,1962),(1962,2184)]
    assert all(s[2:4]==(0,1635) and 0<s[6]<=64 for s in sections)
    n,o=struct.unpack_from('<II',fixed_skin,36)
    assert n==2 and [struct.unpack_from('<BB11H',fixed_skin,o+i*24)[6] for i in range(n)]==[0,1]
    bad=proof['solid'].copy();a=bad.index(True);b=bad.index(False);bad[a],bad[b]=False,True
    for md,sk,mask in [(old+b'changed',skin,proof['solid']),(old,skin+b'changed',proof['solid']),(old,skin,bad)]:
        try: repair(stem,md,sk,mask)
        except (ValueError,AssertionError): pass
        else: raise AssertionError('Corrupt source/classification accepted')
print('PASS: exact repairs for both palettes, complete draw passes, unchanged geometry/animation bytes and mutation rejection.')
