"""Stage the Drakonid (Retail NPC 191518) as independent Alliance 69 and Horde 70 races.

One authored male body shared by both factions. Preparation never builds or installs; `drakonid_deploy.py`
performs the coordinated, backed-up installation after the native helper and worldserver are built.
"""

import argparse
import copy
import hashlib
import json
import re
import math
from pathlib import Path, PureWindowsPath
import shutil
import struct

from PIL import Image
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

import creature_animation_repair as animation
import creature_race_pack as c
import ogre_furbolg_race_pack as o
import retroported_race_pack as p
import drakkin_drakonid_racials as racials
import sethrak_race_pack as tables_lib

WORK = Path('G:/RetroPorterWork/drakonid')
EQUIP = WORK / 'equipment-v1'
STAGE = WORK / 'deploy'
MODEL = 'custom\\drakonid\\native\\drakonid.m2'
TEXTURES = 'custom\\drakonid\\native\\textures\\'
ASSET = Path('Data/Patch-Dn.MPQ')
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11]
PREFIX = 'Dk'
DISPLAY_SCALE = 1.0  # the model itself is baked to its final size (see bake_scale)
MODEL_SCALE = 0.55
ITEM_SCALE = 0.62  # relative to the retail socket scale, after baking
SHOULDER_PITCH = 20.0  # degrees the retail socket frame leans back; corrected so pads sit over the shoulder
SHOULDER_SCALE = 1.5  # shoulder sockets keep 1.0 in the retail model; the baked body is broad
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261012010000000_drakonid.sql'
# race, faction, donor race (start data, language, faction template), model id, display id, source skin
SPECS = ((69, 'alliance', 1, 120077, 60068), (70, 'horde', 2, 120078, 60069))
LABELS = ('Skin Color', 'Head', 'Horns', 'Tail', 'Eye Color')
# Installed indexes stay first; tools/skin_expansion.py prepares the additional HD atlases.
SKINS = ('drakonid2_blue', 'drakonid2_black', 'drakonid2_bronze', 'drakonid2_green', 'drakonid2_red',
         'drakonid2_white', 'drakonid2_olive', 'drakonid2_chromatic', 'drakonid2_twilight',
         'drakonid2_void', 'drakonid2_azure', 'drakonid2_teal', 'drakonid2_indigo',
         'drakonid2_darkteal', 'drakonid2_umber', 'drakonid2_charcoal', 'drakonid2_abyss')
_EYE_IDS = (4218540, 4218485, 4218514, 4218590, 4218479, 4218480, 4218481, 4218482, 4218483, 4218484, 4218486,
            4218487, 4218488, 4218489, 4218490, 4218492, 4218493, 4218494, 4218495, 4218496, 4218497, 4218498,
            4218499, 4218500, 4218501, 4218502, 4218504, 4218505, 4218506, 4218510, 4218511, 4218512, 4218513,
            4218515, 4218516, 4218519, 4218520, 4218522, 4218523, 4218527, 4218528, 4218530, 4218535, 4218536,
            4218538, 4218542, 4218543, 4218544, 4218545, 4218546, 4218547, 4218549, 4218550, 4218551, 4218554,
            4218555, 4218556, 4218559, 4218561, 4218563, 4218565, 4218569, 4218572, 4218573, 4218574, 4218578,
            4218583, 4218585, 4218588, 4218589, 4218592, 4218599, 4218600, 4218602, 4218604, 4218605)
EYES = tuple('drakonid2_eyes_%d' % identifier for identifier in _EYE_IDS)
# Option indices: 0 skin, 1 head, 2 horns, 3 tail, 4 eyes. Head and tail share the face byte; each other
# control owns one byte. Cosmetic values are the staged geosets (source geoset + 3000).
CHOICES = (SKINS, (3101, 3102), (3201, 3202, 3203, 3204, 3205, 3206), (3501, 3502), EYES)
FIELDS = ((0,), (1, 3), (2,), (4,))
# The retail NPC outfit is not shipped, so there are no native outfit decorations to hide.
OUTFIT_GROUPS = ()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def local(root, key):
    return root.joinpath(*PureWindowsPath(key).parts)


def codec():
    descriptors = [None] * len(LABELS)
    capacities = []
    for field, indices in enumerate(FIELDS):
        factor = 1
        for index in indices:
            descriptors[index] = (field, len(CHOICES[index]), factor)
            factor *= len(CHOICES[index])
        capacities.append(factor)
    capacities.append(1)
    return {'descriptors': descriptors, 'capacities': capacities,
            'options': [{'label': label, 'choices': list(values)} for label, values in zip(LABELS, CHOICES)]}


def ranges(race):
    index = race - 69
    start = 1117300 + index * 1000
    return {'CreatureModelData': {'male': 120077 + index}, 'CreatureDisplayInfo': {'male': 60068 + index, 'female': 0},
            'CharSections': [start, start + 999], 'CharHairGeosets': [start, start + 99],
            'BarberShopStyle': [start, start + 99], 'CharStartOutfit': [22200 + index * 10, 22209 + index * 10],
            'NameGen': [93000 + index * 3000, 95999 + index * 3000]}


def manifest(spec):
    race, faction, donor, model, display = spec
    return {'schema_version': 1, 'slug': 'drakonid_' + faction, 'name': 'Drakonid', 'race_ids': [race],
            'enum': 'RACE_DRAKONID_' + faction.upper(), 'faction': faction, 'source_race_id': donor,
            'legacy_mask_race': donor, 'visual_base_race': 6, 'helmet_prefix': PREFIX,
            'client_file_strings': {str(race): 'Drakonid' + faction.title()},
            'glue_token': ('Drakonid' + faction).upper(), 'start_profile': 'elwynn' if race == 69 else 'durotar',
            'donor_totem_race': donor, 'classes': CLASSES, 'source_patch_root': str(WORK / 'converted'),
            'runtime_patch_root': str(STAGE / 'assets'),
            'models': {'male': {'model_id': model, 'display_id': display, 'model_path': MODEL}},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'retail-creature-191518',
                           'hide_helm': False, 'supported_genders': [0], 'profiles': {'0': codec()}},
            'random_playerbot_enabled': False, 'custom_racial_spells': []}


