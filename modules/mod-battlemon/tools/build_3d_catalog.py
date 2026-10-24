"""Build a 3D-only catalog from frozen, verified conversion receipts (no live DB access)."""
import csv, json, hashlib, re, shutil
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
MOD=REPO/'modules/mod-battlemon'; GEN=REPO/'modules/mod-battlemon/generated'
BASE=Path('C:/data/pokemon-mod/2d-version/client/Interface/AddOns/Battlemon')
ADDON=MOD/'addon/Battlemon'; SOURCE=Path('F:/_d-bak/_other/Pixelmon-1.21.1-9.4.0-universal/data/pixelmon/species')
OUT=MOD/'data/3d'; OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def writecsv(p,data,fields):
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
def norm(s):return re.sub('[^A-Z0-9]','',s.upper())
def sql(v):return "'"+str(v).replace('\\','\\\\').replace("'","''")+"'"
if not ADDON.exists():shutil.copytree(BASE,ADDON)
forms={int(x['id']):x for x in rows(BASE/'Data/csv/forms.csv')}; species=rows(BASE/'Data/csv/species.csv'); moves={norm(x['name']):x['internal_name'] for x in rows(BASE/'Data/csv/moves.csv')}
old=read(GEN/'pixelmon-batch/installed-direct.json'); extra=read(GEN/'source-catalog/final-declared-union-package/manifest.json'); inv=read(GEN/'pixelmon-batch/inventory.json')
assert len(old['appearances'])==2985 and len(extra['entries'])==980
appearances={}; used=set(); rescued=[]
for e in old['appearances']:
 appearances[e['form'],int(e['shiny'])]=dict(form=e['form'],shiny=int(e['shiny']),display=(70000 if e['shiny'] else 50000)+e['form'],path='Creature/Battlemon/'+e['stem']+'.m2',origin='original')
for f in inv['forms']:
 for a in f['appearances']:
  key=(f['form'],int(a['shiny']))
  if key in appearances:continue
  hits=[e for e in extra['entries'] if (e['identity']['dex'],e['identity']['form'],e['identity']['palette'],e['identity']['gender'])==(f['dex'],a.get('source_form'),a.get('source_palette'),a.get('gender'))]
  if len(hits)==1:
   e=hits[0];used.add(e['display']);rescued.append(dict(form=f['form'],name=f['name'],shiny=key[1],display=e['display']))
   appearances[key]=dict(form=key[0],shiny=key[1],display=e['display'],path='Creature/Battlemon/PixelmonExtras/'+e['stem']+'.m2',origin='rescued',identity=e['identity'])
groups={}
for e in sorted(extra['entries'],key=lambda e:e['display']):
 if e['display'] in used:continue
 identity=e['identity'].copy(); palette=identity['palette'];identity['palette']='standard' if palette in ('none','shiny') else palette
 groups.setdefault(json.dumps(identity,sort_keys=True),[]).append(e)
source_by_dex={int(d['dex']):d for p in SOURCE.glob('*.json') for d in [read(p)]}
newforms=[];newmoves=[];source_hashes={};unknown_moves=set()
old_form_moves=rows(BASE/'Data/csv/form_moves.csv')
for es in groups.values():
 e=es[0];i=e['identity'];fid=2000+min(x['display'] for x in es)-200000
 assert fid not in forms
 sid=i['dex'] or 1033
 details=[]
 if i['form'] not in ('base','normal'):details.append(i['form'].replace('_',' ').title())
 if i['palette'] not in ('none','shiny'):details.append(i['palette'].replace('_',' ').title())
 if i['gender']!='ALL':details.append(i['gender'].title())
 pred=i['predicate']['type'].split(':')[-1]
 if pred!='always':details.append(pred.replace('_',' ').title())
 if i['branch']:details.append('State '+str(i['branch']))
 name=i['name']+(' ('+', '.join(details)+')' if details else '')
 token='BM3D_'+str(fid)
 f=dict(id=str(fid),species_id=str(sid),sprite=token,variant='pixelmon:'+i['form']+':'+i['palette']+':'+pred,name=name,back_sprite=token);forms[fid]=f;newforms.append(f)
 for e in es:
  shiny=int(e['identity']['palette']=='shiny')
  assert (fid,shiny) not in appearances
  appearances[fid,shiny]=dict(form=fid,shiny=shiny,display=e['display'],path='Creature/Battlemon/PixelmonExtras/'+e['stem']+'.m2',origin='extra',identity=e['identity'])
 # Existing species retain the battle system's authored move catalog. Appearance-only
 # palettes/predicates do not introduce a second incompatible mechanics database.
 if i['dex'] in (0,1026,1029,1032):
  sf=source_by_dex[i['dex']]['forms'][0]
  for entry in sf.get('moves',{}).get('levelUpMoves',[]):
   for attack in entry['attacks']:
    if norm(attack) not in moves:unknown_moves.add(attack);continue
    newmoves.append(dict(form_id=fid,method='level',level=max(1,entry['level']),move_internal_name=moves[norm(attack)]))
 else:
  candidates=[f['form'] for f in inv['forms'] if f['dex']==i['dex'] and any(a.get('source_form')==i['form'] for a in f['appearances'])]
  if candidates:
   original_id=min(candidates)
   for move in old_form_moves:
    if int(move['form_id'])==original_id:
     newmoves.append(dict(form_id=fid,method=move['method'],level=int(move['level']),move_internal_name=move['move_internal_name']))
