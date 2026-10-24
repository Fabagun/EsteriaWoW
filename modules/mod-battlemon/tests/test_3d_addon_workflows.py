"""Load the real 3D addon and exercise user actions through its real protocol callbacks."""
import importlib.util
from pathlib import Path
import sys

M = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(M/'generated/test-deps'))
from lupa.lua51 import LuaRuntime
spec = importlib.util.spec_from_file_location('smoke', M/'tools/smoke_ui.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute(smoke.PRELUDE)
lua.execute(r"""
SlashCmdList={}; StaticPopupDialogs={}; sent={}; errors={}; BattlemonDB={}
function GetTime() return 100 end
function UnitName() return 'Tester' end
function SendAddonMessage(prefix,payload) sent[#sent+1]=payload end
function hooksecurefunc(object, method, hook)
 local original=object[method]
 object[method]=function(...) original(...); hook(...) end
end
local mt=getmetatable(CreateFrame('Frame'))
function mt:GetAlpha() return self.alpha or 1 end
function mt:SetAlpha(a) self.alpha=a end
function mt:SetModel(path) self.path=path end
function mt:SetFacing(value) self.facing=value end
function receive(payload)
 for _,f in ipairs(BM_FRAMES) do
  if f.bmScripts.OnEvent then f.bmScripts.OnEvent(f,'CHAT_MSG_ADDON','BM',payload,'WHISPER','Tester') end
 end
end
function button(text)
 for _,f in ipairs(BM_FRAMES) do
  if f.bmKind=='Button' and f.text and f.text:GetText()==text then return f end
 end
 error('Missing button '..text)
end
function click(b)
 assert(b.bmEnabled~=false,'Disabled button')
 assert(b.bmScripts.OnClick,'Missing click handler')
 b.bmScripts.OnClick(b,'LeftButton')
end
""")
addon=M/'addon/Battlemon'
for line in (addon/'Battlemon.toc').read_text(encoding='utf-8').splitlines():
 if line.endswith('.lua'):
  lua.execute((addon/line.replace('\\','/')).read_text(encoding='utf-8-sig'))
lua.execute(r"""
Battlemon.Print=function(text) if string.find(text,'error',1,true) then errors[#errors+1]=text end end
Battlemon.LoadData()
Battlemon.EnsureProfileDB()
-- Every selectable form resolves species, front/back models and a non-internal name.
local count=0
for _,f in ipairs(Battlemon.FormsList) do
 assert(Battlemon.Species[f.species_id], 'Missing species '..f.id)
 assert(Battlemon.ModelForms[f.id], 'Missing models '..f.id)
 assert(Battlemon.Models[f.sprite], 'Missing sprite alias '..f.id)
 assert(not string.find(Battlemon.FormLabel(f),'pixelmon:',1,true))
 count=count+1
end
assert(count==2345)
-- Use a newly added form, normal and shiny, with owned IDs unrelated to the form IDs.
receive('OWNEDBEGIN')
receive('OWNED\t9001\t2065\t20\t0\tM\t40\tTHUNDERSHOCK\tGROWL\t\t\tRaichu\tBM3D_2065\t0\t0')
receive('OWNED\t9002\t2971\t20\t0\tN\t40\tTACKLE\t\t\t\tPecharunt\tBM3D_2971\t1\t0')
receive('OWNEDEND')
receive('PARTYSLOTS\t9001\t9002\t0\t0\t0\t0')
receive('POINTS\t100')
Battlemon.ShowParty()
click(button('SAVE PARTY'))
assert(sent[#sent]=='SETPARTY\t9001,9002,0,0,0,0')
Battlemon.teamDraft={name='New variants',party={9002,9001,0,0,0,0}}
assert(Battlemon.ApplyDraftToParty())
assert(sent[#sent]=='SETPARTY\t9002,9001,0,0,0,0')
-- Shop purchases send item IDs/quantities; refreshes use authoritative points and inventory.
Battlemon.ShowShop()
receive('SHOP\t0\tPOTION:10\tPOKEBALL:5')
receive('BAG\t0\tPOTION:2')
click(button('BUY')); assert(sent[#sent]=='BUY\tPOTION,1')
click(button('BUY x5')); assert(sent[#sent]=='BUY\tPOTION,5')
receive('POINTS\t5'); receive('BAG\t0\tPOTION:7')
assert(Battlemon.state.bag.POTION==7 and button('BUY').bmEnabled==false)
receive('BAG\t0'); assert(Battlemon.state.bag.POTION==nil)
-- Move edits use owned ID and a server-supplied pool, including tutor costs.
Battlemon.ShowMoves(9002); assert(sent[#sent]=='LEARNSET\t9002')
receive('LEARN\t9002\t10'); receive('LEARNADD\tTACKLE:L:1\tGROWL:T:0'); receive('LEARNEND')
click(button('SAVE MOVES')); assert(sent[#sent]=='SETMOVES\t9002,TACKLE,,,')
-- Selecting an unpaid tutor move blocks unaffordable saves, then sends it once affordable.
local tutor
for _,f in ipairs(BM_FRAMES) do if f.bmKind=='Button' and f.internal=='GROWL' then tutor=f end end
assert(tutor); click(tutor)
assert(button('SAVE MOVES').bmEnabled==false)
receive('POINTS\t10'); assert(button('SAVE MOVES').bmEnabled==true)
click(button('SAVE MOVES')); assert(sent[#sent]=='SETMOVES\t9002,GROWL,,,')
-- A late pool for another owned Pokemon must not enable this Pokemon's save.
receive('LEARN\t9001\t10'); receive('LEARNADD\tTACKLE:L:1'); receive('LEARNEND')
assert(button('SAVE MOVES').bmEnabled==false)
Battlemon.battleActive=true
local before=#sent
Battlemon.ShowMoves(9001); assert(#sent==before)
assert(not Battlemon.ApplyDraftToParty())
Battlemon.ShowParty(); assert(button('SAVE PARTY').bmEnabled==false)
Battlemon.battleActive=false
-- Snapshot pruning must keep supported new forms and remove vanished ownership references.
BattlemonDB.teamPresets={{name='Saved',party={9001,9002,9003,0,0,0}}}
BattlemonDB.favorites={9001,9002,9003}
receive('OWNEDBEGIN')
receive('OWNED\t9002\t2971\t20\t0\tN\t40\tTACKLE\t\t\t\tPecharunt\tBM3D_2971\t1\t0')
receive('OWNEDEND')
assert(BattlemonDB.teamPresets[1].party[1]==0 and BattlemonDB.teamPresets[1].party[2]==9002)
assert(#BattlemonDB.favorites==1 and BattlemonDB.favorites[1]==9002)
assert(#errors==0,table.concat(errors,'\n'))
""")
print('PASS: real addon/catalog load; all 2345 forms; new normal/shiny ownership; party/team commands; shop quantity, affordability and bag refresh; move save; removed ownership cleanup.')

import json
catalog=json.loads((M/'data/3d/catalog.json').read_text(encoding='utf-8'))
for row in catalog['form_moves']:
 assert lua.eval('Battlemon.MovesByInternal')[row['move_internal_name']] is not None, row
 assert lua.eval('Battlemon.Forms')[row['form_id']] is not None, row
print('PASS: tutor affordability, stale learnset rejection, battle edit locks and all '+str(len(catalog['form_moves']))+' added form-move references.')
