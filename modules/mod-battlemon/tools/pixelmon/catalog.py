"""Resolve Battlemon forms against Pixelmon metadata without guessing numeric variants."""
import csv
import json
import math
from pathlib import Path
import re
import unicodedata

SAMPLE_DEX = [2, 3, 5, 6, 8, 9, 10, 12, 15, 16, 19, 37, 41, 54, 58, 63, 66, 72, 74, 77,
              81, 92, 95, 100, 109, 115, 123, 129, 130, 132, 133, 143, 147, 150, 201, 249,
              384, 479, 778, 1000]
SAMPLE_VARIANTS = ['Mega Venusaur', 'Mega Charizard X', 'Mega Charizard Y', 'Mega Blastoise',
                   'Alolan Rattata', 'Alolan Vulpix', 'Galarian Meowth', 'Magikarp (Female)',
                   'Heat Rotom', 'Pikachu (02)']


class Unsupported(ValueError):
    pass


def normalized(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', name.lower())


def choose_form(form, species):
    options = {f['name']: f for f in species['forms']}
    aliases = json.loads(Path(__file__).with_name('variant_aliases.json').read_text(encoding='utf8'))
    alias = next((a for a in aliases['aliases'] if str(a['form']) == str(form.get('id'))), None)
    if alias:
        if (alias['dex'] != species.get('dex') or alias['name'] != form['name']
                or alias['sprite'] != form.get('sprite') or alias['source_form'] not in options):
            raise Unsupported('verified_variant_alias_identity_changed')
        return options[alias['source_form']], alias['gender']
    gender = 'FEMALE' if 'female' in form['variant'].lower() or normalized(form['name']).startswith('female') else 'ALL'
    if gender == 'FEMALE' and 'female' in options:
        return options['female'], 'ALL'
    if not form['variant'] or form['variant'] == 'female':
        defaults = species.get('defaultForms', [])
        if len(defaults) == 1 and defaults[0] in options:
            return options[defaults[0]], gender
        if 'base' in options:
            return options['base'], gender
        # Explicit default identities reviewed against Battlemon's front sprites.
        defaults_by_dex = {201: 'a', 412: 'plant', 413: 'plant', 422: 'west', 423: 'west',
                           550: 'red', 585: 'spring', 586: 'spring', 741: 'baile', 745: 'midday',
                           849: 'amped', 854: 'phony', 855: 'phony', 876: 'male',
                           892: 'singlestrike', 902: 'male', 916: 'male', 931: 'green',
                           978: 'curly', 1012: 'counterfeit', 1013: 'unremarkable'}
        key = defaults_by_dex.get(species.get('dex'))
        if key in options:
            return options[key], gender
        raise Unsupported('ambiguous_default_form')
    # Strip the species name; remaining descriptive text must match an explicit Pixelmon form.
    label = normalized(form['name']).replace(normalized(species['name']), '')
    if species.get('dex') == 201 and form['name'].lstrip().startswith(('?', '!')):
        return options['question' if '?' in form['name'] else 'exclamation'], gender
    # These species express color/pattern variants as palettes, not forms.
    if species.get('dex') in {666, 669, 670, 671} and not any(c.isdigit() for c in label):
        key = 'az' if label == 'eternalflower' else 'base'
        return options[key], gender
    if species.get('dex') == 774 and label.endswith('core'):
        return options['core'], gender
    if label == 'female' and 'base' in options:
        return options['base'], 'FEMALE'
    # Remove descriptive suffixes used by the addon, not semantic form words.
    label = re.sub(r'(forme|form|cloak|mode|type|drive|trim|style|pattern|sea|striped)', '', label)
    aliases = {'sunny': 'sun', 'rainy': 'rain', 'snowy': 'ice', 'galarianstandard': 'galarian',
               '10%': 'tenpercent', '10': 'tenpercent', 'duskmane': 'dusk', 'dawnwings': 'dawn',
               'crownedsword': 'crowned', 'crownedshield': 'crowned'}
    label = aliases.get(label, label)
    candidates = [f for key, f in options.items() if normalized(key) == label]
    if len(candidates) != 1:
        raise Unsupported('unmapped_variant:' + form['name'])
    return candidates[0], gender


def resource_path(source, value):
    if not isinstance(value, str) or not value.startswith('pixelmon:'):
        raise Unsupported('unsupported_resource:' + str(value))
    relative = value.split(':', 1)[1]
    assets = (source/'assets/pixelmon').resolve()
    for folder in ['textures', 'models']:
        path = (assets/folder/relative).resolve()
        if not path.is_relative_to(assets):
            raise Unsupported('resource_path_escape')
        if path.is_file():
            return path
    raise Unsupported('missing_asset:' + relative)


def select_animations(definition):
    # Current SMDModelLoader preserves declaration order; Scene.getAnimation returns
    # the first matching name. This is not the legacy QC loader's last-write map.
    animations = {}
    duplicate = False
    for entry in definition.get('animations', []):
        duplicate |= entry['type'] in animations
        animations.setdefault(entry['type'], entry['animation'])
    if animations and 'idle' not in animations:
        raise Unsupported('missing_idle')
    return animations, duplicate


def resolve_appearance(source, form, species, shiny):
    source_form, gender = choose_form(form, species)
    genders = {g['gender']: g for g in source_form.get('genderProperties', [])}
    # Base sprites conventionally use the male appearance when a species is sexually dimorphic.
    group = genders.get('FEMALE', genders.get('ALL')) if gender == 'FEMALE' else genders.get('ALL', genders.get('MALE'))
    if not group:
        raise Unsupported('missing_gender:' + gender)
    palette_name = 'shiny' if shiny else 'none'
    aliases = json.loads(Path(__file__).with_name('variant_aliases.json').read_text(encoding='utf8'))
    alias = next((a for a in aliases['aliases'] if str(a['form']) == str(form.get('id'))), None)
    if alias and alias.get('palettes'):
        palette_name = alias['palettes']['shiny' if shiny else 'normal']
    dex = species.get('dex')
    label = normalized(form['name']).replace(normalized(species['name']), '')
    color = None
    if dex == 666:
        color = label.removesuffix('pattern') or 'archipelago'
    elif dex in {669, 670, 671} and source_form['name'] == 'base':
        color = label.removesuffix('flower') or 'red'
    elif dex == 774:
        color = label.removesuffix('core') or 'red'
    if color is not None:
        candidates = [p for p in group.get('palettes', [])
                      if normalized(p['name']) == color + ('shiny' if shiny else '')]
        if shiny and dex == 774:
            candidates = [p for p in group.get('palettes', []) if p['name'] == 'shiny']
        palette = candidates[0] if len(candidates) == 1 else None
    else:
        palette = next((p for p in group.get('palettes', []) if p['name'] == palette_name), None)
    if not palette:
        raise Unsupported('missing_palette')
    groups = palette.get('models', [])
    always = [g for g in groups if g.get('model_predicate', {}).get('type') == 'pixelmon:always']
    if len(always) == 1:
        chosen = always[0]
    elif len(groups) == 1 and groups[0].get('model_predicate', {}).get('type') == 'pixelmon:flying':
        chosen = groups[0]
    else:
        raise Unsupported('ambiguous_model_predicates')
    definitions = chosen.get('models', [])
    if isinstance(definitions, dict) and set(definitions) == {'smooth'}:
        definitions = definitions['smooth']
    if not isinstance(definitions, list):
        raise Unsupported('unsupported_models_schema')
    if not definitions:
        raise Unsupported('empty_model_definitions')
    if len(definitions) == 1 and definitions[0].get('model_type') == 'pixelmon:assimp':
        from glb_pipeline import resolve
        return resolve(source, species, source_form, group, palette, definitions[0])
    supported = {'texture', 'model', 'animations', 'scale', 'emissive', 'movement_threshold', 'animation_increment',
                 'offsets', 'rotate_angle'}
    cleaned = []
    legacy_transparency = []
    for part_index, part in enumerate(definitions):
        part = dict(part)
        # Empty attachment metadata has no geometry or runtime transform to apply.
        if part.get('attachments') == []:
            part.pop('attachments')
        if 'texture_transparency' in part:
            # Pixelmon 9.4 ModelData's 12-field codec has no such field. The current
            # SMD loader uses model/texture/animations, and render color comes from
            # RenderContext. Record this obsolete JSON value, never apply fake opacity.
            value = part.pop('texture_transparency')
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 1):
                raise Unsupported('invalid_legacy_texture_transparency')
            legacy_transparency.append(dict(part=part_index, value=value))
        unknown = set(part) - supported
        if unknown:
            raise Unsupported('model_modifiers:' + ','.join(sorted(unknown)))
        cleaned.append(part)
    definition = cleaned[0]
    transforms = []
    if (any('offsets' in p or 'rotate_angle' in p for p in cleaned)
            or any(p.get('scale',1) != definition.get('scale',1) for p in cleaned)):
        from model_transform import source_matrix
        try:
            transforms = [source_matrix(p).tolist() for p in cleaned]
        except ValueError as error:
            raise Unsupported('model_transform:' + str(error)) from error
    if len(cleaned) > 1:
        # Independently bound meshes can share a timeline, but don't silently ignore
        # relative scales, animation rates, or lighting differences between parts.
        for part in cleaned:
            if part.get('animation_increment', 1) != definition.get('animation_increment', 1):
                raise Unsupported('multipart_transform_or_timing_mismatch')
    model = resource_path(source, definition.get('model'))
    if model.suffix.lower() != '.bmd':
        raise Unsupported('model_format:' + model.suffix)
    animations, duplicate = select_animations(definition)
    source_motion = 'animated' if animations else 'static_bind_pose'
    if not animations and len(cleaned) > 1:
        raise Unsupported('multipart_static_timeline_requires_review')
    movement = next((name for name in ['walk', 'fly', 'swim'] if name in animations), 'idle')
    notes = []
    if legacy_transparency:
        notes.append('legacy_texture_transparency_ignored_by_pixelmon_9_4_loader')
    if transforms:
        notes.append('source_model_transform_applied_before_grounding')
    if duplicate:
        notes.append('duplicate_animation_first_declared')
    if source_motion == 'static_bind_pose':
        notes.append('source_has_no_animations_static_bind_pose')
    if gender == 'FEMALE' and group['gender'] == 'ALL':
        notes.append('pixelmon_shared_gender_model')
    if movement != 'walk':
        notes.append('locomotion_uses_' + movement)
    increment = float(definition.get('animation_increment', 1))
    if not 0 < increment <= 4:
        raise Unsupported('unsupported_animation_rate')
    parts = []
    if len(cleaned) > 1:
        for part_index, part in enumerate(cleaned):
            part_animations, part_duplicate = select_animations(part)
            if not part_animations:
                raise Unsupported('multipart_static_timeline_requires_review')
            if part_duplicate and 'duplicate_animation_first_declared' not in notes:
                notes.append('duplicate_animation_first_declared')
            move = next((n for n in ['walk', 'fly', 'swim'] if n in part_animations), 'idle')
            parts.append(dict(model=str(resource_path(source, part.get('model'))),
                              texture=str(resource_path(source, part.get('texture'))),
                              animations={k: str(resource_path(source, part_animations[n]))
                                          for k, n in [('idle', 'idle'), ('walk', move)]},
                              source_transform=transforms[part_index] if transforms else None,
                              emissive=str(resource_path(source, part['emissive'])) if part.get('emissive') else None))
    return dict(model=str(model), texture=str(resource_path(source, definition.get('texture'))),
                emissive=str(resource_path(source, definition['emissive'])) if definition.get('emissive') else None,
                animations={key: str(resource_path(source, animations[value]))
                            for key, value in [('idle', 'idle'), ('walk', movement)]} if animations else {},
                fps=30*increment, source_form=source_form['name'], source_palette=palette['name'],
                gender=group['gender'], notes=notes,
                parts=parts, source_motion=source_motion, legacy_texture_transparency=legacy_transparency,
                source_transform=transforms[0] if transforms else None)