assert not unknown_moves, sorted(unknown_moves)
new_species=[]
for dex in (0,1026,1029,1032):
 src=source_by_dex[dex]; f=src['forms'][0];sid=dex or 1033; b=f['battleStats'];ab=f['abilities'];spawn=f.get('spawn',{})
 row={k:'' for k in species[0]};row.update(id=str(sid),internal_name=norm(src['name']),name=src['name'],type1=f['types'][0],type2=f['types'][1] if len(f['types'])>1 else '',hp=b['hp'],atk=b['attack'],spa=b['specialAttack'],spd=b['specialDefense'],spe=b['speed'],gender_ratio='Genderless' if f.get('malePercentage',-1)<0 else 'FemaleOneEighth' if f.get('malePercentage')==87.5 else 'Female50Percent',growth_rate={'MEDIUM_SLOW':'Parabolic','MEDIUM_FAST':'Medium','SLOW':'Slow','FAST':'Fast','ERRATIC':'Erratic','FLUCTUATING':'Fluctuating'}[f['experienceGroup']],base_exp=spawn.get('baseExp',0),catch_rate=f.get('catchRate',45),happiness=spawn.get('baseFriendship',50),ability1=norm(ab['abilities'][0]) if ab['abilities'] else '',ability2=norm(ab['abilities'][1]) if len(ab['abilities'])>1 else '',hidden_ability=norm(ab['hiddenAbilities'][0]) if ab.get('hiddenAbilities') else '',egg_groups=','.join(f.get('eggGroups',[])),hatch_steps=f.get('eggCycles',0)*256,height=f['dimensions']['height'],weight=f.get('weight',0),generation=src['generation'],sprite=next(x['sprite'] for x in newforms if int(x['species_id'])==sid))
 row['def']=b['defense'];new_species.append(row)
assert not ({int(x['id']) for x in species}&{int(x['id']) for x in new_species})
unsupported=[dict(form=fid,shiny=s,name=f['name']) for fid,f in forms.items() if fid<2000 for s in (0,1) if (fid,s) not in appearances]
active_forms=[f for fid,f in sorted(forms.items()) if any((fid,s) in appearances for s in (0,1))]
writecsv(ADDON/'Data/csv/forms.csv',active_forms,list(forms[1]));writecsv(ADDON/'Data/csv/species.csv',species+new_species,list(species[0]))
# Keep generated runtime data independent of the converter and source pack.
output=dict(schema=1,appearances=list(appearances.values()),forms=active_forms,new_forms=newforms,new_species=new_species,form_moves=newmoves,unsupported_owned=unsupported,rescued=rescued,extra_displays=sorted(e['display'] for e in extra['entries']),inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [GEN/'pixelmon-batch/installed-direct.json',GEN/'pixelmon-batch/inventory.json',GEN/'source-catalog/final-declared-union-package/manifest.json']})
dump(OUT/'catalog.json',output)
print(json.dumps(dict(forms=len(active_forms),appearances=len(appearances),new_forms=len(newforms),new_species=len(new_species),removed_appearances=len(unsupported),rescued=len(rescued),form_moves=len(newmoves))))
