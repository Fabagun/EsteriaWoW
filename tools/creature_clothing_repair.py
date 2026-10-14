"""Route Gnoll/Saberon clothing to alpha-preserving slot14 without changing fur, meshes or characters."""

import argparse
from pathlib import Path
import shutil

from wotlkconv.m2 import parse_m2, write_md20

import gnoll_equipment_repair as installer
import gnoll_race_pack as g
import retroported_race_pack as p
import saberon_race_pack as s
import sethrak_animation_pack as animation

STAGE = Path('C:/Users/Zach/.codex/tmp/creature-clothing-alpha-20261008')
BUILD = Path('C:/cca8-build')
SPECIES = (g, s)


def redirect(model):
    assert not any(t['type'] == 14 for t in model.textures)
    changed = [i for i, t in enumerate(model.textures) if t['type'] == 1]
    assert len(changed) == 1
    model.textures[changed[0]]['type'] = 14
    model.replacable_texture_lookup.extend([65535] * max(0, 16 - len(model.replacable_texture_lookup)))
    model.replacable_texture_lookup[1] = 65535
    model.replacable_texture_lookup[14] = changed[0]


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for species in SPECIES:
            data, provider = files.find(species.MODEL)
            g.c.immutable(STAGE / (species.TOKEN + '-before.m2'), data)
            model = parse_m2(data)
            redirect(model)
            target = g.local(STAGE / 'assets', species.MODEL)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(write_md20(model))
            print('PREPARED', species.TOKEN, provider)
    finally:
        files.close()
    protected = {str(path.relative_to(p.CLIENT_DEFAULT)): p.sha256(path)
                 for path in p.CLIENT_DEFAULT.glob('Esteria*.bin')}
    protected.update({str(name): p.sha256(p.CLIENT_DEFAULT / name) for name in
                      ('Wow.exe', p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL)})
    g.save(STAGE / 'changes.json', {'protected': protected})
    check()
    report = {'files': {}, 'before': {}, 'after': {}, 'protected': protected,
              'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe')}
    storm = p.Storm(p.DLL_DEFAULT)
    for species in SPECIES:
        name = str(species.ASSET_ARCHIVE)
        source = p.CLIENT_DEFAULT / species.ASSET_ARCHIVE
        target = STAGE / species.ASSET_ARCHIVE
        target.parent.mkdir(parents=True, exist_ok=True)
        report['before'][name] = p.sha256(source)
        shutil.copy2(source, target)
        data = g.local(STAGE / 'assets', species.MODEL).read_bytes()
        storm.replace_archive_entries(target, {species.MODEL: data})
        handle = storm.open_archive(target)
        try:
            assert storm.read(handle, species.MODEL) == data
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(source) == report['before'][name]
        report['files'][name] = str(target)
        report['after'][name] = p.sha256(target)
    report['before']['EsteriaAppearance.dll'] = p.sha256(p.CLIENT_DEFAULT / 'EsteriaAppearance.dll')
    g.save(STAGE / 'stage.json', report)
    BUILD.mkdir(exist_ok=True)
    for path in p.CLIENT_DEFAULT.glob('Esteria*.bin'):
        shutil.copy2(path, BUILD / path.name)
    print('PASS staged Gnoll/Saberon archive readbacks; geometry and catalogs untouched')


def check():
    for species in SPECIES:
        before = parse_m2((STAGE / (species.TOKEN + '-before.m2')).read_bytes())
        data = g.local(STAGE / 'assets', species.MODEL).read_bytes()
        after = parse_m2(data)
        animation.check_model(after, data)
        restored = parse_m2(data)
        index = restored.replacable_texture_lookup[14]
        assert restored.textures[index]['type'] == 14
        restored.textures[index]['type'] = 1
        restored.replacable_texture_lookup[1] = index
        restored.replacable_texture_lookup[14] = 65535
        assert write_md20(restored) == write_md20(before), 'Change extends beyond clothing slot'
        assert after.vertices == before.vertices and after.materials == before.materials
        assert after.sequences == before.sequences
        animation.tracks_equal(before, after, len(before.sequences))
    print('PASS both models: only clothing slot1 becomes slot14; fur/rig/materials unchanged')


def install():
    report = p.load_json(STAGE / 'stage.json')
    dll = BUILD / 'EsteriaAppearance.dll'
    assert dll.exists() and p.sha256(dll) != report['before']['EsteriaAppearance.dll']
    report['files']['EsteriaAppearance.dll'] = str(dll)
    report['after']['EsteriaAppearance.dll'] = p.sha256(dll)
    g.save(STAGE / 'stage.json', report)
    installer.STAGE = STAGE
    installer.install(validate=check)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'install'))
    globals()[parser.parse_args().action]()
