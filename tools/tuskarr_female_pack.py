"""Stage the approved HD NPC female Tuskarr fallback, with an independent equipment fit.

Uses skin_expansion's pinned 15-texture acquisition. Never compiles, packs, installs, or applies SQL.
The original male and all saved appearances remain unchanged.
"""

import argparse
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import struct

import skin_expansion as s
import tarasek_equipment as equipment_pass
import sethrak_equipment_repair as equipment
import skyborne_visual_pack as visual
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin

WORK = s.WORK / 'tuskarr-female'
STAGE = WORK / 'stage'
MODEL = 'custom\\tuskarr\\native\\female\\tuskarrfemale.m2'
MODEL_ID, DISPLAY_ID = 120080, 60071
RETAIL = s.TUSKARR / 'output/patch-root/custom/tuskarr/character/tuskarr/tuskarrfemale_hd.m2'
REPAIRED = WORK / 'animation-repair/tuskarrfemale_hd.m2'
DONORS = Path('G:/RetroPorterWork/drakonid/donors/Character')
# Player animations are added by animations(); every later step reads the repaired model once it exists.
SOURCE = REPAIRED if REPAIRED.exists() else RETAIL
SKINS = s.FEMALE_SLOTS[0]
# These source groups provide complete skin anatomy, whiskers, tusks, brows and uncovered arms.
# Clothing/props in replacement slots 12/13 are deliberately excluded from the playable body.
BASE_GEOSETS = {0, 101, 202, 301, 501, 1101}
# The bare chest and crown are the type-12 half of geoset 0; they sample the same body atlas as the skin groups.
TORSO = 0


def animations():
    """Retarget the missing player actions from the best-matching proven player rig, keeping authored tracks."""
    import creature_animation_repair as motion
    import highmountain_complete_tracks as tracks
    import sethrak_animation_pack as checks

    original = visual.read_player_model(RETAIL)
    tracks.embed(original, RETAIL.parent, RETAIL.stem)
    missing = set(checks.ACTIONS) - {q['id'] for q in original.sequences}
    names = {b['bone_name_crc'] for b in original.bones if b['bone_name_crc']}
    candidates, donors = [], {}
    for path in DONORS.rglob('*.m2'):
        donor = visual.read_player_model(path)
        tracks.embed(donor, path.parent, path.stem)
        crcs = {b['bone_name_crc'] for b in donor.bones if b['bone_name_crc']}
        candidates.append({'path': str(path), 'matched_bones': len(names & crcs),
                           'missing': sorted(missing - {q['id'] for q in donor.sequences})})
        donors[str(path)] = donor
    selected = max((r for r in candidates if not r['missing']), key=lambda r: r['matched_bones'])
    model = copy.deepcopy(original)
    added = []
    for action in sorted(missing):
        added.append(motion.retarget(model, donors[selected['path']], action))
        model.sequences[-1].update(bounds_min=model.bounding_box[:3], bounds_max=model.bounding_box[3:],
                                   bounds_radius=model.bounding_sphere_radius)
    aliases = motion.repair_model('tuskarr_female', 1, model)['wrath_action_aliases']
    sockets = add_attachments(model)
    checks.tracks_equal(BoneTracks(original), BoneTracks(model, len(original.bones)), len(original.sequences))
    blob, separated = arrays_module().separate_bone_track_arrays(write_md20(model))
    rebuilt = parse_m2(blob)
    checks.check_model(rebuilt, blob)
    checks.tracks_equal(BoneTracks(original), BoneTracks(rebuilt, len(original.bones)), len(original.sequences))
    assert rebuilt.vertices == original.vertices
    REPAIRED.parent.mkdir(parents=True, exist_ok=True)
    REPAIRED.write_bytes(blob)
    s.t.save(WORK / 'animation-repair.json', {'model': str(REPAIRED), 'sha256': s.digest(blob),
        'original_sequences': len(original.sequences), 'sequences': len(rebuilt.sequences),
        'candidates': candidates, 'selected_donor': selected['path'], 'added_actions': added,
        'compatibility_aliases': aliases, 'attachments': sockets, 'authored_tracks_preserved': True, 'vertices_preserved': True,
        'shared_track_arrays_separated': separated, 'installed': False, 'live_accepted': False})
    print('Animation stage:', len(original.sequences), '->', len(rebuilt.sequences), 'sequences;',
          selected['matched_bones'], 'matching donor bones')