def inventory(source, client):
    with (client/'Interface/AddOns/Battlemon/Data/csv/forms.csv').open(encoding='utf-8-sig') as file:
        forms = list(csv.DictReader(file))
    species = {}
    for path in sorted((source/'data/pixelmon/species').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf8'))
        dex = int(data['dex'])
        if dex in species:
            raise ValueError('Duplicate species dex: ' + str(dex))
        species[dex] = data
    entries = []
    for form in forms:
        entry = dict(form=int(form['id']), dex=int(form['species_id']), name=form['name'], appearances=[])
        for shiny in [False, True]:
            appearance = dict(shiny=shiny)
            try:
                if entry['dex'] not in species:
                    raise Unsupported('missing_species')
                appearance.update(resolve_appearance(source, form, species[entry['dex']], shiny))
                appearance['status'] = 'mapped'
            except Unsupported as error:
                appearance.update(status='unsupported', reason=str(error))
            entry['appearances'].append(appearance)
        entries.append(entry)
    sample = [int(next(f['id'] for f in forms if int(f['species_id']) == dex and not f['variant']))
              for dex in SAMPLE_DEX]
    sample.extend(int(next(f['id'] for f in forms if f['name'] == name)) for name in SAMPLE_VARIANTS)
    assert len(sample) == len(set(sample)) == 50
    return entries, sample
