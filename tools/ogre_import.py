"""Stage and install Horde Ogre and the nine requested portraits without replacing race identities."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
from datetime import datetime

from luaparser import ast
from wotlkconv.m2 import parse_m2, parse_skin
import ogre_furbolg_race_pack as o
import mechagnome_race_pack as db

p = o.p
STAGE = Path('C:/Users/Zach/.codex/tmp/ogre-import-20261006')
DONOR = Path(r'G:\Downloads\HDWoWModels\Project Reforged\Playable_Races_Isolated_2026-10-04\ReadyToPort')
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261007013000000.sql'
ASSET = Path('Data/Patch-T.MPQ')
TABLES = ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo', 'CharSections', 'CharHairGeosets',
          'CharacterFacialHairStyles', 'CharBaseInfo', 'CharStartOutfit', 'NameGen', 'BarberShopStyle')
SERVER = ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo', 'CharSections',
          'CharStartOutfit', 'BarberShopStyle')
WORLD = {'chrraces_dbc': 'ID', 'playercreateinfo': 'race', 'player_race_stats': 'Race',
         'playercreateinfo_item': 'race', 'playercreateinfo_action': 'race', 'player_totem_model': 'RaceID',
         'custom_race_start_spell': 'race', 'custom_race_start_skill': 'race'}
PORTRAITS = (
    ('Horde', 'gnoll', 'male', 'GnollHorde', '_horde'),
    ('Horde', 'ogre', 'female', 'OgreHorde', '_horde'),
    ('Horde', 'ogre', 'male', 'OgreHorde', '_horde'),
    ('Alliance', 'ogre', 'male', 'OgreAlliance', '_alliance'),
    ('Alliance', 'sethrak', 'female', 'SethrakAlliance', '_alliance'),
    ('Alliance', 'sethrak', 'male', 'SethrakAlliance', '_alliance'),
    ('Alliance', 'ogre', 'female', 'OgreAlliance', '_alliance'),
    ('Alliance', 'vrykul', 'female', 'Vrykul', ''),
    ('Alliance', 'vrykul', 'male', 'Vrykul', ''),
)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def patched_glue(name, data):
    text = data.decode('utf-8-sig')
    if name == 'CharacterInfo.lua':
        text = o._insert_once(text, 'local EXACT_RACE_DATA = {\n', o.EXACT_RACE_LINES[0], name)
        text += o.RACE_INFO_BLOCKS[0]
    elif name == 'CharacterCreate.lua':
        text = o.patch_character_create(text)
        text = '\n'.join(line for line in text.split('\n') if '["FURBOLG_' not in line)
        # The existing female Vrykul icon aliases the male art; only update the portrait binding.
        text = text.replace('["VRYKUL_FEMALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
                            'UI-CharacterCreate-VrykulMale"',
                            '["VRYKUL_FEMALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
                            'UI-CharacterCreate-VrykulFemale"')
    elif name == 'GlueStrings.lua':
        text += '\nOGREHORDE="Ogre"; OGREHORDE_MALE=OGREHORDE; OGREHORDE_FEMALE=OGREHORDE;\n'
    elif name == 'GlueParent.lua':
        text = o._insert_once(text, '        ["THINHUMANHORDE"] = true,\n',
                             '        ["OGREHORDE"] = true,\n', name)
        text += o.FOG_LINES[0]
    elif name == 'CharacterSelect.lua':
        anchor = 'elseif ( raceModel == "DARKFALLEN"'
        if text.count(anchor) != 1:
            raise ValueError('CharacterSelect custom-race branch missing')
        text = text.replace(anchor, 'elseif ( raceModel == "OGREHORDE" or raceModel == "DARKFALLEN"', 1)
    elif name == 'ECS_Schema.lua':
        text = o.patch_ecs_schema(text)
        text = '\n'.join(line for line in text.split('\n') if 'FURBOLG' not in line and '[61]' not in line)
        text = text.replace('OgreHorde=true, Furbolg=true,', 'OgreHorde=true,')
    elif name == 'ECS_Integrate.lua':
        anchor = 'or race == 62 or race == 63'
        if anchor not in text:
            raise ValueError('Current ECS exact-race condition missing')
        text = text.replace(anchor, 'or race == 60 ' + anchor)
    ast.parse(text)
    return text.encode('utf-8')


def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    spec = o.spec('ogre')
    allocation = o.load_allocation()
    donor = {f.stem: f.read_bytes() for f in (DONOR / 'Shared/DBFilesClient').glob('*.dbc')}
    baseline = {name: p._full_table(p.CLIENT_DEFAULT / 'Data', name)[0] for name in TABLES}
    output = dict(baseline)
    for name, merge in (('ChrRaces', o.merge_chr_races), ('CreatureModelData', o.merge_creature_model_data),
                        ('CreatureDisplayInfo', o.merge_creature_display_info)):
        ids = {60} if name == 'ChrRaces' else set(allocation['race_allocations']['ogre'][name].values())
        p._ensure_id_free(output[name], name, ids)
        output[name] = merge(output[name], donor[name], spec)
    output['CharSections'], _ = o.build_char_sections(output['CharSections'], donor['CharSections'], allocation, spec)
    output['CharHairGeosets'] = o.build_char_hair_geosets(output['CharHairGeosets'], allocation, spec)
    output['CharacterFacialHairStyles'] = o.build_facial_geosets(output['CharacterFacialHairStyles'], allocation, spec)
    output['CharBaseInfo'] = o.clone_char_base_info(output['CharBaseInfo'], spec)
    outfit = p.RawWdbc(output['CharStartOutfit'])
    p._ensure_id_free(output['CharStartOutfit'],'CharStartOutfit',set(range(22000,22020)))
    # Match the server's last-row-wins index for existing duplicate Orc outfits.
    outfits = {tuple(r[5:8]):r for r in outfit.records if r[4] == 2 and r[5] in spec['class_compat']}
    assert len(outfits) == 20
    additions = [p._replace(p._replace(r,0,4,22000+i),4,1,60) for i,r in enumerate(outfits.values())]
    output['CharStartOutfit'] = outfit.build(list(outfit.records)+additions)
    output['NameGen'], _ = o.clone_namegen(output['NameGen'], allocation, spec)
    # Clone actual Ogre barber selectors rather than Orc styles that the Ogre model lacks.
    t = p.RawWdbc(output['BarberShopStyle'])
    pool, rows = bytearray(t.strings), list(t.records)
    next_id = allocation['race_allocations']['ogre']['BarberShopStyle'][0]
    for gender in (0, 1):
        template = next(r for r in t.records if p._value(r, 148) == 2 and p._value(r, 152) == gender)
        for kind, styles in ((0, range(len(o.APPEARANCE['ogre'][gender]['hair']['styles']))),
                             (1, range(len(o.APPEARANCE['ogre'][gender]['facial']['styles']))),
                             (2, range(6))):
            for style in styles:
                row = p._clone_strings('BarberShopStyle', t, template, pool)
                for field, value in ((0,next_id),(1,kind),(37,60),(38,gender),(39,style)):
                    row = p._replace(row,field*4,4,value)
                rows.append(row)
                next_id += 1
    output['BarberShopStyle'] = t.build(rows, bytes(pool))
    assets = {str(f.relative_to(DONOR/'Ogre')): f.read_bytes()
              for f in (DONOR/'Ogre').rglob('*') if f.is_file() and f.suffix.lower() in ('.m2','.skin','.anim','.blp')}
    key = 'Character\\Ogre\\Female\\ogrefemale00.skin'
    assets[key], repair = o.repair_ogre_female_skin(assets[key])
    storm = o.Storm(p.DLL_DEFAULT)
    key = 'Character\\Jinyu\\Male\\JinyuMaleLower_alpha.blp'
    assets[key] = o._read_archive_entry(storm, o.DONOR_ARCHIVE, key)
    assert o.digest(assets[key]) == o.PINNED_DEPENDENCIES[key]
    read = lambda key: p._effective_file(p.CLIENT_DEFAULT/'Data', key)[0]
    template = read(o.portraits.ICON_TEMPLATE_ENTRY)
    ring = o.portraits.ring_layer(o.portraits.decode_client_blp(read(o.portraits.RING_ENTRY)))
    art_report = []
    for faction, race, gender, token, suffix in PORTRAITS:
        source = o.PICTURES / faction / f'Charactercreate-races_{race}-{gender}{suffix}.png'
        art = o.portraits.portrait_bytes(source, o.portraits.circular_mask())
        plain = o.portraits.encode_portrait(art, template)
        icon = o.portraits.encode_portrait(o.portraits.compose_race_icon(art, ring), template)
        o.portraits.validate_portrait(plain, source)
        sex = gender.title()
        assets[f'{o.CREATOR_ICON_ROOT}UI-CharacterCreate-{token}{sex}.blp'] = icon
        stem = f'{o.CHARACTER_FRAME_ROOT}TemporaryPortrait-{sex}-{token}'
        assets[stem] = assets[stem+'.blp'] = plain
        assets[f'{o.ECS_PORTRAIT_ROOT}ECS-Portrait-{token}{sex}.blp'] = plain
        art_report.append({'source':str(source),'sha256':p.sha256(source),'token':token,'gender':gender})
    # Validate every new section texture against the selected donor or the effective client.
    section = p.RawWdbc(output['CharSections'])
    available = {k.casefold() for k in assets}
    for row in p._table_rows_for_race(output['CharSections'],'CharSections',60):
        for field in (4,5,6):
            key = o._row_string(section,row,field)
            if key and key.casefold() not in available:
                read(key)
    glue = {p.GLUE_ROOT+name:patched_glue(name,read(p.GLUE_ROOT+name)) for name in o.GLUE_PATCHERS}
    for name, data in output.items():
        target = STAGE/'tables'/(name+'.dbc')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        base = STAGE/'baseline-tables'/target.name
        base.parent.mkdir(parents=True,exist_ok=True)
        base.write_bytes(baseline[name])
    for name in SERVER:
        base = (p.SERVER_DBC_ROOT/(name+'.dbc')).read_bytes()
        table, source = p.RawWdbc(base), p.RawWdbc(output[name])
        selected = [r for r in source.records if p._value(r,0) in
                    allocation['race_allocations']['ogre'][name].values()] if name in (
                    'CreatureModelData','CreatureDisplayInfo') else p._table_rows_for_race(output[name],name,60)
        p._ensure_id_free(base,name,{p._value(r,0) for r in selected})
        pool = bytearray(table.strings)
        merged = table.build(list(table.records)+[p._clone_strings(name,source,r,pool) for r in selected],bytes(pool))
        for folder, data in (('server',merged),('baseline-server',base)):
            path = STAGE/folder/(name+'.dbc')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
    MIGRATION.write_text((o.build_sql(spec)+o.build_chrraces_sql(spec)).rstrip()+'\n',encoding='utf-8',newline='\n')
    replacements = {**{p.DBC_ROOT+name+'.dbc':data for name,data in output.items()},**glue,
                    **{key:data for key,data in assets.items() if key.startswith('Interface\\')}}
    archive_before = {}
    for relative in (p.GLOBAL_ARCHIVE_REL,p.LOCALE_ARCHIVE_REL):
        archive_before[str(relative)] = p.sha256(p.CLIENT_DEFAULT/relative)
        target = STAGE/'client'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        o.rebuild_archive_replacing(storm,p.CLIENT_DEFAULT/relative,target,replacements)
        assert target.stat().st_size < 0x80000000
        print('STAGED',relative,flush=True)
    target = STAGE/'client'/ASSET
    if (p.CLIENT_DEFAULT/ASSET).exists():
        raise ValueError('Ogre asset archive already exists')
    storm.create_archive(target,assets)
    entries = {str(relative):p.sha256(STAGE/'client'/relative) for relative in (
        p.GLOBAL_ARCHIVE_REL,p.LOCALE_ARCHIVE_REL,ASSET)}
    save(STAGE/'report.json',{'archives':entries,'before':archive_before,'portraits':art_report,
        'repair':repair,'exe_sha256':p.sha256(p.CLIENT_DEFAULT/'Wow.exe'),
        'migration':str(MIGRATION),'migration_sha256':p.sha256(MIGRATION),'asset_count':len(assets)})
    check()


def check():
    report = p.load_json(STAGE/'report.json')
    for relative, digest in report['archives'].items():
        assert p.sha256(STAGE/'client'/relative) == digest
    for name in TABLES:
        old = p.RawWdbc((STAGE/'baseline-tables'/(name+'.dbc')).read_bytes())
        new = p.RawWdbc((STAGE/'tables'/(name+'.dbc')).read_bytes())
        assert new.records[:len(old.records)] == old.records
        assert new.strings.startswith(old.strings)
        if name not in ('CharBaseInfo','CharStartOutfit','CharacterFacialHairStyles'):
            ids = [p._value(r,0) for r in new.records]
            assert len(ids) == len(set(ids)), name+' duplicate IDs'
    sections = (STAGE/'tables/CharSections.dbc').read_bytes()
    expected, _ = o.build_char_sections((STAGE/'baseline-tables/CharSections.dbc').read_bytes(),
        (DONOR/'Shared/DBFilesClient/CharSections.dbc').read_bytes(),o.load_allocation(),o.spec('ogre'))
    assert sections == expected, 'Ogre sections differ from the filtered donor mapping'
    assert len(p._table_rows_for_race(sections,'CharSections',60)) == 294
    t = p.RawWdbc(sections)
    for row in p._table_rows_for_race(sections,'CharSections',60):
        assert all(not o._row_string(t,row,f) or any(x in o._row_string(t,row,f).lower()
                   for x in ('ogre','jinyu')) for f in (4,5,6))
    storm = o.Storm(p.DLL_DEFAULT)
    for relative in (p.GLOBAL_ARCHIVE_REL,p.LOCALE_ARCHIVE_REL):
        handle = storm.open_archive(STAGE/'client'/relative)
        try:
            for name in TABLES:
                actual = storm.read(handle,p.DBC_ROOT+name+'.dbc')
                expected = (STAGE/'tables'/(name+'.dbc')).read_bytes()
                assert actual == o.order_charsections_entry(p.DBC_ROOT+name+'.dbc',expected), name
            for name in o.GLUE_PATCHERS:
                ast.parse(storm.read(handle,p.GLUE_ROOT+name).decode('utf-8-sig'))
        finally:
            storm.dll.SFileCloseArchive(handle)
    print('CHECKED Ogre rows, donor textures, preserved DBC rows, archive readback and Glue syntax',flush=True)


def fingerprint():
    return {t:hashlib.sha256(db.sql(f'SELECT * FROM `{t}` WHERE `{key}`<>60 ORDER BY 1,2,3;').encode()).hexdigest()
            for t,key in WORLD.items()}


def install():
    check()
    report = p.load_json(STAGE/'report.json')
    processes = subprocess.check_output(['tasklist','/FO','CSV','/NH'],text=True).lower()
    if any(n in processes for n in ('wow.exe','eclipse.exe','mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before installing')
    assert p.sha256(p.CLIENT_DEFAULT/'Wow.exe') == report['exe_sha256']
    for relative, expected in report['before'].items():
        assert p.sha256(p.CLIENT_DEFAULT/relative) == expected, 'client baseline changed'
    assert not (p.CLIENT_DEFAULT/ASSET).exists()
    for name in SERVER:
        assert p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc')) == p.sha256(STAGE/'baseline-server'/(name+'.dbc'))
    for table,key in WORLD.items():
        assert db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{key}`=60;').strip() == '0',table
    assert db.sql('SELECT COUNT(*) FROM characters WHERE race=60;','acore_characters').strip() == '0'
    assert p.sha256(MIGRATION) == report['migration_sha256']
    root = Path('C:/Users/Zach/.codex/backups')/('ogre-import-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    for relative in report['before']:
        target = root/'client'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p.CLIENT_DEFAULT/relative,target)
        assert p.sha256(target) == report['before'][relative]
    shutil.copytree(STAGE/'baseline-server',root/'server')
    for name in SERVER:
        assert p.sha256(root/'server'/(name+'.dbc')) == p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc'))
    appearance_sql = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
                      'FROM characters ORDER BY guid;')
    characters = db.sql(appearance_sql,'acore_characters')
    (root/'characters.tsv').write_text(characters,encoding='utf-8')
    before = fingerprint()
    rollback = '\n'.join(f'DELETE FROM `{t}` WHERE `{key}`=60;' for t,key in WORLD.items())
    rollback += f"\nDELETE FROM updates WHERE name='{MIGRATION.name}';\n"
    (root/'rollback.sql').write_text(rollback,encoding='utf-8')
    save(root/'install-plan.json',report)
    subprocess.run(['docker','stop','ac-worldserver'],check=True)
    receipt = hashlib.sha1(MIGRATION.read_bytes()).hexdigest().upper()
    try:
        db.sql('START TRANSACTION;\n'+MIGRATION.read_text()+
               f"\nINSERT INTO updates (name,hash,state) VALUES ('{MIGRATION.name}','{receipt}','PENDING');\nCOMMIT;")
        for relative in report['archives']:
            source,target = STAGE/'client'/relative,p.CLIENT_DEFAULT/relative
            temporary = target.with_suffix(target.suffix+'.ogre-next')
            shutil.copy2(source,temporary)
            assert p.sha256(temporary) == report['archives'][relative]
            os.replace(temporary,target)
        for name in SERVER:
            shutil.copy2(STAGE/'server'/(name+'.dbc'),p.SERVER_DBC_ROOT/(name+'.dbc'))
            assert p.sha256(STAGE/'server'/(name+'.dbc')) == p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc'))
        assert fingerprint() == before, 'unrelated world rows changed'
        assert db.sql(appearance_sql,'acore_characters') == characters, 'existing characters changed'
    except Exception:
        for relative in report['archives']:
            target = p.CLIENT_DEFAULT/relative
            if relative in report['before']:
                shutil.copy2(root/'client'/relative,target)
            elif target.exists():
                assert p.CLIENT_DEFAULT.resolve() in target.resolve().parents
                target.unlink()
        for name in SERVER:
            shutil.copy2(root/'server'/(name+'.dbc'),p.SERVER_DBC_ROOT/(name+'.dbc'))
        db.sql('START TRANSACTION;\n'+rollback+'\nCOMMIT;')
        raise
    finally:
        subprocess.run(['docker','start','ac-worldserver'],check=True)
    report.update(backup=str(root),receipt=receipt,status='installed_awaiting_live_client_test')
    save(STAGE/'installed.json',report)
    save(root/'installed.json',report)
    print('INSTALLED Horde Ogre and portraits; backup:',root,flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('stage','check','install'))
    globals()[parser.parse_args().action]()