PLAYER = s.TUSKARR / 'integration/patch-root/custom/tuskarr/native/male/tuskarrmale.m2'


def add_attachments(model):
    """Add the player sockets the NPC lacks (shoulders, elbows, knees, hips) from the Tuskarr player rig.

    Each donor socket is a helper bone under a body bone; it is re-parented to the female bone with the same
    name CRC (nearest matching ancestor otherwise) and offset by the difference of the two parent pivots.
    """
    import highmountain_complete_tracks as tracks
    import creature_animation_repair as motion

    provider = visual.read_player_model(PLAYER)
    tracks.embed(provider, PLAYER.parent, PLAYER.stem)
    by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    existing = {a['id'] for a in model.attachments}
    base = motion.sequence(provider, 0)
    added = []
    for attachment in provider.attachments:
        if attachment['id'] in existing:
            continue
        donor_bone = provider.bones[attachment['bone']]
        parent = donor_bone['parent_bone']
        while parent >= 0 and provider.bones[parent]['bone_name_crc'] not in by_crc:
            parent = provider.bones[parent]['parent_bone']
        if parent < 0:
            # A parentless socket (such as the elbow anchor) is a root-space helper and keeps its position.
            assert donor_bone['parent_bone'] < 0, 'No matching parent bone for attachment %d' % attachment['id']
            target, offset, crc = -1, (0.0, 0.0, 0.0), 0
        else:
            source_parent = provider.bones[parent]
            target = by_crc[source_parent['bone_name_crc']]
            crc = source_parent['bone_name_crc']
            offset = tuple(model.bones[target]['pivot'][i] - source_parent['pivot'][i] for i in range(3))
        bone = copy.deepcopy(donor_bone)
        bone['parent_bone'] = target
        bone['pivot'] = tuple(bone['pivot'][i] + offset[i] for i in range(3))
        for name in ('translation', 'rotation', 'scale'):
            constant(bone[name], len(model.sequences), motion.keys(bone[name], base)[1])
        new = copy.deepcopy(attachment)
        enabled = new['animate_attached']
        constant(enabled, len(model.sequences), motion.keys(enabled, base)[1])
        new['bone'] = len(model.bones)
        new['position'] = tuple(new['position'][i] + offset[i] for i in range(3))
        model.bones.append(bone)
        model.attachments.append(new)
        while len(model.attachment_lookup) <= new['id']:
            model.attachment_lookup.append(65535)
        model.attachment_lookup[new['id']] = len(model.attachments) - 1
        added.append({'id': new['id'], 'parent_bone': target, 'matched_crc': crc})
    assert len(model.bones) <= 256, 'Additional sockets exceed the native bone index limit'
    return added


def constant(track, count, values):
    """Rest-pose track: the donor's first value on every sequence, no global clock."""
    track.global_sequence = -1
    track.external.clear()
    track.timestamps = [[0] for _ in range(count)] if values else [[] for _ in range(count)]
    if hasattr(track, 'values'):
        track.values = [[copy.deepcopy(values[0])] for _ in range(count)] if values else [[] for _ in range(count)]
        track.value_spans = [(0, 0)] * count
    track.timestamp_spans = [(0, 0)] * count


class BoneTracks:
    """Authored bone animation only: the retargeter appends $SHL/$SHR event tracks, which shifts model.tracks()."""

    def __init__(self, model, count=None):
        self.sequences = model.sequences
        self._tracks = [track for bone in model.bones[:count] for track in (
            bone['translation'], bone['rotation'], bone['scale'])]

    def tracks(self):
        return self._tracks


def arrays_module():
    import vrykul_female_pack as arrays
    return arrays


