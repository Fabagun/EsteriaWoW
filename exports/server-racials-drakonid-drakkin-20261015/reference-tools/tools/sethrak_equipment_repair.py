"""Prepare Sethrak's running landing and player equipment assets on isolated copies."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import os
import shutil
from datetime import datetime

from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin
from PIL import Image

import sethrak_race_pack as race
import creature_animation_repair as animation
from sethrak_body_regions import body_uvs, collar_height

STAGE = Path(r'C:\Users\Zach\.codex\tmp\sethrak-equipment')
BLENDER = Path(r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
NATIVE = Path(r'C:\Users\Zach\.codex\tmp\sethrak-gear')


def use_running_landing(model):
    """Resolve running touchdown to the model's own run graph, including its events and loop flags."""
    run = animation.sequence(model, 5)
    landing = next(i for i, seq in enumerate(model.sequences) if seq['id'] == 187 and not seq['variation_index'])
    replacement = copy.deepcopy(model.sequences[run])
    replacement.update(id=187, variation_index=0, variation_next=-1, alias_next=run,
                       flags=(replacement['flags'] | 0x40 | 0x20))
    model.sequences[landing] = replacement
    for track in model.tracks():
        if track.global_sequence >= 0:
            continue
        animation.per_sequence(track, model)
        track.timestamps[landing] = copy.deepcopy(track.timestamps[run])
        if hasattr(track, 'values'):
            track.values[landing] = copy.deepcopy(track.values[run])
    return {'animation': 187, 'alias_animation': 5, 'alias_index': run,
            'duration': replacement['duration'], 'movespeed': replacement['movespeed']}


def check_landing(before, after):
    run = animation.sequence(after, 5)
    landing = next(i for i, seq in enumerate(after.sequences) if seq['id'] == 187)
    assert after.sequences[landing]['flags'] & 0x40
    assert animation.sequence(after, 187) == run
    assert after.sequences[landing]['movespeed'] == after.sequences[run]['movespeed']
    assert len(after.sequences) == len(before.sequences)
    for i, (old, new) in enumerate(zip(before.sequences, after.sequences, strict=True)):
        if i != landing:
            assert old == new
    for old, new in zip(before.tracks(), after.tracks(), strict=True):
        if old.global_sequence >= 0:
            assert old.timestamps == new.timestamps
            if hasattr(old, 'values'):
                assert old.values == new.values
            continue
        for i in range(len(before.sequences)):
            if i < len(old.timestamps) and i != landing:
                assert old.timestamps[i] == new.timestamps[i]
                if hasattr(old, 'values'):
                    assert old.values[i] == new.values[i]
        assert new.timestamps[landing] == new.timestamps[run]
        if hasattr(new, 'values'):
            assert new.values[landing] == new.values[run]


