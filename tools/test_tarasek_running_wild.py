"""Validate the staged self-mount contract and exact preservation of existing assets and records."""
from pathlib import Path
import struct
import subprocess

import tarasek_running_wild as r
import tarasek_deploy as d
from wotlkconv.m2 import parse_m2


def main():
    baseline = d.read(r.WORK / 'baseline.json')
    for name in r.TABLES:
        original = r.table(name)
        current = r.t.p.RawWdbc((r.STAGE / f'assets/DBFilesClient/{name}.dbc').read_bytes())
        assert current.records[:len(original.records)] == original.records
        assert current.strings.startswith(original.strings)
    spells = r.t.p.RawWdbc((r.STAGE / 'assets/DBFilesClient/Spell.dbc').read_bytes())
    new = {r.t.p._value(row, 0): r.values(row) for row in spells.records
           if r.t.p._value(row, 0) in (110050, 110051)}
    assert set(new) == {110050, 110051}
    for identifier, speed, level in ((110050, 60, 20), (110051, 100, 40)):
        row = new[identifier]
        assert row[71:74] == [6, 6, 0] and row[95:98] == [78, 32, 0]
        assert row[110:113] == [0, 0, 0] and row[81] + 1 == speed
        assert row[38:40] == [level, level] and row[28] == 16
        assert row[32] & 0x80 and row[131:134] == [110050, 0, 514641]
    model = parse_m2((r.BASE / r.t.MODEL).read_bytes())
    assert len(model.sequences) == 179
    for identifier in r.ANIMATIONS:
        index = model.sequence_lookups[identifier]
        assert index < len(model.sequences) and model.sequences[index]['id'] == identifier
        assert model.sequences[index]['variation_index'] == 0
    with r.t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        assert r.t.sha(files.find(r.t.MODEL)[0]) == baseline['files'][r.t.MODEL]['sha256']
        assert r.t.sha(files.find(r.t.MODEL.replace('.m2', '00.skin'))[0]) \
            == baseline['files'][r.t.MODEL.replace('.m2', '00.skin')]['sha256']
        races = r.t.p.RawWdbc(files.find('DBFilesClient/ChrRaces.dbc')[0])
        race = r.values(next(row for row in races.records if r.t.p._value(row, 0) == 12))
        assert race[4:6] == [29422, 29423]
        for display, model_id in ((29422, 3141), (29423, 3142)):
            table = r.t.p.RawWdbc(files.find('DBFilesClient/CreatureDisplayInfo.dbc')[0])
            row = next(row for row in table.records if r.t.p._value(row, 0) == display)
            assert r.t.p._value(row, 4) == model_id
    # Apply the actual pending SQL inside a rolled-back transaction, comparing every new field.
    probe = ('START TRANSACTION;\n' + r.SQL.read_text() +
             '\nSELECT * FROM spell_dbc WHERE ID IN (110050,110051) ORDER BY ID;\n'
             'SELECT MaleDisplayId,FemaleDisplayId FROM chrraces_dbc WHERE ID=12;\nROLLBACK;')
    actual = d.sql(probe).splitlines()
    assert len(actual) == 3 and actual[2] == '29422\t29423'
    columns = [row.split('\t') for row in d.sql('SHOW COLUMNS FROM spell_dbc;').splitlines()]
    for line in actual[:2]:
        fields = line.split('\t')
        assert len(fields) == 234
        expected = new[int(fields[0])]
        for index, (_, kind, *_) in enumerate(columns):
            if 'text' in kind or 'char' in kind:
                text = r.t.p._string(spells.strings, expected[index]).decode()
                assert ('' if fields[index] == 'NULL' else fields[index]) == text, index
            elif kind == 'float':
                number = struct.unpack('<f', struct.pack('<I', expected[index]))[0]
                assert float(fields[index]) == number, index
            else:
                number = expected[index]
                if 'unsigned' not in kind and number >= 0x80000000:
                    number -= 0x100000000
                assert int(fields[index]) == number, (index, fields[index], number)
    assert d.sql('SELECT COUNT(*) FROM spell_dbc WHERE ID IN (110050,110051);').strip() == '0'
    assert d.sql('SELECT MaleDisplayId,FemaleDisplayId FROM chrraces_dbc WHERE ID=12;') == baseline['worgen']
    assert d.digest(d.NATIVE / 'EsteriaAppearance.dll') == d.digest(r.STAGE / 'EsteriaAppearance.dll')
    for name in ('TestNativeAppearance', 'TestHighmountainMaterials', 'TestCustomizationChoices',
                 'TestCosmeticWings', 'TestRunningWild'):
        output = subprocess.check_output([str(d.NATIVE / (name + '.exe')),
                                          str(d.NATIVE / 'EsteriaAppearance.dll')], text=True)
        print(output.strip())
    output = subprocess.check_output([str(d.NATIVE / 'TestRunningWildThunks.exe'),
        str(r.STAGE / 'EsteriaAppearance.dll'), str(r.STAGE / 'Wow.exe')], text=True)
    print(output.strip())
    sources = ['tools/tarasek_running_wild.py', 'tools/tarasek_running_wild_patch.py',
               'tools/tarasek_running_wild_deploy.py',
               'tools/test_tarasek_running_wild.py', 'client-customization/NativeAppearance.cpp',
               'client-customization/NativeAppearance.def', 'client-customization/RunningWild.inl',
               'client-customization/TestRunningWild.cpp', 'client-customization/TestRunningWildThunks.cpp',
               'client-customization/build-native.bat', 'data/retroported-races/drakkin_alliance.json', str(r.SQL)]
    d.save(r.STAGE / 'validation.json', {'passed': True,
        'source_files': {name: d.digest(Path(name)) for name in sources},
        'helper_sha256': d.digest(r.STAGE / 'EsteriaAppearance.dll'),
        'exe_sha256': d.digest(r.STAGE / 'Wow.exe'), 'all_existing_rows_and_model_preserved': True,
        'native_harnesses': 6, 'sql_transaction_rolled_back': True, 'live_accepted': False})
    print('PASS: six merged tables, 179 authored tracks, spell parity, Worgen identity, SQL rollback and native hooks')


if __name__ == '__main__':
    main()
