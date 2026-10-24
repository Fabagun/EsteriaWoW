"""Append the thirty authored Slime Giant colors without changing existing appearance indices."""

import argparse
import colorsys
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import struct
import subprocess

import numpy as np
from PIL import Image

import slime_giant_race_pack as pack
from slime_giant_client_install import closed, NATIVE
import slime_giant_deploy as server

p = pack.p
ROOT = pack.WORK / 'color-expansion-30'
ART = p.ROOT / 'assets/SlimeSkeleton/ColorVariants'
TABLES = ('CharSections', 'BarberShopStyle')


def save(path, value):
    pack.save(path, (json.dumps(value, indent=2) + '\n').encode())


def encode(image):
    bitmap = p.BlpImage(image.width, image.height, bytearray(image.tobytes()))
    levels = bitmap.mip_chain()
    payloads = [Image.frombytes('RGBA', (level.width, level.height), bytes(level.data)).tobytes('raw', 'BGRA')
                for level in levels]
    data = p.Blp.from_images(levels, compression=3, alpha_type=8, alpha_size=8, payloads=payloads).serialize()
    decoded = p.Blp.parse(data).decode_level(0)
    assert (decoded.width, decoded.height) == image.size and bytes(decoded.data) == image.tobytes()
    return data


def recolor_flow(image, color):
    source = np.asarray(image)
    unique, inverse = np.unique(source[:, :, :3].reshape(-1, 3), axis=0, return_inverse=True)
    hls = np.array([colorsys.rgb_to_hls(*(pixel / 255)) for pixel in unique])
    overlay = np.asarray(Image.open(p.ROOT / 'assets/SlimeSkeleton/SlimeOverlay.png').convert('RGBA'))
    base_hue, base_light, base_saturation = colorsys.rgb_to_hls(*(overlay[400, 100, :3] / 255))
    hue, light, saturation = colorsys.rgb_to_hls(*(int(color[at:at + 2], 16) / 255 for at in (1, 3, 5)))
    hls[:, 0] = (hls[:, 0] + hue - base_hue) % 1
    hls[:, 2] = np.clip(hls[:, 2] * saturation / base_saturation, 0, 1)
    if light < base_light:
        hls[:, 1] *= light / base_light
    else:
        hls[:, 1] = 1 - (1 - hls[:, 1]) * (1 - light) / (1 - base_light)
    palette = np.rint(np.array([colorsys.hls_to_rgb(*pixel) for pixel in hls]) * 255).astype(np.uint8)
    pixels = source.copy()
    pixels[:, :, :3] = palette[inverse].reshape(source.shape[:2] + (3,))
    assert np.array_equal(pixels[:, :, 3], source[:, :, 3])
    return Image.fromarray(pixels)


def extend_table(data, name):
    table = p.RawWdbc(data)
    additions = []
    occupied = {p._value(row, 0) for row in table.records}
    for race, *_ in pack.SPECS:
        if name == 'CharSections':
            old = [row for row in table.records if p._value(row, 4) == race]
            assert len(old) == 22 and max(p._value(row, 36) for row in old) == 4
            for color in range(5, 35):
                for kind, style in ((0, 0), (1, 0), (1, 1), (4, 0)):
                    identity = pack.ranges(race)[name][0] + 100 + (color - 5) * 4 + len(additions) % 4
                    additions.append(struct.pack('<10I', identity, race, 0, kind, 0, 0, 0,
                                                 1 if kind == 1 else 17, style, color))
        else:
            template = next(row for row in table.records if p._value(row, 148) == race
                            and p._value(row, 4) == 3 and p._value(row, 156) == 4)
            for color in range(5, 35):
                identity = pack.ranges(race)[name][0] + 50 + color - 5
                row = p._replace(template, 0, 4, identity)
                additions.append(p._replace(row, 156, 4, color))
    assert not occupied.intersection(p._value(row, 0) for row in additions), name + ' ID collision'
    records = list(table.records) + additions
    if name == 'CharSections':
        records.sort(key=lambda row: tuple(p._value(row, offset) for offset in (4, 8, 12, 32, 36)))
    output = table.build(records, table.strings)
    checked = p.RawWdbc(output)
    after = {p._value(row, 0): row for row in checked.records}
    assert len(after) == len(records)
    assert all(after[p._value(row, 0)] == row for row in table.records), 'Existing DBC row changed'
    return output