def allocation():
    result = p.load_json(p.ALLOCATION_PATH)
    registry = p.load_json(p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json')
    for spec in SPECS:
        race, faction = spec[:2]
        slug = 'drakonid_' + faction
        bounds = ranges(race)
        assert all(race not in ids for key, ids in result['race_ids'].items() if key != slug), 'race id taken'
        assert not any(r['id'] == race for r in registry['npc_only']), 'race id reserved for NPCs'
        for key, other in result['race_allocations'].items():
            if key.startswith('drakonid_'):
                continue  # our own two races are recomputed together; every other race is checked below
            for table, values in bounds.items():
                previous = other.get(table)
                if isinstance(values, list) and isinstance(previous, list):
                    assert max(values[0], previous[0]) > min(values[1], previous[1]), (key, table)
                elif isinstance(values, dict) and isinstance(previous, dict):
                    assert not ((set(values.values()) - {0}) & (set(previous.values()) - {0})), (key, table)
        result['race_ids'][slug] = [race]
        result['race_allocations'][slug] = bounds
        for table, values in bounds.items():
            result['dbc_ranges'][table][1] = max(result['dbc_ranges'][table][1],
                values[1] if isinstance(values, list) else max(values.values()))
    return result


def config():
    path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(path)
    for spec in SPECS:
        race, faction, donor = spec[:3]
        m = manifest(spec)
        entry = {'id': race, 'species_key': m['slug'], 'display_name': 'Drakonid', 'faction': faction,
                 'species_selection': False, 'start_profile': m['start_profile'],
                 'asset_owner': 'retroporter_drakonid', 'legacy_mask_race': donor, 'visual_base_race': 6,
                 'supported_genders': [0]}
        previous = next((row for row in registry['playable'] if row['id'] == race), None)
        assert previous is None or previous == entry, 'Race registry owner changed'
        if previous is None:
            registry['playable'].append(entry)
        save(p.manifest_path(m['slug']), m)
    registry['sources']['retroporter_drakonid'] = str(STAGE / 'assets')
    save(p.ALLOCATION_PATH, allocation())
    save(path, registry)
    c.header()
    print('RESERVED independent Drakonid races 69/70 and regenerated CreatureAppearance.h', flush=True)


def texture_path(name):
    return TEXTURES + name + '.blp'


def scale_values(track, factor):
    """Scale every vec3 / spline-vec3 key of a translation-like track."""
    track.values = [[tuple(x * factor for x in value) for value in row] for row in track.values]
    if isinstance(getattr(track, 'first_value', None), tuple):
        track.first_value = tuple(x * factor for x in track.first_value)


def bake_scale(model, factor, helper_bone=None, item_factor=1.0, shoulder_factor=1.0):
    """Make the model its final in-game size instead of relying on the display scale.

    The glue screens ignore the display scale, and attached items (shoulders, weapons, helmets) are sized
    for ordinary characters, so a scaled-down giant made both wrong. Every length is multiplied; scale tracks
    stay relative, except the helmet helper bone whose scale is an absolute item size.
    """
    vertices = bytearray(model.vertices)
    for i in range(model.vertex_count):
        point = struct.unpack_from('<3f', vertices, i * 48)
        struct.pack_into('<3f', vertices, i * 48, *(x * factor for x in point))
    model.vertices = bytes(vertices)
    for index, bone in enumerate(model.bones):
        bone['pivot'] = tuple(x * factor for x in bone['pivot'])
        scale_values(bone['translation'], factor)
        if index == helper_bone:
            scale_values(bone['scale'], factor)
    for attachment in model.attachments:
        attachment['position'] = tuple(x * factor for x in attachment['position'])
    # Weapon, shield, back and sheath sockets carry the retail 2.2-2.5x item scale, sometimes on a helper bone above
    # the socket. Rescale the nearest scaled bone that no vertex uses; shoulders get their own enlargement.
    skinned = set()
    for i in range(model.vertex_count):
        skinned.update(struct.unpack_from('4B', vertices, i * 48 + 16))
    children = {}
    for index, bone in enumerate(model.bones):
        children.setdefault(bone['parent_bone'], []).append(index)

    def reaches_skin(index):
        stack = [index]
        while stack:
            current = stack.pop()
            if current in skinned:
                return True
            stack.extend(children.get(current, ()))
        return False

    def static_scale(bone):
        """Constant scale (retail exporters leave 1e-6 noise on 'static' keys); None when keyed or absent."""
        values = [v for row in bone['scale'].values for v in row]
        if not values:
            return None
        flat = [x for v in values for x in v]
        return values[0][0] if max(flat) - min(flat) < 1e-3 else None

    def set_static_scale(bone, value):
        bone['flags'] |= 512  # retail shoulder sockets carry the transformed flag; without it the client skips the scale
        track = bone['scale']
        track.global_sequence = -1
        track.external.clear()
        track.interpolation = 0
        track.timestamps = [[0] for _ in model.sequences]
        track.values = [[(value, value, value)] for _ in model.sequences]
        track.timestamp_spans = track.value_spans = [(0, 0)] * len(model.sequences)

    def tilt(bone, degrees):
        """Static pitch about the socket's own Y axis (positive tips the pad's up-axis forward)."""
        half = math.radians(degrees) / 2
        quat = animation.packed((0.0, math.sin(half), 0.0, math.cos(half)))
        track = bone['rotation']
        track.global_sequence = -1
        track.external.clear()
        track.interpolation = 0
        track.timestamps = [[0] for _ in model.sequences]
        track.values = [[quat] for _ in model.sequences]
        track.timestamp_spans = track.value_spans = [(0, 0)] * len(model.sequences)

    rescaled = {}
    for attachment in model.attachments:
        if attachment['bone'] == helper_bone or attachment['id'] in (3, 4, 20):
            continue
        factor_here = shoulder_factor if attachment['id'] in (5, 6) else item_factor
        index = attachment['bone']
        if attachment['id'] in (5, 6):
            # Retail leaves the shoulder sockets unscaled (no scale keys); give them an absolute enlargement.
            if not reaches_skin(index) and index not in rescaled:
                value = static_scale(model.bones[index]) or 1.0
                set_static_scale(model.bones[index], value * factor_here)
                tilt(model.bones[index], SHOULDER_PITCH)
                rescaled[index] = (attachment['id'], round(value, 3), factor_here)
            continue
        while index >= 0:
            keys = [x for row in model.bones[index]['scale'].values for v in row for x in v]
            value = max(keys) if keys and min(keys) > 1.2 else None  # a socket scale may dip during some actions
            if value is not None:
                if not reaches_skin(index) and index not in rescaled:
                    scale_values(model.bones[index]['scale'], factor_here)
                    rescaled[index] = (attachment['id'], round(value, 3), factor_here)
                break
            index = model.bones[index]['parent_bone']
    bake_scale.rescaled = rescaled
    for event in model.events:
        event['position'] = tuple(x * factor for x in event['position'])
    for camera in model.cameras:
        camera['far_clip'] *= factor
        camera['near_clip'] *= factor
        for key in ('position_base', 'target_position_base'):
            camera[key] = tuple(x * factor for x in camera[key])
        for key in ('positions', 'target_position'):
            scale_values(camera[key], factor)
    model.bounding_box = tuple(x * factor for x in model.bounding_box)
    model.bounding_sphere_radius *= factor
    model.collision_box = tuple(x * factor for x in model.collision_box)
    model.collision_sphere_radius *= factor
    model.collision_positions = [tuple(x * factor for x in point) for point in model.collision_positions]
    for sequence in model.sequences:
        sequence['bounds_min'] = tuple(x * factor for x in sequence['bounds_min'])
        sequence['bounds_max'] = tuple(x * factor for x in sequence['bounds_max'])
        sequence['bounds_radius'] *= factor


# Player actions every stock race has and the retail NPC lacks. Motion copied from another rig deforms this skeleton,
# so each one reuses the closest action the model authored itself.
PLAYER_ALIASES = (
    (3, 0), (19, 18), (23, 22), (24, 21), (28, 27), (29, 48), (46, 49), (57, 17), (58, 18), (59, 16), (84, 64),
    (85, 17), (87, 510), (88, 510), (95, 16), (99, 96), (100, 97), (105, 106), (107, 17), (108, 26), (109, 110),
    (111, 26), (112, 106), (118, 16), (121, 14), (131, 9), (132, 1), (139, 96), (143, 5), (185, 60), (193, 0),
    (195, 62), (212, 17), (223, 119), (225, 83), (474, 14), (476, 27), (477, 27), (478, 27), (482, 18), (484, 91),
    (500, 91))


def add_player_actions(model):
    import earthen_race_pack as e
    for action, authored in PLAYER_ALIASES:
        if action in {sequence['id'] for sequence in model.sequences}:
            continue
        index = animation.sequence(model, authored)
        slot = len(model.sequences)
        row = copy.deepcopy(model.sequences[index])
        row.update(id=action, variation_index=0, variation_next=-1, alias_next=slot,
                   flags=(row['flags'] & ~0x40) | 0x20)
        model.sequences.append(row)
        for track in model.tracks():
            if track.global_sequence >= 0:
                continue
            times = copy.deepcopy(track.timestamps[index]) if index < len(track.timestamps) else []
            values = copy.deepcopy(track.values[index]) if hasattr(track, 'values') and index < len(track.values)                 else []
            animation.per_sequence(track, model)
            track.timestamps[slot] = times
            if hasattr(track, 'values'):
                track.values[slot] = values
    e.rebuild_sequence_lookup(model)
    from sethrak_equipment_repair import use_running_landing
    use_running_landing(model)  # landing while moving resumes the run at once, as for the Gnoll
    assert {action for action, _ in PLAYER_ALIASES} <= {sequence['id'] for sequence in model.sequences}


def model_assets():
    """Final shared model: helmet-staged geometry with every texture path moved under the Drakonid namespace."""
    stage = p.load_json(EQUIP / 'helmet-stage.json')
    source = Path(stage['model'])
    model = parse_m2(source.read_bytes())
    for texture in model.textures:
        if texture['type'] == 0 and texture['filename']:
            texture['filename'] = texture_path(PureWindowsPath(texture['filename']).stem)
    add_player_actions(model)
    for texture in model.textures:
        if texture['type'] == 13:
            texture['type'] = 6  # the stock Hair Color row (CharSections type 3) fills the hair slot: it picks the eyes
    model.replacable_texture_lookup = [65535] * 16
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
    skin = parse_skin(source.with_name('drakonid200.skin').read_bytes())
    # The retail eye batch is lit, alpha-keyed and multiplies two layers that are both the eye texture, which
    # blackens or washes it out. Draw the eye texture as one opaque, unlit UV0 sample (as the Highmountain eyes).
    eye_slot = next(i for i, texture in enumerate(model.textures) if texture['type'] == 6)
    eye_material = len(model.materials)
    model.materials.append({'flags': 4, 'blending_mode': 0})
    model.texture_coord_combos[0] = 0
    repaired = 0
    for i, batch in enumerate(skin.batches):
        ops, combo = struct.unpack_from('<HH', batch, 14)
        if any(model.textures[model.texture_combos[combo + k]]['type'] == 6 for k in range(ops)):
            raw = bytearray(batch)
            struct.pack_into('<B', raw, 0, 0)
            struct.pack_into('<H', raw, 10, eye_material)
            struct.pack_into('<HHH', raw, 14, 1, len(model.texture_combos), 0)
            model.texture_combos.append(eye_slot)
            skin.batches[i] = bytes(raw)
            repaired += 1
    assert repaired == 1, 'Expected exactly one eye batch'
    bake_scale(model, MODEL_SCALE, stage['helper_bone'], ITEM_SCALE, SHOULDER_SCALE)
    print('RESCALED attachment sockets', bake_scale.rescaled, flush=True)
    data = write_md20(model)
    check = parse_m2(data)
    assert check.vertex_count == model.vertex_count
    assert abs(check.bones[stage['helper_bone']]['scale'].values[0][0][0] - stage['scale'] * MODEL_SCALE) < 1e-4
    result = {MODEL: data, MODEL[:-3] + '00.skin': write_skin(skin)}
    textures = WORK / 'converted/patch-root/custom/drakonid/creature/drakonid2'
    wanted = set(SKINS) | set(EYES) | {'armorreflect_organic01', 'dragonarmorspec'}
    for path in sorted(textures.glob('*.blp')):
        if path.stem in wanted:
            result[texture_path(path.stem)] = path.read_bytes()
    assert all(texture_path(name) in result for name in (*SKINS, *EYES)), 'A skin or eye texture is missing'
    return result


def helmet_display_ids():
    """ItemDisplayInfo ids of helmets that cover the head and so hide the horns.

    Eye-plane items (goggles, monocles, eyepatches, blindfolds) and low-profile rims/halos/crowns (stock model
    under 0.21 tall in the shared head frame) leave the horns visible.
    """
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    heights = {}
    suffix = p.load_json(EQUIP / 'helmet-fit.json')['source_suffix']
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        result = []
        for row in table.records:
            stem = PureWindowsPath(p._string(table.strings, p._value(row, 4)).decode()).stem
            low = stem.lower()
            if not low.startswith('helm') or low.startswith(('helm_blindfold', 'helm_eyepatch', 'helm_goggles',
                                                              'helm_monocle')):
                continue
            if low not in heights:
                try:
                    model = parse_m2(files.find('Item\\ObjectComponents\\Head\\' + stem + '_' + suffix + '.m2')[0])
                    zs = [struct.unpack_from('<3f', model.vertices, i * 48)[2] for i in range(model.vertex_count)]
                    heights[low] = max(zs) - min(zs) if zs else 1.0
                except FileNotFoundError:
                    heights[low] = 1.0
            if heights[low] >= 0.21:
                result.append(p._value(row, 0))
        return result
    finally:
        files.close()


def selection_catalog():
    """Native selection records: textures, cosmetic groups, outfit decorations, clothing surfaces, helmet hides."""
    from gnoll_texture_repair import clothing_catalog
    records = []

    def record(kind, target, value, selectors=(), key=''):
        assert len(selectors) <= 3 and len(key.encode()) < 128
        selected = [i | j << 16 for i, j in selectors]
        records.append(struct.pack('<7I', 0, kind, target, value,
                       *(selected + [0xffffffff] * (3 - len(selected)))) + key.encode().ljust(128, b'\0'))

    for choice, name in enumerate(SKINS):
        record(1, 11, 0, [(0, choice)], texture_path(name))
    for choice, name in enumerate(EYES):
        record(1, 6, 0, [(4, choice)], texture_path(name))  # hair slot: the eyes (stock Hair Color row)
    for option in (1, 2, 3):
        for choice, geoset in enumerate(CHOICES[option]):
            record(0, geoset // 100, geoset, [(option, choice)])
    for group in OUTFIT_GROUPS:
        record(0, group, group * 100 + 2)
    for geoset in range(20001, 20009):
        record(2, 0, geoset)
    # Dorsal ridge / shoulder-fin shells belong to one tail variant each and show only with it.
    for variant, geosets in sorted(p.load_json(EQUIP / 'report.json')['tail_ridge_shells'].items()):
        for geoset in geosets:
            record(2, 0, geoset, [(3, int(variant))])
    for display in helmet_display_ids():
        record(4, display, 32)
    assert len(records) <= 16384
    catalog, bank = clothing_catalog(struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records))
    return catalog, bank, len(records)


def coverage_catalog():
    """Item display -> body regions its texture components paint (bit n = Wrath region n)."""
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        rows = []
        for row in table.records:
            mask = sum(1 << region for region in range(8) if p._value(row, (15 + region) * 4))
            if mask:
                rows.append((p._value(row, 0), mask))
    finally:
        files.close()
    return struct.pack('<3I', 0x56434253, 1, len(rows)) + b''.join(struct.pack('<2I', *row) for row in rows)


def classify(stem):
    low = stem.lower()
    return 'face' if low.startswith(('helm_blindfold', 'helm_eyepatch', 'helm_goggles', 'helm_monocle')) else 'dome'


def adjust(points, rule):
    pivot, scale, offset = rule['pivot'], rule['scale'], rule['offset']
    return [[pivot[a] + scale * (point[a] - pivot[a]) + offset[a] for a in range(3)] for point in points]


def helmet_assets():
    """`<family>_DkM` copies of the stock Tauren helmets; the shared head bone supplies scale and anchor.

    Only thin eye-plane items (goggles, monocles, eyepatches, blindfolds) get their vertices moved onto the eyes.
    """
    fit = p.load_json(EQUIP / 'helmet-fit.json')
    suffix = fit['source_suffix']
    rule = fit['classes']['face']
    human = p.load_json(EQUIP / 'helmet-fit.human-v1.json')
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    result, report = {}, {'families': 0, 'moved': [], 'missing': [], 'from_human': []}
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        unique = {}
        for row in table.records:
            name = PureWindowsPath(p._string(table.strings, p._value(row, 4)).decode()).stem
            if name:
                unique.setdefault(name.lower(), name)  # archive keys are case-insensitive
        stems = sorted(unique.values())
        folder = 'Item\\ObjectComponents\\Head\\'
        for stem in (s for s in stems if s.lower().startswith('helm')):
            try:
                data = files.find(folder + stem + '_' + suffix + '.m2')[0]
                skin = files.find(folder + stem + '_' + suffix + '00.skin')[0]
            except FileNotFoundError:
                # No Tauren variant: refit the Human one into the Tauren frame the shared head bone expects.
                try:
                    model = parse_m2(files.find(folder + stem + '_HuM.m2')[0])
                    skin = files.find(folder + stem + '_HuM00.skin')[0]
                except FileNotFoundError:
                    report['missing'].append(stem)
                    continue
                vertices = bytearray(model.vertices)
                moved = []
                for i in range(model.vertex_count):
                    point = struct.unpack_from('<3f', vertices, i * 48)
                    point = [(human['anchor'][a] - fit['anchor'][a] + human['scale'] * point[a]) / fit['scale']
                             for a in range(3)]
                    struct.pack_into('<3f', vertices, i * 48, *point)
                    moved.append(point)
                model.vertices = bytes(vertices)
                low = [min(q[a] for q in moved) for a in range(3)]
                high = [max(q[a] for q in moved) for a in range(3)]
                model.bounding_box = (*low, *high)
                model.bounding_sphere_radius = max(sum(x * x for x in q) ** .5 for q in moved)
                data = write_md20(model)
                report['from_human'].append(stem)
            if classify(stem) == 'face':
                model = parse_m2(data)
                vertices = bytearray(model.vertices)
                points = [list(struct.unpack_from('<3f', vertices, i * 48)) for i in range(model.vertex_count)]
                for i, point in enumerate(adjust(points, rule)):
                    struct.pack_into('<3f', vertices, i * 48, *point)
                model.vertices = bytes(vertices)
                moved = adjust(points, rule)
                low = [min(q[a] for q in moved) for a in range(3)]
                high = [max(q[a] for q in moved) for a in range(3)]
                model.bounding_box = (*low, *high)
                model.bounding_sphere_radius = max(sum(x * x for x in q) ** .5 for q in moved)
                data = write_md20(model)
                report['moved'].append(stem)
            result[folder + stem + '_' + PREFIX + 'M.m2'] = data
            result[folder + stem + '_' + PREFIX + 'M00.skin'] = skin
            report['families'] += 1
    finally:
        files.close()
    return result, report


def tables(baseline):
    result, reserved = dict(baseline), allocation()
    capacities = codec()['capacities']
    for spec in SPECS:
        race, faction, donor_id, model_id, display_id = spec
        m, r = manifest(spec), ranges(race)
        p._ensure_id_free(result['ChrRaces'], 'ChrRaces', {race})
        result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], m, reserved)
        table = p.RawWdbc(result['ChrRaces'])
        pool, rows = bytearray(table.strings), []
        for row in table.records:
            if p._value(row, 0) == race:
                for field, value in ((1, 14), (2, donor_id), (7, 7 if race == 69 else 1),
                                      (12, 0), (13, 0 if race == 69 else 1), (68, 0)):
                    row = p._replace(row, field * 4, 4, value)
                row = p._set_string(row, 6, pool, PREFIX)
            rows.append(row)
        result['ChrRaces'] = table.build(rows, bytes(pool))
        # Rows cloned from the installed Gnoll (native player, flags 0x804 so the HD compositor is created).
        models = p.RawWdbc(result['CreatureModelData'])
        model_row = next(row for row in models.records if p._value(row, 0) == 120068)
        pool = bytearray(models.strings)
        model_row = p._clone_strings('CreatureModelData', models, model_row, pool)
        model_row = p._replace(model_row, 0, 4, model_id)
        model_row = p._replace(model_row, 4, 4, p._value(model_row, 4) | 0x804)
        model_row = p._set_string(model_row, 2, pool, MODEL)
        result['CreatureModelData'] = tables_lib.append_rows(result['CreatureModelData'], 'CreatureModelData',
                                                             [model_row], pool)
        displays = p.RawWdbc(result['CreatureDisplayInfo'])
        display = next(row for row in displays.records if p._value(row, 0) == 60059)
        pool = bytearray(displays.strings)
        display = p._clone_strings('CreatureDisplayInfo', displays, display, pool)
        for offset, value in ((0, display_id), (4, model_id), (12, 0), (28, 0), (32, 0), (36, 0)):
            display = p._replace(display, offset, 4, value)
        display = display[:16] + struct.pack('<f', DISPLAY_SCALE) + display[20:]
        result['CreatureDisplayInfo'] = tables_lib.append_rows(result['CreatureDisplayInfo'],
                                                               'CreatureDisplayInfo', [display], pool)
        result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], m)
        outfit = p.RawWdbc(result['CharStartOutfit'])
        donors = {}
        for row in sorted(outfit.records, key=lambda v: p._value(v, 0)):
            if row[4] == donor_id and row[5] in CLASSES and row[6] == 0 and row[7] == 0:
                donors[row[5]] = row
        assert len(donors) == 10, 'Missing faction/class male outfit'
        additions = [p._replace(p._replace(row, 0, 4, r['CharStartOutfit'][0] + i), 4, 1, race)
                     for i, row in enumerate(donors.values())]
        result['CharStartOutfit'] = tables_lib.append_rows(result['CharStartOutfit'], 'CharStartOutfit', additions)
        source = p.RawWdbc(result['NameGen'])
        pool = bytearray(source.strings)
        names = [row for row in source.records if p._value(row, 8) == donor_id and p._value(row, 12) == 0]
        assert names and len(names) <= 3000
        additions = [p._replace(p._replace(p._clone_strings('NameGen', source, row, pool), 0, 4,
                     r['NameGen'][0] + i), 8, 4, race) for i, row in enumerate(names)]
        result['NameGen'] = tables_lib.append_rows(result['NameGen'], 'NameGen', additions, pool)
        source = p.RawWdbc(result['CharSections'])
        pool, added, hair, facial, barber = bytearray(source.strings), [], [], [], []
        body = texture_path(SKINS[0])
        base = r['CharSections'][0]

        def section(kind, style, color):
            row = struct.pack('<10I', base + len(added), race, 0, kind, 0, 0, 0, 1 if kind == 1 else 17, style, color)
            if kind == 0:
                row = p._set_string(row, 4, pool, body)
            elif kind == 3:  # the stock Hair Color row only counts sections that name a texture; it selects the eyes
                row = p._set_string(row, 4, pool, texture_path(EYES[color]))
            added.append(row)

        for color in range(capacities[0]):
            for kind in (0, 1, 4):
                section(kind, 0, color)
        for face in range(1, capacities[1]):
            for color in range(capacities[0]):
                section(1, face, color)
        for style in range(capacities[2]):
            for color in range(capacities[3]):
                section(3, style, color)
            hair.append(struct.pack('<6I', r['CharHairGeosets'][0] + style, race, 0, style, 0, 1))
        for style in range(capacities[4]):
            for color in range(capacities[3]):
                section(2, style, color)
            facial.append(struct.pack('<8I', race, 0, style, 0, 0, 0, 0, 0))
        assert len(added) <= r['CharSections'][1] - r['CharSections'][0] + 1, 'CharSections allocation too small'
        styles = p.RawWdbc(result['BarberShopStyle'])
        for kind, field in ((0, 2), (2, 4), (3, 0)):
            donor = next(row for row in styles.records if p._value(row, 4) == kind)
            for value in range(capacities[field]):
                row = donor
                for offset, n in ((0, r['BarberShopStyle'][0] + len(barber)), (148, race), (152, 0), (156, value)):
                    row = p._replace(row, offset, 4, n)
                barber.append(row)
        assert len(barber) <= r['BarberShopStyle'][1] - r['BarberShopStyle'][0] + 1
        for name, new, strings in (('CharSections', added, pool), ('CharHairGeosets', hair, None),
                                   ('CharacterFacialHairStyles', facial, None), ('BarberShopStyle', barber, None)):
            result[name] = tables_lib.append_rows(result[name], name, new, strings)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def glue(original):
    result = {name: data.decode('utf-8-sig') for name, data in original.items()}

    def insert(name, anchor, text):
        result[name] = o._insert_once(result[name], anchor, text, 'Drakonid ' + name)

    for race, faction, donor, _, _ in SPECS:
        token, key = 'Drakonid' + faction.title(), ('Drakonid' + faction).upper()
        background = 'HUMAN' if race == 69 else 'ORC'
        insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
               f'    [{race}] = {{glueString="{key}", name="Drakonid", faction="{faction.title()}", '
               f'fileString="{token}"}},\n')
        result['CharacterInfo.lua'] += (f'\nRaceInfoByFileString.{key} = {{Name="Drakonid", '
                                        f'Description="Scaled dragonkin who have joined the {faction.title()}."}};\n')
        insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
               f'    ["{key}_MALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\UI-CharacterCreate-{token}Male",\n')
        insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', f'        ["{key}"] = "{background}",\n')
        anchor = ('        ["THINHUMAN"] = true,\n' if race == 69 else '    local hordeRaces = {\n')
        insert('GlueParent.lua', anchor, (f'        ["{key}"] = true,\n' if race == 69
                                          else f'        ["{key}"] = true,\n'))
        result['GlueParent.lua'] += (f'\nCharModelFogInfo.{key}=CharModelFogInfo.{background};\n'
                                     f'CharModelGlowInfo.{key}=CharModelGlowInfo.{background};\n'
                                     f'GlueAmbienceTracks.{key}=GlueAmbienceTracks.{background};\n')
        result['GlueStrings.lua'] += f'\n{key}="Drakonid"; {key}_MALE={key};\n'
        insert('ECS_Schema.lua', 'S.RaceOverride = {\n',
               f'    [{race}] = {{name="Drakonid", faction={1 if race == 69 else 2}, artKey="{token}"}},\n')
        insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
               f'    {{"{key}", {{name="Drakonid", faction={1 if race == 69 else 2}, artKey="{token}"}}}},\n')
        insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', f'    {token}=true,\n')
    refresh = re.search(r'        for i=1,5 do' + chr(92) + 'r?' + chr(92) + 'n            local frame = _G' + chr(92) + '["CharacterCustomizationButtonFrame"' + chr(92) + '.' + chr(92) + '.i' + chr(92) + '];',
                        result['CharacterCreate.lua'])
    assert refresh, 'Stock customization row layout changed'
    labels = ('        if CharacterCreate.selectedRaceID == 69 or CharacterCreate.selectedRaceID == 70 then' + chr(10)
              + '            CharacterCustomizationButtonFrame2Text:SetText("Head & Tail");' + chr(10)
              + '            CharacterCustomizationButtonFrame3Text:SetText("Horns");' + chr(10)
              + '            CharacterCustomizationButtonFrame4Text:SetText("Eye Color");' + chr(10)
              + '            _G["CharacterCustomizationButtonFrame5"]:Hide();' + chr(10)
              + '        end' + chr(10))
    result['CharacterCreate.lua'] = (result['CharacterCreate.lua'][:refresh.start()] + labels
                                     + result['CharacterCreate.lua'][refresh.start():])
    anchor = 'return race == 55 or race == 58 or race == 59 or race == 63 or race == 64;'
    assert result['CharacterCreate.lua'].count(anchor) == 1, 'male-only race list changed'
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(
        anchor, anchor[:-1] + ' or race == 69 or race == 70;')
    anchor = 'race == 63 or race == 64)) then\n                    fields[2] = race;'
    assert result['ECS_Integrate.lua'].count(anchor) == 1, 'ECS roster race list changed'
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace(
        anchor, 'race == 63 or race == 64 or race == 69 or race == 70)) then\n                    fields[2] = race;')
    anchor = 'raceModel == "THINHUMAN"'
    assert result['CharacterSelect.lua'].count(anchor) == 1
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(
        anchor, anchor + ' or raceModel == "DRAKONIDALLIANCE"', 1)
    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for text in result.values():
        compile_chunk(text)
    return {name: text.encode() for name, text in result.items()}


