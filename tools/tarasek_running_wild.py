"""Stage male Drakkin self-mount spells and repair the stale Worgen server display override."""
import argparse
from pathlib import Path
import shutil
import struct

import tarasek_drakkin as t
import tarasek_deploy as d

WORK = Path('C:/RetroPorterWork/tarasek-running-wild')
BASE = WORK / 'baseline'
STAGE = WORK / 'stage'
MIGRATION = 'rev_20261015130000000_tarasek_running_wild_worgen.sql'
SQL = d.ROOT / 'data/sql/updates/pending_db_world' / MIGRATION
TABLES = ('Spell', 'SpellIcon', 'SpellVisual', 'SpellVisualKit', 'AnimationData', 'SkillLineAbility')
ANIMATIONS = {618: (0, 'MountSelfIdle'), 620: (4, 'MountSelfWalk'), 622: (5, 'MountSelfRun'),
              624: (143, 'MountSelfSprint'), 630: (11, 'MountSelfShuffleLeft'),
              632: (12, 'MountSelfShuffleRight'), 634: (13, 'MountSelfWalkBackwards'),
              636: (94, 'MountSelfSpecial'), 638: (38, 'MountSelfJump'),
              640: (37, 'MountSelfJumpStart'), 642: (39, 'MountSelfJumpEnd'),
              644: (187, 'MountSelfJumpLandRun'), 646: (123, 'MountSelfStart')}


def baseline():
    assert not (WORK / 'baseline.json').exists(), 'Baseline is immutable'
    BASE.mkdir(parents=True, exist_ok=True)
    receipt = {'files': {}, 'archives': {}, 'server_dbc': {}}
    with t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        for key in [*(f'DBFilesClient\\{name}.dbc' for name in TABLES), t.MODEL,
                    t.MODEL.replace('.m2', '00.skin')]:
            raw, provider = files.find(key)
            target = BASE / key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            receipt['files'][key] = {'sha256': t.sha(raw), 'provider': provider}
    for path in [*d.CLIENT.glob('Esteria*.bin'), d.CLIENT / 'EsteriaAppearance.dll', d.CLIENT / 'Wow.exe']:
        shutil.copy2(path, BASE / path.name)
        receipt['files'][path.name] = {'sha256': d.digest(path)}
    for key in ('Data/patch-Z.MPQ', 'Data/enUS/patch-enUS-Z.MPQ'):
        receipt['archives'][key] = d.digest(d.CLIENT / key)
    for path in d.SERVER.glob('*.dbc'):
        receipt['server_dbc'][path.name] = d.digest(path)
    receipt['worgen'] = d.sql('SELECT MaleDisplayId,FemaleDisplayId FROM chrraces_dbc WHERE ID=12;')
    assert receipt['worgen'].strip() == '3000026\t3000027'
    for table, where in (('spell_dbc', 'ID IN (110050,110051)'),
                         ('spell_script_names', 'spell_id IN (110050,110051)'),
                         ('spell_ranks', 'first_spell_id=110050 OR spell_id IN (110050,110051)')):
        assert d.sql(f'SELECT COUNT(*) FROM {table} WHERE {where};').strip() == '0'
    d.save(WORK / 'baseline.json', receipt)
    print('Pinned installed model, tables, executable, helper, catalogs, server DBCs and SQL allocations')


