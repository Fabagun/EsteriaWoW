"""Give the converted Vulpera Lightbringer Greathelm the draw passes of its stock Human counterpart.

The stock `Helm_Plate_RaidPaladin_F_01` draws its reflective base once more with the helmet texture alpha-blended
on top, and never layers the glow map. The retail-derived `*_VuF/_VuM` versions lack that overlay pass and layer
the glow map onto the metal, which the 3.3.5a client renders differently from retail. This restores the stock
pass structure; vertices, bones, submeshes and the other batches stay byte-identical.
"""

import argparse
import hashlib
from pathlib import Path
import re
import shutil

from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

import retroported_race_pack as p
import ogre_furbolg_race_pack as o
import skyborne_visual_pack as visual

ARCHIVE = Path('Data/enUS/patch-enUS-Z.MPQ')
HELMET = re.compile(r'^item\\objectcomponents\\head\\helm_plate_raidpaladin_f_01_vu[fm]\.m2$', re.IGNORECASE)


def repair(storm, handle, names):
    replacements, report = {}, {}
    for name in names:
        if not HELMET.match(name):
            continue
        model = parse_m2(storm.read(handle, name))
        stem = name[:-3]
        # The stock model also sets global flag 0x8 and a combiner table [Mod, Add] for its two-layer pass; the
        # retail-derived model has neither, so the client falls back to its default two-layer combiner.
        fixed = parse_m2(storm.read(handle, name))
        fixed.global_flags = 8328
        fixed.texture_combiner_combos = [1, 4]
        replacements[name] = write_md20(fixed)
        report[name] = 'header'
        for skin_name in (n for n in names if n.lower().startswith(stem.lower()) and n.lower().endswith('.skin')
                          and re.fullmatch(r'\d\d\.skin', n[len(stem):], re.IGNORECASE)):
            skin = parse_skin(storm.read(handle, skin_name))
            changed, batches = 0, []
            overlay = next(i for i, m in enumerate(model.materials)
                           if m['flags'] == 16 and m['blending_mode'] == 2)
            for batch in skin.batches:
                count, combo = visual.u16(batch, 14), visual.u16(batch, 16)
                second = model.textures[model.texture_combos[combo + 1]] if count > 1 else None
                if second and second['type'] == 0 and 'glow' in second['filename'].lower():
                    value = bytearray(batch)
                    visual.patch16(value, 14, 1)
                    value[0] = 0
                    batches.append(bytes(value))
                    changed += 1
                elif second and second['type'] == 0 and 'reflect' in second['filename'].lower():
                    value = bytearray(batch)
                    value[0] = 16
                    batches.append(bytes(value))
                    value = bytearray(batch)
                    value[0] = 16
                    visual.patch16(value, 10, overlay)
                    visual.patch16(value, 12, 1)
                    visual.patch16(value, 14, 1)
                    batches.append(bytes(value))
                    changed += 1
                else:
                    value = bytearray(batch)
                    value[0] = 0  # retail-only 0x40/0x80 batch flags; the stock helmet uses none
                    batches.append(bytes(value))
            skin.batches = batches
            if changed:
                replacements[skin_name] = write_skin(skin)
                report[skin_name] = changed
    return replacements, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=p.CLIENT_DEFAULT / 'Data' / ARCHIVE.relative_to('Data'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    storm = p.Storm(p.DLL_DEFAULT)
    handle = storm.open_archive(args.source)
    try:
        names = [name for name, *_ in storm.list_files(handle)]
        replacements, report = repair(storm, handle, names)
    finally:
        storm.dll.SFileCloseArchive(handle)
    assert replacements, 'No glow-layered Vulpera helmet batches found'
    o.rebuild_archive_replacing(storm, args.source, args.out, replacements, compress=True)
    check = storm.open_archive(args.out)
    try:
        for name, payload in replacements.items():
            assert storm.read(check, name) == payload, name
    finally:
        storm.dll.SFileCloseArchive(check)
    print('REPAIRED', report, 'sha256', hashlib.sha256(args.out.read_bytes()).hexdigest(), flush=True)


if __name__ == '__main__':
    main()
