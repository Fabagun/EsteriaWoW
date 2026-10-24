"""Direct path overrides preserve source data and retire only verified experimental files."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from batch import atomic_json, digest
from convert import write_dbc, write_blp
from direct_deploy import build, validate, install, destination, relink_model
from m2 import build_model
from test_skin_sections import fixture as mesh_fixture
from validate import read_model


def fixture(root):
    output, client, server = root/'output', root/'client', root/'server'
    original = client/'Data/patch-W.mpq/Creature/Battlemon'
    original.mkdir(parents=True)
    dbc = client/'Data/patch-z.mpq/DBFilesClient'
    dbc.mkdir(parents=True)
    (client/'Wow.exe').touch()
    (server/'dbc-continuations').mkdir(parents=True)
    asset, stem = 'a_'+'a'*20, '0001_Test_s'
    cache = output/'cache/assets'
    cache.mkdir(parents=True)
    model, skin = build_model(mesh_fixture(), asset, 'Creature\\Battlemon3DBatch\\'+asset+'.blp')
    (cache/(asset+'.m2')).write_bytes(model)
    (cache/(asset+'00.skin')).write_bytes(skin)
    Image.new('RGBA', (16, 16), (20, 50, 150, 255)).save(root/'source.png')
    write_blp(cache/(asset+'.blp'), root/'source.png')
    files = {}
    for ext in ['.m2', '00.skin', '.blp']:
        (original/(stem+ext)).write_bytes(b'original sprite '+ext.encode())
        files[asset+ext] = digest(cache/(asset+ext))
    mr, dr = [0]*28, [0]*16
    mr[0], mr[4], dr[0], dr[1], dr[4] = 70001, 1065353216, 60001, 70001, 1065353216
    write_dbc(dbc/'CreatureModelData.dbc1-battlemon', [(mr, {2: 'Creature\\Battlemon\\'+stem+'.mdx'})], 28, [2])
    write_dbc(dbc/'CreatureDisplayInfo.dbc1-battlemon', [(dr, {i: '' for i in [6,7,8,9]})], 16, [6,7,8,9])
    atomic_json(output/'report.json', dict(records=[dict(form=1, name='Test', shiny=True, status='passed',
                                                      result=dict(asset=asset, files=files))]))
    return output, client, server, asset, stem


class DirectDeployTests(unittest.TestCase):
    def test_relink_preserves_every_decoded_vertex_pose_uv_and_triangle(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server, asset, stem = fixture(Path(directory))
            original = read_model(output/'cache/assets'/(asset+'.m2'))
            manifest = build(output, client)
            validate(output, client, deep=True)
            decoded = read_model(output/'direct-package/Creature/Battlemon'/(stem+'.m2'))
            self.assertEqual(decoded['texture'], 'Creature\\Battlemon\\0001_Test_s.blp')
            for field in ['positions', 'triangles', 'uv', 'bounds']:
                np.testing.assert_array_equal(original[field], decoded[field])
            for a, b in zip(original['poses'], decoded['poses']):
                np.testing.assert_array_equal(a, b)
            self.assertEqual(len(manifest['files']), 3)
            self.assertFalse(any('.dbc' in f for f in manifest['files']))

    def test_install_archive_resume_and_remove_preserve_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server, asset, stem = fixture(Path(directory))
            before = {p: digest(p) for p in client.rglob('*') if p.is_file()}
            layer = 'DBFilesClient/CreatureModelData.dbc9-battlemon-3d-batch'
            old = client/'Data/patch-z.mpq'/layer
            old.write_bytes(b'old experimental layer')
            legacy = client/'Data/patch-z.mpq/Creature/Battlemon3DBatch'/(asset+'.m2')
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b'old hashed asset')
            atomic_json(output/'installed-batch.json', dict(client=str(client.resolve()),
                        server_data=str(server.resolve()), files={'client/'+layer: [digest(old)],
                        'client/Creature/Battlemon3DBatch/'+asset+'.m2': [digest(legacy)]}))
            build(output, client)
            install(output, client, server)
            self.assertFalse(old.exists())
            self.assertFalse(legacy.exists())
            receipt = json.loads((output/'installed-direct.json').read_text())
            for item in receipt['retired']:
                self.assertEqual(digest(Path(item['backup'])), item['sha256'])
            install(output, client, server)
            victim = destination(client, 'Creature/Battlemon/'+stem+'.m2')
            saved = victim.read_bytes()
            victim.write_bytes(b'external edit')
            with self.assertRaisesRegex(ValueError, 'externally modified'):
                install(output, client, server, remove=True)
            victim.write_bytes(saved)
            install(output, client, server, remove=True)
            self.assertFalse(victim.exists())
            self.assertFalse(old.exists())  # Rollback returns to sprites, not old 3D DBC mappings.
            self.assertTrue(all(digest(p)==h for p,h in before.items()))

    def test_unowned_overrides_and_layers_are_never_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server, asset, stem = fixture(Path(directory))
            build(output, client)
            layer = client/'Data/patch-z.mpq/DBFilesClient/CreatureModelData.dbc9-battlemon-3d'
            layer.write_bytes(b'unowned')
            with self.assertRaisesRegex(ValueError, 'ownership receipt'):
                install(output, client, server)
            self.assertEqual(layer.read_bytes(), b'unowned')
            self.assertFalse(destination(client, 'Creature/Battlemon/'+stem+'.m2').exists())
            layer.unlink()
            target = destination(client, 'Creature/Battlemon/'+stem+'.m2')
            target.parent.mkdir(parents=True)
            target.write_bytes(b'unowned')
            with self.assertRaisesRegex(ValueError, 'Unowned'):
                install(output, client, server)
            self.assertEqual(target.read_bytes(), b'unowned')
            with self.assertRaises(ValueError):
                destination(client, 'Creature/Battlemon/../outside.m2')

    def test_existing_dbc_path_can_fill_an_absent_original_sprite(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server, asset, stem = fixture(Path(directory))
            for ext in ['.m2', '00.skin', '.blp']:
                (client/'Data/patch-W.mpq/Creature/Battlemon'/(stem+ext)).unlink()
            manifest = build(output, client)
            self.assertTrue(all(e['original_sha256'] is None for e in manifest['sources'].values()))
            install(output, client, server)
            self.assertTrue(destination(client, 'Creature/Battlemon/'+stem+'.m2').exists())
            original = client/'Data/patch-W.mpq/Creature/Battlemon'/(stem+'.m2')
            original.write_bytes(b'new external original')
            with self.assertRaisesRegex(ValueError, 'original sprite changed'):
                validate(output, client)

    def test_model_changes_outside_reference_descriptors_fail_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server, asset, stem = fixture(Path(directory))
            build(output, client)
            path = output/'direct-package/Creature/Battlemon'/(stem+'.m2')
            data = bytearray(path.read_bytes())
            vertices = struct.unpack_from('<I', data, 0x40)[0]
            data[vertices] ^= 1
            path.write_bytes(data)
            mpath = output/'direct-package/manifest.json'
            manifest = json.loads(mpath.read_text())
            manifest['files']['Creature/Battlemon/'+stem+'.m2'] = digest(path)
            atomic_json(mpath, manifest)
            with self.assertRaisesRegex(ValueError, 'Unexpected change'):
                validate(output, client)


if __name__ == '__main__':
    unittest.main()