def source():
    import highmountain_complete_tracks as tracks

    model = visual.read_player_model(SOURCE)
    tracks.embed(model, SOURCE.parent, SOURCE.stem)
    assert not any(track.external for track in model.tracks())
    skin = parse_skin(RETAIL.with_name('tuskarrfemale_hd00.skin').read_bytes())
    selected, batches = [], []
    for index, row in enumerate(skin.submeshes):
        owned = [b for b in skin.batches if visual.u16(b, 4) == index]
        types = {model.textures[model.texture_combos[visual.u16(b, 16)]]['type'] for b in owned}
        geoset = visual.u16(row, 0)
        torso = geoset == TORSO and types == {12}
        if not torso and (geoset not in BASE_GEOSETS or types != {11}):
            continue
        new_index = len(selected)
        row = bytearray(row)
        visual.patch16(row, 0, 0)
        selected.append(bytes(row))
        # Use the diffuse skin only; the source's modern armor-reflection combiner is unsupported.
        batch = bytearray(owned[0])
        visual.patch16(batch, 2, 0)
        visual.patch16(batch, 4, new_index)
        visual.patch16(batch, 6, new_index)
        visual.patch16(batch, 14, 1)
        visual.patch16(batch, 18, 0)
        if torso:
            reference = next(b for b in skin.batches
                             if model.textures[model.texture_combos[visual.u16(b, 16)]]['type'] == 11)
            visual.patch16(batch, 10, visual.u16(reference, 10))
            visual.patch16(batch, 16, visual.u16(reference, 16))
        batches.append(bytes(batch))
    assert len(selected) == 7
    skin.submeshes, skin.batches = selected, batches
    model.texture_coord_combos[0] = 0
    return model, skin


@contextmanager
def fitting_context():
    """Reuse the proven garment fitter in this process with isolated female inputs and outputs."""
    previous = equipment_pass.WORK, equipment_pass.source
    equipment_pass.WORK, equipment_pass.source = WORK / 'equipment', source
    try:
        yield
    finally:
        equipment_pass.WORK, equipment_pass.source = previous


def fit_work():
    with fitting_context():
        equipment_pass.fit_work()


