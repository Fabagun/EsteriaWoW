"""Run real 3D migrations in disposable MySQL databases, using read-only core schema DDL.

Requires an existing MySQL client option file (credentials are never command-line arguments).
Example: python tests/test_3d_migration_mysql.py --mysql mysql --client-config /private/client.cnf
         --schema-database acore_world
Only newly created bm3d_test_* databases are modified/dropped. Core tables are read via SHOW CREATE.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql', required=True)
    parser.add_argument('--client-config', type=Path, required=True)
    schema = parser.add_mutually_exclusive_group(required=True)
    schema.add_argument('--schema-database')
    schema.add_argument('--schema-json', type=Path)
    args = parser.parse_args()
    if args.schema_database:
        assert re.fullmatch(r'[A-Za-z0-9_]+', args.schema_database)
    cli = [args.mysql, '--defaults-extra-file=' + str(args.client_config.resolve()),
           '--batch', '--raw', '--skip-column-names', '--default-character-set=utf8mb4']
    owned = set()

    def sql(statement, database=None, error=None):
        if database is not None:
            assert database in owned
        proc = subprocess.run(cli + ([database] if database else []), input=statement,
                              text=True, encoding='utf-8', capture_output=True)
        if error:
            assert proc.returncode and error in proc.stderr, proc.stderr
        else:
            assert proc.returncode == 0, proc.stderr
        return proc.stdout.strip()

    def create_database():
        name = 'bm3d_test_' + uuid.uuid4().hex[:16]
        assert re.fullmatch(r'bm3d_test_[0-9a-f]{16}', name)
        sql('CREATE DATABASE `' + name + '` CHARACTER SET utf8mb4;')
        owned.add(name)
        return name

    def module_ddl(relative, table):
        text = (MODULE / relative).read_text(encoding='utf-8')
        match = re.search(r'CREATE TABLE(?: IF NOT EXISTS)? `' + table + r'` \(.*?\n\) ENGINE=.*?;',
                          text, re.S)
        assert match, table
        return match[0]

    world_path = REPO / 'modules/mod-battlemon/migrations/manual/2d-to-3d/world.sql'
    characters_path = REPO / 'modules/mod-battlemon/migrations/manual/2d-to-3d/characters.sql'
    world_sql = world_path.read_text(encoding='utf-8')
    characters_sql = characters_path.read_text(encoding='utf-8')
    catalog = json.loads((MODULE / 'data/3d/catalog.json').read_text(encoding='utf-8'))
    assert 'SELECT creature.guid, id, map' in (REPO / 'src/server/game/Globals/ObjectMgr.cpp').read_text(encoding='utf-8')
    core_tables = ['creature', 'creature_template', 'creature_template_model', 'creature_model_info']
    core = json.loads(args.schema_json.read_text(encoding='utf-8')) if args.schema_json else {}
    if not core:
        for table in core_tables:
            row = sql('SHOW CREATE TABLE `' + args.schema_database + '`.`' + table + '`;')
            core[table] = row.split('\t', 1)[1] + ';'
    assert set(core) == set(core_tables)
    assert '`id` ' in core['creature'] and '`id1` ' not in core['creature']
    tables = core_tables + ['battlemon_forms', 'battlemon_species', 'battlemon_form_moves',
                            'battlemon_3d_removed_spawns']

    def snapshot(db, names):
        return {name: sql('SELECT * FROM `' + name + '` ORDER BY 1,2;', db) for name in names}

    def world_fixture():
        db = create_database()
        schema = '\n'.join(core.values())
        for table in ['battlemon_species', 'battlemon_forms']:
            schema += '\n' + module_ddl('data/sql/db-world/base/2026_08_13_00_battlemon_catalog.sql', table)
        schema += '\n' + module_ddl('data/sql/db-world/base/2026_08_15_00_battlemon_move_pools.sql', 'battlemon_form_moves')
        schema += '''
INSERT INTO creature_template (entry, name, ScriptName) VALUES
(60000,'Base','npc_battlemon_overworld'), (1000045,'Unsupported','npc_battlemon_overworld'),
(70037,'Supported','npc_battlemon_overworld'), (70046,'Foreign script','unrelated_npc'),
(900001,'Unrelated','');
INSERT INTO creature (guid,id,map,position_x,position_y,position_z,orientation) VALUES
(1,70045,0,1,2,3,0),(2,70037,0,4,5,6,0),(3,70046,0,7,8,9,0),(4,900001,0,10,11,12,0);
INSERT INTO battlemon_species (id,internal_name,name,type1) VALUES (25,'PIKACHU','Pikachu','ELECTRIC');
INSERT INTO battlemon_forms (id,species_id,sprite,name) VALUES (37,25,'0025_Pikachu','Pikachu');
INSERT INTO battlemon_form_moves (id,form_id,method,level,move_internal_name) VALUES (1,37,'level',1,'THUNDERSHOCK');
CREATE TABLE battlemon_3d_removed_spawns LIKE creature;
INSERT INTO battlemon_3d_removed_spawns SELECT * FROM creature WHERE guid IN (2,3);
'''
        sql(schema, db)
        # Base module installation includes templates for each rescued original form.
        for form in sorted({x['form'] for x in catalog['rescued']}):
            sql(f"INSERT IGNORE INTO creature_template (entry,name,ScriptName) VALUES ({1000000+form},'Rescued original','npc_battlemon_overworld');", db)
        return db

    def check_world(db, unchanged):
        assert sql('SELECT COUNT(*) FROM battlemon_forms WHERE id>=2000;', db) == str(len(catalog['new_forms']))
        assert sql('SELECT COUNT(*) FROM battlemon_species;', db) == str(1 + len(catalog['new_species']))
        assert sql('SELECT COUNT(*) FROM battlemon_form_moves WHERE id>=300000;', db) == str(len(catalog['form_moves']))
        assert sql('SELECT COUNT(*) FROM creature_model_info WHERE DisplayID BETWEEN 400000 AND 400979;', db) == '980'
        assert sql('SELECT guid FROM creature ORDER BY guid;', db) == '2\n3\n4'
        assert sql('SELECT * FROM creature ORDER BY guid;', db) == unchanged
        assert sql('SELECT guid FROM battlemon_3d_removed_spawns ORDER BY guid;', db) == '1\n2\n3'

    try:
        db = world_fixture()
        unchanged = sql('SELECT * FROM creature WHERE guid<>1 ORDER BY guid;', db)
        sql(world_sql, db)
        check_world(db, unchanged)
        completed = snapshot(db, tables)
        sql(world_sql, db)
        assert snapshot(db, tables) == completed
        print('PASS full world migration, exact cleanup, stale-backup protection and repeat-run equality', flush=True)

        db = world_fixture()
        unchanged = sql('SELECT * FROM creature WHERE guid<>1 ORDER BY guid;', db)
        prefix, cleanup = world_sql.rsplit('CREATE TABLE IF NOT EXISTS `battlemon_3d_removed_spawns`', 1)
        broken = prefix + 'CREATE TABLE IF NOT EXISTS `battlemon_3d_removed_spawns`' + cleanup.replace('`c`.`id`', '`c`.`id1`')
        sql(broken, db, error="Unknown column 'c.id1'")
        assert sql('SELECT COUNT(*) FROM battlemon_forms WHERE id>=2000;', db) == str(len(catalog['new_forms']))
        assert sql('SELECT COUNT(*) FROM creature;', db) == '4'
        sql(world_sql, db)
        check_world(db, unchanged)
        assert snapshot(db, tables) == completed
        print('PASS reproduced reported late failure, then retried corrected full migration safely', flush=True)

        db = world_fixture()
        sql('ALTER TABLE creature RENAME COLUMN id TO id1;', db)
        before = snapshot(db, tables)
        sql(world_sql, db, error='requires runtime creature.id schema')
        assert snapshot(db, tables) == before
        print('PASS incompatible base-dump schema rejected before persistent changes', flush=True)

        db = world_fixture()
        sql("INSERT INTO battlemon_forms (id,species_id,sprite,name) VALUES (2000,25,'FOREIGN','Foreign');", db)
        before = snapshot(db, tables)
        sql(world_sql, db, error='3D form ID collision')
        assert snapshot(db, tables) == before
        print('PASS collision guard preserves existing rows', flush=True)

        db = create_database()
        schema = '\n'.join(module_ddl('data/sql/db-characters/base/2026_08_13_00_battlemon_player.sql', name)
                           for name in ['battlemon_account', 'battlemon_owned', 'battlemon_party'])
        schema += '\n' + module_ddl('data/sql/db-characters/base/2026_08_15_00_battlemon_taught.sql', 'battlemon_owned_taught')
        sql(schema, db)
        sql((MODULE / 'data/sql/db-characters/base/2026_08_13_03_battlemon_shiny.sql').read_text(encoding='utf-8'), db)
        pairs = {(x['form'], x['shiny']) for x in catalog['appearances']}
        target = next(x for x in catalog['unsupported_owned'] if (x['form'], 1-x['shiny']) in pairs)
        rescued = catalog['rescued'][0]
        sql(f"""INSERT INTO battlemon_owned (id,guid,form_id,species_id,sprite,shiny) VALUES
