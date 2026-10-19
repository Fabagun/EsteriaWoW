-- Offline behavioral tests against the actual addon, with a bounded WoW UI harness.
local source = assert(arg[1], "addon source path required")
local legacy = arg[2] == "legacy"
local objects, calls, time, serial = {}, {}, 0, 0
local modifiers = {}
local prototype = {}
local function noop() end
local function object(name, parent)
    local value = { _name = name, _parent = parent, scripts = {}, shown = true }
    setmetatable(value, { __index = function(_, key) return prototype[key] or noop end })
    objects[#objects + 1] = value
    if name then _G[name] = value end
    return value
end
function prototype:SetScript(name, callback) self.scripts[name] = callback end
function prototype:RegisterEvent(name) self.events = rawget(self, "events") or {}; self.events[name] = true end
function prototype:SetPoint(...) self.point = { ... } end
function prototype:SetSize(w, h) self.width, self.height = w, h end
function prototype:SetWidth(w) self.width = w end
function prototype:SetHeight(h) self.height = h end
function prototype:GetWidth() return self.width or 1920 end
function prototype:GetHeight() return self.height or 1080 end
function prototype:SetID(id) self.id = id end
function prototype:GetID() return self.id end
function prototype:GetParent() return self._parent end
function prototype:GetName() return self._name end
function prototype:Show() self.shown = true; if self.scripts.OnShow then self.scripts.OnShow(self) end end
function prototype:Hide() self.shown = false; if self.scripts.OnHide then self.scripts.OnHide(self) end end
function prototype:IsShown() return self.shown end
function prototype:SetText(value) self.value = value end
function prototype:GetText() return self.value or "" end
function prototype:CreateFontString(name) return object(name, self) end
function prototype:CreateTexture(name) return object(name, self) end
function prototype:IsOwned() return false end
function CreateFrame(_, name, parent, template)
    local frame = object(name, parent)
    if template == "ContainerFrameItemButtonTemplate" then
        frame.shown = false -- Native bag templates are explicitly shown by their container owner.
        for _, suffix in ipairs({ "IconTexture", "Count", "Cooldown", "IconQuestTexture" }) do
            object(name .. suffix, frame)
        end
    end
    return frame
end
UIParent = object("UIParent"); UIParent:SetSize(1920, 1080)
GameTooltip = object("GameTooltip")
DEFAULT_CHAT_FRAME = { AddMessage = noop }
UISpecialFrames, StaticPopupDialogs, SlashCmdList = {}, {}, {}
ACCEPT, CANCEL = "Accept", "Cancel"
tinsert = table.insert
function GetTime() return time end
function PlaySound() end
function GetItemQualityColor() return 1, 1, 1, "ffffffff" end
function SetItemButtonTexture(frame, value) frame.texture = value end
function SetItemButtonCount(frame, value) frame.count = value end
function SetItemButtonDesaturated(frame, value) frame.locked = value end
function GetContainerItemInfo() return "icon", 5, false end
function GetItemCooldown() return 0, 0, 0 end
function CooldownFrame_SetTimer() end
function ContainerFrame_UpdateCooldown() end
function ContainerFrameItemButton_OnClick(frame, mouse) calls.physical = {frame:GetParent():GetID(), frame:GetID(), mouse} end
function ContainerFrameItemButton_OnDrag(frame) calls.drag = {frame:GetParent():GetID(), frame:GetID()} end
function DressUpItemLink() end
function ChatEdit_InsertLink() end
function IsControlKeyDown() return modifiers.control end
function IsAltKeyDown() return modifiers.alt end
function IsShiftKeyDown() return modifiers.shift end
function UnitGUID() return "0xF130000001000001" end
function UnitName() return "Inventorytester" end
function SendAddonMessage(...) calls.probe = {...} end
function GetCoinTextureString(value) return tostring(value) end
function GetMoney() return 0 end
function OpenStackSplitFrame(count, owner) calls.split = {count, owner} end
function StaticPopup_Show(...) calls.popup = {...} end
local originalCalls = 0
local function original() originalCalls = originalCalls + 1 end
ToggleBackpack, OpenBackpack, CloseBackpack = original, original, original
ToggleAllBags, OpenAllBags, CloseAllBags = original, original, original
ToggleBag, OpenBag, CloseBag = original, original, original
local satchelInstalls = 0
EsteriaSatchel = { frames = {},
    InstallHooks = function() satchelInstalls = satchelInstalls + 1; ToggleBag = original end,
    Show = function(_, bag) calls.satchelShow = bag end,
    Toggle = function(_, bag) calls.satchelToggle = bag end, ShowAll = noop,
}
local snapshot
if not legacy then
    function EsteriaInventory_Request(...)
        serial = serial + 1
        calls[#calls + 1] = {...}
        return serial
    end
    function EsteriaInventory_GetSnapshot() return snapshot end
end
assert(loadfile(source))()
local events
for _, frame in ipairs(objects) do
    if type(rawget(frame, "events")) == "table" and frame.events.PLAYER_LOGIN then events = frame; break end
end
assert(events, "login event missing")
events.scripts.OnEvent(events, "PLAYER_LOGIN")
local I = EsteriaInventory
assert(#I.buttons == 20, "grid must have exactly 20 pooled item frames")
assert(ToggleBackpack == original, "bag replacement must wait for server handshake")
for _, b in ipairs(I.buttons) do
    local proxy = b:GetParent()
    assert(b:IsShown() and proxy:IsShown(), "inherited hidden bag buttons must be explicitly shown")
    assert(proxy.point[2] >= 20 and proxy.point[2] + proxy.width <= 621, "grid exceeds width")
    assert(-proxy.point[3] + proxy.height < 630, "grid overlaps footer")
end
if legacy then
    I:Show()
    assert(not I.active and ToggleBackpack == original, "missing native support must retain normal bags")
    print("PASS: missing native client fallback and bounded layout")
    return
end
local function tick(seconds) time = time + seconds; events.scripts.OnUpdate(events) end
local function receive(rows, options)
    options = options or {}
    snapshot = { request = options.request or serial, revision = options.revision or 1,
        active = options.active ~= false, capacity = 2048, used = 768, total = options.total or #rows,
        offset = options.offset or 0, price = options.price or 1000000, upgrade = 256,
        status = options.status or 0, message = options.message or "", rows = rows }
    events.scripts.OnEvent(events, "ESTERIA_INVENTORY_UPDATE")
end
local gear = { guid = 1234, entry = 25, count = 5, digital = true, bag = 0, slot = 1,
    quality = 2, inventoryType = 1, category = 1, favorite = false, name = "Enchanted helm",
    link = "item:25:1:2:3:4:-5:6:80", icon = "INV_Helmet_01", durability = 17, maxDurability = 80 }
tick(3)
assert(#calls == 0 and calls.probe[1] == "ESTERIADI" and calls.probe[2] == "HELLO:1",
    "login must use only a stock addon message before server capability discovery")
local function capability(message, sender, channel)
    events.scripts.OnEvent(events, "CHAT_MSG_ADDON", "ESTERIADI", message or "READY:1",
        channel or "WHISPER", sender or "Inventorytester")
end
capability("HELLO:1")
capability("READY:1", "Otherplayer")
capability("READY:1", "Inventorytester", "GUILD")
assert(#calls == 0 and not I.serverReady, "self echoes and unrelated addon messages must not enable native packets")
if arg[2] == "oldserver" then
    tick(9)
    capability()
    assert(#calls == 0, "a stale discovery reply must not enable custom traffic")
    I:Show()
    I:Request(0)
    ToggleBackpack()
    assert(#calls == 0 and not I.active and ToggleBackpack == original,
        "an old server must never receive the new opcode, even on manual inventory requests")
    events.scripts.OnEvent(events, "PLAYER_LEAVING_WORLD")
    events.scripts.OnEvent(events, "PLAYER_ENTERING_WORLD")
    tick(3)
    assert(#calls == 0, "zoning on an old server must retain safe discovery")
    local beforeReload = #objects
    assert(loadfile(source))()
    for index = beforeReload + 1, #objects do
        local frame = objects[index]
        if type(rawget(frame, "events")) == "table" and frame.events.PLAYER_LOGIN then events = frame; break end
    end
    events.scripts.OnEvent(events, "PLAYER_LOGIN")
    tick(3)
    assert(#calls == 0 and not EsteriaInventory.serverReady, "UI reload must retain safe discovery")
    print("PASS: old-server login, echo, timeout, manual requests, zoning and UI reload emit zero custom opcodes")
    return
end
capability()
assert(calls[1][1] == 8 and not I.active, "login must negotiate before taking over bags")
receive({gear})
assert(I.active and ToggleBackpack ~= original, "successful handshake should enable replacement")
assert(I.buttons[1]:IsShown() and I.buttons[1].texture == "Interface\\Icons\\INV_Helmet_01"
    and I.buttons[1].name:GetText() == gear.name, "received items must render visible icons and names")
EsteriaSatchel:InstallHooks()
assert(satchelInstalls == 0 and ToggleBag ~= original, "Satchel poll must not replace negotiated hooks")
EsteriaSatchel:Show(5)
EsteriaSatchel:Show(1)
assert(calls.satchelShow == 5, "carried Satchel suppression must preserve bank Satchels")
ToggleBackpack()
assert(I.frame:IsShown() and calls[#calls][1] == 0, "B must open and browse digital inventory")
receive({gear})
local b = I.buttons[1]
b.scripts.OnClick(b, "RightButton")
assert(calls[#calls][1] == 10 and calls[#calls][3] == gear.guid, "gear must request authoritative equip")
local sent = #calls
b.scripts.OnClick(b, "RightButton")
assert(#calls == sent, "pending mutation must not be submitted twice")
tick(9)
assert(not I.pending and #calls == sent, "timeout must not replay a mutation")
receive({gear})
modifiers.alt = true; b.scripts.OnClick(b, "LeftButton"); modifiers.alt = false
assert(calls[#calls][1] == 7, "Alt-click must toggle favorite")
receive({gear})
modifiers.shift = true; b.scripts.OnClick(b, "LeftButton"); modifiers.shift = false
assert(calls.split[1] == 4 and calls.split[2] == b, "split dialog must exclude the full stack")
b.SplitStack(b, 2)
assert(calls[#calls][1] == 4 and calls[#calls][4] == 2, "split quantity must go to server")
receive({gear})
EsteriaInventorySearch:SetText("ore")
EsteriaInventorySearch.scripts.OnTextChanged(EsteriaInventorySearch)
tick(0.25)
assert(calls[#calls][1] == 0 and calls[#calls][5] == 0 and calls[#calls][8] == "ore", "search must restart at page one")
receive({gear}, {total = 43, offset = 20})
I.frame.scripts.OnMouseWheel(I.frame, -1)
assert(calls[#calls][5] == 40, "wheel must page without creating more frames")
local physical = {}; for key, value in pairs(gear) do physical[key] = value end
physical.digital, physical.bag, physical.slot = false, 4, 237
receive({physical})
b.scripts.OnClick(b, "RightButton")
assert(calls.physical[1] == 4 and calls.physical[2] == 237, "high physical slots must keep native coordinates")
b.scripts.OnDragStart(b)
assert(calls.drag[1] == 4 and calls.drag[2] == 237, "physical drag must use native handler")
I.frame.expand.scripts.OnClick()
assert(calls.popup[2] == 256, "expansion offer must show authoritative increment")
I.snapshot.price = 2000000
StaticPopupDialogs.ESTERIA_INVENTORY_EXPAND.OnAccept()
assert(calls[#calls][1] == 6 and calls[#calls][4] == 1000000, "purchase must use the price actually offered")
receive({gear})
-- Account bank: its snapshots render in the banker window and the bag window's Bank view.
local function bankSnapshot(request)
    snapshot = { request = request or 0, revision = 3, active = true, capacity = 512, used = 1, total = 1,
        offset = 0, price = 100, upgrade = 256, status = 0, message = "", rows = { gear },
        bankUnlocked = true, atBanker = false, unlockCost = 100 }
    events.scripts.OnEvent(events, "ESTERIA_INVENTORY_UPDATE", 1)
end
bankSnapshot()
assert(EsteriaBankContainerFrameItem1.texture == "Interface\\Icons\\INV_Helmet_01", "bank snapshot must render in the banker window")
I:SetView(1)
bankSnapshot(serial)
b.scripts.OnClick(b, "LeftButton")
assert(calls[#calls][1] == 3 and calls[#calls][10] == 1, "bank view click must withdraw from the bank scope")
bankSnapshot(serial)
I:SetView(0)
receive({gear}, {request = serial})
-- Guild bank: the stock API drives a third window with local search, sort and paging.
local guildCalls = {}
function GetItemInfo() return nil end
function GetAuctionItemClasses() return "Weapon", "Armor" end
function GetNumGuildBankTabs() return 2 end
function GetCurrentGuildBankTab() return 1 end
function SetCurrentGuildBankTab() end
function QueryGuildBankTab() end
function GetGuildBankTabInfo(tab) return "Tab " .. tab, "icon", true, true, 0, -1 end
function GetGuildBankItemLink(tab, slot)
    if tab == 1 and slot == 5 then return "|cff1eff00|Hitem:2589:0:0:0:0:0:0:0:80|h[Linen Cloth]|h|r" end
    if tab == 1 and slot == 9 then return "|cff1eff00|Hitem:2592:0:0:0:0:0:0:0:80|h[Wool Cloth]|h|r" end
end
function GetGuildBankItemInfo() return "Interface\\Icons\\INV_Misc_Cloth", 12, false end
function AutoStoreGuildBankItem(tab, slot) guildCalls.store = { tab, slot } end
function PickupGuildBankItem(tab, slot) guildCalls.pickup = { tab, slot } end
function GetGuildBankMoney() return 12345 end
function IsGuildLeader() return false end
events.scripts.OnEvent(events, "GUILDBANKFRAME_OPENED")
local guild = EsteriaGuildBankContainerFrameItem1
assert(guild and guild.row and guild.row.name == "Linen Cloth", "guild bank must list tab items sorted by name")
assert(EsteriaGuildBankContainerFrameItem2.row.name == "Wool Cloth", "guild bank rows must follow the sort order")
guild.scripts.OnClick(guild, "RightButton")
assert(guildCalls.store and guildCalls.store[1] == 1 and guildCalls.store[2] == 5, "right-click must withdraw from the guild slot")
guild.scripts.OnClick(guild, "LeftButton")
assert(guildCalls.pickup[2] == 5, "left-click must pick up the guild slot")
EsteriaGuildBankSearch:SetText("wool")
EsteriaGuildBankSearch.scripts.OnTextChanged(EsteriaGuildBankSearch)
tick(0.25)
assert(EsteriaGuildBankContainerFrameItem1.row.name == "Wool Cloth" and type(EsteriaGuildBankContainerFrameItem2.row) ~= "table", "guild search must filter locally")
-- Tab sizes come from the server (scope 2): capacity above the old 98, and the open requested them.
local metaRequested = false
for _, call in ipairs(calls) do if call[10] == 2 then metaRequested = true end end
assert(metaRequested, "opening the guild bank must request tab sizes from the server")
snapshot = { request = 0, revision = 1, active = true, capacity = 250, used = 0, total = 1, offset = 0, price = 3000,
    upgrade = 1, status = 0, message = "", rows = { { guid = 0, entry = 128, count = 500, durability = 16,
    maxDurability = 250, name = "Tab 1", tag = "" } } }
events.scripts.OnEvent(events, "ESTERIA_INVENTORY_UPDATE", 2)
assert(EsteriaGuildBankFrame.capacity:GetText() == "2 / 128", "guild tab capacity must follow the server value")
events.scripts.OnEvent(events, "GUILDBANKFRAME_CLOSED")
SlashCmdList.ESTERIAINVENTORY("legacy")
ToggleBackpack()
assert(originalCalls == 1, "legacy switch must restore the original bag path")
receive({}, {active = false})
ToggleBackpack()
assert(originalCalls == 2, "unavailable server must retain the original bag path")
events.scripts.OnEvent(events, "PLAYER_LEAVING_WORLD")
events.scripts.OnEvent(events, "PLAYER_ENTERING_WORLD")
local beforeZone = #calls
tick(3)
assert(#calls == beforeZone and not I.serverReady, "zoning must rediscover support before custom requests")
capability()
assert(calls[#calls][1] == 8, "zoning must renegotiate inventory activation")
assert(#I.buttons == 20, "pagination must reuse the frame pool")
print("PASS: handshake, grid bounds, native slots, search, paging, equip, split, favorites, upgrade quote, timeout and fallback")
