-- The server and custom client must share the 254-slot container layout.
local S = { slots = 237, frames = {}, wrappers = {}, ownedWrappers = {}, bankOpen = false }
EsteriaSatchel = S
local WIDTH, HEIGHT = 561, 701
local ART = "Interface\\AddOns\\EsteriaSatchel\\Art\\"
local function isSatchel(bag)
    return type(bag) == "number" and bag >= 1 and bag <= 11
        and (bag <= 4 or S.bankOpen) and GetContainerNumSlots(bag) == S.slots
end

local function position(slot)
    -- Pixel centers measured from the unchanged 1122 x 1402 source artwork.
    if slot <= 225 then
        local row, col = math.floor((slot - 1) / 15), (slot - 1) % 15
        return (77 + col * 68.5) / 2, (207 + row * 71.5) / 2
    end
    return (178 + (slot - 226) * 68.5) / 2, 1280 / 2
end
S.GetSlotPosition = position

function S:Fit(frame)
    local setting = EsteriaSatchelDB and EsteriaSatchelDB.scale or 1
    frame:SetScale(math.min(setting, (UIParent:GetHeight() - 35) / HEIGHT,
        (UIParent:GetWidth() - 35) / WIDTH))
end

function S:Refresh(frame)
    local bag = frame:GetID()
    if not isSatchel(bag) then frame:Hide(); return end
    frame.title:SetText(GetBagName(bag) or "Esteria Grand Satchel")
    local free = GetContainerNumFreeSlots(bag)
    frame.capacity:SetText((free or 0) .. " / 237 free")
    SetBagPortraitTexture(frame.portrait, bag)
    for slot, button in ipairs(frame.items) do
        local texture, count, locked, quality, readable, _, link = GetContainerItemInfo(bag, slot)
        button.hasItem, button.readable = texture and 1 or nil, readable
        SetItemButtonTexture(button, texture)
        SetItemButtonCount(button, count or 0)
        SetItemButtonDesaturated(button, locked)
        local border = button.qualityBorder
        if texture and quality and quality > 1 then
            local r, g, b = GetItemQualityColor(quality)
            border:SetVertexColor(r, g, b); border:Show()
        else border:Hide() end
        local quest = _G[button:GetName() .. "IconQuestTexture"]
        if quest and GetContainerItemQuestInfo then
            local questItem, questID, active = GetContainerItemQuestInfo(bag, slot)
            if texture and (questItem or questID) then
                quest:SetTexture(TEXTURE_ITEM_QUEST_BORDER or "Interface\\ContainerFrame\\UI-ContainerQuestBorder")
                quest:Show()
            else quest:Hide() end
        end
        ContainerFrame_UpdateCooldown(bag, button)
        if GameTooltip:IsOwned(button) then ContainerFrameItemButton_OnEnter(button) end
    end
end

local function savePosition(frame)
    frame:StopMovingOrSizing()
    local point, _, relativePoint, x, y = frame:GetPoint()
    EsteriaSatchelDB.positions[frame:GetID()] = { point, relativePoint, x, y }
end

