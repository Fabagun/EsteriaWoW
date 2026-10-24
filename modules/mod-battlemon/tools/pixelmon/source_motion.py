"""Evidence for authored constant walks; unrelated animation rigs cannot use this policy."""
import hashlib
from pathlib import Path
import numpy as np
from bmd import read_bmd


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_constant_walk(proof):
    for name in ['model','walk']:
        if digest(proof[name]) != proof[name+'_sha256']:
            raise ValueError('Constant-walk source checksum mismatch')
    model = read_bmd(Path(proof['model']))
    animation = read_bmd(Path(proof['walk']))
    names = [bone[0] for bone in animation['bones']]
    if len(names) != len(set(names)):
        raise ValueError('Constant-walk source has ambiguous channel names')
    weighted = {b for links in model['weights'] for b,w in links if w > 0}
    if not weighted or not all(model['bones'][b][0] in names for b in weighted):
        raise ValueError('Constant-walk source does not match weighted model bones')
    frames = animation['frames']
    if not len(frames) or not np.array_equal(frames,np.broadcast_to(frames[:1],frames.shape)):
        raise ValueError('Declared walk source contains actual motion')
    return dict(frames=len(frames),weighted_bones=len(weighted),constant_channels=len(names))


def constant_walk_proof(appearance):
    if appearance.get('parts'):
        raise ValueError('Multipart constant-walk proof requires separate handling')
    proof = dict(model=appearance['model'],walk=appearance['animations']['walk'])
    proof.update({name+'_sha256':digest(proof[name]) for name in ['model','walk']})
    proof['source_check'] = validate_constant_walk(proof)
    return proof
