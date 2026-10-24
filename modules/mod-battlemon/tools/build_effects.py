"""Build an isolated WoW adaptation of supplied Pixelmon attack effects (no installation)."""
import argparse, hashlib, json, math, re, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT/'tools/pixelmon'
sys.path.insert(0, str(TOOLS))
from m2 import build_model
from convert import Dbc, write_dbc, float_bits
from blp_compression import encode

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(s): return re.sub('[^A-Z0-9]', '', s.upper())
def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)

def geometry(effect, duration, seed):
    """Bounded, deterministic crossed-sprite geometry for WotLK; not Java particle emulation."""
    rng = np.random.default_rng(seed)
    family = effect['id'].lower()
    n = min(96, max(12, int(effect.get('totalPoints', effect.get('segments', 32)))))
    times = np.unique(np.linspace(0, duration, 41).astype(int))
    centers = np.zeros((len(times), n, 3)); scales = np.zeros_like(centers)
    spread = rng.normal(size=(n, 3)); spread /= np.linalg.norm(spread, axis=1)[:, None]
    phases = np.arange(n)/n
    radius = min(4., max(.2, float(effect.get('radius', 2))))
    size = min(1.3, max(.08, float(effect.get('scale', .3))))
    speed = max(.05, min(2., float(effect.get('speed', .5))))
    variation = min(3., max(0., float(effect.get('variation', .25))))
    for f, t in enumerate(times / duration):
        envelope = max(.001, min(1., t*8, (1-t)*8))
        for i, phase in enumerate(phases):
            u = (t*speed*2 + phase) % 1
            angle = phase*math.tau
            if family in ('beam', 'lightning'):
                x = u*14
                jitter = variation if family == 'beam' else .55
                pos = [x, math.sin(x*3+phase*7+t*9)*jitter, math.cos(x*2+phase*9+t*8)*jitter]
            elif family == 'ball':
                pos = np.array([14*min(1., t*1.6), 0, 0]) + spread[i]*float(effect.get('size', .65))
            elif family in ('buff', 'tube'):
                height = float(effect.get('height', 3))
                r = radius*(1-u) if effect.get('conical', False) else radius
                pos = [r*math.cos(angle+t*3), r*math.sin(angle+t*3), u*height-1]
            elif family == 'rain':
                width = float(effect.get('maxHorizontalDisplacement', 2))
                height = max(1., float(effect.get('heightAboveTarget', 4)))
                pos = [spread[i,0]*width, spread[i,1]*width, height*(1-u)-1]
            elif family in ('radial', 'explosion'):
                pos = spread[i]*radius*min(1., t*2)
                if family == 'radial': pos[2] *= .2
            else: raise ValueError('Unsupported family '+family)
            centers[f,i] = pos
            scales[f,i] = size*envelope*(.7+.3*math.sin(phase*20+t*5))
    verts=[]; weights=[]; triangles=[]
    # Crossed quads work from all viewing angles without camera-dependent bone flags.
    for i in range(n):
        for axis in range(3):
            for corner, uv in zip([(-1,-1),(1,-1),(1,1),(-1,1)],[(0,1),(1,1),(1,0),(0,0)]):
                xyz=[0.,0.,0.];xyz[(axis+1)%3]=corner[0]*.5;xyz[(axis+2)%3]=corner[1]*.5
                normal=[0.,0.,0.];normal[axis]=1
                verts.append([*xyz,*normal,*uv]);weights.append([(i,1.)])
            j=len(verts)-4;triangles.extend([j,j+1,j+2,j,j+2,j+3])
    mn=(centers-scales).min(axis=(0,1))-.01;mx=(centers+scales).max(axis=(0,1))+.01
    seq=dict(duration=duration,speed=0.,bounds=(mn,mx),times=times,translations=centers,
        rotations=np.tile([0.,0.,0.,1.],(len(times),n,1)),scales=scales)
    mesh=dict(vertices=np.array(verts),weights=weights,triangles=triangles,bones=[('p'+str(i),-1) for i in range(n)],
        bounds=(mn,mx),skeleton_policy='glb_hierarchical_trs',sequences=[dict(seq,id=x) for x in (0,4,5)])
    return mesh

