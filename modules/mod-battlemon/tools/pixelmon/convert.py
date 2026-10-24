"""Generate the four-species Pixelmon test layer; never modifies base assets/DBCs."""
import argparse
from io import BytesIO
import csv
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from m2 import prepare, build_model
from texture import pad_islands

PILOT = [(1, 1, 'bulbasaur'), (6, 4, 'charmander'), (11, 7, 'squirtle'), (37, 25, 'pikachu')]
LAYER = '.dbc9-battlemon-3d'
MODULE = Path(__file__).resolve().parents[2]


class Dbc:
    def __init__(self, path):
        data = Path(path).read_bytes()
        if data[:4] != b'WDBC':
            raise ValueError(f'Invalid DBC: {path}')
        count, self.fields, stride, size = struct.unpack_from('<4I', data, 4)
        if stride != self.fields*4 or len(data) != 20 + count*stride + size:
            raise ValueError('DBC layout mismatch')
        self.rows = {}
        for i in range(count):
            row = list(struct.unpack_from(f'<{self.fields}I', data, 20+i*stride))
            if row[0] in self.rows:
                raise ValueError('Duplicate DBC ID')
            self.rows[row[0]] = row
        self.strings = data[20+count*stride:]

    def string(self, offset):
        end = self.strings.index(b'\0', offset)
        return self.strings[offset:end].decode('utf8')


def float_bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def write_dbc(path, rows, fields, strings):
    pool = bytearray(b'\0')
    records = []
    for original, replacements in rows:
        row = original.copy()
        for column in strings:
            value = replacements[column]
            row[column] = len(pool) if value else 0
            if value:
                pool.extend(value.encode('utf8') + b'\0')
        records.append(struct.pack(f'<{fields}I', *row))
    path.write_bytes(b'WDBC' + struct.pack('<4I', len(rows), fields, fields*4, len(pool))
                     + b''.join(records) + pool)