function S:Create(bag)
    if self.frames[bag] then return self.frames[bag] end
    -- ConsolePort recognizes native bag item actions through the ContainerFrame name.
    local name = "EsteriaSatchelContainerFrame" .. bag
    local frame = CreateFrame("Frame", name, UIParent)
    frame:Hide(); frame:SetID(bag); frame:SetSize(WIDTH, HEIGHT); frame.size = self.slots
    frame:SetFrameStrata("HIGH"); frame:SetToplevel(true)
    frame:SetMovable(true); frame:EnableMouse(true); frame:SetClampedToScreen(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", function(f) f:StartMoving() end)
    frame:SetScript("OnDragStop", savePosition)
    frame:SetScript("OnShow", function(f) S:Fit(f); S:Refresh(f); PlaySound("igBackPackOpen") end)
    frame:SetScript("OnHide", function(f)
        if StackSplitFrame:IsShown() and StackSplitFrame.owner and StackSplitFrame.owner:GetParent() == f then
            StackSplitFrame:Hide()
        end
        GameTooltip:Hide(); PlaySound("igBackPackClose")
    end)
    local saved = EsteriaSatchelDB.positions[bag]
    if saved then frame:SetPoint(saved[1], UIParent, saved[2], saved[3], saved[4])
    else frame:SetPoint("RIGHT", UIParent, "RIGHT", -25 - ((bag - 1) % 4) * 20, 0) end
    -- Nine 512-square TGA tiles preserve every source pixel and its alpha.
    for row = 0, 2 do
        for col = 0, 2 do
            local w, h = math.min(512, 1122 - col * 512), math.min(512, 1402 - row * 512)
            local tile = frame:CreateTexture(nil, "BACKGROUND")
            tile:SetTexture(ART .. "Bag" .. row .. col .. ".tga")
            tile:SetSize(w / 2, h / 2)
            tile:SetTexCoord(0, w / 512, 0, h / 512)
            tile:SetPoint("TOPLEFT", frame, "TOPLEFT", col * 256, -row * 256)
        end
    end
    frame.portrait = frame:CreateTexture(nil, "ARTWORK")
    frame.portrait:SetSize(37, 37); frame.portrait:SetPoint("CENTER", frame, "TOPLEFT", 39, -48)
    frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    frame.title:SetPoint("TOPLEFT", 83, -34); frame.title:SetWidth(410)
    frame.capacity = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.capacity:SetPoint("TOP", frame, "TOP", 0, -65)
    local close = CreateFrame("Button", name .. "Close", frame, "UIPanelCloseButton")
    close:SetSize(28, 28); close:SetPoint("CENTER", frame, "TOPLEFT", 524, -43)
    close:SetScript("OnClick", function() frame:Hide() end)
    frame.items = {}
    for slot = 1, self.slots do
        local button = CreateFrame("Button", name .. "Item" .. slot, frame, "ContainerFrameItemButtonTemplate")
        button:SetID(slot); button:SetSize(30, 31); button:ClearAllPoints()
        local x, y = position(slot)
        button:SetPoint("CENTER", frame, "TOPLEFT", x, -y)
        button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        button:RegisterForDrag("LeftButton")
        button:SetNormalTexture(""); button:SetPushedTexture("")
        local icon = _G[button:GetName() .. "IconTexture"]
        if icon then icon:ClearAllPoints(); icon:SetAllPoints(button) end
        local quest = _G[button:GetName() .. "IconQuestTexture"]
        if quest then quest:ClearAllPoints(); quest:SetAllPoints(button) end
        local border = button:CreateTexture(nil, "OVERLAY")
        border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
        border:SetBlendMode("ADD"); border:SetSize(48, 49); border:SetPoint("CENTER"); border:Hide()
        button.qualityBorder = border
        button:Show(); frame.items[slot] = button
    end
    tinsert(UISpecialFrames, name)
    self.frames[bag] = frame
    if ConsolePort and ConsolePort.AddFrame then ConsolePort:AddFrame(frame) end
    return frame
end

function S:Show(bag)
    if not isSatchel(bag) then return end
    if CanOpenPanels and not CanOpenPanels() then return end
    local frame = self:Create(bag)
    frame:Show(); frame:Raise(); self:Refresh(frame)
    return true
end

function S:Toggle(bag)
    local frame = self.frames[bag]
    if frame and frame:IsShown() then frame:Hide() else return self:Show(bag) end
end

function S:ShowAll()
    for bag = 1, self.bankOpen and 11 or 4 do if isSatchel(bag) then self:Show(bag) end end
end

function S:CloseAll()
    for _, frame in pairs(self.frames) do frame:Hide() end
end

function S:IsAnyShown()
    for _, frame in pairs(self.frames) do if frame:IsShown() then return true end end
end

local function normalInventoryShown()
    local mod = DragonUI and DragonUI.BagsterModule
    if mod and mod.BagsterModule.applied and mod.frames then
        for _, frame in pairs(mod.frames) do
            if not frame.isBank and frame:IsShown() then return true end
        end
        return false
    end
    return IsBagOpen(0) and true or false
end

local function wrapGlobal(name, factory)
    local current = _G[name]
    if current and not S.ownedWrappers[current] then
        local wrapper = factory(current)
        S.wrappers[name] = wrapper; S.ownedWrappers[wrapper] = true; _G[name] = wrapper
    end
end

function S:InstallHooks()
    wrapGlobal("ContainerFrame_GenerateFrame", function(original)
        return function(frame, size, bag, ...)
            if size == S.slots then return S:Show(bag) end
            return original(frame, size, bag, ...)
        end
    end)
    for _, name in ipairs({ "ToggleBag", "OpenBag", "CloseBag" }) do
        local action = name
        wrapGlobal(action, function(original)
            return function(bag, ...)
                if isSatchel(bag) then
                    if S.batch then return end
                    if action == "ToggleBag" then return S:Toggle(bag) end
                    if action == "OpenBag" then return S:Show(bag) end
                    local frame = S.frames[bag]; if frame then frame:Hide() end
                    return
                end
                return original(bag, ...)
            end
        end)
    end
    for _, name in ipairs({ "OpenAllBags", "ToggleAllBags" }) do
        wrapGlobal(name, function(original)
            return function(forceOpen, ...)
                if S.batch then return original(forceOpen, ...) end
                local hasSatchel, allSatchelsShown = false, true
                for bag = 1, S.bankOpen and 11 or 4 do
                    if isSatchel(bag) then
                        hasSatchel = true
                        if not S.frames[bag] or not S.frames[bag]:IsShown() then allSatchelsShown = false end
                    end
                end
                if hasSatchel and normalInventoryShown() and allSatchelsShown and not forceOpen then
                    CloseAllBags(); return
                end
                S.batch = true
                if hasSatchel then
                    local mod = DragonUI and DragonUI.BagsterModule
                    if mod and mod.BagsterModule.applied then mod:Show(0)
                    else OpenAllBags(true) end
                else original(forceOpen, ...) end
                S.batch = false
                if normalInventoryShown() then S:ShowAll() else S:CloseAll() end
                -- ConsolePort uses this return value to remember the open state.
                return (normalInventoryShown() or S:IsAnyShown()) and true or nil
            end
        end)
    end
    wrapGlobal("CloseAllBags", function(original)
        return function(...) original(...); S:CloseAll() end
    end)
    local mod = DragonUI and DragonUI.BagsterModule
    if mod and mod.ItemFrame and not self.bagsterHooked then
        self.bagsterHooked = true
        local originalSize, originalHas = mod.ItemFrame.GetBagSize, mod.ItemFrame.HasItem
        mod.ItemFrame.GetBagSize = function(frame, bag)
            local size = originalSize(frame, bag)
            return size == S.slots and 0 or size
        end
        mod.ItemFrame.HasItem = function(frame, bag, slot, ...)
            if originalSize(frame, bag) == S.slots then return false end
            return originalHas(frame, bag, slot, ...)
        end
        for _, name in ipairs({ "Show", "Hide", "Toggle" }) do
            local action, original = name, mod[name]
            mod[action] = function(m, bag, ...)
                if isSatchel(bag) then
                    if action == "Show" then return S:Show(bag) end
                    if action == "Toggle" then return S:Toggle(bag) end
                    local frame = S.frames[bag]; if frame then frame:Hide() end
                    return
                end
                local result = original(m, bag, ...)
                if bag == 0 and not S.batch then
                    if normalInventoryShown() then S:ShowAll() else S:CloseAll() end
                end
                return result
            end
        end
        -- Discard any mixed view created before this addon's PLAYER_LOGIN.
        if mod.frames then
            for _, frame in pairs(mod.frames) do
                if frame.itemFrame then frame.itemFrame:ReloadAllItems() end
            end
        end
    end
end

local driver = CreateFrame("Frame")
S.driver = driver
for _, event in ipairs({ "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "BAG_UPDATE", "ITEM_LOCK_CHANGED",
    "BAG_UPDATE_COOLDOWN", "BANKFRAME_OPENED", "BANKFRAME_CLOSED", "DISPLAY_SIZE_CHANGED",
    "UI_SCALE_CHANGED", "QUEST_ACCEPTED", "UNIT_QUEST_LOG_CHANGED" }) do driver:RegisterEvent(event) end
driver:SetScript("OnEvent", function(_, event, bag)
    if event == "PLAYER_LOGIN" then
        EsteriaSatchelDB = EsteriaSatchelDB or {}
        EsteriaSatchelDB.positions = EsteriaSatchelDB.positions or {}
        if not GetContainerSlotCapacity or GetContainerSlotCapacity() < S.slots then
            DEFAULT_CHAT_FRAME:AddMessage("|cffff5050Esteria Satchel requires the Esteria large-bag client.|r")
        end
    elseif event == "BANKFRAME_OPENED" then S.bankOpen = true; S.showBank = true
    elseif event == "BANKFRAME_CLOSED" then
        S.bankOpen = false
        for id, frame in pairs(S.frames) do if id > 4 then frame:Hide() end end
    end
    if not EsteriaSatchelDB then return end
    S:InstallHooks()
    S.dirty = true
end)
local elapsed = 0
driver:SetScript("OnUpdate", function(_, delta)
    elapsed = elapsed + delta
    if elapsed > 0.5 and EsteriaSatchelDB then elapsed = 0; S:InstallHooks() end
    if not S.dirty then return end
    S.dirty = false
    if S.showBank then
        S.showBank = false
        for bag = 5, 11 do if isSatchel(bag) then S:Show(bag) end end
    end
    for _, frame in pairs(S.frames) do
        S:Fit(frame)
        if frame:IsShown() then S:Refresh(frame) end
    end
end)
SLASH_ESTERIASATCHEL1 = "/satchel"
SlashCmdList.ESTERIASATCHEL = function(message)
    local scale = tonumber(message)
    if scale then
        EsteriaSatchelDB.scale = math.max(0.4, math.min(1.5, scale))
        for _, frame in pairs(S.frames) do S:Fit(frame) end
    elseif S:IsAnyShown() then S:CloseAll() else S:ShowAll() end
end
