"""Install paired Battlemon eDBC layers on the remote server after pulling Git.
Usage: python3 modules/mod-battlemon/tools/install_3d_dbcs.py --server-data env/dist/bin/data
No SQL, compilation or service restart is performed.
"""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'data/3d'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ids(p):
 d=p.read_bytes();assert d[:4]==b'WDBC',p
 n,fields,stride,strings=struct.unpack_from('<4I',d,4)
 assert stride==fields*4 and len(d)==20+n*stride+strings,p
 return {struct.unpack_from('<I',d,20+i*stride)[0] for i in range(n)}
def install(data):
 data=data.resolve();target=data/'dbc-continuations';manifest=json.loads((SOURCE/'dbc-manifest.json').read_text())
 for name,h in manifest.items():
  src=SOURCE/'dbc-continuations'/name;assert sha(src)==h,src
  dest=target/name
  if dest.exists():assert sha(dest)==h,'Different existing eDBC layer: '+str(dest)
  # Additive extras must never collide with another active layer.
  if name.endswith('pixelmon-extras'):
   wanted=ids(src)
   for p in data.rglob(name.split('.')[0]+'.dbc*'):
    if p==dest or 'Battlemon-Deferred' in p.parts:continue
    assert not (ids(p)&wanted),'DBC ID collision: '+str(p)
 target.mkdir(parents=True,exist_ok=True)
 made=[]
 try:
  for name,h in manifest.items():
   dest=target/name
   if not dest.exists():shutil.copy2(SOURCE/'dbc-continuations'/name,dest);made.append(dest)
   assert sha(dest)==h
 except BaseException:
  for p in made:
   if sha(p)==manifest[p.name]:p.unlink()
  raise
 print('Verified',len(manifest),'Battlemon 3D eDBC files in',target)
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--server-data',type=Path,required=True);install(ap.parse_args().server_data)
