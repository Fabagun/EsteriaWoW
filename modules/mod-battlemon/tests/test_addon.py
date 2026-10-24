"""Execute the actual companion addon and base Net.lua in Lua 5.1 API mocks."""
import sys,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'generated/test-deps'))
from lupa.lua51 import LuaRuntime
from luaparser import ast
spec=importlib.util.spec_from_file_location('smoke',ROOT/'tools/smoke_ui.py')
smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)
spec=importlib.util.spec_from_file_location('installer',ROOT/'tools/install_addon.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
CLIENT=Path(sys.argv[1])
net=(CLIENT/'Core/Net.lua').read_text(encoding='utf-8')
if installer.NEW not in net:net=net.replace(installer.OLD,installer.NEW)
addon=(ROOT/'addon/BattlemonBattles/BattlemonBattles.lua').read_text(encoding='utf-8')
ast.parse(net);ast.parse(addon)
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute(smoke.PRELUDE)
lua.execute(r"""
StaticPopupDialogs={};SlashCmdList={};sent={};after={};clock=100
function BM_FIND(caption)
 for i=#BM_FRAMES,1,-1 do
  local f=BM_FRAMES[i]
  if f.bmKind=='Button' and f:GetText()==caption then return f end
 end
end
MainMenuBar=CreateFrame('Frame');MainMenuBar:Show()
MultiBarBottomLeft=CreateFrame('Frame');MultiBarBottomLeft:Hide()
MultiBarBottomRight=CreateFrame('Frame');MultiBarBottomRight:Show()
function GetTime() return clock end
function UnitName() return 'Tester' end
function SendAddonMessage(prefix,message) sent[#sent+1]={prefix,message} end
function EasyMenu(menu) lastMenu=menu end
function StaticPopup_Show(id) popup=id end
Battlemon={state={bag={POKEBALL=3,POTION=2},balls=3},battle={},MovesByInternal={},ItemsById={}}
function Battlemon.Print(text) lastPrint=text end
function Battlemon.Copy(t) local c={} for k,v in pairs(t) do c[k]=v end return c end
function Battlemon.After(delay,fn) after[#after+1]=fn end
Battlemon.BattleMusic={Start=function() end,Stop=function() end}
function Battlemon.ShowParty() partyOpened=true end
function Battlemon.ShowShop() shopOpened=true end
function Battlemon.HideMain() assert(not Battlemon.ForfeitBattle(),'Hiding old panel forfeited battle') end
function Battlemon.StartWildBattle() Battlemon.Send('WILD') end
function fire(event,...)
 for _,f in ipairs(BM_FRAMES) do
  local handler=f.bmScripts.OnEvent
  if handler then handler(f,event,...) end
 end
end
classic=0
""")
lua.execute(net)
lua.execute("Battlemon.OnNet('WILD',function() classic=classic+1 end)")
lua.execute(addon)
result=lua.execute(r"""
local PB=BattlemonBattles
PB.Open()
fire('CHAT_MSG_ADDON','BMB','MODE\tpet\t1\t1','WHISPER','SomeoneElse')
assert(PB.mode==nil,'spoofed messages accepted')
fire('CHAT_MSG_ADDON','BMB','MODE\tpet\t1\t1','WHISPER','Tester')
assert(PB.mode=='pet')
fire('CHAT_MSG_ADDON','BM','MSG\tNot ready yet','WHISPER','Tester')
assert(lastPrint=='Not ready yet','Wild start error was hidden')
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
assert(PB.state.active and PB.state.kind=='WILD' and classic==0)
assert(not MainMenuBar:IsShown() and not MultiBarBottomLeft:IsShown())
local player='P\t1\t37\t25\tPikachu\t8\t1\tM\t40\t50\t0025_Pikachu\t0025_Pikachu\t1\t0\tTACKLE\tTackle\t12\t35'
local enemy='E\t0\t1\t1\tBulbasaur\t8\t1\tM\t35\t45\t0001_Bulbasaur\t0001_Bulbasaur\t1\t0\tTACKLE\tTackle\t12\t35'
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM',enemy,'WHISPER','Tester')
assert(not PB.ui.party:IsShown(), 'party selector should start closed')
assert(not PB.ui.struggle:IsShown(), 'Struggle should be hidden while PP remains')
PB.ui.change:Click(); assert(PB.ui.party:IsShown(), 'Change Pokemon must open party selector')
fire('CHAT_MSG_ADDON','BM','BPARTY\t1\t1\t40\t50\t8\t0\t1\tPikachu','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','BPARTY\t3\t9\t27\t27\t3\t0\t0\tVenusaur','WHISPER','Tester')
assert(PB.ui.team[3].bmEnabled, 'healthy wild bench slot must be enabled')
local enables=0
local originalEnable=PB.ui.team[3].Enable
PB.ui.team[3].Enable=function(self) enables=enables+1; originalEnable(self) end
PB.Refresh(); PB.Refresh()
assert(enables==0, 'render refresh must not reset a pressed, already-enabled party button')
PB.ui.team[3]:Click()
assert(sent[#sent][1]=='BM' and sent[#sent][2]=='SWITCH\t3', 'wild switching lost its server slot')
assert(not PB.ui.party:IsShown(), 'selection must close party drawer')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
PB.ui.items:Click(); assert(PB.ui.choices:IsShown(), 'bag must open right drawer')
PB.ui.choices.rows[1]:Click(); assert(sent[#sent][2]=='USEITEM\tPOTION')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
PB.state.player.moves[1].pp=0; PB.Refresh()
assert(PB.ui.struggle:IsShown(), 'all moves exhausted should reveal fallback')
PB.ui.struggle:Click(); assert(sent[#sent][2]=='MOVE\t1', 'wild fallback must use server-validated move path')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
assert(not PB.ui.struggle:IsShown(), 'refreshed PP should hide fallback')
PB.ui.moves[1]:Click()
assert(sent[#sent][1]=='BM' and sent[#sent][2]=='MOVE\t1','wild moves must use existing engine')
fire('CHAT_MSG_ADDON','BM','CATCH\t1\t3\t3','WHISPER','Tester')
assert(PB.state.catch and PB.ui.capture == nil)
assert(PB.ui.choices:IsShown() and #PB.ui.choices.entries==2, 'capture choices must open automatically')
assert(not PB.ui.choices.close:IsShown(), 'capture is resolved by a ball or skip, not closing')
PB.ui.choices.rows[1]:Click();assert(sent[#sent][2]=='BALL\tPOKEBALL')
assert(not PB.ui.choices:IsShown(), 'ball drawer should close after selection')
fire('CHAT_MSG_ADDON','BM','END\tWIN','WHISPER','Tester')
assert(not PB.state.active and MainMenuBar:IsShown() and not MultiBarBottomLeft:IsShown())
PB.classicCheckbox:SetChecked(true);PB.classicCheckbox:Click()
assert(sent[#sent][2]=='MODE\tclassic','checkbox did not request classic wild UI')
assert(not PB.classicCheckbox:GetChecked(),'preference changed before server acknowledgement')
PB.Receive('MODE\tclassic\t1\t1')
assert(PB.classicCheckbox:GetChecked(),'acknowledged classic choice not checked')
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
assert(classic==1,'classic mode must still route original handler')
PB.Receive('START\tDUEL\tPlayerbot')
assert(PB.state.active and PB.state.kind=='DUEL' and PB.mode=='classic' and PB.ui.root:IsShown(), 'classic wild preference blocked automatic duel UI')
PB.Receive(player);PB.Receive(enemy)
PB.Receive('TEAM\t1\tPikachu\t8\t40\t50\t1')
PB.Receive('TEAM\t2\tCharmander\t8\t30\t40\t0')
PB.Receive('TURN\t17\tCHOOSE\t45')
PB.ui.moves[1]:Click()
assert(sent[#sent][1]=='BMB' and sent[#sent][2]=='ACTION\t17\tMOVE\t1')
local count=#sent;PB.ui.moves[1]:Click();assert(#sent==count,'duplicate action not blocked')
PB.Receive('WAIT');PB.ui.team[2]:Click();assert(#sent==count,'waiting side submitted')
PB.Receive('TURN\t18\tSWITCH\t45');PB.ui.team[2]:Click()
assert(sent[#sent][2]=='ACTION\t18\tSWITCH\t2')
PB.Receive('ERROR\tCannot switch');PB.Receive('TURN\t19\tCHOOSE\t45')
PB.ui.leave:Click();assert(popup=='BATTLEMON_BATTLES_FORFEIT')
StaticPopupDialogs[popup].OnAccept();assert(sent[#sent][2]=='FORFEIT')
PB.Receive('END\tLOSE');assert(not PB.state.active and MainMenuBar:IsShown())
PB.Receive('INVITE\tOtherPlayer');BM_FIND('Accept'):Click();assert(sent[#sent][2]=='ACCEPT')
PB.Receive('INVITE\tOtherPlayer');BM_FIND('Decline'):Click();assert(sent[#sent][2]=='DECLINE')
PB.classicCheckbox:SetChecked(false);PB.classicCheckbox:Click()
assert(sent[#sent][2]=='MODE\tpet','unchecking did not request new wild UI')
PB.Receive('MODE\tpet\t0\t1')
assert(not PB.classicCheckbox:GetChecked() and not PB.classicCheckbox.bmEnabled, 'realm policy not reflected')
PB.Receive('MODE\tpet\t1\t1')
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
fire('PLAYER_REGEN_DISABLED');assert(sent[#sent][2]=='FORFEIT' and MainMenuBar:IsShown())
PB.Receive('END\tRUN')
BattlemonBattlesDB.mode='classic';after={};fire('PLAYER_LOGIN')
after[#after-1]();PB.Receive('MODE\tpet\t1\t1');after[#after]()
assert(sent[#sent][2]=='MODE\tclassic','HELLO overwrote saved preference')

-- Supplied type artwork follows the move, including refreshed/empty slots.
PB.Receive('START\tDUEL\tPlayerbot'); PB.Receive(player); PB.Receive(enemy)
for kind in string.gmatch('NORMAL FIGHTING FLYING POISON GROUND ROCK BUG GHOST STEEL FIRE WATER GRASS ELECTRIC PSYCHIC ICE DRAGON DARK FAIRY', '%S+') do
 PB.state.player.moves[1].data.type=kind; PB.Refresh()
 assert(PB.ui.moves[1].pbSkin==kind, 'Wrong artwork for '..kind)
end
PB.state.player.moves[1].data.type='UNRECOGNIZED'; PB.Refresh()
assert(PB.ui.moves[1].pbSkin=='UNKNOWN')
PB.Receive('END\tRUN')
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
Battlemon.state.bag={POKEBALL=3,GREATBALL=2,ULTRABALL=1,MASTERBALL=1}
fire('CHAT_MSG_ADDON','BM','CATCH\t1\t3\t3','WHISPER','Tester')
assert(#PB.ui.choices.entries==5 and PB.ui.choices.pageSize==5)
for i,kind in ipairs({'POKEBALL','GREATBALL','ULTRABALL','MASTERBALL'}) do
 assert(PB.ui.choices.rows[i].entry.icon==kind, 'Ball icon does not match item')
end
PB.ui.choices.rows[4]:Click(); assert(sent[#sent][2]=='BALL\tMASTERBALL')
PB.Receive('END\tWIN')
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
Battlemon.state.bag={POTION=1,ITEMA=1,ITEMB=1,ITEMC=1,ITEMD=1,ITEME=1}
PB.ui.items:Click()
assert(PB.ui.choices.pageSize==4 and not PB.ui.choices.rows[5]:IsShown())
assert(not PB.ui.choices.rows[1].icon:IsShown(), 'Stale ball icon in bag')
PB.ui.choices.next:Click()
assert(PB.ui.choices.page==2 and PB.ui.choices.rows[2].entry.text=='POTION x1')
PB.ui.choices.rows[2]:Click(); assert(sent[#sent][2]=='USEITEM\tPOTION')
PB.Receive('END\tRUN')

-- Ordinary result packets and the network watchdog must not unlock a playing turn.
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM',enemy,'WHISPER','Tester')
PB.ui.moves[1]:Click()
PB.Receive('PLAYBACK\t1')
local sentBefore=#sent
fire('CHAT_MSG_ADDON','BM','MSG\tPikachu used Tackle!','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM',player,'WHISPER','Tester')
clock=clock+20
PB.ui.root.bmScripts.OnUpdate()
PB.ui.moves[1]:Click(); PB.ui.items:Click()
assert(#sent==sentBefore, 'Animation barrier was bypassed by a packet or watchdog')
assert(not PB.ui.moves[1].bmEnabled and not PB.ui.choices:IsShown())
fire('CHAT_MSG_ADDON','BM','CATCH\t1\t3\t3','WHISPER','Tester')
assert(not PB.ui.choices:IsShown(), 'Capture menu opened before the finishing attack')
PB.Receive('PLAYBACK\t0')
assert(PB.ui.choices:IsShown(), 'Capture menu did not open when playback finished')
fire('CHAT_MSG_ADDON','BM','END\tWIN','WHISPER','Tester')
assert(not PB.ui.root:IsShown(), 'Battle HUD lingered after the final result')
PB.Receive('START\tDUEL\tPlayerbot'); PB.Receive(player); PB.Receive(enemy)
PB.Receive('PLAYBACK\t1'); PB.Receive('TURN\t99\tCHOOSE\t45')
sentBefore=#sent; PB.ui.moves[1]:Click()
assert(#sent==sentBefore, 'Duel TURN bypassed animation playback')
PB.Receive('PLAYBACK\t0'); PB.ui.moves[1]:Click()
assert(sent[#sent][2]=='ACTION\t99\tMOVE\t1')
PB.Receive('END\tLOSE')
assert(not PB.ui.root:IsShown(), 'Duel HUD lingered after the final result')
-- Center services open the existing full-featured panels only on authenticated packets.
shopOpened=false; partyOpened=false
fire('CHAT_MSG_ADDON','BM','CENTER\tSHOP','WHISPER','SomeoneElse')
assert(not shopOpened)
fire('CHAT_MSG_ADDON','BM','CENTER\tSHOP','WHISPER','Tester')
assert(shopOpened)
fire('CHAT_MSG_ADDON','BM','CENTER\tPARTY','WHISPER','Tester')
assert(partyOpened)
-- Capture result survives immediate battle dismissal, but expires and resets.
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','CATCH\t1\t1\t3','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','MSG\tOh no! The wild Pikachu broke free!','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','MSG\tIt got away!','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','END\tWIN','WHISPER','Tester')
assert(not PB.ui.root:IsShown() and PB.captureBanner:IsShown())
assert(PB.captureBanner.label:GetText()=='Pikachu broke free!')
clock=clock+5; PB.captureBanner.bmScripts.OnUpdate(PB.captureBanner)
assert(PB.captureBanner:IsShown())
clock=clock+2; PB.captureBanner.bmScripts.OnUpdate(PB.captureBanner)
assert(not PB.captureBanner:IsShown())
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','MSG\tGotcha! SHINY Pikachu was caught!','WHISPER','Tester')
fire('CHAT_MSG_ADDON','BM','END\tWIN','WHISPER','Tester')
assert(PB.captureBanner:IsShown() and PB.captureBanner.label:GetText()=='SHINY Pikachu was captured!')
fire('CHAT_MSG_ADDON','BM','WILD','WHISPER','Tester')
assert(not PB.captureBanner:IsShown())
PB.Receive('END\tRUN')
return 'PASS: Lua5.1 loading, actual Net.lua routing, spoof rejection, classic preservation, wild moves/catch, duel actions/revisions, duplicate suppression, forced switching, invitations, forfeit, UI restoration'
""")
print(result)
