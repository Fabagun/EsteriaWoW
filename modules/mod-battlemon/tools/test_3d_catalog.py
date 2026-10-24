"""Catalog integrity and actual Lua 5.1 preview/ownership lifecycle checks. No core build."""
import sys,json,importlib.util,re
from pathlib import Path
MOD=Path(__file__).resolve().parents[1];REPO=MOD.parents[1];ADDON=MOD/'addon/Battlemon'
sys.path.insert(0,str(REPO/'modules/mod-battlemon/generated/test-deps'))
from lupa.lua51 import LuaRuntime
from luaparser import ast
spec=importlib.util.spec_from_file_location('smoke',MOD/'tools/smoke_ui.py');smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)
d=json.loads((MOD/'data/3d/catalog.json').read_text());pairs={(x['form'],x['shiny']) for x in d['appearances']};displays=[x['display'] for x in d['appearances']]
assert len(pairs)==3965 and len(set(displays))==3965
assert set(d['extra_displays'])<=set(displays) and len(d['extra_displays'])==980
assert all((x['form'],x['shiny']) not in pairs for x in d['unsupported_owned'])
assert len(d['unsupported_owned'])==161 and len(d['rescued'])==16
assert all((x['form'],x['shiny']) in pairs for x in d['rescued'])
for p in ADDON.rglob('*.lua'):ast.parse(p.read_text(encoding='utf-8-sig'))
lua=LuaRuntime(unpack_returned_tuples=True);lua.execute(smoke.PRELUDE)
lua.execute('''
function hooksecurefunc(object, method, hook)
 local original=object[method]
 object[method]=function(...) original(...);hook(...) end
end
local f=CreateFrame('Frame')
local mt=getmetatable(f)
function mt:GetAlpha() return self.alpha or 1 end
function mt:SetAlpha(a) self.alpha=a end
function mt:SetModel(path) self.path=path end
function mt:SetFacing(value) self.facing=value end
Battlemon={}
''')
for line in (ADDON/'Battlemon.toc').read_text().splitlines():
 if line.startswith('Data\\') or line in ['Core\\CSV.lua','Core\\Data.lua','Core\\Sprites.lua','Core\\Profile.lua']:
  p=ADDON/line.replace('\\','/');assert p.is_file(),line;lua.execute(p.read_text(encoding='utf-8-sig'))
lua.execute('Battlemon.LoadData()')
assert lua.eval('#Battlemon.FormsList')==2345
for x in d['appearances']:
 assert lua.eval(f'Battlemon.ModelForms[{x["form"]}][{x["shiny"]}]')==x['path'].replace('/','\\')
# Old shared back-sprite tokens must never override a different front/form model.
assert lua.eval('Battlemon.Models["0025_Pikachu"][0]')=='Creature\\Battlemon\\0025_Pikachu.m2'
lua.execute('''
local parent=CreateFrame('Frame');local tex=parent:CreateTexture();tex:Show()
assert(Battlemon.SetPokemonTexture(tex,'Front','0025_Pikachu',false))
local model=tex.battlemonModel
assert(model:IsShown())
tex:Hide();assert(not model:IsShown());tex:Show();assert(model:IsShown())
tex:SetAlpha(0.4);assert(model:GetAlpha()==0.4)
assert(not Battlemon.SetPokemonTexture(tex,'Front','no-such-model',false))
tex:Show();assert(not model:IsShown())
assert(Battlemon.SetPokemonTexture(tex,'Back','0025_Pikachu',false))
assert(model:IsShown() and model.facing==math.pi)
Battlemon.state={owned={[12]={id=12}},partySlots={12,0,0,0,0,0}}
BattlemonDB={teamPresets={{name='Saved team',party={11,12,13,0,0,0}}},favorites={11,12,13}}
Battlemon.PruneRemovedOwned()
assert(BattlemonDB.teamPresets[1].party[1]==0 and BattlemonDB.teamPresets[1].party[2]==12)
assert(#BattlemonDB.favorites==1 and BattlemonDB.favorites[1]==12)
''')
# Player-facing labels must not expose source keys or corrupt encoded text.
for form in lua.eval('Battlemon.FormsList').values():
 label=lua.eval('Battlemon.FormLabel')(form)
 assert 'pixelmon:' not in label and ':always' not in label, label
 assert not any(bad in label for bad in ['\u00c3', '\u00c2']), label
assert lua.eval('Battlemon.FormLabel(Battlemon.DefaultForm[29])') == 'Nidoran (Female)'
assert lua.eval('Battlemon.FormLabel(Battlemon.DefaultForm[32])') == 'Nidoran (Male)'
assert lua.eval('Battlemon.FormLabel(Battlemon.Forms[2065])') == 'Raichu (Christmas)'
assert lua.eval('Battlemon.FormLabel(Battlemon.Forms[2064])') == 'Raichu (Alolan, Summer)'
assert lua.eval('Battlemon.FormLabel(Battlemon.Forms[2970])') == 'Pecharunt (Closed Shell)'
assert lua.eval('Battlemon.FormLabel(Battlemon.Forms[2971])') == 'Pecharunt (Open Shell)'
dex=(ADDON/'UI/DexFrame.lua').read_text(encoding='utf-8')
assert not any(bad in dex for bad in ['\u00c3','\u00c2'])
lua.execute("""
local parent=CreateFrame('Frame');local tex=parent:CreateTexture();tex:Show()
Battlemon.SetPokemonTexture(tex,'Front','1025_Pecharunt',false)
local model=tex.battlemonModel
model.SetPosition=function(self,x,y,z) self.previewZ=z end
tex.battlemonPreviewZ=0.35
Battlemon.SetPokemonTexture(tex,'Front','1025_Pecharunt',false)
assert(model.previewZ==0.35)
tex.battlemonPreviewZ=0
Battlemon.SetPokemonTexture(tex,'Front','1025_Pecharunt',false)
assert(model.previewZ==0)
Battlemon.SetPokemonTexture(tex,'Front','0025_Pikachu',false)
assert(model.previewZ==0)
""")
print('PASS: readable form labels, no Pokedex mojibake, and preview offset reset on reused models.')
print('PASS: 3965 exact appearance pairs, all 980 extras, 16 rescued variants, 161 exact removal pairs, 2345 forms; Lua 5.1 catalog loading, model visibility/reuse/facing, alias identity and stale saved-team cleanup.')

# Exercise the actual changed panel, not the older all-panel harness stubs.
for rel in ['Core/Util.lua', 'Core/UI.lua', 'UI/DexFrame.lua']:
 lua.execute((ADDON/rel).read_text(encoding='utf-8'))
lua.execute('Battlemon.state.dexOwned={}; Battlemon.state.dexShiny={}; local f=Battlemon.BuildDex(); f:Show(); Battlemon.RefreshDex()')
print('PASS: real Pokedex panel build and refresh with the loaded catalog.')