def appearance_catalog(original):
    magic, version, count = struct.unpack_from('<3I', original)
    stride = 12 + 16 * 144
    assert (magic, version) == (0x50504145, 2) and len(original) == 12 + count * stride
    assert all(struct.unpack_from('<I', original, 12 + i * stride)[0] not in (69, 70) for i in range(count))
    offsets = (0x28, 0x2C, 0x34, 0x24, 0x30)
    rows = []
    for race in (69, 70):
        row = bytearray(struct.pack('<3I', race, 0, len(LABELS)))
        for field, n, factor in codec()['descriptors']:
            row.extend(struct.pack('<4I', offsets[field], n, factor, 0) + bytes(128))
        row.extend(bytes((16 - len(LABELS)) * 144))
        assert len(row) == stride
        rows.append(bytes(row))
    return struct.pack('<3I', magic, version, count + 2) + original[12:] + b''.join(rows)


def geometry_catalog(original, skin):
    magic, version, count = struct.unpack_from('<3I', original)
    assert (magic, version) == (0x4D474145, 1)
    at = 12
    for _ in range(count):
        name = original[at:at + 128].split(b'\0')[0].decode()
        assert name.lower() != MODEL.lower(), 'Drakonid geometry already registered'
        at += 132 + struct.unpack_from('<I', original, at + 128)[0]
    assert at == len(original)
    return struct.pack('<3I', magic, version, count + 1) + original[12:] \
        + MODEL.encode().ljust(128, b'\0') + struct.pack('<I', len(skin)) + skin


