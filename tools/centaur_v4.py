"""Stage the Centaur-only native display control and verify the matched repair assets."""

from collections import Counter
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import centaur_deploy as deploy
from centaur_clothing import save
from sethrak_equipment_repair import mesh_triangles
from wotlkconv.m2 import parse_m2, parse_skin

WORK = deploy.WORK / 'repair-v4'
UI_NAME = 'Interface\\FrameXML\\InterfaceOptionsPanels.xml'
MIGRATION = Path('data/sql/updates/pending_db_world/rev_20261020040000000_centaur_model_gender.sql')


def stage_ui():
    with deploy.pack.p.ClientFiles(str(deploy.CLIENT / 'Data'), 'enUS') as files:
        data, source = files.find(UI_NAME)
    path = WORK / 'InterfaceOptionsPanels.xml'
    assert not path.exists() or path.read_bytes() == data, 'Display panel baseline changed'
    path.write_bytes(data)
    text = data.decode('utf-8-sig')
    start = text.index('<CheckButton name="$parentShowHelm"')
    end = text.index('</CheckButton>', start) + len('</CheckButton>')
    block = text[start:end].replace('$parentShowHelm', '$parentShowLegArmor')
    block = block.replace('ShowingHelm()', 'ShowingLegArmor()').replace('ShowHelm(value)', 'ShowLegArmor(value)')
    block = block.replace('SHOW_HELM', '"Show leg armor"')
    block = block.replace('OPTION_TOOLTIP_"Show leg armor"',
                          '"Show leg armor on this Centaur. Other players see this choice."')
    block = block.replace('relativeTo="$parentShowCloak" relativePoint="BOTTOMLEFT"',
                          'relativeTo="$parentShowHelm" relativePoint="TOPLEFT"')
    block = block.replace('x="0" y="-8"', 'x="190" y="0"')
    block = block.replace('self:RegisterEvent("PLAYER_FLAGS_CHANGED");',
                          'self:RegisterEvent("PLAYER_FLAGS_CHANGED");\n'
                          'self:RegisterEvent("PLAYER_ENTERING_WORLD"); self:Hide();')
    block = block.replace('if ( arg1 == "player" ) then',
                          'if event == "PLAYER_ENTERING_WORLD" or arg1 == "player" then\n'
                          'if ShowingLegArmor() == nil then self:Hide(); return; end\nself:Show();')
    updated = (text[:end] + '\n' + block + text[end:]).encode('utf-8')
    tree = ET.fromstring(updated)
    from lupa.lua51 import LuaRuntime
    lua = LuaRuntime()
    compile_chunk = lua.eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for scripts in tree.iter():
        if scripts.tag.rsplit('}', 1)[-1] == 'Scripts':
            for script in scripts:
                if script.text:
                    compile_chunk('return function(self, event, ...)\n' + script.text + '\nend')
    destination = WORK / 'client-ui/InterfaceOptionsPanels.xml'
    destination.parent.mkdir(exist_ok=True)
    destination.write_bytes(updated)
    print('STAGED Centaur-only native Show leg armor checkbox beside Show helm:', source)


def triangle_records(root, identifier):
    model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
    skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
    result = {}
    for row in skin.submeshes:
        geoset = struct.unpack_from('<H', row)[0]
        counter = result.setdefault(geoset, Counter())
        for tri in mesh_triangles(skin, row):
            counter[tuple(model.vertices[i * 48:(i + 1) * 48] for i in tri)] += 1
    return result


def verify():
    import test_centaur_refine
    test_centaur_refine.main()
    root = deploy.pack.STAGE / 'assets/custom/centaur'
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    archive = storm.open_archive(deploy.CLIENT / deploy.ASSET)
    baseline = WORK / 'baseline'
    baseline.mkdir(exist_ok=True)
    try:
        for identifier in (4036647, 4081379):
            for extension in ('.m2', '00.skin'):
                name = f'{identifier}-clothing{extension}'
                data = storm.read(archive, 'custom/centaur/' + name)
                path = baseline / name
                assert not path.exists() or path.read_bytes() == data, 'Installed asset baseline changed'
                path.write_bytes(data)
    finally:
        storm.dll.SFileCloseArchive(archive)
    report = {}
    for sex, identifier in enumerate((4036647, 4081379)):
        before, after = triangle_records(baseline, identifier), triangle_records(root, identifier)
        assert before.keys() == after.keys()
        assert all(before[g] == after[g] for g in before if g // 100 != 15), 'Unrelated clothing changed'
        model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
        skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
        cape_points = []
        for row in skin.submeshes:
            if struct.unpack_from('<H', row)[0] // 100 == 15:
                cape_points.extend(struct.unpack_from('<3f', model.vertices, i * 48)
                                   for tri in mesh_triangles(skin, row) for i in tri)
        assert cape_points and all(-.63 < x < .45 and abs(y) < .27 and 1.5 < z < 2.03
                                   for x, y, z in cape_points), 'Capes must follow the horse back'
        transfer = json.loads((deploy.WORK / 'clothing' / str(sex) / 'transfer-result.json').read_text())
        assert transfer['cape_vertices'] and len(transfer['capes']) > 0
        report[str(identifier)] = {'unrelated_clothing_identical': True, 'cape_variants': len(after) - sum(
            g // 100 != 15 for g in after), 'cape_triangles': sum(sum(c.values()) for g, c in after.items()
                                                               if g // 100 == 15)}
    assert (deploy.NATIVE / 'Engine/Source/Retail/CentaurAppearance.h').read_bytes() == Path(
        'src/server/shared/CentaurAppearance.h').read_bytes()
    assert MIGRATION.read_text() == deploy.pack.model_info_sql(), 'Initial and repair gender rows must agree'
    save(WORK / 'art-validation.json', report)
    print('PASS both draped cloak collections; every non-cape triangle/UV/weight record is unchanged')


if __name__ == '__main__':
    stage_ui()
    verify()
