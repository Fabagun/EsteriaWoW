"""Stage narrow Slime Giant identity/portrait repairs without touching installed files."""

import json
from pathlib import Path
import re

from PIL import Image, ImageChops
from lupa.lua51 import LuaRuntime

import race_portrait_pack as portraits
import slime_giant_race_pack as pack

p = pack.p
STAGE = pack.WORK / 'ui-repair-20261020'
SOURCE = Path('R:/Users/Zach/Pictures/Portraits')
NAME_FIELDS = (*range(14, 30), *range(31, 47), *range(48, 64))


def repair_races(data):
    source = p.RawWdbc(data)
    assert (source.fields, source.record_size) == (69, 276)
    donor = next(row for row in source.records if p._value(row, 0) == 29)
    assert p._value(donor, 32) == 7
    pool = bytearray(source.strings)
    records = []
    for row in source.records:
        race = p._value(row, 0)
        if race in (71, 72):
            faction = 'Alliance' if race == 71 else 'Horde'
            assert p._value(row, 8) == (1 if race == 71 else 2)
            assert p._value(row, 52) == (0 if race == 71 else 1)
            row = p._replace(row, 32, 4, 7)
            row = p._set_string(row, 11, pool, 'SlimeGiant' + faction)
            for field in NAME_FIELDS:
                row = p._set_string(row, field, pool, 'Slime Giant')
        records.append(row)
    result = source.build(records, bytes(pool))
    checked = p.RawWdbc(result)
    changed = {p._value(old, 0) for old, new in zip(source.records, checked.records) if old != new}
    assert changed == {71, 72}, changed
    assert len(source.records) == len(checked.records)
    for row in checked.records:
        race = p._value(row, 0)
        if race in (71, 72):
            assert p._value(row, 32) == 7
            assert p._string(checked.strings, p._value(row, 44)).decode() == (
                'SlimeGiantAlliance' if race == 71 else 'SlimeGiantHorde')
            assert all(p._string(checked.strings, p._value(row, field * 4)) == b'Slime Giant'
                       for field in NAME_FIELDS)
    return result


def check_glue(glue):
    lua = LuaRuntime(unpack_returned_tuples=True)
    compile_lua = lua.eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for text in glue.values():
        compile_lua(text)
    lua.execute('strupper=string.upper; function GetFactionForRace() return nil,"WrongOrdinal" end')
    info = glue['CharacterInfo.lua']
    start = info.index('local EXACT_RACE_DATA = {')
    end = info.index('local function GetRaceNamesByFaction(')
    lua.execute(info[start:end] + '\nGetExact=GetExactRaceIDForFileString; GetFaction=GetFactionForRaceID;')
    lua.execute('ECS={Const={TEX={portraitNs="ECS-Portrait-",create="Create-"},FALLBACK_RACE_NAME="?"}};')
    lua.execute(glue['ECS_Schema.lua'])
    creator = glue['CharacterCreate.lua']
    table_start = creator.index('RACE_ICON_TEXTURES = {')
    table_end = creator.index('\n}', table_start) + 2
    lua.execute(creator[table_start:table_end])
    male_only = re.search(r'function CharacterCreate_IsMaleOnlyRace\(race\).*?\nend', creator, re.S)
    assert male_only
    lua.execute(male_only[0])
    for race, faction, donor, *_ in pack.SPECS:
        token = 'SlimeGiant' + faction.title()
        key = token.upper()
        assert lua.globals().GetExact(token) == race
        assert lua.globals().GetFaction(race) == faction.title()
        assert lua.globals().CharacterCreate_IsMaleOnlyRace(race)
        for identity in (lua.globals().ECS.Schema.GetRace(race, None, None, None),
                         lua.globals().ECS.Schema.GetRace(None, key, None, None)):
            assert identity.name == 'Slime Giant' and identity.faction == donor and identity.artKey == token
        assert lua.globals().ECS.Schema.GetPortrait(token, 0) == 'ECS-Portrait-' + token + 'Male'
        assert lua.globals().RACE_ICON_TEXTURES[key + '_MALE'].endswith(token + 'Male')
    assert pack.repair_portrait_glue(glue) == glue, 'Glue repair must be idempotent'