def stage():
    catalog = p.load_json(ART / 'manifest.json')
    assert catalog['count'] == 30 and len(pack.COLORS) == 35
    flow = p.Blp.parse((pack.WORK / 'correct-source/3491672.blp').read_bytes()).decode_level(0)
    flow = Image.frombytes('RGBA', (flow.width, flow.height), bytes(flow.data))
    assets = {}
    sources = {}
    for index, row in enumerate(catalog['variants']):
        source = ART / row['skin']
        assert p.sha256(source) == row['skin_sha256'], 'Authored skin changed: ' + str(source)
        image = Image.open(source).convert('RGBA')
        assert image.size == (512, 512)
        sources[str(source)] = p.sha256(source)
        for part, art in enumerate((image, recolor_flow(flow, row['base_color']))):
            name = f'custom\\slimegiant\\colors\\{index * 2 + part}.blp'
            target = ROOT / 'assets' / Path(name.replace('\\', '/'))
            pack.save(target, encode(art))
            assets[name] = {'path': str(target), 'sha256': p.sha256(target)}
    archives = {}
    storm = p.Storm(p.DLL_DEFAULT)
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL, Path('Data/Patch-SG.MPQ')):
        live = p.CLIENT_DEFAULT / relative
        entries = dict(assets) if relative.name == 'Patch-SG.MPQ' else {}
        if not entries:
            handle = storm.open_archive(live)
            try:
                for name in TABLES:
                    entry = p.DBC_ROOT + name + '.dbc'
                    target = ROOT / 'entries' / relative.name / (name + '.dbc')
                    pack.save(target, extend_table(storm.read(handle, entry), name))
                    entries[entry] = {'path': str(target), 'sha256': p.sha256(target)}
            finally:
                storm.dll.SFileCloseArchive(handle)
        archives[str(relative)] = {'path': str(live), 'before': p.sha256(live), 'entries': entries}
    server_files = {}
    for name in TABLES:
        live = p.SERVER_DBC_ROOT / (name + '.dbc')
        target = ROOT / 'server' / live.name
        pack.save(target, extend_table(live.read_bytes(), name))
        server_files[str(live)] = {'before': p.sha256(live), 'path': str(target), 'sha256': p.sha256(target)}
    clothing = p.CLIENT_DEFAULT / 'Data/Patch-SG.MPQ'
    handle = storm.open_archive(clothing)
    try:
        armor = {name: pack.digest(storm.read(handle, name)) for name in
                 ('custom\\slimegiant\\3490792-clothing.m2', 'custom\\slimegiant\\3490792-clothing00.skin')}
    finally:
        storm.dll.SFileCloseArchive(handle)
    save(ROOT / 'plan.json', {'archives': archives, 'server_files': server_files, 'sources': sources,
                             'colors': list(pack.COLORS), 'unchanged_armor': armor,
                             'skin_indices': {'existing': [0, 4], 'appended': [5, 34]}, 'installed': False})
    print('Staged sixty lossless textures, two appended DBC tables for both factions, and preserved armor hashes')