def prepare():
    from collections import defaultdict
    import numpy as np
    import saberon_equipment_fit as fitting
    import tarasek_cape as cape
    import vrykul_female_pack as arrays

    original, skin = source()
    model = copy.deepcopy(original)
    vertices, meshes = bytearray(model.vertices), []
    for index, row in enumerate(skin.submeshes):
        meshes.append({'row': row, 'batches': [b for b in skin.batches if visual.u16(b, 4) == index],
                       'geoset': 0, 'triangles': equipment.mesh_triangles(skin, row)})
    texture = len(model.textures)
    model.textures.append({'type': 14, 'flags': 0, 'filename': ''})
    combo = len(model.texture_combos)
    model.texture_combos.append(texture)
    material = len(model.materials)
    model.materials.append({'flags': 16, 'blending_mode': 2})
    batch = struct.pack('<12H', 0, 0, 0, 0, 65535, material, 0, 1, combo, 0, 0, 0)
    body = [tri for mesh in meshes for tri in mesh['triangles']]
    normals = fitting.surface_normals(model, body)
    regional, mapped = defaultdict(list), {}
    for tri in body:
        result = equipment_pass.region_uv(model, tri)
        if result is None:
            continue
        region, uvs = result
        face = []
        for v, uv in zip(tri, uvs, strict=True):
            identity = (v, *[round(x, 7) for x in uv])
            if identity not in mapped:
                record = bytearray(original.vertices[v * 48:(v + 1) * 48])
                point, normal = equipment.vertex_record(original, v)['position'], normals[v]
                struct.pack_into('<3f', record, 0, *[p + n * .012 for p, n in zip(point, normal)])
                struct.pack_into('<3f', record, 20, *normal)
                struct.pack_into('<2f', record, 32, *uv)
                mapped[identity] = len(vertices) // 48
                vertices.extend(record)
            face.append(mapped[identity])
        regional[region].append(tuple(face))
    assert set(regional) == set(range(8)), 'Missing female armor region: ' + str(sorted(regional))
    for region, faces in regional.items():
        meshes.append({'row': skin.submeshes[0], 'batches': [batch], 'geoset': 20001 + region,
                       'triangles': faces})
    work = s.t.p.load_json(WORK / 'equipment/fit-work.json')
    fitted = s.t.p.load_json(WORK / 'equipment/donor-fit.json')
    remap = {}
    for mesh in work['equipment']:
        faces = []
        for tri in mesh['triangles']:
            face = []
            for index in tri:
                if index not in remap:
                    v = work['donor'][index]
                    point = np.array(work['inverse_skinning'][str(index)]) @ np.array([*fitted[str(index)], 1])
                    record = bytearray(48)
                    struct.pack_into('<3f', record, 0, *point[:3])
                    record[12:20] = bytes(v['weights'] + v['bones'])
                    struct.pack_into('<3f', record, 20, *v['normal'])
                    struct.pack_into('<2f', record, 32, *v['uv'])
                    remap[index] = len(vertices) // 48
                    vertices.extend(record)
                face.append(remap[index])
            faces.append(tuple(face))
        meshes.append({'row': skin.submeshes[0], 'batches': [batch], 'geoset': mesh['geoset'],
                       'triangles': faces})
    with fitting_context():
        donor, donor_skin = equipment_pass.donor()
    cape_texture = len(model.textures)
    model.textures.append({'type': 2, 'flags': 0, 'filename': ''})
    cape_combo = len(model.texture_combos)
    model.texture_combos.append(cape_texture)
    cape_material = len(model.materials)
    model.materials.append({'flags': 4, 'blending_mode': 1})
    cape_batch = struct.pack('<12H', 16, 0, 0, 0, 65535, cape_material, 0, 1, cape_combo, 0, 0, 0)
    cape.cape_surfaces(model, vertices, meshes, skin, donor, donor_skin, cape_batch)
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    raw = Skin()
    for mesh in meshes:
        row = bytearray(mesh['row'])
        first, lookup = len(raw.indices), len(raw.vertices)
        used = list(dict.fromkeys(v for tri in mesh['triangles'] for v in tri))
        indices = {v: lookup + i for i, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(indices[v] for tri in mesh['triangles'] for v in tri)
        for offset, value in ((0, mesh['geoset']), (2, first >> 16), (4, lookup), (6, len(used)),
                              (8, first & 65535), (10, len(mesh['triangles']) * 3)):
            visual.patch16(row, offset, value)
        index = len(raw.submeshes)
        raw.submeshes.append(bytes(row))
        for old_batch in mesh['batches']:
            new_batch = bytearray(old_batch)
            visual.patch16(new_batch, 4, index)
            visual.patch16(new_batch, 6, index)
            raw.batches.append(bytes(new_batch))
    compact = visual.compact_bone_palettes(model, raw)
    assert model.vertices[:len(original.vertices)] == original.vertices
    model.replacable_texture_lookup = [65535] * 16
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
    blob, separated = arrays.separate_bone_track_arrays(write_md20(model))
    destination = STAGE / 'assets' / MODEL
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    destination.with_name('tuskarrfemale00.skin').write_bytes(write_skin(compact))
    for fid in SKINS:
        original_texture = s.WORK / 'tuskarr/converted' / (str(fid) + '.blp')
        s.pin(STAGE / 'assets' / texture_path(fid), original_texture.read_bytes())
    reflect = RETAIL.with_name('armorreflect4.blp')  # fixed type-0 texture the M2 still names; no batch samples it
    s.pin(STAGE / 'assets/custom/tuskarr/character/tuskarr/armorreflect4.blp', reflect.read_bytes())
    actions = {q['id'] for q in model.sequences}
    import sethrak_animation_pack as checks
    s.t.save(WORK / 'model.json', {'model': str(destination), 'sha256': s.digest(blob),
        'source_sha256': s.t.p.sha256(SOURCE), 'vertices': model.vertex_count,
        'maximum_palette': max(visual.u16(row, 12) for row in compact.submeshes),
        'regional_triangles': {str(k): len(v) for k, v in regional.items()},
        'source_vertices_uvs_preserved': True, 'shared_track_arrays_separated': separated,
        'missing_player_actions': sorted(set(checks.ACTIONS) - actions),
        'installed': False, 'live_accepted': False})
    print('Prepared female HD body, eight equipment regions, fitted garments and animated cloak')


def texture_path(fid):
    return 'custom\\tuskarr\\native\\female\\tuskarrfemale_' + str(fid) + '.blp'


LABELS = ('Skin Color', 'Face', 'Hair Style', 'Hair Color', 'Facial Hair')
CAPACITIES = (len(SKINS), 1, 1, 1, 1)
RACE = 55
TABLES = ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo', 'CharSections', 'CharHairGeosets',
          'CharacterFacialHairStyles', 'CharStartOutfit', 'NameGen')
