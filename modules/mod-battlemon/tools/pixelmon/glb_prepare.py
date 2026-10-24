"""Experimental hierarchical GLB conversion. No catalog or deployment integration."""
import numpy as np
from glb_source import GLB, source_positions, decompose, rotation


def prepare_glb(path):
    glb=GLB(path);geo=glb.geometry()
    animations={a['name']:a for a in glb.data['animations']}
    if set(animations)!={'idle','walk'}:raise ValueError('Unreviewed GLB animations')
    initial=source_positions(glb,geo,glb.local_trs(animations['idle'],0))
    axis=np.array([[0.,0,1],[1,0,0],[0,1,0]])
    p=initial@axis.T;height=np.ptp(p[:,2])
    coord=np.eye(4);coord[:3,:3]=axis/height;coord[:3,3]=[0,0,-p[:,2].min()/height]
    vertices=np.column_stack([(np.c_[geo['POSITION'],np.ones(len(p))]@coord.T)[:,:3],
                              geo['NORMAL']@axis.T,geo['TEXCOORD_0']])
    # M2 chooses interpolation per bone track, not per animation. Preserve any varying STEP
    # translations in a separate parent bone; the ordinary node carries LINEAR translations.
    step_nodes=set()
    for animation in animations.values():
        for channel in animation['channels']:
            sampler=animation['samplers'][channel['sampler']]
            values=glb.accessor(sampler['output'])
            if sampler.get('interpolation')=='STEP' and np.ptp(values,axis=0).max()>1e-9:
                if channel['target']['path']!='translation':raise ValueError('Varying STEP rotation/scale needs support')
                step_nodes.add(channel['target']['node'])
    bones=[('coordinate_root',-1)];nodes={};step_bones={}
    for node in glb.order:
        parent=nodes[glb.parents[node]] if glb.parents[node]>=0 else 0
        if node in step_nodes:
            step_bones[node]=len(bones);bones.append(('step_translation_'+str(node),parent));parent=len(bones)-1
        nodes[node]=len(bones);bones.append((glb.data['nodes'][node].get('name',str(node)),parent))
    helpers={};constant={0:decompose(coord)}
    used=sorted(set(geo['JOINTS_0'][geo['WEIGHTS_0']>0].astype(int)))
    for joint in used:
        bone=len(bones);helpers[joint]=bone;bones.append(('inverse_bind_'+str(joint),nodes[geo['skin']['joints'][joint]]))
        constant[bone]=decompose(geo['inverse_bind'][joint]@np.linalg.inv(coord))
    if len(bones)>256:raise ValueError('GLB global bone budget exceeded')
    weights=[]
    for indices,values in zip(geo['JOINTS_0'],geo['WEIGHTS_0']):
        links=sorted([(helpers[int(i)],float(w)) for i,w in zip(indices,values) if w>0],key=lambda x:-x[1])
        total=sum(w for _,w in links);weights.append([(i,w/total) for i,w in links])
    sequences=[]
    for name,anim_id in [('idle',0),('walk',4),('walk',5)]:
        animation=animations[name]
        original_times=np.unique(np.r_[0,*[glb.accessor(s['input']).ravel() for s in animation['samplers']]])
        millis=np.rint(original_times*1000).astype(int)
        if np.any(np.diff(millis)<=0):raise ValueError('GLB key times collide at millisecond precision')
        step_channels={c['target']['node'] for c in animation['channels']
                       if c['target']['path']=='translation' and
                       animation['samplers'][c['sampler']].get('interpolation')=='STEP'}
        translations=[];rotations=[];scales=[];posed=[]
        for seconds in original_times:
            t,q,s=glb.local_trs(animation,float(seconds))
            ts=np.zeros((len(bones),3));qs=np.tile([0.,0,0,1],(len(bones),1));ss=np.ones((len(bones),3))
            for bone,triple in constant.items():ts[bone],qs[bone],ss[bone]=triple
            for node,bone in nodes.items():
                ts[bone],qs[bone],ss[bone]=t[node],q[node],s[node]
                if node in step_bones and node in step_channels:
                    ts[step_bones[node]]=t[node];ts[bone]=0
            translations.append(ts);rotations.append(qs);scales.append(ss)
            source=source_positions(glb,geo,(t,q,s))
            posed.append((np.c_[source,np.ones(len(source))]@coord.T)[:,:3])
        posed=np.array(posed)
        sequences.append(dict(id=anim_id,duration=int(millis[-1]),speed=0 if name=='idle' else 1,
            times=millis.tolist(),translations=np.array(translations),rotations=np.array(rotations),
            scales=np.array(scales),bounds=(posed.min(axis=(0,1)),posed.max(axis=(0,1)))))
    minimum=np.min([s['bounds'][0] for s in sequences],axis=0)
    maximum=np.max([s['bounds'][1] for s in sequences],axis=0)
    return dict(vertices=vertices,weights=weights,triangles=geo['indices'].tolist(),bones=bones,
                sequences=sequences,bounds=(minimum,maximum),skeleton_policy='glb_hierarchical_trs',
                translation_interpolation={bone:0 for bone in step_bones.values()},
                glb_coordinate=coord,glb_source=glb,glb_geometry=geo)
