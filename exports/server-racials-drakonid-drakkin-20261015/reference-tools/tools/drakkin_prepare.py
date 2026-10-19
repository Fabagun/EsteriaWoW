"""Convert the supplied body with its exact animation FileDataID mapping, without touching inputs."""
import copy
import hashlib
import json
from pathlib import Path
import struct

from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.convert import _collect_anims
from wotlkconv.m2.downgrade import downgrade_model
from wotlkconv.m2.skin import downgrade_skin, write_skin
from wotlkconv.listfile import Listfile
from wotlkconv.options import Options
from wotlkconv.resolve import AssetSource
from wotlkconv.report import FileResult
import highmountain_complete_tracks as tracks
import vrykul_female_pack as arrays

ROOT = Path('G:/RetroPorterWork/kobold')
SOURCE = Path('G:/Kobold/KoboldTestV25')
PREFIX = 'custom\\kobold\\'

def main():
    out = ROOT / 'converted'
    out.mkdir(parents=True, exist_ok=True)
    entries = json.loads((SOURCE / 'patch.json').read_text())['files']
    list_path = ROOT / 'source-listfile.csv'
    list_path.write_text(''.join(f"{f['id']};{f['file']}\n" for f in entries), encoding='utf-8')
    listing = Listfile.load(str(list_path))
    source = AssetSource(listing, [SOURCE])
    model = parse_m2((SOURCE / 'koboldfemale.m2').read_bytes())
    original = copy.deepcopy(model)
    # Only body and eye slots are drawn by this supplied SKIN; unused Retail materials have no surfaces.
    model.texture_file_ids = [0] * len(model.textures)
    for texture in model.textures:
        texture.update(type=0, filename=PREFIX + 'koboldeyes00_00.blp')
    model.textures[0].update(type=8, filename='')
    model.textures[9].update(type=0, filename=PREFIX + 'koboldeyes00_00.blp')
    missing = {ref.anim_id for ref in model.anim_file_ids if source.by_file_id(ref.file_id, '.anim') is None}
    assert missing == {1220, 1492, 1770}, missing
    removed_indices = {i for i, q in enumerate(model.sequences) if q['id'] in missing}
    for q in model.sequences:
        if q['flags'] & 0x40:
            assert q['alias_next'] not in removed_indices, 'Missing action is an alias target'
    for track in model.tracks():
        for i in removed_indices:
            assert track.global_sequence < 0 or i not in track.external
            if i < len(track.timestamps):
                track.timestamps[i] = []
            if hasattr(track, 'values') and i < len(track.values):
                track.values[i] = []
            track.external.discard(i)
            if i < len(track.timestamp_spans):
                track.timestamp_spans[i] = (0, 0)
            if hasattr(track, 'value_spans') and i < len(track.value_spans):
                track.value_spans[i] = (0, 0)
    for i in removed_indices:
        model.sequences[i]['flags'] |= 0x20
    model.anim_file_ids = [ref for ref in model.anim_file_ids if ref.anim_id not in missing]
    opts = Options()
    result = FileResult(source='koboldfemale.m2', kind='m2')
    downgrade_model(model, opts, listing, source, result)
    assert result.ok, result
    for asset in _collect_anims(model, 'koboldfemale', source, opts, result):
        assert asset.result.ok and asset.data, asset.result
        (out / asset.filename).write_bytes(asset.data)
    tracks.embed(model, out, 'koboldfemale')
    model.replacable_texture_lookup = [65535] * 16
    model.replacable_texture_lookup[8] = 0
    skin = parse_skin((SOURCE / 'koboldfemale00.skin').read_bytes())
    skin_result = FileResult(source='koboldfemale00.skin', kind='skin')
    assert downgrade_skin(skin, opts, bool(model.texture_combiner_combos), skin_result), skin_result
    for i, mesh in enumerate(skin.submeshes):
        mesh = bytearray(mesh)
        struct.pack_into('<H', mesh, 0, 0)
        skin.submeshes[i] = bytes(mesh)
    payload, separated = arrays.separate_bone_track_arrays(write_md20(model))
    (out / 'koboldfemale.m2').write_bytes(payload)
    (out / 'koboldfemale00.skin').write_bytes(write_skin(skin))
    parsed = parse_m2(payload)
    assert parsed.version == 264 and parsed.vertices == original.vertices
    assert all(q['flags'] & 0x20 for q in parsed.sequences)
    assert all(not t.external for t in parsed.tracks())
    report = {'source_model_sha256': hashlib.sha256((SOURCE / 'koboldfemale.m2').read_bytes()).hexdigest(),
              'vertices': parsed.vertex_count, 'bones': len(parsed.bones), 'sequences': len(parsed.sequences),
              'missing_unused_modern_actions': sorted(missing), 'all_available_animation_tracks_embedded': True,
              'shared_track_arrays_separated': separated, 'source_geosets': [3301, 3502, 4102],
              'armor_meshes_supplied': False, 'conversion_diagnostics': str(result),
              'source_hashes': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for root in (SOURCE, Path('G:/Kobold/KoboldColours_FIX')) for p in root.iterdir() if p.is_file()}}
    (ROOT / 'conversion.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
