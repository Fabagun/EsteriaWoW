"""Repair Gnoll's player-model metadata and essential body visibility without changing saved characters."""

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import struct
import subprocess

import gnoll_race_pack as g
import retroported_race_pack as p

STAGE = Path('C:/Users/Zach/.codex/tmp/gnoll-render-repair')
KEY = p.DBC_ROOT + 'CreatureModelData.dbc'


def flags(data):
    table = p.RawWdbc(data)
    rows = [row for row in table.records if p._value(row, 0) == 120068]
    assert len(rows) == 1
    assert p._string(table.strings, p._value(rows[0], 8)).decode().lower() == g.MODEL.lower()
    assert p._value(rows[0], 4) in (0, 0x804)
    result = table.build([p._replace(row, 4, 4, p._value(row, 4) | 0x804)
                          if p._value(row, 0) == 120068 else row for row in table.records])
    changed = p.RawWdbc(result)
    assert changed.strings == table.strings and changed.count == table.count
    assert all(after == (p._replace(before, 4, 4, 0x804) if p._value(before, 0) == 120068 else before)
               for before, after in zip(table.records, changed.records, strict=True))
    return result


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        before = files.find(KEY)[0]
    finally:
        files.close()
    after = flags(before)
    (STAGE / 'CreatureModelData.dbc').write_bytes(after)
    report = {'before': {}, 'after': {}, 'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe')}
    storm = p.Storm(p.DLL_DEFAULT)
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = p.CLIENT_DEFAULT / relative, STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        report['before'][str(relative)] = p.sha256(live)
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, {KEY: after})
        assert target.stat().st_size < 0x80000000
        handle = storm.open_archive(target)
        try:
            assert storm.read(handle, KEY) == after
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == report['before'][str(relative)]
        report['after'][str(relative)] = p.sha256(target)
    source = p.SERVER_DBC_ROOT / 'CreatureModelData.dbc'
    server = flags(source.read_bytes())
    (STAGE / 'server-CreatureModelData.dbc').write_bytes(server)
    report['server_before'] = p.sha256(source)
    report['server_after'] = p.sha256(STAGE / 'server-CreatureModelData.dbc')
    report['dll_before'] = p.sha256(p.CLIENT_DEFAULT / 'EsteriaAppearance.dll')
    report['dll_after'] = p.sha256(Path('C:/g63-build/EsteriaAppearance.dll'))
    g.save(STAGE / 'repair.json', report)
    print('PASS isolated repair: only Gnoll model Flags change from NPC0 to player/HD0x804', flush=True)


def install():
    from mechagnome_race_pack import sql
    r = p.load_json(STAGE / 'repair.json')
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Exit WoW/Eclipse/archive editors before installing this repair')
    assert subprocess.check_output(['docker', 'inspect', 'ac-worldserver', '--format',
                                    '{{.State.Running}}'], text=True).strip() == 'false'
    assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == r['exe_sha256']
    assert sql('SELECT COUNT(*) FROM creaturemodeldata_dbc WHERE ID=120068;').strip() == '0'
    assert p.sha256(p.CLIENT_DEFAULT / 'EsteriaAppearance.dll') == r['dll_before']
    assert p.sha256(Path('C:/g63-build/EsteriaAppearance.dll')) == r['dll_after']
    server = p.SERVER_DBC_ROOT / 'CreatureModelData.dbc'
    assert p.sha256(server) == r['server_before']
    for relative, sha in r['before'].items():
        assert p.sha256(p.CLIENT_DEFAULT / relative) == sha
        assert p.sha256(STAGE / 'client' / relative) == r['after'][relative]
    backup = Path('C:/Users/Zach/.codex/backups') / ('gnoll-render-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    targets = {p.CLIENT_DEFAULT / rel: STAGE / 'client' / rel for rel in r['before']}
    targets[p.CLIENT_DEFAULT / 'EsteriaAppearance.dll'] = Path('C:/g63-build/EsteriaAppearance.dll')
    targets[server] = STAGE / 'server-CreatureModelData.dbc'
    saved = {}
    for target in targets:
        relative = target.relative_to(p.CLIENT_DEFAULT) if p.CLIENT_DEFAULT in target.parents \
            else Path('server') / target.name
        copy = backup / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, copy)
        assert p.sha256(copy) == p.sha256(target)
        saved[str(target)] = str(copy)
    appearance = sql('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
                     'FROM characters ORDER BY guid;', 'acore_characters')
    try:
        for target, source in targets.items():
            shutil.copy2(source, target)
            assert p.sha256(target) == p.sha256(source)
        assert appearance == sql('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
                                 'FROM characters ORDER BY guid;', 'acore_characters')
    except Exception:
        for target, copy in saved.items():
            shutil.copy2(copy, target)
        raise
    r.update(backup=str(backup), installed={str(target): p.sha256(target) for target in targets},
             status='installed_pending_fresh_client_readback')
    g.save(STAGE / 'installed.json', r)
    g.save(backup / 'repair.json', r)
    print('INSTALLED guarded Gnoll render repair', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install'))
    globals()[parser.parse_args().action]()
