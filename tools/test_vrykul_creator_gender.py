"""Exercise the real creator race/female-click handlers in Lua 5.1."""

from lupa.lua51 import LuaRuntime, LuaError
import vrykul_female_pack as v


def check(text):
    lua = LuaRuntime()
    lua.execute('''
SEX_MALE=2; SEX_FEMALE=3; MALE="Male"; FEMALE="Female"; sex=SEX_MALE; selected=1;
CharacterCreate={selectedRaceID=56,selectedRace=1}; strupper=string.upper;
RACE_ICON_TEXTURES={}; RACE_ICON_TCOORDS={HUMAN_MALE={0,1,0,1},HUMAN_FEMALE={0,1,0,1}};
local function widget()
    local w={shown=true};
    function w:Show() self.shown=true; end
    function w:Hide() self.shown=false; end
    function w:SetChecked(value) self.checked=value; end
    function w:GetChecked() return self.checked; end
    function w:SetText(value) self.text=value; end
    function w:SetTexture() end
    function w:SetTexCoord() end
    return w;
end
CharacterCreateGender=widget(); CharacterCreateGenderButtonMale=widget();
CharacterCreateGenderButtonFemale=widget(); CharacterCreateRaceLabel=widget(); CharacterCreateRaceIcon=widget();
function GetSelectedSex() return sex; end
function SetSelectedSex(value) sex=value; end
function GetSelectedRace() return selected; end
function SetSelectedRace(value) selected=value; end
function SetCharacterRace(slot) CharacterCreate.selectedRaceID=_G["CharacterCreateRaceButton"..slot].raceID; end
function GetSelectedClass() return "Hero","Hero",1; end
function GetAvailableRaces() end
function GetAvailableClasses() end
function GetNameForRace() return "Vrykul","Vrykul"; end
function GetFactionForRace() return "Alliance","Alliance"; end
function GetRaceIconTextureKey(_,gender) return "HUMAN_"..gender; end
for _,name in ipairs({"PlaySound","CharacterCreateEnumerateRaces","CharacterCreateEnumerateClasses",
    "CharacterCreate_UpdateHairCustomization","CharacterChangeFixup","CharacterCreate_UpdateButtonCheckedStates",
    "SetCharacterClass","SetCharacterCreateFacing"}) do _G[name]=function() end; end
CharacterCreateRaceButton1=widget(); CharacterCreateRaceButton1:SetChecked(1);
''')
    start = text.index('function CharacterCreate_IsMaleOnlyRace(')
    lua.execute(text[start:text.index('\nend', start)+4])
    start = text.index('function CharacterRace_OnClick(')
    lua.execute(text[start:text.index('function CharacterCreate_ResetState()', start)])
    start = text.index('-- Only Naga has an authored second playable body type')
    lua.execute(text[start:text.index('-- Esteria Vrykul preview sizing.', start)])
    for race in (1, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63):
        lua.globals().race_under_test = race
        lua.execute('''
CharacterCreateRaceButton1.raceID=race_under_test;
CharacterCreate.selectedRaceID=race_under_test;
sex=SEX_MALE;
SetCharacterGender(SEX_FEMALE);
local maleOnly=race_under_test==55 or race_under_test==58 or race_under_test==59 or race_under_test==63;
assert(sex==(maleOnly and SEX_MALE or SEX_FEMALE),"female-click race "..race_under_test);
assert(not maleOnly or not CharacterCreateGenderButtonFemale.shown);
assert(maleOnly or CharacterCreateGenderButtonFemale.checked==1);
assert(maleOnly or CharacterCreateGenderButtonFemale.shown);
-- Choosing the race while female must retain that choice for races with two bodies.
sex=SEX_FEMALE; selected=0;
CharacterRace_OnClick(CharacterCreateRaceButton1,1);
assert(sex==(maleOnly and SEX_MALE or SEX_FEMALE),"race-click race "..race_under_test);
''')
    assert v.patch_creator_gender(text) == text
    print('Lua 5.1: Vrykul female clicks/race changes retained; single-body race restrictions preserved')


if __name__ == '__main__':
    live = (v.STAGE/'live-CharacterCreate.lua').read_text(encoding='utf-8')
    patched = v.patch_creator_gender(live)
    if live != patched:
        start = patched.index('function CharacterCreate_IsMaleOnlyRace(')
        helper = patched[start:patched.index('\nend', start)+4]
        try:
            check(live+'\n'+helper)
        except LuaError as error:
            assert 'female-click race 56' in str(error)
            print('Reproduced the installed Lua forcing female Vrykul back to male')
        else:
            raise AssertionError('The original click handler should reproduce the reported failure')
    check(patched)
