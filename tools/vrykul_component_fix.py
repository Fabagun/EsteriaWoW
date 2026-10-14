"""Normalize only female Vrykul's imported character textures and install the checked asset archive."""

from datetime import datetime
from pathlib import Path
import os
import shutil
import subprocess

import vrykul_female_pack as v

STAGE = v.STAGE/'component-fix'


def check(assets):
    count = 0
    for key, payload in assets.items():
        if not key.lower().startswith('character\\vrykul\\female\\') or not key.lower().endswith('.blp'):
            continue
        source = v.p.Blp.parse(v.SOURCE.joinpath(*v.p.PureWindowsPath(key).parts).read_bytes()).decode_level(0)
        image = v.p.Blp.parse(payload)
        assert image.compression == 1 and payload[10] == 8
        assert len(payload) <= 0xfffff
        assert len(image.mips) == min(image.width, image.height).bit_length()
        decoded = image.decode_level(0)
        assert (image.width, image.height) == (source.width, source.height)
        assert bytes(decoded.data[3::4]) == bytes(source.data[3::4])
        count += 1
    assert count == 25
    print('CHECKED 25 indexed components, preserved dimensions/alpha and native buffer limits', flush=True)


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    live = v.p.CLIENT_DEFAULT/v.ASSET
    before = v.p.sha256(live)
    storm = v.o.Storm(v.p.DLL_DEFAULT)
    handle = storm.open_archive(live)
    try:
        original = {key: storm.read(handle, key) for key, *_ in storm.list_files(handle)
                    if key not in ('(listfile)', '(attributes)')}
    finally:
        storm.dll.SFileCloseArchive(handle)
    assets = dict(original)
    report = v.normalize_components(assets)
    check(assets)
    for key in assets:
        assert key in report or assets[key] == original[key], 'unrelated asset changed'
    target = STAGE/'Patch-7.MPQ'
    storm.create_archive(target, assets)
    handle = storm.open_archive(target)
    try:
        assert all(storm.read(handle, key) == payload for key, payload in assets.items())
    finally:
        storm.dll.SFileCloseArchive(handle)
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before installing the checked component textures')
    assert v.p.sha256(live) == before, 'live asset archive changed during staging'
    backup = Path('C:/Users/Zach/.codex/backups')/('vrykul-components-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    shutil.copy2(live, backup/live.name)
    assert v.p.sha256(backup/live.name) == before
    expected = v.p.sha256(target)
    temporary = live.with_suffix('.component-next.MPQ')
    shutil.copy2(target, temporary)
    assert v.p.sha256(temporary) == expected
    os.replace(temporary, live)
    assert v.p.sha256(live) == expected
    receipt = {'backup': str(backup), 'before': before, 'after': expected, 'components': report,
               'changed_archive': str(live), 'live_client_test': False}
    v.old.save(backup/'installed.json', receipt)
    v.old.save(STAGE/'installed.json', receipt)
    print('INSTALLED indexed female Vrykul components; backup:', backup, flush=True)


if __name__ == '__main__':
    main()
