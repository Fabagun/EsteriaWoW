"""Partition WotLK draw sections into compact palettes that fit D3D9 vertex shader constants."""
import numpy as np

# WotLK's bone upload starts at constant register 31 and consumes three registers per bone.
# A 256-register device cannot accept a 79-bone draw. Use the standard 64-bone skin tier.
MAX_SECTION_BONES = 64


def partition(mesh):
    triangles = np.asarray(mesh['triangles']).reshape(-1, 3)
    groups, faces, palette = [], [], set()
    for triangle in triangles:
        needed = {bone for vertex in triangle for bone, weight in mesh['weights'][vertex] if weight > 0}
        if not needed or len(needed) > MAX_SECTION_BONES:
            raise ValueError('Triangle exceeds the section bone budget')
        if faces and len(palette | needed) > MAX_SECTION_BONES:
            groups.append((faces, sorted(palette)))
            faces, palette = [], set()
        faces.append(triangle)
        palette.update(needed)
    if faces:
        groups.append((faces, sorted(palette)))
    vertices, weights, indices, combos, properties, sections, original = [], [], [], [], [], [], []
    for faces, palette in groups:
        remap, local = {}, {bone: i for i, bone in enumerate(palette)}
        start_vertex, start_index, start_bone = len(vertices), len(indices), len(combos)
        combos.extend(palette)
        for triangle in faces:
            for source in triangle:
                source = int(source)
                if source not in remap:
                    remap[source] = len(vertices)
                    vertices.append(mesh['vertices'][source])
                    links = mesh['weights'][source]
                    weights.append(links)
                    properties.append([local[b] if w > 0 else 0 for b, w in links]+[0]*(4-len(links)))
                    original.append(source)
                indices.append(remap[source])
        sections.append(dict(vertex_start=start_vertex, vertex_count=len(vertices)-start_vertex,
                             index_start=start_index, index_count=len(indices)-start_index,
                             bone_start=start_bone, bone_count=len(palette),
                             influences=max(len(w) for w in weights[start_vertex:])))
    if not sections or max(len(vertices), len(indices), len(combos)) > 65535:
        raise ValueError('Partitioned skin exceeds 16-bit address limits')
    return dict(vertices=np.array(vertices), weights=weights, triangles=indices, combos=combos,
                properties=properties, sections=sections, original=original)
