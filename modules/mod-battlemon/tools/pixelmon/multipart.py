"""Compose separately bound Pixelmon meshes without normalizing their parts independently."""
from pathlib import Path

import numpy as np
from PIL import Image


def texture_layout(paths):
    textures = list(dict.fromkeys(str(p) for p in paths))
    columns = 1 << (len(textures)-1).bit_length()
    if columns > 4:
        raise ValueError('Multipart atlas exceeds four textures')
    return textures, columns


def compose(meshes, texture_paths):
    if not meshes or len(meshes) != len(texture_paths):
        raise ValueError('Multipart mesh/texture count mismatch')
    textures, columns = texture_layout(texture_paths)
    standing = np.array([m['standing_bounds'] for m in meshes])
    ground = float(standing[:, 0, 2].min())
    height = float(standing[:, 1, 2].max()-ground)
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Invalid multipart standing height')
    scale = 1/height
    shift = np.array([0., 0., -ground*scale])
    vertices, weights, triangles, bones = [], [], [], []
    translations = [[] for _ in meshes[0]['sequences']]
    rotations = [[] for _ in translations]
    bounds = [[] for _ in translations]
    vertex_offset = 0
    for part, (mesh, texture) in enumerate(zip(meshes, texture_paths)):
        used = sorted({b for links in mesh['weights'] for b, w in links if w > 0})
        remap = {b: len(bones)+i for i, b in enumerate(used)}
        bones.extend((f'part{part}:{mesh["bones"][b][0]}', -1) for b in used)
        v = mesh['vertices'].copy()
        v[:, :3] = v[:, :3]*scale+shift
        if len(textures) > 1:
            if np.any(v[:, 6:8] < -1e-6) or np.any(v[:, 6:8] > 1+1e-6):
                raise ValueError('Multipart atlas requires non-wrapping source UVs')
            # Match the atlas' duplicated border: 1/32 on each side of a tile.
            v[:, 6] = (textures.index(str(texture))+1/32+v[:, 6]*15/16)/columns
            v[:, 7] = 1/32+v[:, 7]*15/16
        vertices.append(v)
        weights.extend([[(remap[b], w) for b, w in links if w > 0] for links in mesh['weights']])
        triangles.extend(index+vertex_offset for index in mesh['triangles'])
        vertex_offset += len(v)
        if len(mesh['sequences']) != len(translations):
            raise ValueError('Multipart sequence count mismatch')
        for i, (seq, reference) in enumerate(zip(mesh['sequences'], meshes[0]['sequences'])):
            if (seq['id'] != reference['id'] or seq['duration'] != reference['duration']
                    or not np.array_equal(seq['times'], reference['times'])):
                raise ValueError('Multipart animation timing mismatch')
            q = seq['rotations'][:, used]
            q = q/np.linalg.norm(q, axis=-1, keepdims=True)
            x, y, z, w = np.moveaxis(q, -1, 0)
            rotated_z = np.stack([2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y)], axis=-1)
            # C M C^-1: preserve every part's animation in the common grounded coordinate system.
            translations[i].append(seq['translations'][:, used]*scale+shift-rotated_z*shift[2])
            rotations[i].append(q)
            bounds[i].append(np.array(seq['bounds'])*scale+shift)
    if len(bones) > 256 or vertex_offset > 65535 or len(triangles) > 65535:
        raise ValueError('Multipart mesh exceeds M2 bone/vertex/index limits')
    sequences = []
    for i, reference in enumerate(meshes[0]['sequences']):
        boxes = np.array(bounds[i])
        sequences.append(dict(reference, translations=np.concatenate(translations[i], axis=1),
                              rotations=np.concatenate(rotations[i], axis=1),
                              bounds=(boxes[:, 0].min(axis=0), boxes[:, 1].max(axis=0))))
    boxes = np.array([s['bounds'] for s in sequences])
    return dict(vertices=np.concatenate(vertices), weights=weights, triangles=triangles, bones=bones,
                sequences=sequences, bounds=(boxes[:, 0].min(axis=0), boxes[:, 1].max(axis=0)),
                skinning_error=max(m['skinning_error'] for m in meshes)*scale,
                max_dropped_weight=max(m['max_dropped_weight'] for m in meshes),
                part_count=len(meshes),
                binding_notes=[f'part{i}:{note}' for i, m in enumerate(meshes)
                               for note in m.get('binding_notes', [])])


def make_atlas(paths, destination):
    textures, columns = texture_layout(paths)
    if len(textures) == 1:
        return Path(textures[0])
    images = [Image.open(p).convert('RGBA') for p in textures]
    largest = max(max(im.size) for im in images)
    # Reserve duplicated edge texels without reducing the source's pixel density.
    needed = max(32, (largest*16+14)//15)
    tile = 1 << (needed-1).bit_length()
    if tile*columns > 4096:
        raise ValueError('Multipart atlas exceeds 4096 pixels')
    margin = tile//32
    inner = tile-2*margin
    atlas = Image.new('RGBA', (tile*columns, tile))
    for index, im in enumerate(images):
        pixels = np.array(im.resize((inner, inner), Image.Resampling.LANCZOS))
        padded = np.pad(pixels, ((margin, margin), (margin, margin), (0, 0)), mode='edge')
        atlas.paste(Image.fromarray(padded), (index*tile, 0))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(destination)
    return destination