def prepare_landing():
    manifest = race.p.load_manifest('sethrak')
    deployment = race.p.load_json(race.STAGE / 'deployment.json')
    source_record = next(r for r in deployment['files'] if r['target'].lower().endswith('patch-j.mpq'))
    live = Path(source_record['target'])
    assert race.p.sha256(live) == source_record['after_sha256'], 'Installed Sethrak archive changed'
    before_dir = STAGE / 'before'
    before_dir.mkdir(parents=True, exist_ok=True)
    report = {'status': 'landing_staged', 'models': {}, 'installed_archive_sha256': source_record['after_sha256']}
    for sex, info in manifest['models'].items():
        key = info['model_path']
        data = race.animations.local(race.STAGE / 'assets', key).read_bytes()
        before = parse_m2(data)
        model = copy.deepcopy(before)
        change = use_running_landing(model)
        encoded = write_md20(model)
        after = parse_m2(encoded)
        check_landing(before, after)
        race.animations.check_model(after, encoded)
        assert before.vertices == after.vertices and before.bone_combos == after.bone_combos
        path = race.animations.local(STAGE / 'landing', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        race.c.immutable(before_dir / (sex + '.m2'), data)
        skin_key = key[:-3] + '00.skin'
        skin = race.animations.local(race.STAGE / 'assets', skin_key).read_bytes()
        race.c.immutable(before_dir / (sex + '00.skin'), skin)
        report['models'][sex] = {'path': key, 'before_sha256': hashlib.sha256(data).hexdigest(),
                                'after_sha256': hashlib.sha256(encoded).hexdigest(), **change}
        print('PASS', sex, 'running landing uses existing run; takeoff/air/standing landing retained', flush=True)
    race.save(STAGE / 'landing-report.json', report)


def vertex_record(model, index):
    data = model.vertices[index * 48:(index + 1) * 48]
    return {'position': list(struct.unpack_from('<3f', data)), 'uv': list(struct.unpack_from('<2f', data, 32)),
            'normal': list(struct.unpack_from('<3f', data, 20)), 'weights': list(data[12:16]),
            'bones': list(data[16:20]), 'index': index}


def mesh_triangles(skin, row):
    start = race.visual.u16(row, 8) | race.visual.u16(row, 2) << 16
    return [tuple(skin.vertices[i] for i in skin.indices[at:at + 3])
            for at in range(start, start + race.visual.u16(row, 10), 3)]


def descendants(model, root):
    result = {root}
    for _ in model.bones:
        new = {i for i, bone in enumerate(model.bones) if bone['parent_bone'] in result}
        if new <= result:
            return result
        result.update(new)
    raise ValueError('Cyclic target bone hierarchy')


def export_body_work():
    """Pin fitted player donors and export only the body work needed by Blender's UV/bake tools."""
    manifest = race.p.load_manifest('sethrak')
    files = race.p.ClientFiles(str(race.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for gender, sex in enumerate(('male', 'female')):
            model = parse_m2((STAGE / 'before' / (sex + '.m2')).read_bytes())
            skin = parse_skin((STAGE / 'before' / (sex + '00.skin')).read_bytes())
            key = f'Character\\Draenei2\\{sex.title()}\\Draenei{sex.title()}2.m2'
            source_data, provider = files.find(key)
            source_skin_data, _ = files.find(key[:-3] + '00.skin')
            race.c.immutable(STAGE / 'donors' / (sex + '.m2'), source_data)
            race.c.immutable(STAGE / 'donors' / (sex + '00.skin'), source_skin_data)
            donor, donor_skin = parse_m2(source_data), parse_skin(source_skin_data)
            human_key = f'Character\\Human2\\{sex.title()}\\Human{sex.title()}2.m2'
            human_data, _ = files.find(human_key)
            race.c.immutable(STAGE / 'donors' / ('human-' + sex + '.m2'), human_data)
            by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}

            def target_bone(index):
                visited = set()
                while index >= 0 and index not in visited:
                    visited.add(index)
                    crc = donor.bones[index]['bone_name_crc']
                    if crc in by_crc:
                        return by_crc[crc]
                    index = donor.bones[index]['parent_bone']
                raise ValueError('Equipment donor has no compatible parent bone')

            fitted = []
            for i in range(donor.vertex_count):
                v = vertex_record(donor, i)
                original = list(v['position'])
                for slot, weight in enumerate(v['weights']):
                    if not weight:
                        continue
                    source_bone = donor.bones[v['bones'][slot]]
                    target = target_bone(v['bones'][slot])
                    v['bones'][slot] = target
                    for axis in range(3):
                        v['position'][axis] += weight / 255 * (
                            model.bones[target]['pivot'][axis] - source_bone['pivot'][axis])
                fitted.append(v)
            # Preserve the distinctive head and tail on their original skin UVs.
            protected = descendants(model, model.key_bone_lookup[41])
            protected |= descendants(model, model.key_bone_lookup[59])
            protected |= descendants(model, model.key_bone_lookup[60])
            collar = max(model.bones[model.key_bone_lookup[i]]['pivot'][2] for i in (0, 1)) + 0.02
            body, kept = [], []
            for index, row in enumerate(skin.submeshes):
                batches = [b for b in skin.batches if race.visual.u16(b, 4) == index]
                body_material = any(
                    model.textures[model.texture_combos[race.visual.u16(b, 16)]]['type'] == 11
                    or 'snakeloa_1_body' in model.textures[model.texture_combos[race.visual.u16(b, 16)]]['filename']
                    for b in batches)
                if not body_material:
                    continue
                for tri in mesh_triangles(skin, row):
                    weights = sum(sum(model.vertices[v * 48 + 12 + j]
                                      for j in range(4) if model.vertices[v * 48 + 16 + j] in protected)
                                  for v in tri)
                    above_collar = any(
                        struct.unpack_from('<f', model.vertices, v * 48 + 8)[0]
                        > collar_height(model, struct.unpack_from('<3f', model.vertices, v * 48), collar)
                        for v in tri)
                    (kept if weights >= 255 or above_collar else body).append(tri)
            assert body and kept
            body_meshes, equipment = [], []
            for index, row in enumerate(donor_skin.submeshes):
                batches = [b for b in donor_skin.batches if race.visual.u16(b, 4) == index]
                types = {donor.textures[donor.texture_combos[race.visual.u16(b, 16)]]['type'] for b in batches}
                geoset = race.visual.u16(row, 0)
                if geoset == 0 and types == {1}:
                    body_meshes.extend(mesh_triangles(donor_skin, row))
                elif ((400 <= geoset < 1600 or 1800 <= geoset < 1900) and types <= {1, 2}):
                    equipment.append({'geoset': geoset, 'triangles': mesh_triangles(donor_skin, row),
                                      'texture_type': next(iter(types))})
            assert body_meshes and equipment
            pngs = []
            sources = manifest['appearance']['skin_textures'] if gender == 0 else ['snakeloa_1_body_blue']
            for color, stem in enumerate(sources):
                directory = 'sethrak_melee' if gender == 0 else 'snakeloa'
                path = race.animations.local(race.animations.OUT / 'patch-root',
                    race.animations.PREFIX + 'textures\\creature\\' + directory + '\\' + stem + '.blp')
                image = race.p.Blp.parse(path.read_bytes()).decode_level(0)
                target = STAGE / 'source-images' / (sex + '-' + str(color) + '.png')
                target.parent.mkdir(parents=True, exist_ok=True)
                Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(target)
                pngs.append(str(target))
            region_uvs = body_uvs(model, body, collar)
            race.save(STAGE / (sex + '-body-work.json'), {
                'sex': sex, 'target': [vertex_record(model, i) for i in range(model.vertex_count)],
                'body': body, 'original_only': kept, 'donor': fitted, 'donor_body': body_meshes,
                'equipment': equipment, 'skin_sources': pngs, 'donor_provider': provider,
                'region_uvs': region_uvs,
                'donor_sha256': hashlib.sha256(source_data).hexdigest()})
            print('EXPORTED', sex, len(body), 'body triangles,', len(equipment), 'equipment geosets', flush=True)
    finally:
        files.close()


def packed_skin(model, meshes):
    """Share identical armor triangles without changing their geometry; stay below Wrath's index boundary."""
    identity, vertices, mapping = {}, bytearray(), []
    for at in range(0, len(model.vertices), 48):
        vertex = model.vertices[at:at + 48]
        if vertex not in identity:
            identity[vertex] = len(vertices) // 48
            vertices.extend(vertex)
        mapping.append(identity[vertex])
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    for mesh in meshes:
        mesh['triangles'] = [tuple(mapping[i] for i in tri) for tri in mesh['triangles']]

    def used_bones(triangles):
        return {model.vertices[v * 48 + 16 + slot] for tri in triangles for v in tri for slot in range(4)
                if model.vertices[v * 48 + 12 + slot]}

    armor_bones = used_bones([tri for mesh in meshes if mesh['family'] == 'armor' for tri in mesh['triangles']])
    if len(armor_bones) > 75:
        raise ValueError(f'Fitted armor exceeds a shared native palette: {len(armor_bones)} bones')
    chunks = []
    for mesh in meshes:
        if mesh['family'] == 'armor':
            chunks.append({**mesh, 'palette': sorted(armor_bones)})
            continue
        triangles, bones = [], set()
        for tri in mesh['triangles']:
            needed = used_bones([tri])
            if triangles and len(bones | needed) > 75:
                chunks.append({**mesh, 'triangles': triangles, 'palette': sorted(bones)})
                triangles, bones = [], set()
            triangles.append(tri)
            bones.update(needed)
        if triangles:
            chunks.append({**mesh, 'triangles': triangles, 'palette': sorted(bones)})
    output = Skin(bone_count_max=75)
    model.bone_combos = []
    palettes, lookups, triangles = {}, {}, {}
    for mesh in chunks:
        palette = tuple(mesh['palette'])
        if palette not in palettes:
            palettes[palette] = len(model.bone_combos)
            model.bone_combos.extend(palette)
        local_bones = {bone: index for index, bone in enumerate(palette)}
        positions = []
        for tri in mesh['triangles']:
            key = (palette, tri)
            if key not in triangles:
                triangles[key] = len(output.indices)
                for vertex in tri:
                    lookup = (palette, vertex)
                    if lookup not in lookups:
                        lookups[lookup] = len(output.vertices)
                        output.vertices.append(vertex)
                        at = vertex * 48
                        output.bones += bytes(local_bones[model.vertices[at + 16 + i]]
                                              if model.vertices[at + 12 + i] else 0 for i in range(4))
                    output.indices.append(lookups[lookup])
            positions.append(triangles[key])
        runs = []
        for start in sorted(set(positions)):
            if runs and runs[-1][0] + runs[-1][1] == start:
                runs[-1][1] += 3
            else:
                runs.append([start, 3])
        for start, count in runs:
            row = bytearray(mesh['row'])
            used = output.indices[start:start + count]
            for offset, value in ((0, mesh['geoset']), (2, 0), (4, min(used)),
                                  (6, max(used) - min(used) + 1), (8, start), (10, count),
                                  (12, len(palette)), (14, palettes[palette])):
                race.visual.patch16(row, offset, value)
            index = len(output.submeshes)
            output.submeshes.append(bytes(row))
            for original in mesh['batches']:
                batch = bytearray(original)
                race.visual.patch16(batch, 4, index)
                race.visual.patch16(batch, 6, index)
                output.batches.append(bytes(batch))
    if len(output.indices) > 65535 or len(output.vertices) > 65535 or len(output.submeshes) > 4096:
        raise ValueError(f'Equipment pack exceeds native capacity: {len(output.indices)} indices, '
                         f'{len(output.vertices)} vertices, {len(output.submeshes)} meshes')
    return output


def prepare_equipment():
    manifest = race.p.load_manifest('sethrak')
    report = {'status': 'equipment_prepared', 'models': {}, 'assets': {}}
    for sex, info in manifest['models'].items():
        work = race.p.load_json(STAGE / (sex + '-body-work.json'))
        fitted_path = STAGE / (sex + '-equipment-fit.json')
        if fitted_path.exists():
            fitted = race.p.load_json(fitted_path)
            for index, point in fitted.items():
                work['donor'][int(index)]['position'] = point
        uv = race.p.load_json(STAGE / (sex + '-body-uv.json'))
        model = parse_m2(race.animations.local(STAGE / 'landing', info['model_path']).read_bytes())
        skin = parse_skin((STAGE / 'before' / (sex + '00.skin')).read_bytes())
        donor = parse_m2((STAGE / 'donors' / (sex + '.m2')).read_bytes())
        donor_skin = parse_skin((STAGE / 'donors' / (sex + '00.skin')).read_bytes())
        body_uv = {tuple(tri): uv[i * 3:i * 3 + 3] for i, tri in enumerate(work['body'])}
        vertices = bytearray(model.vertices)
        body_texture = len(model.textures)
        model.textures.append({'type': 1, 'flags': 0, 'filename': ''})
        body_combo = len(model.texture_combos)
        model.texture_combos.append(body_texture)
        material = len(model.materials)
        model.materials.append({'flags': 0, 'blending_mode': 0})
        body_batch = struct.pack('<12H', 0, 0, 0, 0, 65535, material, 0, 1, body_combo, 0, 0, 0)
        remap_uv, meshes = {}, []
        for index, row in enumerate(skin.submeshes):
            batches = [b for b in skin.batches if race.visual.u16(b, 4) == index]
            base, clothing = [], []
            for tri in mesh_triangles(skin, row):
                if tri not in body_uv:
                    base.append(tri)
                    continue
                converted = []
                for vertex, new_uv in zip(tri, body_uv[tri], strict=True):
                    key = (vertex, *[round(v, 7) for v in new_uv])
                    if key not in remap_uv:
                        data = bytearray(model.vertices[vertex * 48:(vertex + 1) * 48])
                        struct.pack_into('<2f', data, 32, *new_uv)
                        remap_uv[key] = len(vertices) // 48
                        vertices.extend(data)
                    converted.append(remap_uv[key])
                # The body stays visible even when bulk leggings disable the default leg selectors.
                clothing.append(tuple(converted))
            armor = any(model.textures[model.texture_combos[race.visual.u16(b, 16)]]['type'] == 12
                        or 'snakeloa_2_armor' in
                        model.textures[model.texture_combos[race.visual.u16(b, 16)]]['filename']
                        or 'snakeloa_fx2' in model.textures[model.texture_combos[race.visual.u16(b, 16)]]['filename']
                        for b in batches)
            geoset = race.visual.u16(row, 0)
            if armor:
                geoset = 21000 + geoset
            elif geoset and not clothing:
                geoset = 20000 + geoset
            if base:
                meshes.append({'row': row, 'batches': batches, 'triangles': base, 'geoset': geoset,
                               'family': 'armor' if armor else 'body'})
            if clothing:
                meshes.append({'row': row, 'batches': [body_batch], 'triangles': clothing,
                               'geoset': 0, 'family': 'body'})
        donor_map = {}
        cape_texture = None
        for equipment in work['equipment']:
            if equipment['geoset'] // 100 == 15:
                continue
            if equipment['geoset'] in (401, 1301) or equipment['geoset'] // 100 in (5, 9, 11):
                continue  # Preserve Sethrak's own hands, feet and legs in the default equipment selectors.
            for vertex in {v for tri in equipment['triangles'] for v in tri}:
                if vertex in donor_map:
                    continue
                source = work['donor'][vertex]
                data = bytearray(donor.vertices[vertex * 48:(vertex + 1) * 48])
                struct.pack_into('<3f', data, 0, *source['position'])
                data[16:20] = bytes(source['bones'])
                donor_map[vertex] = len(vertices) // 48
                vertices.extend(data)
        for equipment in work['equipment']:
            if equipment['geoset'] // 100 == 15:
                continue
            if equipment['geoset'] in (401, 1301) or equipment['geoset'] // 100 in (5, 9, 11):
                continue
            index = next(i for i, row in enumerate(donor_skin.submeshes)
                         if race.visual.u16(row, 0) == equipment['geoset'])
            row = bytearray(donor_skin.submeshes[index])
            row[18:20] = b'\0\0'
            texture = body_texture
            if equipment['texture_type'] == 2:
                if cape_texture is None:
                    cape_texture = len(model.textures)
                    model.textures.append({'type': 2, 'flags': 0, 'filename': ''})
                texture = cape_texture
            combo = len(model.texture_combos)
            model.texture_combos.append(texture)
            batch = struct.pack('<12H', 16, 0, 0, 0, 65535, material, 0, 1, combo, 0, 0, 0)
            meshes.append({'row': bytes(row), 'batches': [batch], 'geoset': equipment['geoset'],
                           'triangles': [tuple(donor_map[v] for v in tri) for tri in equipment['triangles']],
                           'family': 'armor'})
        cape_texture = len(model.textures)
        model.textures.append({'type': 2, 'flags': 0, 'filename': ''})
        cape_combo = len(model.texture_combos)
        model.texture_combos.append(cape_texture)
        cape_material = len(model.materials)
        model.materials.append({'flags': 4, 'blending_mode': 1})
        top = max(model.bones[model.key_bone_lookup[i]]['pivot'][2] for i in (0, 1)) + 0.03
        spine = model.key_bone_lookup[4]
        back = model.bones[spine]['pivot'][0] - 0.28
        for style, bottom in zip(range(1502, 1507), (0.95, 0.75, 0.55, 0.3, 0.12), strict=True):
            start = len(vertices) // 48
            for point, uv in (((back, -0.34, top), (0.0, 0.0)), ((back, 0.34, top), (1.0, 0.0)),
                              ((back - 0.03, -0.4, bottom), (0.0, 1.0)),
                              ((back - 0.03, 0.4, bottom), (1.0, 1.0))):
                vertex = bytearray(48)
                struct.pack_into('<3f', vertex, 0, *point)
                vertex[12] = 255
                vertex[16] = spine
                struct.pack_into('<3f', vertex, 20, -1, 0, 0)
                struct.pack_into('<2f', vertex, 32, *uv)
                vertices.extend(vertex)
            batch = struct.pack('<12H', 16, 0, 0, 0, 65535, cape_material, 0, 1, cape_combo, 0, 0, 0)
            row = bytearray(skin.submeshes[0])
            row[18:20] = struct.pack('<H', spine)
            meshes.append({'row': bytes(row), 'batches': [batch], 'geoset': style,
                           'triangles': [(start, start + 1, start + 2), (start + 2, start + 1, start + 3)],
                           'family': 'armor'})
        human = parse_m2((STAGE / 'donors' / ('human-' + sex + '.m2')).read_bytes())
        repair_attachment_points(model, donor, human)
        model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
        model.replacable_texture_lookup = [65535] * 16
        for index, texture in enumerate(model.textures):
            if texture['type']:
                model.replacable_texture_lookup[texture['type']] = index
        compact = packed_skin(model, meshes)
        encoded, encoded_skin = write_md20(model), write_skin(compact)
        path = race.animations.local(STAGE / 'assets', info['model_path'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        path.with_name(path.stem + '00.skin').write_bytes(encoded_skin)
        rebuilt = parse_m2(encoded)
        race.animations.check_model(rebuilt, encoded)
        report['models'][sex] = {'path': info['model_path'], 'vertices': model.vertex_count,
                                'indices': len(compact.indices), 'meshes': len(compact.submeshes),
                                'body_triangles': len(work['body']),
                                'equipment_geosets': sorted({race.visual.u16(row, 0)
                                                            for row in compact.submeshes
                                                            if 400 <= race.visual.u16(row, 0) < 1900})}
        print('PACKED', sex, report['models'][sex], flush=True)
    race.save(STAGE / 'equipment-report.json', report)


def repair_attachment_points(model, donor, human, bone_map=None):
    """Use the authored player attachment frames on matching arm/shoulder/torso parents."""
    by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    if bone_map:
        by_crc.update({donor.bones[source]['bone_name_crc']: target for source, target in bone_map.items()})
    for identifier in (0, 5, 6, 28):
        source_model = human if identifier in (5, 6) else donor
        source = next(a for a in source_model.attachments if a['id'] == identifier)
        auxiliary = source_model.bones[source['bone']]
        parent_index = auxiliary['parent_bone']
        while source_model.bones[parent_index]['bone_name_crc'] not in by_crc:
            parent_index = source_model.bones[parent_index]['parent_bone']
            if parent_index < 0:
                raise ValueError('Player attachment has no matching target ancestor')
        parent = source_model.bones[parent_index]
        target = by_crc[parent['bone_name_crc']]
        offset = tuple(model.bones[target]['pivot'][i] - parent['pivot'][i] for i in range(3))
        bone = copy.deepcopy(auxiliary)
        bone['parent_bone'] = target
        bone['pivot'] = tuple(bone['pivot'][i] + offset[i] for i in range(3))
        for name in ('rotation', 'translation', 'scale'):
            track = bone[name]
            values = next((slot for slot in track.values if slot), [])
            if values and len(set(values)) != 1:
                raise ValueError('Attachment frame is not static: ' + str(identifier))
            track.global_sequence = -1
            track.external.clear()
            track.timestamps = [[0] if values else [] for _ in model.sequences]
            track.values = [[values[0]] if values else [] for _ in model.sequences]
            track.timestamp_spans = track.value_spans = [(0, 0)] * len(model.sequences)
        attached = copy.deepcopy(source)
        attached['bone'] = len(model.bones)
        attached['position'] = tuple(source['position'][i] + offset[i] for i in range(3))
        track = attached['animate_attached']
        track.global_sequence = -1
        track.timestamps = [[0] for _ in model.sequences]
        track.values = [[1] for _ in model.sequences]
        track.external.clear()
        track.timestamp_spans = track.value_spans = [(0, 0)] * len(model.sequences)
        model.bones.append(bone)
        existing = next((i for i, a in enumerate(model.attachments) if a['id'] == identifier), None)
        if existing is None:
            existing = len(model.attachments)
            model.attachments.append(attached)
        else:
            model.attachments[existing] = attached
        while len(model.attachment_lookup) <= identifier:
            model.attachment_lookup.append(65535)
        model.attachment_lookup[identifier] = existing
    assert len(model.bones) <= 256


def prepare_catalogs():
    from haranir_race_pack import lznt1

    manifest = race.p.load_manifest('sethrak')
    pinned = STAGE / 'before/EsteriaSethrak.bin'
    if not pinned.exists():
        race.c.immutable(pinned, (race.p.CLIENT_DEFAULT / 'EsteriaSethrak.bin').read_bytes())
    original = pinned.read_bytes()
    records = []
    for offset in range(12, len(original), 156):
        data = bytearray(original[offset:offset + 156])
        gender, kind, target, value = struct.unpack_from('<4I', data)
        if kind == 0:
            struct.pack_into('<4I', data, 0, gender, 2, 0, 21000 + value)
        records.append(bytes(data))

    def record(gender, kind, target, value, selectors=(), path=''):
        choices = [i | v << 16 for i, v in selectors]
        records.append(struct.pack('<7I', gender, kind, target, value,
            *(choices + [0xffffffff] * (3 - len(choices)))) + path.encode().ljust(128, b'\0'))

    record(1, 2, 0, 21000)  # Female armor originally shared the unconditional geoset with the base body.
    record(1, 2, 0, 20102)  # Keep the body's authored glow independently of its NPC armor.
    bank = bytearray(struct.pack('<4I', 0x31544845, 1, 0, 0))
    blob_count = 0
    for gender, sex in enumerate(('male', 'female')):
        count = manifest['appearance']['profiles'][str(gender)]['capacities'][0]
        for color in range(count):
            image = Image.open(STAGE / (sex + '-player-skin-' + str(color) + '.png')).convert('RGBA')
            source = Image.open(STAGE / 'source-images' / (sex + '-' + str(color) + '.png')).convert('RGBA')
            combined = Image.new('RGB', (max(source.width, image.width), source.height + image.height))
            combined.paste(source.convert('RGB'), (0, 0))
            combined.paste(image.convert('RGB'), (0, source.height))
            palette_image = combined.quantize(colors=256)
            image = image.convert('RGB').quantize(palette=palette_image).convert('RGBA')
            quantized = source.convert('RGB').quantize(palette=palette_image).convert('RGBA')
            image.save(STAGE / (sex + '-player-skin-' + str(color) + '.png'))
            quantized.save(STAGE / (sex + '-skin-shared-palette-' + str(color) + '.png'))
            from wotlkconv.blp.image import Image as BlpImage
            colors = palette_image.getpalette()
            palette = [tuple(colors[i:i + 3]) for i in range(0, 768, 3)]
            key = 'custom\\sethrak\\equipment\\skin-' + sex + '-' + str(color) + '.blp'
            payload = race.p._encode_wotlk_paletted(
                BlpImage(source.width, source.height, bytearray(quantized.tobytes())),
                palette, race.p.PaletteMapper(palette))
            path = race.animations.local(STAGE / 'assets', key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            if gender == 0:
                for index, data in enumerate(records):
                    fields = struct.unpack_from('<7I', data)
                    if fields[:3] == (0, 1, 11) and fields[4] == color << 16:
                        records[index] = data[:28] + key.encode().ljust(128, b'\0')
            else:
                model_path = race.animations.local(STAGE / 'assets', manifest['models'][sex]['model_path'])
                model = parse_m2(model_path.read_bytes())
                for texture in model.textures:
                    if 'snakeloa_1_body_blue' in texture['filename']:
                        texture['filename'] = key
                model_path.write_bytes(write_md20(model))
            packed = lznt1(image.tobytes())
            offset = len(bank)
            bank.extend(struct.pack('<3I', image.width, image.height, len(packed)) + packed)
            record(gender, 3, 0, offset, [(0, color)], '1:1')
            blob_count += 1
    struct.pack_into('<2I', bank, 8, blob_count, int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little'))
    (STAGE / 'EsteriaSethrakTextures.bin').write_bytes(bank)
    (STAGE / 'EsteriaSethrak.bin').write_bytes(struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records))
    geometry = (race.p.CLIENT_DEFAULT / 'EsteriaAppearanceGeometry.bin').read_bytes()
    snapshot = STAGE / 'before-revision' / (hashlib.sha256(geometry).hexdigest() + '-geometry.bin')
    race.c.immutable(snapshot, geometry)
    magic, version, count = struct.unpack_from('<3I', geometry)
    output, offset, changed = [], 12, set()
    by_key = {v['model_path'].lower(): v['model_path'] for v in manifest['models'].values()}
    for _ in range(count):
        key = geometry[offset:offset + 128].split(b'\0')[0].decode()
        length = struct.unpack_from('<I', geometry, offset + 128)[0]
        end = offset + 132 + length
        if key.lower() in by_key:
            skin = race.animations.local(STAGE / 'assets', by_key[key.lower()][:-3] + '00.skin').read_bytes()
            output.append(geometry[offset:offset + 128] + struct.pack('<I', len(skin)) + skin)
            changed.add(key.lower())
        else:
            output.append(geometry[offset:end])
        offset = end
    assert changed == set(by_key) and offset == len(geometry)
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(geometry[:12] + b''.join(output))
    print('PREPARED clothing material banks and two native geometry snapshots', flush=True)


def export_preview(plate_displays=(25749, 24513)):
    """Export the actual staged meshes and representative installed item textures for visual review."""
    manifest = race.p.load_manifest('sethrak')
    files = race.p.ClientFiles(str(race.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    regions = ('ArmUpperTexture', 'ArmLowerTexture', 'HandTexture', 'TorsoUpperTexture',
               'TorsoLowerTexture', 'LegUpperTexture', 'LegLowerTexture', 'FootTexture')
    # Wrath uses the 256x256 atlas scaled to the accepted 512x512 player textures.
    rects = ((0, 0, 256, 128), (0, 128, 256, 256), (0, 256, 256, 320), (256, 0, 512, 128),
             (256, 128, 512, 192), (256, 192, 512, 320), (256, 320, 512, 448), (256, 448, 512, 512))
    try:
        table = race.p.RawWdbc(files.find(race.p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        displays = {race.p._value(r, 0): r for r in table.records}
        for gender, sex in enumerate(('male', 'female')):
            textures = {}
            for kind, ids in (('shirt', [18924]), ('plate', plate_displays), ('robe', [15820])):
                atlas = Image.open(STAGE / (sex + '-player-skin-0.png')).convert('RGBA')
                for display in ids:
                    row = displays[display]
                    for field, directory, rect in zip(range(15, 23), regions, rects, strict=True):
                        stem = race.p._string(table.strings, race.p._value(row, field * 4)).decode()
                        if not stem:
                            continue
                        payload = None
                        for suffix in ('_U', '_M' if gender == 0 else '_F', '', '_F' if gender == 0 else '_M'):
                            key = 'Item\\TextureComponents\\' + directory + '\\' + stem + suffix + '.blp'
                            try:
                                payload = files.find(key)[0]
                                break
                            except FileNotFoundError:
                                continue
                        if payload is None:
                            raise FileNotFoundError('Preview item component is absent: ' + stem)
                        pixels = race.p.Blp.parse(payload).decode_level(0)
                        image = Image.frombytes('RGBA', (pixels.width, pixels.height), bytes(pixels.data))
                        image = image.resize((rect[2] - rect[0], rect[3] - rect[1]), Image.Resampling.LANCZOS)
                        atlas.alpha_composite(image, (rect[0], rect[1]))
                path = STAGE / (sex + '-preview-' + kind + '.png')
                atlas.save(path)
                textures[kind] = str(path)
            key = manifest['models'][sex]['model_path']
            model = parse_m2(race.animations.local(STAGE / 'assets', key).read_bytes())
            skin = parse_skin(race.animations.local(STAGE / 'assets', key[:-3] + '00.skin').read_bytes())
            bitmap_paths, meshes = {}, []
            for index, texture in enumerate(model.textures):
                if texture['type'] in (1, 2):
                    continue
                if texture['type'] == 11:
                    bitmap_paths[str(index)] = str(STAGE / (sex + '-skin-shared-palette-0.png'))
                    continue
                name = texture['filename']
                if texture['type'] == 12:
                    name = race.animations.PREFIX + 'textures\\creature\\sethrak_melee\\sethrak_melee_brown.blp'
                if not name:
                    continue
                path = race.animations.local(STAGE / 'assets', name)
                if not path.exists():
                    path = race.animations.local(race.animations.OUT / 'patch-root', name)
                pixels = race.p.Blp.parse(path.read_bytes()).decode_level(0)
                target = STAGE / (sex + '-texture-' + str(index) + '.png')
                Image.frombytes('RGBA', (pixels.width, pixels.height), bytes(pixels.data)).save(target)
                bitmap_paths[str(index)] = str(target)
            for index, row in enumerate(skin.submeshes):
                batches = [b for b in skin.batches if race.visual.u16(b, 4) == index]
                if not batches:
                    continue
                texture = model.texture_combos[race.visual.u16(batches[0], 16)]
                meshes.append({'geoset': race.visual.u16(row, 0), 'texture': texture,
                               'texture_type': model.textures[texture]['type'],
                               'triangles': mesh_triangles(skin, row)})
            race.save(STAGE / (sex + '-preview.json'), {'sex': sex,
                'vertices': [vertex_record(model, i) for i in range(model.vertex_count)], 'meshes': meshes,
                'textures': bitmap_paths, 'gear_textures': textures,
                'base_atlas': str(STAGE / (sex + '-player-skin-0.png'))})
    finally:
        files.close()


def stage_pack(include_native=True):
    from test_sethrak_equipment import check

    check()
    manifest = race.p.load_manifest('sethrak')
    updates = {}
    for info in manifest['models'].values():
        key = info['model_path']
        for name in (key, key[:-3] + '00.skin'):
            updates[name] = race.animations.local(STAGE / 'assets', name).read_bytes()
    for path in (STAGE / 'assets/custom/sethrak/equipment').glob('*.blp'):
        updates[str(race.p.PureWindowsPath(path.relative_to(STAGE / 'assets')))] = path.read_bytes()
    live = race.p.CLIENT_DEFAULT / race.ASSET_ARCHIVE
    previous = STAGE / 'last-install.json'
    expected = (race.p.load_json(previous)['changes'][0]['after_sha256'] if previous.exists()
                else race.p.load_json(STAGE / 'landing-report.json')['installed_archive_sha256'])
    assert race.p.sha256(live) == expected
    target = STAGE / 'pack' / race.ASSET_ARCHIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live, target)
    assert race.p.sha256(target) == expected
    storm = race.p.Storm(race.p.DLL_DEFAULT)
    storm.replace_archive_entries(target, updates)
    handle = storm.open_archive(target)
    try:
        for key, value in updates.items():
            assert storm.read(handle, key) == value
    finally:
        storm.dll.SFileCloseArchive(handle)
    relatives = [race.ASSET_ARCHIVE, Path('EsteriaAppearance.dll'), Path('EsteriaSethrak.bin'),
                 Path('EsteriaSethrakTextures.bin'), Path('EsteriaAppearanceGeometry.bin')]
    sources = [target, NATIVE / 'EsteriaAppearance.dll', STAGE / 'EsteriaSethrak.bin',
               STAGE / 'EsteriaSethrakTextures.bin', STAGE / 'EsteriaAppearanceGeometry.bin']
    if not include_native:
        del relatives[1]
        del sources[1]
    report = {'status': 'checked_awaiting_client_close', 'changes': [], 'native_tests_passed': True,
              'preview_directory': str(STAGE), 'server_changes': False,
              'native_helper_changed': include_native,
              'exe_sha256': race.p.sha256(race.p.CLIENT_DEFAULT / 'Wow.exe')}
    for relative, source in zip(relatives, sources, strict=True):
        report['changes'].append({'target': str(race.p.CLIENT_DEFAULT / relative), 'source': str(source),
            'before_sha256': race.p.sha256(race.p.CLIENT_DEFAULT / relative), 'after_sha256': race.p.sha256(source)})
    race.save(STAGE / 'pack-report.json', report)
    print('CHECKED deployment pack;', len(relatives), 'client files, no SQL/server/character changes', flush=True)


def install():
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any('"' + name + '"' in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW, Eclipse and MPQEditor before installing the checked equipment pack')
    report = race.p.load_json(STAGE / 'pack-report.json')
    assert report['status'] == 'checked_awaiting_client_close'
    assert race.p.sha256(race.p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    for record in report['changes']:
        assert race.p.sha256(Path(record['target'])) == record['before_sha256']
        assert race.p.sha256(Path(record['source'])) == record['after_sha256']
    backup = Path(r'C:\Users\Zach\.codex\backups') / ('sethrak-equipment-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True, exist_ok=False)
    for record in report['changes']:
        saved = backup / Path(record['target']).name
        shutil.copy2(record['target'], saved)
        assert race.p.sha256(saved) == record['before_sha256']
        record['backup'] = str(saved)
    race.save(backup / 'plan.json', report)
    try:
        for record in report['changes']:
            target = Path(record['target'])
            temporary = target.with_name(target.name + '.gear-next')
            if temporary.exists():
                raise FileExistsError(temporary)
            shutil.copy2(record['source'], temporary)
            assert race.p.sha256(temporary) == record['after_sha256']
            os.replace(temporary, target)
    except Exception:
        for record in report['changes']:
            shutil.copy2(record['backup'], record['target'])
        raise
    for record in report['changes']:
        assert race.p.sha256(Path(record['target'])) == record['after_sha256']
    assert race.p.sha256(race.p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    report.update(status='installed_awaiting_live_test', backup=str(backup))
    race.save(STAGE / 'last-install.json', report)
    race.save(backup / 'install.json', report)
    print('INSTALLED backed-up run-landing and equipment pack:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('landing', 'body', 'equipment', 'catalogs', 'preview',
                                         'stage', 'stage-fit', 'install'))
    args = parser.parse_args()
    if args.action == 'landing':
        prepare_landing()
    elif args.action == 'body':
        export_body_work()
    elif args.action == 'equipment':
        prepare_equipment()
    elif args.action == 'catalogs':
        prepare_catalogs()
    elif args.action == 'preview':
        export_preview()
    elif args.action == 'stage':
        stage_pack()
    elif args.action == 'stage-fit':
        stage_pack(include_native=False)
    else:
        install()
