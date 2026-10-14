"""Apply only the tested creator gender-policy repair to both active Z archives."""

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

import vrykul_female_pack as v
from test_vrykul_creator_gender import check


def main():
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before replacing their active creator Lua')
    storm = v.o.Storm(v.p.DLL_DEFAULT)
    entry = v.p.GLUE_ROOT+'CharacterCreate.lua'
    originals, patches, hashes = {}, {}, {}
    for relative in (v.p.GLOBAL_ARCHIVE_REL, v.p.LOCALE_ARCHIVE_REL):
        archive = v.p.CLIENT_DEFAULT/relative
        handle = storm.open_archive(archive)
        try:
            payload = storm.read(handle, entry)
        finally:
            storm.dll.SFileCloseArchive(handle)
        text = payload.decode('utf-8-sig')
        patched = v.patch_creator_gender(text)
        check(patched)
        originals[str(relative)] = payload
        patches[str(relative)] = patched.encode('utf-8')
        hashes[str(relative)] = v.p.sha256(archive)
    if all(originals[key] == patches[key] for key in patches):
        print('Creator gender policy is already repaired in both active Z archives')
        return
    root = Path('C:/Users/Zach/.codex/backups')/('vrykul-creator-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    for relative, expected in hashes.items():
        source, target = v.p.CLIENT_DEFAULT/relative, root/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert v.p.sha256(target) == expected
        (root/(Path(relative).name+'.CharacterCreate.lua')).write_bytes(originals[relative])
    try:
        for relative, payload in patches.items():
            archive = v.p.CLIENT_DEFAULT/relative
            assert v.p.sha256(archive) == hashes[relative], 'archive changed after backup'
            storm.replace_archive_entries(archive, {entry: payload})
            assert archive.stat().st_size < 0x80000000
            handle = storm.open_archive(archive)
            try:
                assert storm.read(handle, entry) == payload
            finally:
                storm.dll.SFileCloseArchive(handle)
    except BaseException:
        for relative in hashes:
            shutil.copy2(root/relative, v.p.CLIENT_DEFAULT/relative)
        raise
    report = {'backup': str(root), 'before': hashes,
              'after': {relative: v.p.sha256(v.p.CLIENT_DEFAULT/relative) for relative in patches},
              'changed_entry': entry, 'lua_click_test': True, 'live_client_test': False}
    v.old.save(root/'installed.json', report)
    v.old.save(v.STAGE/'creator-gender-fix.json', report)
    print('Installed and read-back verified the creator gender repair:', root, flush=True)


if __name__ == '__main__':
    main()
