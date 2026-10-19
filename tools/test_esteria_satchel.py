"""Lua 5.1 regression harness for the satchel, using the extracted native FrameXML.

Run: rtk proxy python tools/test_esteria_satchel.py
Requires lupa.lua51 and .agents/plans/esteria-satchel/ContainerFrame.lua/xml.
Mocks rendering and native C APIs; it does not prove client/server protocol or combat
security. Native Lua bag generation, opening, item handlers, and XML scripts execute.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / ".agents/plans/esteria-satchel"
ADDON = ROOT / "client-customization/EsteriaSatchel/EsteriaSatchel.lua"

MOCK = r'''
unpack=unpack; tinsert=table.insert; ceil=math.ceil; mod=math.fmod
NUM_BAG_SLOTS=4; NUM_BANKBAGSLOTS=7; KEYRING_CONTAINER=-2; BANK_CONTAINER=-1
UISpecialFrames={}; SlashCmdList={}; DEFAULT_CHAT_FRAME={AddMessage=function() end}
bags={[0]=16,[1]=237,[2]=20,[3]=0,[4]=0,[5]=237}
contents={}; calls={}; modified=nil; now=0; nativeTemplates={}
local function record(action,bag,slot,value)
    calls[#calls+1]={action,bag,slot,value}
end
function lastcall(action)
    for i=#calls,1,-1 do if calls[i][1]==action then return unpack(calls[i]) end end
end
function expectcall(action,bag,slot)
    local a,b,s=lastcall(action)
    assert(a==action and b==bag and s==slot,
        action..' expected '..bag..':'..slot..', got '..tostring(b)..':'..tostring(s))
end
local methods={}
local function noop() end
for _,name in ipairs({'SetFrameStrata','SetToplevel','SetMovable','EnableMouse',
    'SetClampedToScreen','RegisterForDrag','RegisterForClicks','Raise','StartMoving',
    'StopMovingOrSizing','SetBlendMode','SetDrawLayer','LockHighlight','UnlockHighlight',
    'SetAlpha','SetHitRectInsets','SetPushedTexture','SetNormalTexture','SetChecked'}) do
    methods[name]=noop
end
function methods:GetName() return self.name end
function methods:GetID() return self.id or 0 end
function methods:SetID(id) self.id=id end
function methods:GetParent() return self.parent end
function methods:SetParent(p) self.parent=p end
function methods:SetWidth(w) self.width=w end
function methods:SetHeight(h) self.height=h end
function methods:SetSize(w,h) self.width=w; self.height=h end
function methods:GetWidth() return self.width or 37 end
function methods:GetHeight() return self.height or 37 end
function methods:GetRight() return 500 end
function methods:SetScale(s) self.scale=s end
function methods:GetScale() return self.scale or 1 end
function methods:SetPoint(...) self.point={...} end
function methods:GetPoint() return unpack(self.point) end
function methods:ClearAllPoints() self.point=nil end
function methods:SetAllPoints(f) self.allPoints=f or self.parent end
function methods:SetTexture(t) self.texture=t end
function methods:SetTexCoord(...) self.texcoord={...} end
function methods:SetText(t) self.text=t end
function methods:SetVertexColor(r,g,b,a)
    assert(a==nil or type(a)=='number', 'vertex alpha must be numeric')
    self.vertex={r,g,b,a}
end
function methods:SetScript(e,f) self.scripts[e]=f end
function methods:GetScript(e) return self.scripts[e] end
function methods:RegisterEvent(e) self.events[e]=true end
function methods:UnregisterEvent(e) self.events[e]=nil end
function methods:UnregisterAllEvents() self.events={} end
function methods:IsShown() return self.shown end
function methods:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
function methods:Show()
    if self.shown then return end
    self.shown=true
    if self.scripts.OnShow then self.scripts.OnShow(self) end
end
function methods:Hide()
    if not self.shown then return end
    self.shown=false
    if self.scripts.OnHide then self.scripts.OnHide(self) end
end
function methods:CreateTexture(name,layer)
    local t=CreateFrame('Texture',name,self); t.layer=layer; return t
end
function methods:CreateFontString(name,layer,template)
    return CreateFrame('FontString',name,self)
end
function CreateFrame(kind,name,parent,template)
    assert(not name or not _G[name], 'Duplicate frame '..tostring(name))
    local f=setmetatable({name=name,parent=parent,kind=kind,scripts={},events={},shown=true},
        {__index=methods})
    if name then _G[name]=f end
    if template=='ContainerFrameItemButtonTemplate' then
        assert(name,'Native item texture names need a named button')
        for _,suffix in ipairs({'IconTexture','IconQuestTexture','Count','Cooldown'}) do
            CreateFrame('Texture',name..suffix,f)
        end
        f.shown=false
        for event,script in pairs(nativeTemplates) do f:SetScript(event,script) end
        if f.scripts.OnLoad then f.scripts.OnLoad(f) end
    end
    return f
end
UIParent=CreateFrame('Frame','UIParent'); UIParent:SetSize(1920,1080)
BankFrame=CreateFrame('Frame','BankFrame'); BankFrame:Hide()
MerchantFrame=CreateFrame('Frame','MerchantFrame'); MerchantFrame:Hide(); MerchantFrame.selectedTab=1
StackSplitFrame=CreateFrame('Frame','StackSplitFrame'); StackSplitFrame:Hide()
GameTooltip=CreateFrame('Frame','GameTooltip')
function GameTooltip:SetOwner(owner,anchor) self.owner=owner end
function GameTooltip:GetOwner() return self.owner end
function GameTooltip:IsOwned(owner) return self.owner==owner end
function GameTooltip:SetBagItem(bag,slot) record('tooltip',bag,slot); return false,0 end
function GetScreenWidth() return UIParent:GetWidth() end
function GetScreenHeight() return UIParent:GetHeight() end
function CanOpenPanels() return true end
function IsOptionFrameOpen() return false end
function UnitIsDead() return false end
function GetContainerNumSlots(bag) return bags[bag] or 0 end
function GetContainerSlotCapacity() return 254 end
function GetContainerNumFreeSlots(bag) return GetContainerNumSlots(bag)-1,0 end
function GetBagName(bag) return 'Test Bag '..bag end
function GetContainerItemInfo(bag,slot)
    assert(slot>=1 and slot<=GetContainerNumSlots(bag),'Invalid one-based item query')
    local value=contents[bag..':'..slot]
    if value then return value.texture,value.count,value.locked,value.quality,value.readable,false,value.link end
    return nil,0,false,0,false,false,nil
end
function GetContainerItemLink(bag,slot) return select(7,GetContainerItemInfo(bag,slot)) end
function GetContainerItemCooldown(bag,slot) return 0,0,1 end
function GetContainerItemQuestInfo(bag,slot) return false,nil,false end
function SetBagPortraitTexture(t,bag) t.bag=bag end
function SetItemButtonTexture(b,t) b.texture=t end
function SetItemButtonCount(b,c) b.count=c end
function SetItemButtonDesaturated(b,locked) b.locked=locked end
function SetItemButtonTextureVertexColor(b,...) b.tint={...} end
function CooldownFrame_SetTimer(b,start,duration,enabled) b.timer={start,duration,enabled} end
function GetItemQualityColor() return 0.1,1,0.1,'ff19ff19' end
function PlaySound() end
function UpdateBagButtonHighlight() end
function UpdateMicroButtons() end
function PickupContainerItem(bag,slot) record('pickup',bag,slot) end
function UseContainerItem(bag,slot) record('use',bag,slot) end
function SplitContainerItem(bag,slot,count) record('split',bag,slot,count) end
function SocketContainerItem(bag,slot) record('socket',bag,slot) end
function OpenStackSplitFrame(count,owner)
    StackSplitFrame.owner=owner; owner.hasStackSplit=1; StackSplitFrame:Show()
end
function IsModifiedClick(kind) return modified and (not kind or modified==kind) end
function HandleModifiedItemClick(link)
    if modified=='CHATLINK' then record('link',nil,nil,link); return true end
end
function MerchantFrame_ResetRefundItem() end
function MerchantFrame_SetRefundItem() end
function SpellCanTargetItem() return false end
function GetCursorInfo() return nil end
function CursorHasItem() return false end
function InRepairMode() return false end
function ResetCursor() end
function ShowInspectCursor() end
function fire(event,...)
    local f=EsteriaSatchel.driver
    assert(f.events[event], 'Event not registered '..event)
    f.scripts.OnEvent(f,event,...)
end
function tick(delta) EsteriaSatchel.driver.scripts.OnUpdate(EsteriaSatchel.driver,delta or 0.01) end
function createStock()
    MainMenuBarBackpackButton=CreateFrame('Button','MainMenuBarBackpackButton')
    for i=0,3 do local b=CreateFrame('Button','CharacterBag'..i..'Slot'); b:SetID(20+i) end
    for i=1,13 do
        local name='ContainerFrame'..i
        local f=CreateFrame('Frame',name,UIParent); f:Hide()
        f:SetScript('OnShow',ContainerFrame_OnShow); f:SetScript('OnHide',ContainerFrame_OnHide)
        for _,suffix in ipairs({'BackgroundTop','BackgroundMiddle1','BackgroundMiddle2',
            'BackgroundBottom','Background1Slot','MoneyFrame','Name','Portrait','PortraitButton'}) do
            CreateFrame('Texture',name..suffix,f)
        end
        for slot=1,36 do CreateFrame('Button',name..'Item'..slot,f,'ContainerFrameItemButtonTemplate') end
        ContainerFrame_OnLoad(f)
    end
end
'''

DRAGON = r'''
DragonUI={}; local m={frames={},BagsterModule={applied=true},ItemFrame={}}
DragonUI.BagsterModule=m
local inventory=CreateFrame('Frame','MockDragonInventory'); inventory:Hide()
local bank=CreateFrame('Frame','MockDragonBank'); bank:Hide(); bank.isBank=true
m.frames={inventory,bank}
function m:Show(bag) if bag>4 or bag==-1 then bank:Show() else inventory:Show() end end
function m:Hide(bag) if bag>4 or bag==-1 then bank:Hide() else inventory:Hide() end end
function m:Toggle(bag)
    local f=(bag>4 or bag==-1) and bank or inventory
    if f:IsShown() then f:Hide() else f:Show() end
end
function m.ItemFrame:GetBagSize(bag) return self.cached and self.cached[bag] or GetContainerNumSlots(bag) end
function m.ItemFrame:HasItem(bag,slot) return slot>=1 and slot<=self:GetBagSize(bag) end
function installDragonGlobals()
    ToggleBag=function(bag) m:Toggle(bag) end
    OpenBackpack=function() m:Show(0) end
    ToggleBackpack=function() m:Toggle(0) end
    OpenAllBags=function() m:Toggle(0) end
    ToggleAllBags=function() m:Toggle(0) end
    CloseAllBags=function() m:Hide(0); m:Hide(-1) end
end
installDragonGlobals()
'''


class Harness:
    def __init__(self, dragon=False):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCK)
        self.lua.execute((NATIVE / "ContainerFrame.lua").read_text())
        xml = ET.parse(NATIVE / "ContainerFrame.xml").getroot()
        template = next(node for node in xml if node.get("name") == "ContainerFrameItemButtonTemplate")
        scripts = next(node for node in template if node.tag.rsplit("}", 1)[-1] == "Scripts")
        for node in scripts:
            event = node.tag.rsplit("}", 1)[-1]
            self.lua.globals().nativeTemplates[event] = self.lua.eval(
                "function(self, button, motion, ...)\n" + (node.text or "") + "\nend")
        self.lua.execute("createStock()")
        if dragon:
            self.lua.execute(DRAGON)
        self.lua.execute(ADDON.read_text())
        self.lua.execute("fire('PLAYER_LOGIN'); fire('PLAYER_ENTERING_WORLD'); tick()")

    def run(self, script):
        self.lua.execute(script)


class SatchelBehavior(unittest.TestCase):
    def test_layout_and_native_high_slot_handlers(self):
        h = Harness()
        h.run(r'''
        OpenBag(1); local f=EsteriaSatchel.frames[1]
        assert(f:IsShown() and #f.items==237 and f.size==237)
        local positions={}
        for slot,b in ipairs(f.items) do
            assert(b:GetID()==slot and b:GetParent():GetID()==1)
            local x,y=EsteriaSatchel.GetSlotPosition(slot)
            assert(x-15>0 and x+15<561 and y-15.5>0 and y+15.5<701)
            local key=x..':'..y; assert(not positions[key]); positions[key]=true
        end
        for _,slot in ipairs({1,100,101,127,128,129,237}) do
            contents['1:'..slot]={texture='item',count=20,quality=2,link='item:'..slot}
            local b=f.items[slot]
            modified=nil; b.scripts.OnDragStart(b,'LeftButton'); expectcall('pickup',1,slot)
            b.scripts.OnReceiveDrag(b); expectcall('pickup',1,slot)
            b.scripts.OnClick(b,'RightButton'); expectcall('use',1,slot)
            modified='SPLITSTACK'; b.scripts.OnClick(b,'LeftButton')
            assert(StackSplitFrame.owner==b and StackSplitFrame:IsShown())
            b.SplitStack(b,3); expectcall('split',1,slot)
            assert(select(4,lastcall('split'))==3)
            modified='CHATLINK'; b.scripts.OnClick(b,'LeftButton')
            assert(select(4,lastcall('link'))=='item:'..slot)
            modified=nil; b.scripts.OnEnter(b); expectcall('tooltip',1,slot)
        end
        ''')

    def test_refresh_and_unequip(self):
        h = Harness()
        h.run(r'''
        OpenBag(1); local f=EsteriaSatchel.frames[1]; local b=f.items[237]
        contents['1:237']={texture='newicon',count=7,locked=true,quality=2,readable=true}
        GameTooltip:SetOwner(b)
        fire('BAG_UPDATE',1); assert(b.texture~='newicon')
        tick(); assert(b.texture=='newicon' and b.count==7 and b.locked and b.readable and b.hasItem)
        assert(b.qualityBorder:IsShown()); expectcall('tooltip',1,237)
        assert(_G[b:GetName()..'Cooldown'].timer[3]==1)
        contents['1:237']=nil; fire('ITEM_LOCK_CHANGED',1,237); tick()
        assert(not b.texture and not b.hasItem and not b.qualityBorder:IsShown())
        bags[1]=0; fire('BAG_UPDATE',1); tick(); assert(not f:IsShown())
        bags[2]=237; OpenBag(2); assert(EsteriaSatchel.frames[2]:IsShown())
        assert(EsteriaSatchel.frames[2].items[237]:GetParent():GetID()==2)
        ''')

    def test_stock_allbags_toggle_force_and_normal_bag(self):
        h = Harness()
        h.run(r'''
        assert(OpenAllBags()==true)
        assert(IsBagOpen(0) and IsBagOpen(2) and EsteriaSatchel.frames[1]:IsShown())
        assert(not IsBagOpen(1),'237 bag reached stock frame pool')
        assert(OpenAllBags()==nil)
        assert(not IsBagOpen(0) and not IsBagOpen(2) and not EsteriaSatchel:IsAnyShown())
        assert(OpenAllBags(true)==true); assert(OpenAllBags(true)==true)
        assert(IsBagOpen(0) and EsteriaSatchel:IsAnyShown())
        CloseAllBags(); OpenBag(2)
        local frame=_G['ContainerFrame'..IsBagOpen(2)]
        assert(frame.size==20 and not EsteriaSatchel:IsAnyShown())
        assert(frame.items==nil and _G[frame:GetName()..'Item1']:GetID()==20)
        ToggleBag(2); assert(not IsBagOpen(2))
        ''')

    def test_bank_multibag_and_pending_close(self):
        h = Harness()
        h.run(r'''
        bags[4]=237; bags[11]=237
        fire('BANKFRAME_OPENED'); tick()
        assert(EsteriaSatchel.frames[5]:IsShown() and EsteriaSatchel.frames[11]:IsShown())
        OpenAllBags(true)
        assert(EsteriaSatchel.frames[1]:IsShown() and EsteriaSatchel.frames[4]:IsShown())
        assert(#EsteriaSatchel.frames[11].items==237)
        local b=EsteriaSatchel.frames[11].items[237]
        b.scripts.OnClick(b,'RightButton'); expectcall('use',11,237)
        fire('BANKFRAME_CLOSED'); tick()
        assert(not EsteriaSatchel.frames[5]:IsShown() and not EsteriaSatchel.frames[11]:IsShown())
        assert(EsteriaSatchel.frames[1]:IsShown())
        fire('BANKFRAME_OPENED'); fire('BANKFRAME_CLOSED'); tick()
        assert(not EsteriaSatchel.frames[5]:IsShown())
        ''')

    def test_dragon_exclusion_allbags_and_rehook(self):
        h = Harness(dragon=True)
        h.run(r'''
        local m=DragonUI.BagsterModule
        local view=setmetatable({}, {__index=m.ItemFrame})
        assert(view:GetBagSize(1)==0 and not view:HasItem(1,101))
        assert(view:GetBagSize(2)==20 and view:HasItem(2,20))
        view.cached={[5]=237}; assert(view:GetBagSize(5)==0 and not view:HasItem(5,237))
        assert(OpenAllBags()==true and m.frames[1]:IsShown() and EsteriaSatchel.frames[1]:IsShown())
        assert(OpenAllBags()==nil and not m.frames[1]:IsShown() and not EsteriaSatchel:IsAnyShown())
        assert(OpenAllBags(true)==true); assert(OpenAllBags(true)==true)
        local old=OpenAllBags
        for i=1,5 do EsteriaSatchel:InstallHooks(); assert(OpenAllBags==old) end
        installDragonGlobals(); assert(OpenAllBags~=old)
        tick(0.6); assert(EsteriaSatchel.ownedWrappers[OpenAllBags])
        assert(OpenAllBags()==nil); assert(OpenAllBags()==true)
        OpenAllBags=old; EsteriaSatchel:InstallHooks(); assert(OpenAllBags==old)
        CloseAllBags(); m:Show(1); assert(EsteriaSatchel.frames[1]:IsShown() and not m.frames[1]:IsShown())
        m:Hide(1); assert(not EsteriaSatchel.frames[1]:IsShown())
        m:Show(0); assert(EsteriaSatchel.frames[1]:IsShown()); m:Hide(0)
        assert(not EsteriaSatchel:IsAnyShown())
        -- DragonUI's bank callback runs before the addon's BANKFRAME_OPENED event.
        m:Show(-1); m:Show(0); fire('BANKFRAME_OPENED'); tick()
        assert(EsteriaSatchel.frames[5]:IsShown())
        fire('BANKFRAME_CLOSED'); tick(); assert(not EsteriaSatchel.frames[5]:IsShown())
        ''')

    def test_consoleport_open_state_contract(self):
        for dragon in (False, True):
            with self.subTest(dragon=dragon):
                h = Harness(dragon=dragon)
                h.run(r'''
                local cpBagsOpen=false
                local function toggle()
                    CloseAllBags()
                    if not cpBagsOpen then cpBagsOpen=OpenAllBags()
                    else CloseAllBags(); cpBagsOpen=false end
                end
                toggle(); assert(cpBagsOpen and EsteriaSatchel:IsAnyShown())
                toggle(); assert(not cpBagsOpen and not EsteriaSatchel:IsAnyShown())
                toggle(); assert(cpBagsOpen and EsteriaSatchel:IsAnyShown())
                ''')

    def test_consoleport_cursor_registration_and_bag_nodes(self):
        h = Harness()
        h.run(r'''
        local registered={}
        ConsolePort={AddFrame=function(self, frame) registered[frame]=true end}
        EsteriaSatchel:Show(1)
        local frame=EsteriaSatchel.frames[1]
        assert(registered[frame], 'satchel must join ConsolePort UI cursor frames')
        for _, node in ipairs(frame.items) do
            assert(node:GetParent():GetName():match('ContainerFrame'))
            assert(node:GetName():match(node:GetParent():GetName()..'Item'))
        end
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
