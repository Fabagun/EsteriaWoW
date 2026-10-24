"""Duplicate names are harmless only outside every source-weighted ancestor chain."""
from collections import Counter


def check_duplicate_names(model_bones, animation_bones, source_weights):
    animation_names = [name for name,parent in animation_bones]
    if len(animation_names) != len(set(animation_names)):
        raise ValueError('Ambiguous duplicate animation bone names')
    live = {bone for links in source_weights for bone,weight in links if weight > 0}
    for start in tuple(live):
        seen = set()
        bone = start
        while bone >= 0:
            if bone in seen:
                raise ValueError('Cyclic source bone hierarchy')
            seen.add(bone);live.add(bone);bone=model_bones[bone][1]
    counts=Counter(name for name,parent in model_bones)
    notes=[]
    for name,count in counts.items():
        if count < 2:
            continue
        indices=[i for i,(n,parent) in enumerate(model_bones) if n==name]
        if sum(i in live for i in indices)>1:
            raise ValueError('Ambiguous duplicate weighted bone names')
        notes.append('unweighted_duplicate_leaf_or_branch:'+name)
    return notes