(11,100,{target['form']},25,'Unsupported',{target['shiny']}),
(12,100,{target['form']},25,'Supported alternate',{1-target['shiny']}),
(13,100,{rescued['form']},25,'Rescued',{rescued['shiny']});
INSERT INTO battlemon_party (guid,slot,owned_id) VALUES (100,1,11),(100,2,12),(100,3,13);
INSERT INTO battlemon_owned_taught (owned_id,move_internal_name) VALUES (11,'TACKLE'),(12,'TACKLE'),(13,'TACKLE');""", db)
        characters = ['battlemon_owned', 'battlemon_party', 'battlemon_owned_taught']
        original = snapshot(db, characters)
        sql(characters_sql, db)
        assert sql('SELECT id FROM battlemon_owned ORDER BY id;', db) == '12\n13'
        assert sql('SELECT owned_id FROM battlemon_party ORDER BY owned_id;', db) == '12\n13'
        assert sql('SELECT owned_id FROM battlemon_owned_taught ORDER BY owned_id;', db) == '12\n13'
        assert sql('SELECT id FROM battlemon_3d_removed_owned;', db) == '11'
        cleaned = snapshot(db, characters + ['battlemon_3d_removed_owned', 'battlemon_3d_removed_party', 'battlemon_3d_removed_owned_taught'])
        sql(characters_sql, db)
        assert snapshot(db, list(cleaned)) == cleaned
        sql((MODULE / 'data/3d/rollback-characters.sql').read_text(encoding='utf-8'), db)
        assert snapshot(db, characters) == original
        print('PASS exact character-palette removal, rescued preservation, retry and rollback', flush=True)
        print('World SQL SHA256:', hashlib.sha256(world_path.read_bytes()).hexdigest(), flush=True)
    finally:
        for db in sorted(owned):
            assert re.fullmatch(r'bm3d_test_[0-9a-f]{16}', db)
            sql('DROP DATABASE `' + db + '`;')
        print('Removed disposable test databases; existing databases were read-only.', flush=True)


if __name__ == '__main__':
    main()