def portrait():
    """Head-and-shoulders render used by the creator icon, roster portrait and character frame."""
    import subprocess
    import sethrak_equipment_repair as equipment_blender
    scene = EQUIP / 'previews/empty-slots'
    subprocess.run([str(equipment_blender.BLENDER), '-b', '--factory-startup', '--python',
                    str(Path(__file__).with_name('drakonid_portrait_blender.py')), '--', str(scene)],
                   stdout=subprocess.DEVNULL, check=True)
    target = STAGE / 'preview/portrait.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(scene / 'portrait.png', target)
    print('RENDERED portrait', target, flush=True)


def portrait_assets():
    import race_portrait_pack as portraits
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
    finally:
        files.close()
    art = Image.open(STAGE / 'preview/portrait.png').convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
    art.putalpha(portraits.circular_mask())
    plain = portraits.encode_portrait(art, template)
    icon = portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
    result = {}
    for faction in ('alliance', 'horde'):
        token = 'Drakonid' + faction.title()
        stem = portraits.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-Male-' + token
        result[portraits.CREATOR_ICON_ROOT + f'UI-CharacterCreate-{token}Male.blp'] = icon
        result[stem] = result[stem + '.blp'] = plain
        result[f'Interface\\Glues\\CharacterSelect\\ECS-Portrait-{token}Male.blp'] = plain
    return result