def write_blp(path, source):
    image = Image.open(source).convert('RGBA')
    # Resample the full image (never pad its canvas): normalized UVs stay fixed.
    dimensions = tuple(1 << (n-1).bit_length() for n in image.size)
    if max(dimensions) > 4096:
        raise ValueError(f'Texture exceeds the 4096 pixel export limit: {source}')
    if image.size != dimensions:
        image = image.resize(dimensions, Image.Resampling.LANCZOS)
    width, height = image.size
    offsets, sizes, chunks = [0]*16, [0]*16, []
    position = 148+1024
    mip = pad_islands(image, 8)
    while True:
        dds = BytesIO()
        encoded = mip if min(mip.size) >= 4 else mip.resize((max(4, mip.width), max(4, mip.height)))
        encoded.save(dds, format='DDS', pixel_format='DXT5')
        raw = dds.getvalue()[128:]
        expected = ((mip.width+3)//4)*((mip.height+3)//4)*16
        if len(raw) != expected:
            raise ValueError('Unexpected DDS encoder layout')
        i = len(chunks)
        offsets[i], sizes[i] = position, len(raw)
        chunks.append(raw)
        position += len(raw)
        if mip.size == (1, 1):
            break
        mip = mip.resize((max(1, mip.width//2), max(1, mip.height//2)), Image.Resampling.BOX)
        mip = pad_islands(mip, 2)
    path.write_bytes(b'BLP2' + struct.pack('<I4B2I', 1, 2, 8, 7, 1, width, height)
                     + struct.pack('<16I', *offsets) + struct.pack('<16I', *sizes)
                     + bytes(1024) + b''.join(chunks))
    # Decode through Pillow's independent BLP reader, also used by preview tooling.
    decoded = Image.open(path).convert('RGBA')
    if decoded.size != image.size:
        raise ValueError('BLP round-trip dimension mismatch')


def generate(args):
    source = args.pixelmon.resolve()
    client = args.client.resolve()
    target = args.output.resolve()
    dbc_dir = client / 'Data/patch-z.mpq/DBFilesClient'
    display = Dbc(dbc_dir / 'CreatureDisplayInfo.dbc1-battlemon')
    model = Dbc(dbc_dir / 'CreatureModelData.dbc1-battlemon')
    if (display.fields, model.fields) != (16, 28):
        raise ValueError('Expected WotLK DBC field counts')
    with (client / 'Interface/AddOns/Battlemon/Data/csv/forms.csv').open(encoding='utf-8-sig') as f:
        forms = {int(row['id']): row for row in csv.DictReader(f)}
    asset_dir = target / 'client/Creature/Battlemon3D'
    client_dbc = target / 'client/DBFilesClient'
    server_dbc = target / 'server/dbc-continuations'
    for directory in (asset_dir, client_dbc, server_dbc):
        directory.mkdir(parents=True, exist_ok=True)
    display_rows, model_rows, report = [], [], []
    for form_id, dex, name in PILOT:
        form = forms[form_id]
        if int(form['species_id']) != dex or form['variant']:
            raise ValueError(f'Pilot form mapping changed: {form}')
        folder = source / f'assets/pixelmon/textures/pokemon/{dex:03}_{name}/all/base'
        reference = folder / f'none/{name}.bmd'
        animations = {animation: folder / f'none/{animation}.bmd' for animation in ['idle', 'walk']}
        mesh = prepare(reference, animations, fps=args.fps)
        for shiny in [False, True]:
            stem = form['sprite'] + ('_shiny' if shiny else '')
            display_id = (60000 if shiny else 50000) + form_id
            row = display.rows[display_id].copy()
            model_id = row[1]
            mr = model.rows[model_id].copy()
            old_model = model.string(mr[2])
            if not old_model.lower().startswith('creature\\battlemon\\'):
                raise ValueError(f'Refusing non-Battlemon model override: {old_model}')
            texture = folder / ('shiny' if shiny else 'none') / 'texture.png'
            m2_path = asset_dir / (stem+'.m2')
            m2, skin = build_model(mesh, stem, f'Creature\\Battlemon3D\\{stem}.blp')
            m2_path.write_bytes(m2)
            (asset_dir / (stem+'00.skin')).write_bytes(skin)
            write_blp(asset_dir / (stem+'.blp'), texture)
            mn, mx = mesh['bounds']
            mr[1] = 0
            mr[4] = float_bits(1)
            mr[14] = float_bits(max(mx[0]-mn[0], mx[1]-mn[1]))
            mr[15] = float_bits(mx[2]-mn[2])
            mr[17:23] = [float_bits(v) for v in [*mn, *mx]]
            row[4] = float_bits(1)
            model_rows.append((mr, {2: f'Creature\\Battlemon3D\\{stem}.mdx'}))
            display_rows.append((row, {column: '' for column in [6, 7, 8, 9]}))
            report.append(dict(name=form['name'], form=form_id, shiny=shiny, display=display_id,
                               model=model_id, asset=stem, vertices=len(mesh['vertices']),
                               triangles=len(mesh['triangles'])//3, bones=len(mesh['bones']),
                               animations=[dict(id=s['id'], name=s['name'], duration_ms=s['duration'])
                                           for s in mesh['sequences']],
                               bounds=[mn.tolist(), mx.tolist()],
                               max_four_weight_error=mesh['skinning_error'],
                               max_dropped_weight=mesh['max_dropped_weight'],
                               source=str(reference), source_sha256=hashlib.sha256(reference.read_bytes()).hexdigest()))
            print(stem, len(mesh['vertices']), 'vertices,', len(mesh['bones']), 'bones', flush=True)
    for name, rows, fields, strings in [('CreatureModelData', model_rows, 28, [2]),
                                       ('CreatureDisplayInfo', display_rows, 16, [6, 7, 8, 9])]:
        path = client_dbc / (name+LAYER)
        write_dbc(path, rows, fields, strings)
        (server_dbc/path.name).write_bytes(path.read_bytes())
    files = {str(p.relative_to(target)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
             for subdir in ['client', 'server'] for p in (target/subdir).rglob('*') if p.is_file()}
    manifest = dict(schema=1, layer=LAYER, fps=args.fps, models=report, files=files,
                    texture_padding=dict(base_pixels=8, per_mip_pixels=2))
    (target/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')
    print('Generated', len(report), 'models in', target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixelmon', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=MODULE/'generated/pixelmon-3d')
    parser.add_argument('--fps', type=float, default=30)
    args = parser.parse_args()
    if not 0 < args.fps <= 120:
        parser.error('--fps must be between 0 and 120')
    generate(args)
