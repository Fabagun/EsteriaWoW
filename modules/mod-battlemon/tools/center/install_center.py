"""Install Center assets with collision guards; does not run SQL or build/restart the core."""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
MODULE=Path(__file__).resolve().parents[2];DATA=MODULE/'data/center';ID=900500
NAME='GameObjectDisplayInfo.dbc9-battlemon-center'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ids(p):
 b=p.read_bytes();assert b[:4]==b'WDBC',p;n,f,s,z=struct.unpack_from('<4I',b,4);assert s==f*4 and len(b)==20+n*s+z,p
 return {struct.unpack_from('<I',b,20+i*s)[0] for i in range(n)}
def model_records(b):
 assert b[:8]==b'VMAP_4.8','Unsupported GameObjectModels.dtree version'
 p=8;records={}
 while p<len(b):
  start=p;entry,wmo,n=struct.unpack_from('<IBI',b,p);p+=9;assert n<500;p+=n+24;assert p<=len(b) and entry not in records
  records[entry]=b[start:p]
 return records

def install(client=None,server=None,apply=False):
 manifest=json.loads((DATA/'delivery-manifest.json').read_text());copies=[];extra=None
 history=DATA/'previous-delivery-manifests.json'
 previous=json.loads(history.read_text()) if history.exists() else []
 def known(src,digest):return any(row.get(src.relative_to(DATA).as_posix())==digest for row in previous)
 for name,digest in manifest.items():assert sha(DATA/name)==digest,'Source changed: '+name
 def add(src,dst):
  if dst.exists():
   digest=sha(dst)
   if sha(src)==digest:return
   assert known(src,digest),'Existing target differs from known Center releases: '+str(dst)
  copies.append((src,dst))
 if client:
  patch=client/'Data/patch-z.mpq';assert patch.is_dir(),'Expected existing patch-z.mpq folder'
  target=patch/'DBFilesClient'/NAME
  for p in (client/'Data').glob('*.mpq/DBFilesClient/GameObjectDisplayInfo.dbc*'):
   if p.resolve()!=target.resolve():assert ID not in ids(p),'Client display ID collision: '+str(p)
  for src in (DATA/'client').rglob('*'):
   if src.is_file():add(src,patch/src.relative_to(DATA/'client'))
  add(DATA/'server'/NAME,target)
 if server:
  assert (server/'dbc/GameObjectDisplayInfo.dbc').is_file(),'Wrong server data directory'
  target=server/'dbc-continuations'/NAME
  for folder in ['dbc','dbc-continuations']:
   for p in (server/folder).glob('GameObjectDisplayInfo.dbc*'):
    if p.resolve()!=target.resolve():assert ID not in ids(p),'Server display ID collision: '+str(p)
  add(DATA/'server'/NAME,target)
  add(DATA/'server/BattlemonCenter.wmo.vmo',server/'vmaps/BattlemonCenter.wmo.vmo')
  path=server/'vmaps/GameObjectModels.dtree';old=path.read_bytes();records=model_records(old);record=(DATA/'server/GameObjectModels.center-record').read_bytes()
  if ID in records:
   if records[ID]!=record:
    assert known(DATA/'server/GameObjectModels.center-record',hashlib.sha256(records[ID]).hexdigest()),'Collision model ID already used'
    extra=(path,old,b'VMAP_4.8'+b''.join(record if key==ID else value for key,value in records.items()))
  else:extra=(path,old,old+record)
 print('Center preflight:',len(copies),'files to install/update; collision registration:',bool(extra))
 if not apply:return
 for src,dst in copies:
  dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists():
   digest=sha(dst);assert known(src,digest),'Target changed after preflight: '+str(dst)
   owner=client if client and dst.is_relative_to(client) else server
   backup=owner/'battlemon-center-backups'/dst.relative_to(owner)
   backup=backup.with_name(backup.name+'.'+digest[:12]);backup.parent.mkdir(parents=True,exist_ok=True)
   if backup.exists():assert sha(backup)==digest,'Unexpected backup contents'
   else:shutil.copyfile(dst,backup)
  shutil.copyfile(src,dst);assert sha(src)==sha(dst)
 if extra:
  path,old,new=extra;assert path.read_bytes()==old,'Collision index changed during installation'
  backup=server/'battlemon-center-backups'/('GameObjectModels.dtree.'+hashlib.sha256(old).hexdigest()[:12])
  backup.parent.mkdir(parents=True,exist_ok=True)
  if backup.exists():assert backup.read_bytes()==old,'Unexpected previous backup'
  else:backup.write_bytes(old)
  temp=path.with_name(path.name+'.battlemon-center-tmp');assert not temp.exists();temp.write_bytes(new);temp.replace(path)
 print('PASS: Center assets installed. No SQL, core build or service restart performed.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--client',type=Path);p.add_argument('--server-data',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
 if not a.client and not a.server_data:p.error('Specify --client or --server-data')
 install(a.client,a.server_data,a.apply)