# skin_expansion.py already grows CharSections for the other races; chain from its stage so both can install.
CHAINED = ('CharSections',)
BASELINE = WORK / 'baseline'
CATALOGS = ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin', 'EsteriaTuskarr.bin',
            'EsteriaTuskarrTextures.bin')


def config():
    """Register gender 1 for race 55 in the manifest, allocation and registry; the male stays untouched."""
    t = s.t
    path = t.p.manifest_path('tuskarr')
    manifest = t.p.load_json(path)
    appearance = manifest['appearance']
    assert appearance['supported_genders'] == [0] and 'female' not in manifest['models']
    manifest['models']['female'] = {'model_id': MODEL_ID, 'display_id': DISPLAY_ID, 'model_path': MODEL,
                                    'display_scale': 1.0}
    appearance['supported_genders'] = [0, 1]
    appearance['female_source'] = 'hd-npc'
    appearance['profiles']['1'] = {'capacities': list(CAPACITIES), 'options': [
        {'label': label, 'choices': list(choices)} for label, choices in zip(
            LABELS, (SKINS, (0,), (0,), (0,), (0,)), strict=True)]}
    appearance['female_model'] = {'file_data_id': 4039116, 'creature_model_id': 12844,
        'source_build': appearance['source_build'], 'skin_slot': 1, 'skin_file_data_ids': list(SKINS),
        'excluded_slots': {'2': 'clothing and props', '3': 'accessory pieces'},
        'runtime_patch_root': str(STAGE / 'assets')}
    t.save(path, manifest)
    allocation = t.p.load_json(t.p.ALLOCATION_PATH)
    own = allocation['race_allocations']['tuskarr']
    for name, value in (('CreatureModelData', MODEL_ID), ('CreatureDisplayInfo', DISPLAY_ID)):
        for slug, bounds in allocation['race_allocations'].items():
            if slug != 'tuskarr' and isinstance(bounds.get(name), dict):
                assert value not in bounds[name].values(), (slug, name, value)
        own[name]['female'] = value
        allocation['dbc_ranges'][name][1] = max(allocation['dbc_ranges'][name][1], value)
    t.save(t.p.ALLOCATION_PATH, allocation)
    registry_path = t.REPO / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = t.p.load_json(registry_path)
    entry = next(e for e in registry['playable'] if e['id'] == RACE)
    entry['supported_genders'] = [0, 1]
    t.save(registry_path, registry)
    s.common.header()
    print('Registered female Tuskarr in manifest, allocation, race registry and generated header')


def capture():
    """Pin the effective client tables, catalogs and Glue the female stage is built from."""
    t = s.t
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for name in TABLES:
            key = t.p.DBC_ROOT + name + '.dbc'
            chained = s.WORK / 'stage/client/DBFilesClient' / (name + '.dbc')
            data = chained.read_bytes() if name in CHAINED and chained.exists() else files.find(key)[0]
            s.pin(BASELINE / 'client' / (name + '.dbc'), data)
            server = t.p.SERVER_DBC_ROOT / (name + '.dbc')
            chained = s.WORK / 'stage/server' / (name + '.dbc')
            if name in CHAINED and chained.exists():
                server = chained
            if server.exists():
                s.pin(BASELINE / 'server' / (name + '.dbc'), server.read_bytes())
        s.pin(BASELINE / 'CharacterCreate.lua', files.find(t.p.GLUE_ROOT + 'CharacterCreate.lua')[0])
    finally:
        files.close()
    for name in CATALOGS:
        chained = s.WORK / 'stage/catalogs' / name
        source = chained if chained.exists() else t.p.CLIENT_DEFAULT / name
        s.pin(BASELINE / name, source.read_bytes())
    for name in ('Wow.exe', 'EsteriaAppearance.dll'):
        s.pin(BASELINE / 'runtime' / name, (t.p.CLIENT_DEFAULT / name).read_bytes())
    print('Captured', len(TABLES), 'tables, catalogs and Glue baseline')