def pinned(directory, name):
    path = STAGE / directory / name
    return path.read_bytes() if path.exists() else None


def snapshot_glue(name):
    """Original creator/glue Lua from the pre-install archive snapshots (live copies already hold this race)."""
    storm = p.Storm(p.DLL_DEFAULT)
    for relative in (p.LOCALE_ARCHIVE_REL, p.GLOBAL_ARCHIVE_REL):
        snapshot = STAGE / 'baseline-archives' / relative
        if not snapshot.exists():
            continue
        handle = storm.open_archive(snapshot)
        try:
            return storm.read(handle, p.GLUE_ROOT + name)
        except Exception:
            continue
        finally:
            storm.dll.SFileCloseArchive(handle)
    return None


def catalog_baseline(name):
    """Catalog as it was before any Drakonid install; pinned from the verified install backup on first use."""
    path = STAGE / 'baseline-catalogs' / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        plan = p.load_json(STAGE / 'install-plan.json') if (STAGE / 'install-plan.json').exists() else None
        source = Path(plan['backup']) / 'client' / name if plan else p.CLIENT_DEFAULT / name
        path.write_bytes(source.read_bytes())
    return path.read_bytes()


def migration_sql():
    sql = ''
    for race, faction, donor, _, display in SPECS:
        sql += o.build_sql({'name': 'Drakonid', 'race_id': race, 'faction': faction,
                            'donor_start_race': donor, 'donor_totem_race': donor})
        sql = sql.rstrip() + '\n' + racials.racial_grant_sql(race) + '\n'
        sql += o.CHRRACES_TEMPLATE.format(race=race, faction_template=donor, male_display=display,
            female_display=0, prefix=PREFIX, base_language=7 if race == 69 else 1,
            file_string='Drakonid' + faction.title(), alliance=0 if race == 69 else 1, name='Drakonid')
    return sql.replace('ogre_furbolg_race_pack.py', 'drakonid_race_pack.py').rstrip() + '\n'


