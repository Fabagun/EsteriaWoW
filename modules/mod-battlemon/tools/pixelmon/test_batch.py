"""Safety and resume checks for the bulk converter; runs without Pixelmon or a game server."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from batch import ASSETS, LAYER, atomic_json, cached_result, check_texture_interior, digest, fingerprint
from batch_deploy import deploy, target, validate_package
from catalog import choose_form, resolve_appearance, resource_path, Unsupported
from convert import write_dbc


class MappingTests(unittest.TestCase):
    def test_numeric_and_ambiguous_forms_are_not_guessed(self):
        species = dict(name='Unown', forms=[dict(name='a'), dict(name='b')], defaultForms=['a', 'b'])
        with self.assertRaisesRegex(Unsupported, 'ambiguous_default'):
            choose_form(dict(name='Unown', variant=''), species)
        with self.assertRaisesRegex(Unsupported, 'unmapped_variant'):
            choose_form(dict(name='Unown (02)', variant='02'), species)
        picked, gender = choose_form(dict(name='Unown B', variant='b'), species)
        self.assertEqual(picked['name'], 'b')

    def test_female_uses_all_gender_group_but_never_male_only(self):
        species = dict(name='Test', forms=[dict(name='base', genderProperties=[dict(gender='ALL', palettes=[])])])
        with self.assertRaisesRegex(Unsupported, 'missing_palette'):
            resolve_appearance(Path('.'), dict(name='Test (Female)', variant='female'), species, False)
        with self.assertRaisesRegex(Unsupported, 'missing_palette'):
            resolve_appearance(Path('.'), dict(name='Test', variant=''), species, True)

        species['forms'][0]['genderProperties'][0]['gender'] = 'MALE'
        with self.assertRaisesRegex(Unsupported, 'missing_gender:FEMALE'):
            resolve_appearance(Path('.'), dict(name='Test (Female)', variant='female'), species, False)

    def test_resource_cannot_escape_source(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(Unsupported, 'resource_path_escape'):
                resource_path(Path(directory), 'pixelmon:../../../outside.bmd')

    def test_intentional_cutout_is_not_filled_as_a_seam(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'cutout.png'
            Image.new('RGBA', (32, 32), (255, 0, 0, 0)).save(source)
            vertices = np.zeros((6, 8))
            vertices[:, 6:8] = [[.1, .1], [.9, .1], [.1, .9]]*2
            with self.assertRaisesRegex(Unsupported, 'interior_transparency'):
                check_texture_interior(source, dict(vertices=vertices, triangles=list(range(6))))


class ResumeTests(unittest.TestCase):
    def test_cache_checks_assets_and_source_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source.bmd'
            source.write_bytes(b'first')
            appearance = dict(model=str(source), texture=str(source), animations=dict(idle=str(source)), fps=30)
            key = fingerprint(appearance, 'revision-one')
            self.assertNotEqual(key, fingerprint(appearance, 'revision-two'))
            source.write_bytes(b'second')
            self.assertNotEqual(key, fingerprint(appearance, 'revision-one'))
            asset = root/'cache/assets/test.m2'
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b'valid')
            atomic_json(root/'cache/results'/('key.json'), dict(status='passed', files={'test.m2': digest(asset)}))
            self.assertEqual(cached_result(root, 'key')['status'], 'passed')
            asset.write_bytes(b'corrupt')
            self.assertIsNone(cached_result(root, 'key'))
            atomic_json(root/'cache/results/failed.json', dict(status='failed', reason='unsupported'))
            self.assertEqual(cached_result(root, 'failed')['status'], 'failed')
            self.assertIsNone(cached_result(root, 'failed', retry_failed=True))


def fixture(root):
    output, client, server = root/'output', root/'client', root/'server'
    package = output/'package'
    asset = 'a_'+'1'*20
    files = {}
    for ext in ['.m2', '00.skin', '.blp']:
        relative = 'client/'+ASSETS+'/'+asset+ext
        path = package/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture-only')
        files[relative] = digest(path)
    mr, dr = [0]*28, [0]*16
    mr[0], dr[0], dr[1] = 70002, 50002, 70002
    for side, folder in [('client', 'DBFilesClient'), ('server', 'dbc-continuations')]:
        for name, row, strings in [('CreatureModelData', mr, {2: (ASSETS+'/'+asset+'.mdx').replace('/', '\\')}),
                                   ('CreatureDisplayInfo', dr, {i: '' for i in [6, 7, 8, 9]})]:
            relative = side+'/'+folder+'/'+name+LAYER
            path = package/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            write_dbc(path, [(row, strings)], len(row), list(strings))
            files[relative] = digest(path)
    manifest = dict(schema=1, layer=LAYER, files=files,
                    appearances=[dict(form=2, name='Ivysaur', shiny=False, display=50002, model=70002, asset=asset)])
    atomic_json(package/'manifest.json', manifest)
    (client/'Data/patch-z.mpq').mkdir(parents=True)
    (client/'Wow.exe').touch()
    (server/'dbc-continuations').mkdir(parents=True)
    return output, client, server


class DeployTests(unittest.TestCase):
    def test_install_resume_external_edit_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server = fixture(Path(directory))
            baseline = client/'Data/patch-z.mpq/original-sprite'
            baseline.write_bytes(b'unchanged')
            # Fail after the first copy: the written journal makes the partial install recoverable.
            import batch_deploy
            original_copy = batch_deploy.shutil.copyfile
            calls = 0
            def interrupted_copy(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('simulated interruption')
                return original_copy(source, destination)
            with patch('batch_deploy.shutil.copyfile', side_effect=interrupted_copy):
                with self.assertRaises(OSError):
                    deploy(output, client, server)
            deploy(output, client, server)
            receipt = json.loads((output/'installed-batch.json').read_text())
            relative = next(iter(receipt['files']))
            victim = target(relative, client, server)
            before = victim.read_bytes()
            victim.write_bytes(b'external edit')
            with self.assertRaisesRegex(ValueError, 'externally changed'):
                deploy(output, client, server, remove=True)
            victim.write_bytes(before)
            # Removal uses the receipt even if a later build replaces or loses the package manifest.
            (output/'package/manifest.json').unlink()
            deploy(output, client, server, remove=True)
            self.assertTrue(all(not target(r, client, server).exists() for r in receipt['files']))
            self.assertEqual(baseline.read_bytes(), b'unchanged')

    def test_package_tamper_unowned_files_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            output, client, server = fixture(Path(directory))
            manifest = validate_package(output/'package')
            relative = next(iter(manifest['files']))
            victim = target(relative, client, server)
            victim.parent.mkdir(parents=True, exist_ok=True)
            victim.write_bytes(b'someone else owns this')
            with self.assertRaisesRegex(ValueError, 'Unowned'):
                deploy(output, client, server)
            with self.assertRaises(ValueError):
                target('client/../outside', client, server)
            path = output/'package'/relative
            path.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                validate_package(output/'package')

    def test_static_source_policy_requires_explicit_annotation(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _, _ = fixture(Path(directory))
            path = output/'package/manifest.json'
            manifest = json.loads(path.read_text())
            entry = manifest['appearances'][0]
            entry['source_motion'] = 'static_bind_pose'
            atomic_json(path, manifest)
            with self.assertRaisesRegex(ValueError, 'Missing explicit static'):
                validate_package(output/'package')
            entry['notes'] = ['source_has_no_animations_static_bind_pose']
            atomic_json(path, manifest)
            validate_package(output/'package')
            entry['source_motion'] = 'skip_checks'
            atomic_json(path, manifest)
            with self.assertRaisesRegex(ValueError, 'Unknown source motion'):
                validate_package(output/'package')

    def test_duplicate_mapping_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _, _ = fixture(Path(directory))
            path = output/'package/manifest.json'
            manifest = json.loads(path.read_text())
            manifest['appearances'].append(copy.deepcopy(manifest['appearances'][0]))
            atomic_json(path, manifest)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                validate_package(output/'package')


if __name__ == '__main__':
    unittest.main()