def read(kind, name):
    return (BASELINE / kind / (name + '.dbc')).read_bytes()


def retail_model():
    """Retail CreatureModelData for the HD female (model 12844), from the pinned DB2 snapshot."""
    from retroporter.config import DEFAULT
    from retroporter.wotlk import load_db2
    return load_db2(DEFAULT, 'tuskarr', 'CreatureModelData').rows[12844]


def table_updates(kind):
    """Append female rows only. Every existing row, string offset and ID is preserved."""
    import ogre_furbolg_race_pack as order
    import sethrak_race_pack as tables
    import vrykul_female_pack as clone
    p = s.t.p
    result = {name: read(kind, name) for name in TABLES if (BASELINE / kind / (name + '.dbc')).exists()}
    ranges = p.load_json(p.ALLOCATION_PATH)['race_allocations']['tuskarr']
    if 'ChrRaces' in result:
        table = p.RawWdbc(result['ChrRaces'])
        rows = []
        for row in table.records:
            if p._value(row, 0) == RACE:
                assert p._value(row, 20) == 0, 'Female Tuskarr display already installed'
                row = p._replace(row, 20, 4, DISPLAY_ID)
            rows.append(row)
        result['ChrRaces'] = table.build(rows, table.strings)
    retail = retail_model()
    for name, donor_id, new_id in (('CreatureModelData', 120059, MODEL_ID), ('CreatureDisplayInfo', 60050, DISPLAY_ID)):
        if name not in result:
            continue
        table = p.RawWdbc(result[name])
        assert not any(p._value(r, 0) == new_id for r in table.records), 'New ID is occupied: ' + name
        row = next(r for r in table.records if p._value(r, 0) == donor_id)
        pool = bytearray(table.strings)
        row = p._clone_strings(name, table, row, pool)
        row = p._replace(row, 0, 4, new_id)
        if name == 'CreatureModelData':
            row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
            row = p._set_string(row, 2, pool, MODEL)
            for field, value in ((4, retail['ModelScale']), (14, retail['CollisionWidth']),
                                 (15, retail['CollisionHeight']), (16, retail['MountHeight']),
                                 *[(17 + i, v) for i, v in enumerate(retail['GeoBox'])],
                                 (23, retail['WorldEffectScale']), (24, retail['AttachedEffectScale']),
                                 (25, retail['MissileCollisionRadius']), (26, retail['MissileCollisionPush']),
                                 (27, retail['MissileCollisionRaise'])):
                row = row[:field * 4] + struct.pack('<f', value) + row[field * 4 + 4:]
        else:
            row = p._replace(row, 4, 4, MODEL_ID)
            for offset in (12, 28, 32, 36):
                row = p._replace(row, offset, 4, 0)
            row = row[:16] + struct.pack('<f', 1.0) + row[20:]
        result[name] = tables.append_rows(result[name], name, [row], pool)
    if 'CharSections' in result:
        table = p.RawWdbc(result['CharSections'])
        pool, rows = bytearray(table.strings), list(table.records)
        assert not any(p._value(r, 4) == RACE and p._value(r, 8) == 1 for r in rows), 'Female sections installed'
        flags = {p._value(r, 12): p._value(r, 28) for r in rows if p._value(r, 4) == RACE and p._value(r, 8) == 0}
        low, high = ranges['CharSections']
        used = {p._value(r, 0) for r in rows}
        free = iter(i for i in range(low, high + 1) if i not in used)

        def section(kind, color):
            row = struct.pack('<10I', next(free), RACE, 1, kind, 0, 0, 0, flags[kind], 0, color)
            if kind == 0:
                row = p._set_string(row, 4, pool, texture_path(SKINS[color]))
            rows.append(row)

        for color in range(len(SKINS)):
            for kind in (0, 1, 4):
                section(kind, color)
        section(2, 0)
        section(3, 0)
        result['CharSections'] = order.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc',
            table.build(rows, bytes(pool)))
    if 'CharHairGeosets' in result:
        table = p.RawWdbc(result['CharHairGeosets'])
        low, high = ranges['CharHairGeosets']
        used = {p._value(r, 0) for r in table.records}
        row = struct.pack('<6I', next(i for i in range(low, high + 1) if i not in used), RACE, 1, 0, 0, 1)
        result['CharHairGeosets'] = table.build(list(table.records) + [row], table.strings)
    if 'CharacterFacialHairStyles' in result:
        table = p.RawWdbc(result['CharacterFacialHairStyles'])
        result['CharacterFacialHairStyles'] = table.build(
            list(table.records) + [struct.pack('<8I', RACE, 1, 0, 0, 0, 0, 0, 0)], table.strings)
    for name, source_race, source_gender in (('CharStartOutfit', RACE, 0), ('NameGen', 3, 1)):
        if name not in result:
            continue
        low, high = ranges[name]
        layout = p.WDBC_LAYOUTS[name]
        at, width = {'CharStartOutfit': (6, 1), 'NameGen': (12, 4)}[name]
        used = [p._value(r, 0) for r in p.RawWdbc(result[name]).records if low <= p._value(r, 0) <= high]
        rows = [r for r in p.RawWdbc(result[name]).records
                if p._value(r, layout.race_offset, layout.race_width) == source_race
                and p._value(r, at, width) == source_gender]
        assert rows and max(used) + len(rows) <= high, name + ' donor rows missing or allocation exhausted'
        # Female names come from the dwarf donor; the starting outfit mirrors the installed male Tuskarr.
        transforms = [[(layout.race_offset, layout.race_width, RACE), (at, width, 1), (0, 4, max(used) + 1 + i)]
                      for i in range(len(rows))]
        result[name] = clone.append_rows(result[name], result[name], name, rows, transforms)
    return result