def main():
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('client',type=Path)
    args=ap.parse_args();source=args.source;out=ROOT/'assets/battle-effects';out.mkdir(parents=True,exist_ok=True)
    dbroot=args.client/'data/patch-z.mpq/DBFilesClient'
    model=Dbc(dbroot/'CreatureModelData.dbc1-battlemon');disp=Dbc(dbroot/'CreatureDisplayInfo.dbc1-battlemon')
    dr=disp.rows[50001];mr=model.rows[dr[1]]
    occupied=set();baselines={}
    for folder in [args.client/'data',ROOT.parents[1]/'env/dist/bin/data']:
        for table in ('CreatureDisplayInfo','CreatureModelData'):
            for p in folder.rglob(table+'.dbc*'):
                occupied.update(Dbc(p).rows);baselines[str(p)]=sha(p)
    start=310000
    if any(x in occupied for x in range(start,start+1000)):raise ValueError('Effect ID range occupied')
    plans={};records=[];modelrows=[];disprows=[];sourcehashes={};textures={}
    defaults={'NORMAL':'attack','HEART_PURPLE':'heartpurple','HEART_RED':'heartred','UP_ARROW':'uparrow','DOWN_ARROW':'downarrow'}
    folder='Creature/BattlemonEffects'
    definitions=sorted((source/'data/pixelmon/pixelmon/battle/animation/attack').rglob('*.json'))
    for p in definitions:
        data=json.loads(p.read_text());sourcehashes[str(p.relative_to(source))]=sha(p)
        attacks=data['condition']['attacks']; actions=[]
        for entry in data['actions']:
            action=entry['action'];kind=action['type'].split(':')[-1]
            delay=int(data['markers'][entry['from']]*50)
            if kind!='attack_effect':
                assert kind in ('leap_forward','run','vertical_stomp'),kind
                actions.append(dict(kind=kind,delay=delay,duration=int(action.get('duration_ticks',20)*50)))
                continue
            effect=action['effect'];index=start+len(records);stem='fx_'+str(index)
            movefile=source/'data/pixelmon/moves'/(attacks[0].split(':')[-1]+'.json')
            move=json.loads(movefile.read_text()) if movefile.exists() else {}
            if movefile.exists():sourcehashes[str(movefile.relative_to(source))]=sha(movefile)
            typ=move.get('attackType','NORMAL').lower()
            colorpath=source/'data/pixelmon/pixelmon/battle/type'/(typ+'.json')
            color=json.loads(colorpath.read_text())['color'];sourcehashes[str(colorpath.relative_to(source))]=sha(colorpath)
            rgb=effect.get('rgb',[color['red'],color['green'],color['blue']])
            tex=effect.get('texture',{'grass':'LEAF','water':'WATER','fire':'FLAME'}.get(typ,'NORMAL'))
            name='lightning1' if effect['id'].lower()=='lightning' else defaults.get(tex,tex.lower())
            texture=source/'assets/pixelmon/textures/particle'/(name+'.png')
            sourcehashes[str(texture.relative_to(source))]=sha(texture)
            image=Image.open(texture).convert('RGBA');pixels=np.array(image)
            pixels[:,:,:3]=(pixels[:,:,:3].astype(float)*np.array(rgb)/255).astype('uint8')
            image=Image.fromarray(pixels)
            dimensions=tuple(1 << (x-1).bit_length() for x in image.size)
            factor=max(1,512//max(dimensions));dimensions=tuple(x*factor for x in dimensions)
            if dimensions!=image.size:image=image.resize(dimensions,Image.Resampling.LANCZOS)
            mips=[image]
            while mips[-1].size!=(1,1):
                last=mips[-1];mips.append(last.resize((max(1,last.width//2),max(1,last.height//2)),Image.Resampling.LANCZOS))
            blp,quality=encode(mips)
            if quality[0]['alpha_mae']>5 or quality[0]['rgb_mae_visible']>8:raise ValueError('Texture quality failed '+name)
            duration=min(5000,max(900,int(effect.get('lifetimeTicks',effect.get('durationTicks',30))*50)))
            mesh=geometry(effect,duration,index)
            m2,skin=build_model(mesh,stem,(folder+'/'+stem+'.blp').replace('/','\\'),'source_alpha_blend')
            # Fullbright, double-sided alpha blending, limited to these new effect models.
            m2=bytearray(m2);count,offset=struct.unpack_from('<II',m2,0x70);assert count==1
            struct.pack_into('<HH',m2,offset,5,2)
            for ext,payload in [('.m2',m2),('00.skin',skin),('.blp',blp)]:save(out/'client'/folder/(stem+ext),payload)
            raw=out/'raw'/(stem+'.png');raw.parent.mkdir(parents=True,exist_ok=True);image.save(raw)
            mn,mx=mesh['bounds'];m=mr.copy();d=dr.copy()
            m[0],m[1],m[4]=index,0,float_bits(1);m[14],m[15]=float_bits(1),float_bits(1)
            m[17:23]=[float_bits(v) for v in [*mn,*mx]]
            d[0],d[1],d[4]=index,index,float_bits(1)
            modelrows.append((m,{2:(folder+'/'+stem+'.mdx').replace('/','\\')}));disprows.append((d,{c:'' for c in [6,7,8,9]}))
            at_target=effect.get('atTarget',effect['id'].lower() in ('rain','explosion','radial'))
            rec=dict(id=index,stem=stem,source=str(p.relative_to(source)),effect=effect,texture=str(texture.relative_to(source)),
                rgb=rgb,duration=duration,delay=delay,at_target=at_target,inverted=effect.get('inverted',False),quality=quality)
            records.append(rec);actions.append(dict(kind='effect',id=index,delay=delay,duration=duration,at_target=at_target,inverted=rec['inverted']))
        for attack in attacks:
            k=key(attack.split(':')[-1]);assert k not in plans,k;plans[k]=actions
    for table,rows,fields,cols in [('CreatureModelData',modelrows,28,[2]),('CreatureDisplayInfo',disprows,16,[6,7,8,9])]:
        for side,sub in [('client','DBFilesClient'),('server','dbc-continuations')]:
            p=out/side/sub/(table+'.dbc9-battlemon-effects');p.parent.mkdir(parents=True,exist_ok=True);write_dbc(p,rows,fields,cols)
    header=['// Generated from Pixelmon 9.4.1; regenerate with tools/build_effects.py.','#pragma once','#include <string>','#include <unordered_map>','#include <vector>',
        'namespace BattlemonEffects','{','struct Action','{','    unsigned kind, display, delay, duration;','    bool target, inverted;','};',
        'inline std::unordered_map<std::string, std::vector<Action>> const Plans = {']
    for name,actions in sorted(plans.items()):
        values=[]
        for a in actions:
            kind={'effect':0,'leap_forward':1,'run':2,'vertical_stomp':3}[a['kind']]
            values.append('{%d,%d,%d,%d,%s,%s}'%(kind,a.get('id',0),a['delay'],a['duration'],str(a.get('at_target',False)).lower(),str(a.get('inverted',False)).lower()))
        header.append('    {"'+name+'", {'+','.join(values)+'}},')
    header+=['};','}'];(ROOT/'src/BattlemonEffectCatalog.h').write_text('\n'.join(header)+'\n',encoding='utf-8')
    manifest=dict(source=str(source),definitions=len(definitions),moves=len(plans),effects=records,plans=plans,source_hashes=sourcehashes,
        baseline_hashes=baselines,adaptation='Deterministic WotLK crossed-sprite particle families; bounded count 12..96, duration .9..5s, scale .08..1.3; source textures/colors/actions retained. Not exact Java particle simulation.',
        files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Built',len(plans),'move plans and',len(records),'effect models')
if __name__=='__main__':main()