def stage():
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    entries, winning = {}, {}
    try:
        for entry in [p.DBC_ROOT + 'ChrRaces.dbc', *(p.GLUE_ROOT + name for name in pack.GLUE)]:
            data, origin = files.find(entry)
            pack.pinned(STAGE / 'baseline' / Path(entry.replace('\\', '/')).name, data)
            entries[entry] = data
            winning[entry] = {'source': origin, 'sha256': pack.digest(data)}
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
    finally:
        files.close()
    glue = {name: entries[p.GLUE_ROOT + name].decode('utf-8-sig').replace('\r\n', '\n')
            for name in pack.GLUE}
    patched = pack.repair_portrait_glue(glue)
    check_glue(patched)
    replacements = {p.DBC_ROOT + 'ChrRaces.dbc': repair_races(entries[p.DBC_ROOT + 'ChrRaces.dbc'])}
    replacements.update({p.GLUE_ROOT + name: text.encode() for name, text in patched.items()
                         if text != glue[name]})
    art, sources = {}, {}
    preview = Image.new('RGBA', (256, 160), (30, 30, 30, 255))
    for index, (_, faction, *_) in enumerate(pack.SPECS):
        token = 'SlimeGiant' + faction.title()
        source = SOURCE / ('Charactercreate-races_slime-giant_' + faction + '.png')
        before = p.sha256(source)
        pack.pinned(STAGE / 'source-art' / source.name, source.read_bytes())
        with Image.open(source) as original:
            pixels = original.convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
        pixels.putalpha(ImageChops.multiply(pixels.getchannel('A'), portraits.circular_mask()))
        plain = p.encode_portrait(pixels, template)
        icon = p.encode_portrait(portraits.compose_race_icon(pixels, ring), template)
        for sex in ('Male', 'Female'):
            # Both aliases use the single authored body; female selection remains disabled.
            names = ((f'Glues\\CharacterCreate\\UI-CharacterCreate-{token}{sex}', icon),
                     (f'Glues\\CharacterSelect\\ECS-Portrait-{token}{sex}', plain),
                     (f'CharacterFrame\\TemporaryPortrait-{sex}-{token}', plain))
            for name, data in names:
                entry = 'Interface\\' + name + '.blp'
                p.validate_portrait(data, Path(entry))
                art[entry] = data
                if name.startswith('CharacterFrame'):
                    art[entry[:-4]] = data
        assert p.sha256(source) == before
        sources[str(source)] = before
        preview.alpha_composite(portraits.decode_client_blp(icon).resize((128, 128)), (index * 128, 16))
    preview.save(STAGE / 'portrait-preview.png')
    all_payloads = {**replacements, **art}
    entry_files = {}
    for entry, data in all_payloads.items():
        path = STAGE / 'entries' / Path(entry.replace('\\', '/'))
        pack.save(path, data)
        entry_files[entry] = {'path': str(path), 'sha256': pack.digest(data)}
    archives = {}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL, Path('Data/Patch-SG.MPQ')):
        live = p.CLIENT_DEFAULT / relative
        payloads = art if relative.name == 'Patch-SG.MPQ' else replacements
        archives[str(relative)] = {'path': str(live), 'baseline_sha256': p.sha256(live),
                                   'entries': {entry: entry_files[entry] for entry in payloads}}
    server = p.SERVER_DBC_ROOT / 'ChrRaces.dbc'
    baseline = pack.pinned(STAGE / 'baseline-server' / server.name, server.read_bytes())
    server_output = STAGE / 'server' / server.name
    pack.save(server_output, repair_races(baseline))
    report = {'installed': False, 'race_ids': [71, 72], 'archives': archives,
              'winning_entries': winning, 'source_art_sha256': sources,
              'server': {'path': str(server), 'baseline_sha256': pack.digest(baseline),
                         'replacement': str(server_output), 'sha256': p.sha256(server_output)},
              'checks': ['only ChrRaces 71/72 changed', '48 localized labels per race',
                         'numeric creature type restored', 'distinct client file strings', 'Lua 5.1 compile',
                         'file-string to actual RaceID lookup', 'both faction identities and portrait keys',
                         'male-only policy preserved', 'BLP mip/alpha validation', 'original art hashes preserved']}
    pack.save(STAGE / 'repair-plan.json', (json.dumps(report, indent=2) + '\n').encode())
    print('STAGED ONLY:', STAGE / 'repair-plan.json')


