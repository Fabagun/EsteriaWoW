"""Independent structural/decoded delivery checks for the effect-only material policy."""
import hashlib,json,shutil,struct,sys,tempfile
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/pixelmon'))
from validate import read_model
from convert import Dbc
from texture import decode_blp
from blp_compression import encode

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(path, temporary):
    data=bytearray(path.read_bytes())
    count,offset=struct.unpack_from('<II',data,0x70)
    if count!=1 or struct.unpack_from('<HH',data,offset)!=(5,2):raise ValueError('Wrong effect material')
    # Reuse geometry validation with a temporary material-only normalization.
    # The real fullbright/two-sided material above is independently required.
    struct.pack_into('<HH',data,offset,0,2)
    tmp=temporary/path.name;tmp.write_bytes(data)
    shutil.copyfile(path.with_name(path.stem+'00.skin'),tmp.with_name(tmp.stem+'00.skin'))
    return read_model(tmp,texture_policy='source_alpha_blend',skeleton_policy='glb_hierarchical_trs')

def main():
    package=ROOT/'assets/battle-effects';manifest=json.loads((package/'manifest.json').read_text())
    out=ROOT/'generated/effects-review';out.mkdir(parents=True,exist_ok=True)
    for name,wanted in manifest['files'].items():
        if sha(package/name)!=wanted:raise ValueError('Changed package file '+name)
    for name,wanted in manifest['source_hashes'].items():
        if sha(Path(manifest['source'])/name)!=wanted:raise ValueError('Changed source '+name)
    families={};records=[]
    with tempfile.TemporaryDirectory() as td:
        for row in manifest['effects']:
            path=package/'client/Creature/BattlemonEffects'/(row['stem']+'.m2')
            d=decode(path,Path(td));texture=path.with_suffix('.blp')
            if d['texture'].replace('\\','/')!='Creature/BattlemonEffects/'+texture.name:raise ValueError('Wrong texture path')
            raw=Image.open(package/'raw'/(row['stem']+'.png')).convert('RGBA');mips=[raw]
            while mips[-1].size!=(1,1):
                im=mips[-1];mips.append(im.resize((max(1,im.width//2),max(1,im.height//2)),Image.Resampling.LANCZOS))
            encoded,metrics=encode(mips)
            if encoded!=texture.read_bytes() or metrics!=row['quality']:raise ValueError('Compression not reproducible')
            for i,im in enumerate(mips):
                if decode_blp(texture,i).size!=im.size:raise ValueError('Bad mip')
            family=row['effect']['id'].lower();families[family]=families.get(family,0)+1
            # Render three decoded poses, not generator-side geometry.
            if families[family]==1 or row['source'].endswith(('flamethrower.json','thunder_shock.json','water_gun.json')):
                texname=row['stem']+'.png';decode_blp(texture).save(out/texname)
                for f in [6,20,34]:
                    item=dict(name=row['stem']+'_'+str(f),family=family,positions=d['poses'][0][f].tolist(),
                        triangles=d['triangles'].tolist(),uv=d['uv'].tolist(),texture=texname,bounds=d['bounds'].tolist())
                    (out/(item['name']+'.json')).write_text(json.dumps(item))
            records.append(dict(id=row['id'],vertices=len(d['positions']),frames=len(d['poses'][0]),mips=len(mips)))
        # The serialized reader must reject corrupted bone references and out-of-bounds tracks.
        path=package/'client/Creature/BattlemonEffects'/(manifest['effects'][0]['stem']+'.m2')
        original=path.read_bytes();negative=Path(td)/'negative.m2'
        shutil.copyfile(path.with_name(path.stem+'00.skin'),negative.with_name('negative00.skin'))
        for kind in ['bone','bounds','material']:
            data=bytearray(original)
            if kind=='bone':
                _,v=struct.unpack_from('<II',data,0x3c);data[v+16]=255
            elif kind=='bounds':struct.pack_into('<6f',data,0xa0,0,0,0,.001,.001,.001)
            else:
                _,m=struct.unpack_from('<II',data,0x70);struct.pack_into('<H',data,m,0)
            negative.write_bytes(data)
            try:
                nested=Path(td)/kind;nested.mkdir();decode(negative,nested)
            except ValueError:pass
            else:raise ValueError('Corruption accepted: '+kind)
    for table in ['CreatureModelData','CreatureDisplayInfo']:
        a=package/'client/DBFilesClient'/(table+'.dbc9-battlemon-effects')
        b=package/'server/dbc-continuations'/a.name
        if a.read_bytes()!=b.read_bytes():raise ValueError('Client/server rows differ')
        if set(Dbc(a).rows)!={r['id'] for r in manifest['effects']}:raise ValueError('Wrong IDs')
    result=dict(passed=True,models=len(records),families=families,negative_checks=3,records=records,
        manifest_sha256=sha(package/'manifest.json'))
    (out/'checks.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='records'}))
if __name__=='__main__':main()
