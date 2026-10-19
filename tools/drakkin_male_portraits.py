"""Stage/install the supplied male Drakkin art through the existing race portrait pipeline."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

import tarasek_drakkin as t
import tarasek_deploy as d
import race_portrait_pack as art


WORK = Path('C:/RetroPorterWork/drakkin-male-portraits')
PICTURES = Path('R:/Users/Zach/Pictures/Portraits')
ARCHIVES = ('Data/patch-Z.MPQ', 'Data/enUS/patch-enUS-Z.MPQ')
INTERNAL = {'(listfile)', '(attributes)'}


def inventory(storm, path):
    handle = storm.open_archive(path)
    try:
        return {name.lower(): t.sha(storm.read(handle, name))
                for name, *_ in storm.list_files(handle) if name.lower() not in INTERNAL}
    finally:
        storm.dll.SFileCloseArchive(handle)


def assets():
    return {str(path.relative_to(WORK / 'assets')).replace('/', '\\'): path.read_bytes()
            for path in (WORK / 'assets').rglob('*') if path.is_file()}


def stage():
    assert not (WORK / 'report.json').exists(), 'Use a new workspace for another portrait revision'
    WORK.mkdir(parents=True, exist_ok=True)
    report = {'sources': {}, 'archives': {}, 'entries': {}, 'status': 'staged', 'live_accepted': False}
    preview = Image.new('RGBA', (560, 340), (25, 25, 25, 255))
    labels = ImageDraw.Draw(preview)
    with t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        template = files.find(art.ICON_TEMPLATE_ENTRY)[0]
        ring = art.ring_layer(art.decode_client_blp(files.find(art.RING_ENTRY)[0]))
        select_border = art.decode_client_blp(files.find(
            'Interface\\Glues\\CharacterSelect\\ECS-Portrait-Border.blp')[0])
        for column, faction in enumerate(('Alliance', 'Horde')):
            source = PICTURES / f'Charactercreate-races_drakkin-male_{faction.lower()}.png'
            report['sources'][str(source)] = d.digest(source)
            pixels = art.portrait_bytes(source, art.circular_mask())
            plain = art.encode_portrait(pixels, template)
            bordered = art.compose_race_icon(pixels, ring)
            token = 'Drakkin' + faction
            stem = art.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-Male-' + token
            entries = {art.CREATOR_ICON_ROOT + 'UI-CharacterCreate-' + token + 'Male.blp':
                       art.encode_portrait(bordered, template),
                       'Interface\\Glues\\CharacterSelect\\ECS-Portrait-' + token + 'Male.blp': plain,
                       stem: plain, stem + '.blp': plain}
            for key, payload in entries.items():
                art.validate_portrait(payload, Path(key))
                target = WORK / 'assets' / key
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                report['entries'][key] = t.sha(payload)
            # Preview the decoded delivered BLPs, with the same separately drawn ECS border.
            decoded_icon = art.decode_client_blp(next(iter(entries.values())))
            preview.alpha_composite(decoded_icon.resize((128, 128), Image.Resampling.NEAREST),
                                    (column * 280 + 76, 24))
            selected = Image.new('RGBA', (128, 128))
            selected.alpha_composite(art.decode_client_blp(plain).resize((98, 98), Image.Resampling.LANCZOS),
                                     (15, 15))
            selected.alpha_composite(select_border.resize((128, 128), Image.Resampling.LANCZOS))
            preview.alpha_composite(selected, (column * 280 + 76, 184))
            labels.text((column * 280 + 70, 8), faction + ' - Creation', fill='white')
            labels.text((column * 280 + 70, 166), 'Character Select', fill='white')
    preview.convert('RGB').save(WORK / 'portrait-preview.png')
    updates = assets()
    assert len(updates) == 8
    storm = t.p.Storm(t.p.DLL_DEFAULT)
    for relative in ARCHIVES:
        live = d.CLIENT / relative
        target = WORK / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = d.digest(live)
        shutil.copy2(live, target)
        assert d.digest(target) == before
        original = inventory(storm, target)
        storm.replace_archive_entries(target, updates)
        assert target.stat().st_size < 0x80000000
        changed = inventory(storm, target)
        assert original.keys() == changed.keys(), 'This update should only replace existing art'
        expected = {key.lower(): t.sha(payload) for key, payload in updates.items()}
        assert all(changed[key] == digest for key, digest in expected.items())
        assert {key: digest for key, digest in original.items() if key not in expected} == {
            key: digest for key, digest in changed.items() if key not in expected}, 'Unrelated content changed'
        assert d.digest(live) == before, 'Live archive changed during staging'
        report['archives'][relative] = {'before': before, 'after': d.digest(target),
                                        'bytes': target.stat().st_size,
                                        'unchanged_entries': len(original) - len(expected)}
        print('STAGED; all unrelated entries byte-identical:', relative, flush=True)
    d.save(WORK / 'report.json', report)


def verify():
    report = d.read(WORK / 'report.json')
    with t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        for key, expected in report['entries'].items():
            payload, provider = files.find(key)
            assert t.sha(payload) == expected, (key, provider)
            art.validate_portrait(payload, Path(key))
    for relative, record in report['archives'].items():
        assert d.digest(d.CLIENT / relative) == record['after'], relative
    print('VERIFIED: eight effective portrait entries and both installed archives')


def install():
    d.closed_client()
    report = d.read(WORK / 'report.json')
    assert report['status'] == 'staged'
    backup = Path('C:/EsteriaBackups') / ('Drakkin-male-portraits-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    assert not backup.exists()
    for source, expected in report['sources'].items():
        assert d.digest(Path(source)) == expected, source
    for relative, record in report['archives'].items():
        assert d.digest(d.CLIENT / relative) == record['before'], relative
        assert d.digest(WORK / 'client' / relative) == record['after'], relative
        assert shutil.disk_usage(d.CLIENT).free > record['bytes'] + 256 * 1024 * 1024
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(d.CLIENT / relative, target)
        assert d.digest(target) == record['before']
    d.save(backup / 'install-plan.json', report)
    (backup / 'ROLLBACK.txt').write_text(
        'Restore these two archives only while WoW/editors are closed. The install plan contains hashes.\n'
        'Do not restore over later client changes without rebasing them. No server or database changes.\n',
        encoding='utf-8', newline='\n')
    for relative, record in report['archives'].items():
        d.closed_client()
        assert d.digest(d.CLIENT / relative) == record['before']
        d.replace(WORK / 'client' / relative, d.CLIENT / relative, record['after'])
    verify()
    report.update(status='installed_fresh_client_visual_check_pending', backup=str(backup))
    d.save(WORK / 'report.json', report)
    print('INSTALLED; backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install', 'verify'))
    globals()[parser.parse_args().action]()
