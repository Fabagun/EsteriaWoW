"""Known obsolete source fields must not hide meaningful modifiers or discard parts."""
from pathlib import Path
import unittest
from unittest.mock import patch

from catalog import resolve_appearance, Unsupported


def fixture():
    animations = [dict(type='idle', animation='idle.bmd'), dict(type='walk', animation='walk.bmd')]
    parts = [dict(model='body.bmd', texture='body.png', animations=animations),
             dict(model='shell.bmd', texture='shell.png', animations=animations, texture_transparency=.4)]
    species = dict(dex=0, name='Test', forms=[dict(name='base', genderProperties=[dict(gender='ALL',
                   palettes=[dict(name='none', models=[dict(model_predicate=dict(type='pixelmon:always'),
                                                          models=parts)])])])])
    return dict(name='Test', variant=''), species, parts


class LegacyMetadataTests(unittest.TestCase):
    def resolve(self, form, species):
        with patch('catalog.resource_path', side_effect=lambda root, value: root/value):
            return resolve_appearance(Path('source'), form, species, False)

    def test_ignored_field_preserves_every_model_texture_animation_and_transform(self):
        form, species, parts = fixture()
        with_field = self.resolve(form, species)
        self.assertEqual(len(with_field['parts']), 2)
        self.assertEqual([p['model'] for p in with_field['parts']],
                         [str(Path('source/body.bmd')), str(Path('source/shell.bmd'))])
        self.assertEqual(with_field['legacy_texture_transparency'], [dict(part=1, value=.4)])
        parts[1].pop('texture_transparency')
        without = self.resolve(form, species)
        for key in ['model', 'texture', 'parts', 'animations', 'fps', 'source_motion', 'source_transform']:
            self.assertEqual(with_field[key], without[key])
        self.assertIn('legacy_texture_transparency_ignored_by_pixelmon_9_4_loader', with_field['notes'])

    def test_dandy_palette_alias_is_explicit_and_identity_checked(self):
        form, species, parts = fixture()
        form.update(id='1048', name='Dandy Trim Furfrou', sprite='0676_Furfrou_06', variant='06')
        species.update(dex=676, name='Furfrou')
        species['forms'][0]['name'] = 'dandy'
        palette = species['forms'][0]['genderProperties'][0]['palettes'][0]
        palette['name'] = 'base'
        result = self.resolve(form, species)
        self.assertEqual(result['source_palette'], 'base')
        form['sprite'] = 'wrong_sprite'
        with self.assertRaisesRegex(Unsupported, 'identity_changed'):
            self.resolve(form, species)

    def test_empty_attachments_are_allowed_but_real_attachments_are_not_discarded(self):
        form, species, parts = fixture()
        parts[0]['attachments'] = []
        self.assertEqual(len(self.resolve(form,species)['parts']),2)
        parts[0]['attachments'] = [dict(attachment_point='Head',model='hat.bmd')]
        with self.assertRaisesRegex(Unsupported,'attachments'):
            self.resolve(form,species)

    def test_relative_part_scales_preserve_both_source_transforms(self):
        form, species, parts = fixture()
        parts[0]['scale'] = 1.3
        parts[1]['scale'] = 1.0
        result = self.resolve(form,species)
        self.assertAlmostEqual(result['parts'][0]['source_transform'][0][0],1.3)
        self.assertAlmostEqual(result['parts'][1]['source_transform'][0][0],1.0)
        parts[1]['animation_increment'] = .5
        with self.assertRaisesRegex(Unsupported,'timing'):
            self.resolve(form,species)

    def test_unknown_modifiers_and_invalid_legacy_values_still_fail(self):
        form, species, parts = fixture()
        for value in [True, '0.4', None, -1, 1.1, float('nan')]:
            parts[1]['texture_transparency'] = value
            with self.assertRaisesRegex(Unsupported, 'invalid_legacy'):
                self.resolve(form, species)
        parts[1]['texture_transparency'] = .4
        parts[1]['normal_map'] = 'normal.png'
        with self.assertRaisesRegex(Unsupported, 'model_modifiers:normal_map'):
            self.resolve(form, species)
        parts[1].pop('normal_map')
        parts[1]['emissive'] = 'emissive.png'
        result = self.resolve(form, species)
        self.assertEqual(result['parts'][1]['emissive'], str(Path('source/emissive.png')))
        self.assertIsNone(result['parts'][0]['emissive'])


if __name__ == '__main__':
    unittest.main()