def install():
    closed()
    plan = p.load_json(ROOT / 'plan.json')
    assert not plan['installed']
    assert all(p.sha256(Path(path)) == sha for path, sha in plan['sources'].items())
    before_server = p.load_json(ROOT / 'server-before.json')
    assert server.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}') == before_server['image']
    image = server.docker('inspect', 'ac-worldserver', '--format', '{{.Config.Image}}')
    after_server = server.docker('image', 'inspect', image, '--format', '{{.Id}}')
    validation = p.load_json(ROOT / 'server-validation.json')
    assert validation['image'] == after_server and validation['all_passed']
    assert p.sha256(p.ROOT / 'src/server/shared/CreatureAppearance.h') == validation['header_sha256']
    assert after_server != before_server['image'], 'Expanded server build is not ready'
    executable = NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    native_validation = p.load_json(ROOT / 'native-validation.json')
    assert p.sha256(executable) == native_validation['sha256']
    assert all(p.sha256(NATIVE / name) == sha for name, sha in native_validation['source_files'].items())
    backup = p.CLIENT_DEFAULT / '_backups' / ('slime-colors-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True, exist_ok=False)
    storm = p.Storm(p.DLL_DEFAULT)
    replacements = []
    for relative, info in plan['archives'].items():
        live = Path(info['path'])
        assert p.sha256(live) == info['before'], 'Installed archive changed: ' + relative
        saved = backup / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, saved)
        assert p.sha256(saved) == info['before']
        temporary = ROOT / 'packages' / Path(relative).name
        temporary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, temporary)
        entries = {name: Path(row['path']).read_bytes() for name, row in info['entries'].items()}
        assert all(pack.digest(entries[name]) == row['sha256'] for name, row in info['entries'].items())
        storm.replace_archive_entries(temporary, entries)
        handle = storm.open_archive(temporary)
        try:
            assert all(storm.read(handle, name) == data for name, data in entries.items())
            if relative.endswith('Patch-SG.MPQ'):
                assert all(pack.digest(storm.read(handle, name)) == sha for name, sha in plan['unchanged_armor'].items())
        finally:
            storm.dll.SFileCloseArchive(handle)
        replacements.append((temporary, live, saved, p.sha256(temporary)))
    for path, info in plan['server_files'].items():
        live = Path(path)
        assert p.sha256(live) == info['before'] and p.sha256(Path(info['path'])) == info['sha256']
        saved = backup / 'server' / live.name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, saved)
        assert p.sha256(saved) == info['before']
        replacements.append((Path(info['path']), live, saved, info['sha256']))
    metadata = p.CLIENT_DEFAULT / 'WowClientRetailVulkan.build.json'
    data = p.load_json(metadata)
    live_exe = p.CLIENT_DEFAULT / 'WowClientRetailVulkan.exe'
    assert p.sha256(live_exe) == data['sha256']
    for live in (live_exe, metadata):
        shutil.copy2(live, backup / live.name)
        assert p.sha256(live) == p.sha256(backup / live.name)
    data.update(sha256=p.sha256(executable), backup_directory=str(backup), live_acceptance='pending')
    data['slime_color_expansion'] = {'colors': plan['colors'], 'receipt': str(ROOT / 'receipt.json')}
    for name in ('Engine/Source/Retail/SlimeGiant.h', 'WoW/Common/ComponentCore/RetailRace.cpp',
                 'Tools/RetailAssets/tests.cpp'):
        item = next((item for item in data['source_files'] if item['path'] == name), None)
        if item is None:
            item = {'path': name}
            data['source_files'].append(item)
        item['sha256'] = p.sha256(NATIVE / name)
    data['features'] = [feature.replace('five colors', '35 colors') for feature in data['features']]
    data['features'].append('Slime Giant: thirty appended custom skins with matching animated slime textures')
    staged_metadata = ROOT / metadata.name
    save(staged_metadata, data)
    replacements.extend(((executable, live_exe, backup / live_exe.name, p.sha256(executable)),
                         (staged_metadata, metadata, backup / metadata.name, p.sha256(staged_metadata))))
    subprocess.run(['rtk', 'proxy', 'docker', 'compose', 'stop', 'ac-worldserver'], check=True)
    characters = server.sql(server.APPEARANCE, 'acore_characters')
    pack.save(backup / 'characters-appearance.tsv', characters)
    try:
        for source, live, saved, sha in replacements:
            server.atomic_copy(source, live, sha)
        assert server.sql(server.APPEARANCE, 'acore_characters') == characters
        subprocess.run(['rtk', 'proxy', 'docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], check=True)
        assert server.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}') == after_server
    except Exception:
        for source, live, saved, sha in replacements:
            shutil.copy2(saved, live)
        configured = server.docker('inspect', 'ac-worldserver', '--format', '{{.Config.Image}}')
        subprocess.run(['rtk', 'proxy', 'docker', 'image', 'tag', before_server['image'], configured], check=True)
        subprocess.run(['rtk', 'proxy', 'docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], check=True)
        raise
    receipt = {'installed': True, 'backup': str(backup), 'server_image': after_server,
               'previous_server': before_server, 'colors': plan['colors'], 'unchanged_armor': plan['unchanged_armor'],
               'files': {str(live): sha for _, live, _, sha in replacements}, 'live_acceptance': 'pending'}
    plan['installed'] = True
    save(ROOT / 'plan.json', plan)
    save(ROOT / 'receipt.json', receipt)
    save(backup / 'receipt.json', receipt)
    installed = {str(live): sha for _, live, _, sha in replacements}
    for name in ('client-install-receipt.json', 'client-install-plan.json', 'installation-receipt.json'):
        path = pack.WORK / name
        saved = backup / 'receipt-state' / name
        pack.save(saved, path.read_bytes())
        state = p.load_json(path)
        if name == 'installation-receipt.json':
            state['customization']['Slime Color'] = plan['colors']
            state['client_executable_sha256'] = p.sha256(executable)
            state['server_image'] = after_server
            state['slime_color_expansion'] = str(ROOT / 'receipt.json')
            for relative in state['client_files']:
                target = str(p.CLIENT_DEFAULT / relative)
                if target in installed:
                    state['client_files'][relative] = installed[target]
        else:
            for item in state['files']:
                target = str(p.CLIENT_DEFAULT / item['relative'])
                if target in installed:
                    item['sha256'] = installed[target]
        save(path, state)
    print('Installed 35 Slime Color options for Alliance and Horde; backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