def stage():
    assert (STAGE / 'preview/portrait.png').exists(), 'Run the portrait action first'
    # Revisions rebuild from the pre-install baselines pinned by the first stage, never from live files
    # that already contain this race.
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        baseline = {name: pinned('baseline', name + '.dbc') or files.find(p.DBC_ROOT + name + '.dbc')[0]
                    for name in tables_lib.TABLES}
        original = {name: pinned('baseline', name) or snapshot_glue(name) or files.find(p.GLUE_ROOT + name)[0]
                    for name in tables_lib.GLUE}
        for name, data in original.items():
            (STAGE / 'baseline' / name).write_bytes(data)
        spell_baseline = files.find(p.DBC_ROOT + 'Spell.dbc')[0]
    finally:
        files.close()
    if not (STAGE / 'baseline/ChrRaces.dbc').exists():
        assert not (p.CLIENT_DEFAULT / ASSET).exists(), 'MPQ slot is occupied by an unpinned install'
    output, patched = tables(baseline), glue(original)
    # Spell.dbc is shared with the other racial packs, so it is rebuilt from whatever the client
    # ships now rather than pinned; racial rows already present are skipped.
    output['Spell'] = racials.merge_spell_table(spell_baseline)
    (STAGE / 'baseline').mkdir(parents=True, exist_ok=True)
    (STAGE / 'baseline/Spell.dbc').write_bytes(spell_baseline)
    for directory, values in (('baseline', baseline), ('client-dbc', output), ('glue', patched)):
        for name, data in values.items():
            path = STAGE / directory / (name if directory == 'glue' else name + '.dbc')
            path.parent.mkdir(parents=True, exist_ok=True)
            if directory == 'baseline' and path.exists():
                assert path.read_bytes() == data, 'Baseline changed'
            path.write_bytes(data)
    race_ids = {spec[0] for spec in SPECS}
    for name in tables_lib.SERVER_TABLES:
        path = STAGE / 'baseline-server' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            base = path.read_bytes()
        else:
            base = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
            path.write_bytes(base)
        source, target = p.RawWdbc(output[name]), p.RawWdbc(base)
        if name == 'CreatureModelData':
            rows = [row for row in source.records if p._value(row, 0) in {s[3] for s in SPECS}]
        elif name == 'CreatureDisplayInfo':
            rows = [row for row in source.records if p._value(row, 0) in {s[4] for s in SPECS}]
        else:
            rows = [row for race in sorted(race_ids) for row in p._table_rows_for_race(output[name], name, race)]
        p._ensure_id_free(base, name, {p._value(row, 0) for row in rows})
        pool = bytearray(target.strings)
        data = target.build(list(target.records) + [p._clone_strings(name, source, row, pool) for row in rows],
                            bytes(pool))
        path = STAGE / 'server/dbc' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    sql = migration_sql()
    if MIGRATION.exists():
        assert MIGRATION.read_text() == sql, 'Migration revision is occupied'
    MIGRATION.write_text(sql, encoding='utf-8', newline='\n')
    (STAGE / 'drakonid.sql').write_text(sql, encoding='utf-8', newline='\n')
    assets = model_assets()
    helmets, helmet_report = helmet_assets()
    assets.update(helmets)
    assets.update(portrait_assets())
    skin = assets[MODEL[:-3] + '00.skin']
    (STAGE / 'EsteriaAppearance.bin').write_bytes(appearance_catalog(catalog_baseline('EsteriaAppearance.bin')))
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(
        geometry_catalog(catalog_baseline('EsteriaAppearanceGeometry.bin'), skin))
    catalog, bank, count = selection_catalog()
    (STAGE / 'EsteriaDrakonid.bin').write_bytes(catalog)
    (STAGE / 'EsteriaDrakonidTextures.bin').write_bytes(bank)
    (STAGE / 'EsteriaDrakonidCoverage.bin').write_bytes(coverage_catalog())
    for key, data in assets.items():
        path = local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    replacements = {p.DBC_ROOT + name + '.dbc': data for name, data in output.items()}
    replacements.update({p.GLUE_ROOT + name: data for name, data in patched.items()})
    storm = p.Storm(p.DLL_DEFAULT)
    dest = STAGE / 'client' / ASSET
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()  # a revision regenerates its own staged archive
    storm.create_archive(dest, assets)
    report = {'race_ids': sorted(race_ids), 'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe'),
              'assets': {key: hashlib.sha256(value).hexdigest() for key, value in assets.items()},
              'selection_records': count, 'helmet_families': helmet_report['families'],
              'helmet_families_moved': helmet_report['moved'], 'helmet_families_missing': helmet_report['missing'],
              'helmet_families_from_human': helmet_report['from_human'],
              'archive_baselines': {}, 'archives': {str(ASSET): p.sha256(dest)},
              'catalogs': {name: p.sha256(STAGE / name) for name in (
                  'EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin', 'EsteriaDrakonid.bin',
                  'EsteriaDrakonidTextures.bin', 'EsteriaDrakonidCoverage.bin')},
              'catalog_baselines': {name: hashlib.sha256(catalog_baseline(name)).hexdigest() for name in (
                  'EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin')},
              'migration': str(MIGRATION), 'status': 'staged_build_and_install_required', 'live_installed': False}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live = p.CLIENT_DEFAULT / relative
        snapshot, target = STAGE / 'baseline-archives' / relative, STAGE / 'client' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            shutil.copy2(live, snapshot)
        before = p.sha256(snapshot)  # pre-install baseline, pinned by the first stage
        print('STAGING', relative, flush=True)
        live_hash = p.sha256(live)
        o.rebuild_archive_replacing(storm, snapshot, target, replacements, compress=True)
        assert p.sha256(live) == live_hash, 'Live archive changed during staging'
        report['archive_baselines'][str(relative)] = before
        report['archives'][str(relative)] = p.sha256(target)
    save(STAGE / 'report.json', report)
    print('STAGED Drakonid races 69/70', STAGE, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('config', 'portrait', 'stage'))
    args = parser.parse_args()
    {'config': config, 'portrait': portrait, 'stage': stage}[args.action]()
