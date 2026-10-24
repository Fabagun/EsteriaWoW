"""Pixelmon 9.4 SMDModelLoader weights and homogeneous vertex-shader reference.

Source buildMesh keeps four strongest links (stable ties), optionally normalizes
below .975, and cel.vsh preserves homogeneous W through World/View/Projection.
This is the displayed four-weight surface, not unlimited raw BMD influences.
"""
import numpy as np


def shader_weights(links):
    links = [(int(b), np.float32(w)) for b, w in links]
    if any(not np.isfinite(w) or w < 0 for _, w in links):
        raise ValueError('Invalid source weight')
    if len(links) > 4:
        links = sorted(links, key=lambda item: -float(item[1]))[:4]
    if not links:
        links = [(0, np.float32(1))]
    total = np.float32(0)
    for _, weight in links:
        total = np.float32(total + weight)
    if not total > 0:
        raise ValueError('Source weights have zero sum')
    if float(total) < .975:
        factor = np.float32(1) / total
        links = [(bone, np.float32(weight * factor)) for bone, weight in links]
    return links


def source_positions(vertices, raw_weights, transforms):
    # Independently accumulate the actual four shader inputs, including their W.
    positions = np.c_[vertices[:, :3], np.ones(len(vertices))]
    selected = [shader_weights(links) for links in raw_weights]
    result = np.zeros((len(transforms), len(vertices), 4))
    for bone in range(transforms.shape[1]):
        weights = np.array([sum(float(w) for b, w in links if b == bone) for links in selected])
        if np.any(weights):
            result += np.einsum('fij,vj->fvi', transforms[:, bone], positions) * weights[None,:,None]
    if not np.isfinite(result).all() or np.any(result[:,:,3] <= 0):
        raise ValueError('Invalid source homogeneous position')
    return result[:,:,:3] / result[:,:,3,None]