def install():
    import shutil
    import subprocess
    from datetime import datetime, timezone
    from slime_giant_client_install import closed
    closed()
    plan = p.load_json(STAGE / 'repair-plan.json')
    assert not plan['installed'], 'This repair is already installed'
    backup = p.CLIENT_DEFAULT / '_backups' / ('slime-identity-' +
        datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True, exist_ok=False)
    result = {'backup': str(backup), 'archives': {}, 'server': {}, 'live_acceptance': 'pending'}
    storm = p.Storm(p.DLL_DEFAULT)
    # Complete and read back every staged archive before replacing any installed archive.
    prepared = []
    for relative, info in plan['archives'].items():
        live = Path(info['path'])
        assert p.sha256(live) == info['baseline_sha256'], 'Client archive changed: ' + relative
        saved = backup / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, saved)
        assert p.sha256(saved) == info['baseline_sha256']
        temporary = live.with_name(live.name + '.slime-identity-next')
        shutil.copy2(live, temporary)
        entries = {name: Path(row['path']).read_bytes() for name, row in info['entries'].items()}
        assert all(pack.digest(entries[name]) == row['sha256'] for name, row in info['entries'].items())
        storm.replace_archive_entries(temporary, entries)
        handle = storm.open_archive(temporary)
        try:
            for name, data in entries.items():
                assert storm.read(handle, name) == data
        finally:
            storm.dll.SFileCloseArchive(handle)
        prepared.append((temporary, live, p.sha256(temporary)))
        result['archives'][relative] = {'backup': str(saved), 'before': info['baseline_sha256'],
                                        'after': prepared[-1][2]}
    server = plan['server']
    live = Path(server['path'])
    assert p.sha256(live) == server['baseline_sha256'], 'Mounted server DBC changed'
    assert p.sha256(Path(server['replacement'])) == server['sha256']
    saved = backup / 'server/ChrRaces.dbc'
    pack.save(saved, live.read_bytes())
    assert p.sha256(saved) == server['baseline_sha256']
    result['server'] = dict(server, backup=str(saved))
    pack.save(backup / 'repair-receipt.json', (json.dumps(result, indent=2) + '\n').encode())
    subprocess.run(['docker', 'compose', 'stop', 'ac-worldserver'], cwd=p.ROOT, check=True)
    try:
        for temporary, target, expected in prepared:
            temporary.replace(target)
            assert p.sha256(target) == expected
        pack.save(live, Path(server['replacement']).read_bytes())
        assert p.sha256(live) == server['sha256']
    except Exception:
        for relative, row in result['archives'].items():
            shutil.copy2(row['backup'], p.CLIENT_DEFAULT / relative)
        shutil.copy2(saved, live)
        raise
    finally:
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], cwd=p.ROOT, check=True)
    plan['installed'] = True
    result['installed'] = True
    for path, value in ((STAGE / 'repair-plan.json', plan), (STAGE / 'repair-receipt.json', result),
                        (backup / 'repair-receipt.json', result)):
        pack.save(path, (json.dumps(value, indent=2) + '\n').encode())
    print('INSTALLED identity and supplied portraits; rollback:', backup, flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=('stage', 'install'), default='stage')
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
