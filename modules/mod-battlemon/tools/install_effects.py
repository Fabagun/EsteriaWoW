"""Hash-owned additive effect delivery. No Pokemon/PixelmonExtras paths are modified."""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'assets/battle-effects'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ids(p):
 d=p.read_bytes()
 if d[:4]!=b'WDBC':raise ValueError('Not a DBC '+str(p))
 n,f,stride,strings=struct.unpack_from('<4I',d,4)
 if stride!=f*4 or len(d)!=20+n*stride+strings:raise ValueError('Bad DBC')
 return {struct.unpack_from('<I',d,20+i*stride)[0] for i in range(n)}
def install(destination,side):
 destination=destination.resolve();manifest=json.loads((PACKAGE/'manifest.json').read_text())
 files={name[len(side)+1:]:digest for name,digest in manifest['files'].items() if name.startswith(side+'/')}
 if not files:raise ValueError('Empty package')
 receipt=destination/('battlemon-effects-'+side+'-receipt.json')
 previous=json.loads(receipt.read_text()) if receipt.exists() else {}
 if previous and previous.get('files')!=files:raise ValueError('Existing effect version differs; explicit migration required')
 targets={name:(destination/name).resolve() for name in files}
 for name,target in targets.items():
  if not target.is_relative_to(destination):raise ValueError('Path escape')
  if sha(PACKAGE/side/name)!=files[name]:raise ValueError('Package changed '+name)
  if target.exists() and (not previous or sha(target)!=files[name]):raise ValueError('Unowned or changed destination '+str(target))
 wanted={e['id'] for e in manifest['effects']}
 for table in ['CreatureModelData','CreatureDisplayInfo']:
  for p in (destination.parent if side=='client' else destination).rglob(table+'.dbc*'):
   if p.resolve() in targets.values():continue
   if ids(p)&wanted:raise ValueError('DBC ID collision '+str(p))
 made=[]
 try:
  for name,target in targets.items():
   if not target.exists():
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PACKAGE/side/name,target);made.append(target)
   if sha(target)!=files[name]:raise ValueError('Copy verification failed')
  receipt.write_text(json.dumps(dict(files=files,manifest_sha256=sha(PACKAGE/'manifest.json')),indent=2))
 except Exception:
  for target in made:
   name=target.relative_to(destination).as_posix()
   if target.exists() and sha(target)==files[name]:target.unlink()
  raise
 print(side, 'verified',len(files),'files at',destination)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--client-patch',type=Path);ap.add_argument('--server-data',type=Path);a=ap.parse_args()
 if not a.client_patch and not a.server_data:ap.error('Choose client patch directory or server data directory')
 if a.client_patch:install(a.client_patch,'client')
 if a.server_data:install(a.server_data,'server')
if __name__=='__main__':main()