def selections():
    """Gender 1 records appended to the existing catalog; the male records and their bank offsets stay."""
    from haranir_race_pack import lznt1
    catalog = (BASELINE / 'EsteriaTuskarr.bin').read_bytes()
    bank = bytearray((BASELINE / 'EsteriaTuskarrTextures.bin').read_bytes())
    magic, version, count = struct.unpack_from('<3I', catalog)
    assert (magic, version) == (0x314D4845, 1) and len(catalog) == 12 + count * 156
    assert not any(struct.unpack_from('<I', catalog, 12 + i * 156)[0] == 1 for i in range(count)), 'Female installed'
    bank_magic, bank_version, items, _ = struct.unpack_from('<4I', bank)
    assert (bank_magic, bank_version) == (0x31544845, 1)
    pixels = bytearray(512 * 512 * 4)
    pixels[0] = 1  # Keep RtlCompressBuffer's all-zero sparse-block special case out of this layer.
    packed = lznt1(bytes(pixels))
    offset = len(bank)
    bank.extend(struct.pack('<3I', 512, 512, len(packed)) + packed)
    struct.pack_into('<I', bank, 8, items + 1)
    struct.pack_into('<I', bank, 12, int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little'))
    records = []

    def record(kind, target, value, selectors=(), path=''):
        choices = [i | j << 16 for i, j in selectors]
        records.append(struct.pack('<7I', 1, kind, target, value,
            *(choices + [0xffffffff] * (3 - len(choices)))) + path.encode().ljust(128, b'\0'))

    for i, fid in enumerate(SKINS):
        record(1, 11, 0, [(0, i)], texture_path(fid))
    for geoset in range(20001, 20009):
        record(2, 0, geoset)
    record(3, 0, offset, (), '1:0')
    return struct.pack('<3I', magic, version, count + len(records)) + catalog[12:] + b''.join(records), bytes(bank)


def appearance():
    original = (BASELINE / 'EsteriaAppearance.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    stride = 2316
    assert (magic, version) == (0x50504145, 2) and len(original) == 12 + count * stride
    assert not any(struct.unpack_from('<2I', original, 12 + i * stride) == (RACE, 1) for i in range(count))
    record = bytearray(struct.pack('<3I', RACE, 1, 5))
    for offset, capacity in zip((0x28, 0x2c, 0x34, 0x24, 0x30), CAPACITIES, strict=True):
        record.extend(struct.pack('<4I', offset, capacity, 1, 0) + bytes(128))
    record.extend(bytes(11 * 144))
    assert len(record) == stride
    return struct.pack('<3I', magic, version, count + 1) + original[12:] + bytes(record)


def geometry():
    import drakonid_race_pack as drakonid
    skin = (STAGE / 'assets' / MODEL.replace('\\', '/')).with_name('tuskarrfemale00.skin').read_bytes()
    previous = drakonid.MODEL
    drakonid.MODEL = MODEL
    try:
        return drakonid.geometry_catalog((BASELINE / 'EsteriaAppearanceGeometry.bin').read_bytes(), skin)
    finally:
        drakonid.MODEL = previous


def glue(data):
    from lupa.lua51 import LuaRuntime
    text = data.decode('utf-8-sig')
    old = 'return race == 55 or race == 58'
    assert text.count(old) == 1, 'Installed Tuskarr gender policy changed'
    text = text.replace(old, 'return race == 58')
    icon = '["TUSKARR_FEMALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\UI-CharacterCreate-TuskarrMale"'
    assert text.count(icon) == 1, 'Installed Tuskarr female icon changed'
    text = text.replace(icon, icon.replace('TuskarrMale', 'TuskarrFemale'))
    LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')(text)
    return text.encode()


def portraits():
    import race_portrait_pack as art
    files = s.t.p.ClientFiles(str(s.t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        template = files.find(art.ICON_TEMPLATE_ENTRY)[0]
        ring = art.ring_layer(art.decode_client_blp(files.find(art.RING_ENTRY)[0]))
    finally:
        files.close()
    image = art.portrait_bytes(s.PORTRAIT, art.circular_mask())
    plain = art.encode_portrait(image, template)
    icon = art.encode_portrait(art.compose_race_icon(image, ring), template)
    stem = art.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-Female-Tuskarr'
    return {art.CREATOR_ICON_ROOT + 'UI-CharacterCreate-TuskarrFemale.blp': icon, stem: plain,
            stem + '.blp': plain, 'Interface\\Glues\\CharacterSelect\\ECS-Portrait-TuskarrFemale.blp': plain}


def stage():
    t = s.t
    capture()
    client, server = table_updates('client'), table_updates('server')
    for directory, tables in (('client-dbc', client), ('server-dbc', server)):
        for name, blob in tables.items():
            path = STAGE / directory / (name + '.dbc')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
    catalog, bank = selections()
    outputs = {'EsteriaAppearance.bin': appearance(), 'EsteriaAppearanceGeometry.bin': geometry(),
               'EsteriaTuskarr.bin': catalog, 'EsteriaTuskarrTextures.bin': bank}
    for name, blob in outputs.items():
        (STAGE / name).write_bytes(blob)
    lua = glue((BASELINE / 'CharacterCreate.lua').read_bytes())
    (STAGE / 'CharacterCreate.lua').write_bytes(lua)
    assets = {str(t.PureWindowsPath(path.relative_to(STAGE / 'assets'))): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    for key, blob in portraits().items():
        path = STAGE / 'assets' / key.replace('\\', '/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        assets[key] = blob
    receipt = {'state': 'loose_integration_staged', 'race_id': RACE, 'gender': 1, 'model_id': MODEL_ID,
               'display_id': DISPLAY_ID, 'installed': False, 'packaged': False, 'native_built': False,
               'server_built': False, 'live_accepted': False,
               'baselines': {str(path.relative_to(BASELINE)): s.digest(path.read_bytes())
                             for path in sorted(BASELINE.rglob('*')) if path.is_file()},
               'client_tables': {name: s.digest(blob) for name, blob in client.items()},
               'server_tables': {name: s.digest(blob) for name, blob in server.items()},
               'catalogs': {name: s.digest(blob) for name, blob in outputs.items()},
               'assets': {name: s.digest(blob) for name, blob in assets.items()},
               'source_files': {name: t.p.sha256(t.REPO / name) for name in (
                   'tools/tuskarr_female_pack.py', 'tools/skin_expansion.py',
                   'client-customization/HaranirMaterials.inl', 'src/server/shared/CreatureAppearance.h')}}
    t.save(WORK / 'stage.json', receipt)
    print('Staged female Tuskarr tables, catalogs, Glue and portrait; no MPQ/build/install')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('animations', 'fit-work', 'prepare', 'config', 'stage'))
    globals()[parser.parse_args().action.replace('-', '_')]()
