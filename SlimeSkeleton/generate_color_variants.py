"""Recolor the slime without resampling, then composite it over the unchanged skeleton."""

import colorsys
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
COLORS = [
    ('crimson', '#D93447'), ('scarlet', '#F04A2F'), ('ember_orange', '#EF7C2B'),
    ('peach', '#EFA87D'), ('amber', '#D99A28'), ('lemon', '#D6CD36'),
    ('chartreuse', '#A2C936'), ('lime', '#63D63C'), ('toxic_green', '#2DC350'),
    ('emerald', '#209769'), ('jade', '#48BD9B'), ('mint', '#98DCC2'),
    ('teal', '#2BA8A2'), ('turquoise', '#35CFD2'), ('ice_blue', '#9DDCEB'),
    ('sky_blue', '#52AFE4'), ('azure', '#3679DE'), ('cobalt', '#3D4CC0'),
    ('indigo', '#6651BF'), ('violet', '#9655CB'), ('lilac', '#C7A0DD'),
    ('magenta', '#CC43BC'), ('hot_pink', '#E959A3'), ('rose', '#CB6E89'),
    ('wine', '#7B304A'), ('bronze', '#9C7545'), ('copper', '#BD673D'),
    ('pearl', '#D8DBD7'), ('silver', '#9AA3AC'), ('charcoal', '#414A53'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = [ROOT / 'SkeletonUnderlay.png', ROOT / 'SlimeOverlay.png']
    source_hashes = {path.name: digest(path) for path in sources}
    underlay, overlay = [Image.open(path).convert('RGBA') for path in sources]
    assert underlay.size == overlay.size == (512, 512)
    original = np.asarray(overlay)
    skeleton = np.asarray(underlay)
    visible = original[:, :, 3] > 0
    untouched = ~visible
    baseline = np.asarray(Image.alpha_composite(underlay, overlay))
    rgb, inverse = np.unique(original[:, :, :3][visible], axis=0, return_inverse=True)
    hls = np.array([colorsys.rgb_to_hls(*(pixel / 255)) for pixel in rgb])
    base_hue, base_light, base_saturation = colorsys.rgb_to_hls(*(original[400, 100, :3] / 255))
    output = ROOT / 'ColorVariants'
    output.mkdir(exist_ok=False)
    for name in ('CompleteSkins', 'RecoloredOverlays'):
        (output / name).mkdir()
    width, height = overlay.size
    # Every preview tile also stays at native resolution; labels occupy separate padding.
    preview = Image.new('RGB', (width * 6, (height + 32) * 5), '#25282D')
    draw = ImageDraw.Draw(preview)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
    records = []
    for index, (name, color) in enumerate(COLORS, 1):
        target = tuple(int(color[at:at + 2], 16) / 255 for at in (1, 3, 5))
        hue, light, saturation = colorsys.rgb_to_hls(*target)
        edited = hls.copy()
        edited[:, 0] = (edited[:, 0] + hue - base_hue) % 1
        edited[:, 2] = np.clip(edited[:, 2] * saturation / base_saturation, 0, 1)
        if light < base_light:
            edited[:, 1] *= light / base_light
        else:
            edited[:, 1] = 1 - (1 - edited[:, 1]) * (1 - light) / (1 - base_light)
        palette = np.rint(np.array([colorsys.hls_to_rgb(*pixel) for pixel in edited]) * 255).astype(np.uint8)
        pixels = original.copy()
        pixels[visible, :3] = palette[inverse]
        recolored = Image.fromarray(pixels)
        combined = Image.alpha_composite(underlay, recolored)
        tag = f'{index:02d}_{name}'
        overlay_path = output / 'RecoloredOverlays' / f'slime_overlay_{tag}.png'
        skin_path = output / 'CompleteSkins' / f'slimeskeleton_skin_{tag}.png'
        recolored.save(overlay_path)
        combined.save(skin_path)
        actual = np.asarray(Image.open(skin_path))
        saved_overlay = np.asarray(Image.open(overlay_path))
        assert combined.size == overlay.size and Image.open(skin_path).size == overlay.size
        assert np.array_equal(saved_overlay[:, :, 3], original[:, :, 3])
        assert np.array_equal(actual[:, :, 3], baseline[:, :, 3])
        assert np.array_equal(actual[untouched], skeleton[untouched]), 'Skeleton pixels changed'
        assert np.array_equal(saved_overlay[untouched], original[untouched]), 'Transparent pixels changed'
        x, y = ((index - 1) % 6) * width, ((index - 1) // 6) * (height + 32)
        preview.paste(Image.alpha_composite(Image.new('RGBA', combined.size, '#30343A'), combined).convert('RGB'),
                      (x, y))
        draw.text((x + 10, y + height + 5), f'{index:02d}  {name.replace("_", " ").title()}',
                  fill='white', font=font)
        records.append({'name': name, 'base_color': color, 'skin': str(skin_path.relative_to(output)),
                        'overlay': str(overlay_path.relative_to(output)), 'skin_sha256': digest(skin_path),
                        'overlay_sha256': digest(overlay_path)})
    assert len(set(row['skin_sha256'] for row in records)) == len(COLORS)
    assert {path.name: digest(path) for path in sources} == source_hashes, 'Source files changed'
    preview.save(output / 'Preview.png')
    manifest = {'count': len(records), 'size': [width, height], 'mode': 'RGBA',
                'method': 'HLS recoloring with relative hue and shading preserved; exact alpha composite at (0, 0)',
                'source_sha256': source_hashes, 'source_files_unchanged': True,
                'alpha_preserved': True, 'skeleton_pixels_unchanged': True,
                'resized_or_cropped': False, 'variants': records}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    with ZipFile(output / 'CompleteSkins.zip', 'w', compression=ZIP_DEFLATED) as archive:
        for row in records:
            archive.write(output / row['skin'], Path(row['skin']).name)
    print(f'Created and validated {len(records)} complete 512x512 RGBA skins: {output}')


if __name__ == '__main__':
    main()