def values(row):
    return list(struct.unpack('<' + 'I' * (len(row) // 4), row))


def table(name):
    return t.p.RawWdbc((BASE / f'DBFilesClient/{name}.dbc').read_bytes())


def extend(name, rows, strings=None):
    original = table(name)
    identifiers = {t.p._value(row, 0) for row in original.records}
    assert not identifiers & {row[0] for row in rows}, name
    records = [struct.pack('<' + 'I' * original.fields, *row) for row in rows]
    raw = original.build([*original.records, *records], strings)
    check = t.p.RawWdbc(raw)
    assert check.records[:len(original.records)] == original.records
    assert check.strings.startswith(original.strings)
    target = STAGE / f'assets/DBFilesClient/{name}.dbc'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def tables():
    casts = t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS')
    times = t.p.RawWdbc(casts.find('DBFilesClient/SpellCastTimes.dbc')[0])
    assert values(next(r for r in times.records if t.p._value(r, 0) == 16))[1] == 1500
    casts.close()
    source = table('Spell')
    donor = values(next(row for row in source.records if t.p._value(row, 0) == 458))
    columns = [row.split('\t') for row in d.sql('SHOW COLUMNS FROM spell_dbc;').splitlines()]
    assert len(columns) == len(donor) == 234
    pool = bytearray(source.strings)
    spell_rows = []
    text_fields = set()
    for start in (136, 153, 170, 187):
        text_fields.update(range(start, start + 16))
    for identifier, speed, level in ((110050, 60, 20), (110051, 100, 40)):
        row = list(donor)
        row[0], row[38], row[39], row[81], row[110] = identifier, level, level, speed - 1, 0
        row[131], row[132], row[133] = 110050, 0, 514641
        row[32] |= 0x80 # Server must dismount on entering water; this form has no client mount model.
        # Normal Wrath mounted aura/speed, without a second mount model or a transformation.
        assert (row[95], row[96]) == (78, 32)
        for index in text_fields:
            row[index] = 0
        for index, text in ((136, 'Running Wild'), (153, f'{speed}% Speed'),
                            (170, 'Drop to all fours to run as fast as a wild animal.'),
                            (187, f'Ground movement speed increased by {speed}%.')):
            row[index] = len(pool)
            pool.extend(text.encode() + b'\0')
        spell_rows.append(row)
    extend('Spell', spell_rows, bytes(pool))
    icons = table('SpellIcon')
    extend('SpellIcon', [[514641, len(icons.strings)]],
           icons.strings + b'Interface\\Icons\\ability_racial_runningwild\0')
    visuals = table('SpellVisual')
    visual = values(next(r for r in visuals.records if t.p._value(r, 0) == 5499))
    visual[0], visual[1] = 110050, 110050
    extend('SpellVisual', [visual])
    kit = [0] * table('SpellVisualKit').fields
    kit[0], kit[1], kit[2] = 110050, 646, 618
    kit[17:21] = [0xffffffff] * 4
    extend('SpellVisualKit', [kit])
    animations = table('AnimationData')
    by_id = {t.p._value(r, 0): values(r) for r in animations.records}
    pool = bytearray(animations.strings)
    rows = []
    for identifier, (behavior, name) in ANIMATIONS.items():
        row = list(by_id[behavior])
        row[0], row[1], row[5] = identifier, len(pool), behavior
        pool.extend(name.encode() + b'\0')
        rows.append(row)
    extend('AnimationData', rows, bytes(pool))
    abilities = table('SkillLineAbility')
    donor_ability = values(next(r for r in abilities.records if t.p._value(r, 8) == 458))
    rows = []
    for identifier in (110050, 110051):
        row = list(donor_ability)
        row[0], row[2] = identifier, identifier
        # Race66 cannot fit a legacy race mask. The bound server script enforces gender/race eligibility.
        assert row[3] == 0 and row[4] == 0 and row[1] == 777
        rows.append(row)
    extend('SkillLineAbility', rows)

    # Emit only non-default fields from the exact staged records, keeping SQL and client semantics equal.
    selected = [i for i in range(234) if i not in text_fields and any(row[i] for row in spell_rows)]
    selected += [136, 153, 170, 187]
    selected.sort()
    def sql_value(row, i):
        if i in text_fields:
            return "'" + t.p._string(bytes(pool_spell), row[i]).decode().replace("'", "''") + "'"
        if columns[i][1] == 'float':
            return repr(struct.unpack('<f', struct.pack('<I', row[i]))[0])
        value = row[i]
        if 'unsigned' not in columns[i][1] and value >= 0x80000000:
            value -= 0x100000000
        return str(value)
    pool_spell = t.p.RawWdbc((STAGE / 'assets/DBFilesClient/Spell.dbc').read_bytes()).strings
    lines = ['-- Male Drakkin Running Wild: normal mount rules, authored Tarasek self-mount animation.',
             '-- Bindings enforce race66 male and riding skill; high RaceIDs cannot use legacy race masks.',
             'DELETE FROM `spell_dbc` WHERE `ID` IN (110050, 110051);',
             'INSERT INTO `spell_dbc` (', ',\n'.join('    `' + columns[i][0] + '`' for i in selected),
             ') VALUES']
    for n, row in enumerate(spell_rows):
        lines += ['(', ',\n'.join('    ' + sql_value(row, i) for i in selected),
                  ');' if n == 1 else '),']
    lines += ['', 'DELETE FROM `spell_script_names` WHERE `spell_id` IN (110050, 110051);',
              'INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`) VALUES',
              "(110050, 'spell_drakkin_running_wild'),", "(110051, 'spell_drakkin_running_wild');", '',
              'DELETE FROM `spell_ranks` WHERE `first_spell_id` = 110050;',
              'INSERT INTO `spell_ranks` (`first_spell_id`, `spell_id`, `rank`) VALUES',
              '(110050, 110050, 1),', '(110050, 110051, 2);', '',
              '-- The old3000026/3000027 override truncates to Battlemon50906/50907 in PlayerInfo.',
              '-- Match the existing winning ChrRaces DBC; preserve both actual Pokémon entries.',
              'UPDATE `chrraces_dbc` SET `MaleDisplayId` = 29422, `FemaleDisplayId` = 29423',
              'WHERE `ID` = 12 AND `MaleDisplayId` = 3000026 AND `FemaleDisplayId` = 3000027;', '']
    SQL.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    shutil.copy2(SQL, STAGE / 'pending_db_world.sql')
    rollback = ('DELETE FROM `spell_script_names` WHERE `spell_id` IN (110050,110051);\n'
                'DELETE FROM `spell_ranks` WHERE `first_spell_id`=110050;\n'
                'DELETE FROM `spell_dbc` WHERE `ID` IN (110050,110051);\n'
                'UPDATE `chrraces_dbc` SET `MaleDisplayId`=3000026, `FemaleDisplayId`=3000027\n'
                'WHERE `ID`=12 AND `MaleDisplayId`=29422 AND `FemaleDisplayId`=29423;\n')
    (STAGE / 'rollback-world.sql').write_text(rollback, encoding='utf-8', newline='\n')
    print('Merged six client tables and generated the two scoped spell rows plus Worgen override repair')


def pack():
    baseline = d.read(WORK / 'baseline.json')
    assets = {str(path.relative_to(STAGE / 'assets')): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    assert len(assets) == len(TABLES)
    storm = t.p.Storm(t.p.DLL_DEFAULT)
    report = {'assets': {key: t.sha(raw) for key, raw in assets.items()}, 'archives': {},
              'installed': False, 'live_accepted': False}
    for key, expected in baseline['archives'].items():
        assert d.digest(d.CLIENT / key) == expected
        target = STAGE / 'client' / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(d.CLIENT / key, target)
        storm.replace_archive_entries(target, assets)
        assert target.stat().st_size < 0x80000000
        archive = storm.open_archive(target)
        try:
            for name, raw in assets.items():
                assert storm.read(archive, name) == raw, name
        finally:
            storm.dll.SFileCloseArchive(archive)
        report['archives'][key] = {'before': expected, 'after': d.digest(target),
                                   'bytes': target.stat().st_size, 'readback_verified': True}
        print('PACKED', key, target.stat().st_size, flush=True)
    d.save(STAGE / 'report.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('baseline', 'tables', 'pack'))
    globals()[parser.parse_args().action]()
