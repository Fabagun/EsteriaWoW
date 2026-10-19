"""Repair male Drakkin selectors that the creator refresh shows outside customization."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil

import tarasek_drakkin as t
import tarasek_deploy as d
from drakkin_male_portraits import inventory
from lupa.lua51 import LuaRuntime


WORK = Path('C:/RetroPorterWork/drakkin-customization-visibility')
KEY = 'Interface\\GlueXML\\CharacterCreate.lua'
ARCHIVES = ('Data/patch-Z.MPQ', 'Data/enUS/patch-enUS-Z.MPQ')


def patch(data):
    text = data.decode('utf-8-sig')
    start = text.index('        if CharacterCreate.selectedRaceID == 66 and GetSelectedSex() == SEX_MALE then')
    end = text.index('        elseif CharacterCreate.selectedRaceID == 66', start)
    original = text[start:end]
    changed = original
    for index in (3, 4):
        old = f'            CharacterCustomizationButtonFrame{index}:Show();'
        new = (f'            if CharCreateOkayButton:IsShown() then CharacterCustomizationButtonFrame{index}:Show();\n'
               f'            else CharacterCustomizationButtonFrame{index}:Hide(); end')
        assert changed.count(old) == 1, 'Installed selector layout changed'
        changed = changed.replace(old, new)
    return (text[:start] + changed + text[end:]).encode()


def validate(original, changed):
    compiler = LuaRuntime()
    compiler.eval('function(s) local f,e=loadstring(s); assert(f,e); end')(changed.decode())
    # Run the actual installed refresh, including expanded-race branches, in Lua5.1.
    def harness(data):
        runtime = LuaRuntime()
        runtime.execute('''
            SEX_MALE=0; SEX_FEMALE=1; selectedSex=0;
            CharacterCreate={}; CharacterCreateFrame={};
            CHAR_CUSTOMIZATION1_DESC="Skin Color"; CHAR_CUSTOMIZATION2_DESC="Face";
            function GetSelectedSex() return selectedSex; end
            function CreateFrame(_, name, parent)
                local f={shown=false, parent=parent};
                function f:Show() self.shown=true; end
                function f:Hide() self.shown=false; end
                function f:IsShown() return self.shown; end
                function f:GetParent() return self.parent; end
                function f:ClearAllPoints() end
                function f:SetPoint(...) end
                function f:SetID(id) self.id=id; end
                function f:SetText(text) self.text=text; end
                _G[name]=f; return f;
            end
            CreateFrame("Button","CharCreateOkayButton");
            for i=1,29 do
                CreateFrame("Frame","CharacterCustomizationButtonFrame"..i,CharacterCreateFrame);
                CreateFrame("FontString","CharacterCustomizationButtonFrame"..i.."Text");
            end
            function CycleCharCustomization(_, id)
                return 0, id<=9 and 3 or 1, "Choice "..id;
            end
            function selectScreen(race, sex, personalize)
                CharacterCreate.selectedRaceID=race; selectedSex=sex;
                CharCreateOkayButton.shown=personalize;
                for i=1,5 do _G["CharacterCustomizationButtonFrame"..i].shown=personalize; end
            end
            function snapshot()
                local result={};
                for i=1,29 do
                    result[#result+1]=tostring(_G["CharacterCustomizationButtonFrame"..i].shown)
                        ..":"..tostring(_G["CharacterCustomizationButtonFrame"..i.."Text"].text);
                end
                return table.concat(result,"|");
            end
        ''')
        text = data.decode('utf-8-sig')
        start = text.index('-- Esteria native appearance controls:')
        end = text.index('function CharacterCustomization_Left(id)', start)
        refresh = runtime.execute(text[start:end] + '\nreturn EA_REFRESH;')
        return runtime, refresh

    before, old_refresh = harness(original)
    after, refresh = harness(changed)
    cases = 0
    for race in range(1, 71):
        for sex in (0, 1):
            # Includes repeated refresh, entering customization, Back, and race/gender changes.
            for personalize in (False, False, True, True, False):
                before.globals().selectScreen(race, sex, personalize)
                after.globals().selectScreen(race, sex, personalize)
                for _ in range(3):
                    old_refresh()
                    refresh()
                if race == 66 and sex == 0:
                    for index in (3, 4):
                        assert after.globals()[f'CharacterCustomizationButtonFrame{index}'].shown == personalize
                    assert after.globals().CharacterCustomizationButtonFrame3Text.text == 'Horns'
                    assert after.globals().CharacterCustomizationButtonFrame4Text.text == 'Eye Color'
                else:
                    assert before.globals().snapshot() == after.globals().snapshot(), (race, sex, personalize)
                cases += 1
    print('PASS: Lua5.1 compile; 700 screen/race/gender states with repeated refreshes', flush=True)


def stage():
    assert not (WORK / 'report.json').exists(), 'Use a new workspace for another revision'
    WORK.mkdir(parents=True, exist_ok=True)
    with t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        original, provider = files.find(KEY)
    changed = patch(original)
    validate(original, changed)
    (WORK / 'CharacterCreate.before.lua').write_bytes(original)
    (WORK / 'CharacterCreate.lua').write_bytes(changed)
    report = {'status': 'staged', 'entry': KEY, 'entry_sha256': t.sha(changed), 'provider': provider,
              'archives': {}, 'live_accepted': False}
    storm = t.p.Storm(t.p.DLL_DEFAULT)
    for relative in ARCHIVES:
        live = d.CLIENT / relative
        target = WORK / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = d.digest(live)
        shutil.copy2(live, target)
        assert d.digest(target) == before
        previous = inventory(storm, target)
        storm.replace_archive_entries(target, {KEY: changed})
        assert target.stat().st_size < 0x80000000
        current = inventory(storm, target)
        expected = dict(previous)
        expected[KEY.lower()] = t.sha(changed)
        assert current == expected, 'Unexpected archive content change'
        report['archives'][relative] = {'before': before, 'after': d.digest(target),
                                        'bytes': target.stat().st_size,
                                        'unchanged_entries': len(previous) - 1}
        print('STAGED; all other entries preserved:', relative, flush=True)
    d.save(WORK / 'report.json', report)


def install():
    d.closed_client()
    report = d.read(WORK / 'report.json')
    assert report['status'] == 'staged'
    backup = Path('C:/EsteriaBackups') / (
        'Drakkin-customization-visibility-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    assert not backup.exists()
    for relative, record in report['archives'].items():
        assert d.digest(d.CLIENT / relative) == record['before']
        assert d.digest(WORK / 'client' / relative) == record['after']
        assert shutil.disk_usage(d.CLIENT).free > record['bytes'] + 256 * 1024 * 1024
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(d.CLIENT / relative, target)
        assert d.digest(target) == record['before']
    d.save(backup / 'install-plan.json', report)
    (backup / 'ROLLBACK.txt').write_text(
        'Close WoW/editors before restoring the two backed-up archives. Their hashes are in install-plan.json.\n'
        'Do not restore over later client updates without rebasing those changes. No server/SQL changes.\n',
        encoding='utf-8', newline='\n')
    for relative, record in report['archives'].items():
        d.closed_client()
        assert d.digest(d.CLIENT / relative) == record['before']
        d.replace(WORK / 'client' / relative, d.CLIENT / relative, record['after'])
    with t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        assert t.sha(files.find(KEY)[0]) == report['entry_sha256']
    for relative, record in report['archives'].items():
        assert d.digest(d.CLIENT / relative) == record['after']
    report.update(status='installed_fresh_client_check_pending', backup=str(backup))
    d.save(WORK / 'report.json', report)
    print('INSTALLED AND VERIFIED; backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    globals()[parser.parse_args().action]()
