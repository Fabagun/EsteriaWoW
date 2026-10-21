"""Stage approved race/team moves and preserve a scoped rollback; never apply SQL."""

import json

import slime_centaur_racials as r
from slime_giant_deploy import sql

MIGRATION = r.p.ROOT / 'data/sql/updates/pending_db_characters/rev_20261021010000000_slime_centaur_factions.sql'


def registry():
    path = r.p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    data = json.loads(path.read_text())
    for row in list(data['playable']):
        if row['id'] not in (71, 72, 73, 74):
            continue
        row['species_selection'] = False
        if row['id'] in (71, 74):
            data['playable'].remove(row)
            if not any(item['id'] == row['id'] for item in data['npc_only']):
                data['npc_only'].append({'id': row['id'], 'name': row['display_name'],
                                         'legacy_id': row['legacy_mask_race'], 'not_playable': True})
    data['faction_pairs'] = [pair for pair in data['faction_pairs']
                             if pair['species_key'] not in ('slime_giant', 'centaur')]
    r.save(path, (json.dumps(data, indent=2) + '\n').encode())
    for slug in ('slime_giant_alliance', 'slime_giant_horde', 'centaur_alliance', 'centaur_horde'):
        path = r.p.manifest_path(slug)
        data = json.loads(path.read_text())
        race = data['race_ids'][0]
        data['creation_enabled'] = race in (72, 73)
        if race in r.GRANTS:
            data['custom_racial_spells'] = list(r.GRANTS[race]) + (list(range(111000, 111004)) if race == 73 else [])
        r.save(path, (json.dumps(data, indent=2) + '\n').encode())


def stage():
    fields = ('guid', 'race', 'teamId', 'map', 'zone', 'position_x', 'position_y', 'position_z', 'orientation')
    raw = sql('SELECT ' + ','.join(fields) + ',class,online FROM characters WHERE race IN (71,74) ORDER BY guid;',
              'acore_characters')
    rows = [line.decode().split('\t') for line in raw.splitlines()]
    assert rows and all(row[-1] == '0' for row in rows), 'Migration requires offline characters'
    ids = ','.join(row[0] for row in rows)
    # Preserve guild, party, inventory, appearance, quests and professions. No destructive faction service cleanup.
    assert sql('SELECT COUNT(*) FROM character_queststatus WHERE guid IN (' + ids + ');',
               'acore_characters').strip() == b'0', 'Review active faction quests before staging migration'
    skills = sql('SELECT guid,skill,value,max FROM character_skills WHERE guid IN (' + ids
                 + ') AND skill IN (98,109) ORDER BY guid,skill;', 'acore_characters')
    binds = sql('SELECT guid,mapId,zoneId,posX,posY,posZ FROM character_homebind WHERE guid IN (' + ids
                + ') ORDER BY guid;', 'acore_characters')
    forward = ['-- Approved Slime Giant 71 -> 72 and Centaur 74 -> 73 moves. Apply with worldserver stopped.']
    rollback = ['-- Restore the exact pre-migration race/team/location/language/homebind values.']
    for row in rows:
        guid, old_race = int(row[0]), int(row[1])
        race, team, donor, language = (72, 1, 2, 109) if old_race == 71 else (73, 0, 1, 98)
        origin = sql('SELECT map,zone,position_x,position_y,position_z,orientation FROM playercreateinfo '
                     f'WHERE race={race} AND class={int(row[-2])};').strip().decode().split('\t')
        assert len(origin) == 6
        values = [str(race), str(team), *origin]
        forward.append('UPDATE `characters` SET ' + ', '.join(f'`{key}` = {value}'
                        for key, value in zip(fields[1:], values))
                        + f' WHERE `guid` = {guid} AND `race` = {old_race} AND `online` = 0;')
        rollback.append('UPDATE `characters` SET ' + ', '.join(f'`{key}` = {value}'
                         for key, value in zip(fields[1:], row[1:9]))
                         + f' WHERE `guid` = {guid} AND `race` = {race} AND `online` = 0;')
        rollback.append(f'DELETE FROM `character_skills` WHERE `guid` = {guid} AND `skill` IN (98, 109);')
        rollback.append(f'DELETE FROM `character_homebind` WHERE `guid` = {guid};')
        forward += [f'DELETE FROM `character_skills` WHERE `guid` = {guid} AND `skill` IN (98, 109);',
                    'INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES\n'
                    f'({guid}, {language}, 300, 300);',
                    f'DELETE FROM `character_homebind` WHERE `guid` = {guid};',
                    'INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES\n'
                    f'({guid}, ' + ', '.join(origin[:5]) + ');']
    for table, data, columns in (('character_skills', skills, ('guid', 'skill', 'value', 'max')),
                                 ('character_homebind', binds, ('guid', 'mapId', 'zoneId', 'posX', 'posY', 'posZ'))):
        for line in data.splitlines():
            values = line.decode().split('\t')
            rollback.append('INSERT INTO `' + table + '` (' + ', '.join('`' + c + '`' for c in columns)
                            + ') VALUES\n(' + ', '.join(values) + ');')
    r.save(MIGRATION, ('\n'.join(forward) + '\n').encode())
    r.save(r.WORK / 'migration/rollback-characters.sql', ('\n'.join(rollback) + '\n').encode())
    r.save(r.WORK / 'migration/characters-before.tsv', raw)
    r.save(r.WORK / 'migration/languages-before.tsv', skills)
    r.save(r.WORK / 'migration/homebind-before.tsv', binds)
    report = {'affected_guids': [int(row[0]) for row in rows], 'count': len(rows), 'applied': False,
              'forward': str(MIGRATION), 'rollback': str(r.WORK / 'migration/rollback-characters.sql')}
    r.save(r.WORK / 'migration/report.json', (json.dumps(report, indent=2) + '\n').encode())
    registry()
    print('STAGED', len(rows), 'race/team moves, matching languages and safe starts, with exact rollback')


if __name__ == '__main__':
    stage()
