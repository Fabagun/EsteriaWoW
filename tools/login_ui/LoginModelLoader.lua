local function SetLoginModelFile(model, data)
    -- Model frames keep their native update handler; setup runs from the login parent.
    model:SetAlpha(1)
    model:SetPosition(0, 0, 0)
    model:SetFacing(0)
    model:SetModelScale(1)
    model:SetModel(data.camera and "Character/Human/Male/HumanMale.mdx" or data[LOGIN_MODEL_STRUCT.MODEL_PATH])
    model.loginLoad = { data = data, phase = data.camera and "donor" or "target", time = 0, frames = 0 }
end

function LoginModels_Update(parent, elapsed)
    local pending = false
    for _, model in ipairs(parent.Models or {}) do
        local state = model.loginLoad
        if state then
            pending = true
            state.time = state.time + elapsed
            state.frames = state.frames + 1
            local data = state.data
            if state.phase == "donor" then
                model:SetPosition(0, 0, 0)
                model:SetFacing(0)
                model:SetModelScale(1)
            end
            if state.time >= 0.12 and state.frames >= 3 then
                if state.phase == "donor" then
                    model:SetCamera(data.camera)
                    model:SetModel(data[LOGIN_MODEL_STRUCT.MODEL_PATH])
                    state.phase = "target"
                    state.time = 0
                    state.frames = 0
                else
                    if not data.camera then model:SetCamera(0) end
                    model:SetFogNear(0)
                    model:SetFogFar(1200)
                    model:SetPosition(data[LOGIN_MODEL_STRUCT.POS_X], data[LOGIN_MODEL_STRUCT.POS_Y],
                                      data[LOGIN_MODEL_STRUCT.POS_Z])
                    model:SetFacing(data[LOGIN_MODEL_STRUCT.FACING])
                    model:SetModelScale(data[LOGIN_MODEL_STRUCT.SCALE])
                    model:SetSequence(data[LOGIN_MODEL_STRUCT.SEQUENCE])
                    if data[LOGIN_MODEL_STRUCT.LIGHT] then
                        model:SetLight(unpack(data[LOGIN_MODEL_STRUCT.LIGHT]))
                    end
                    model:SetAlpha(data[LOGIN_MODEL_STRUCT.ALPHA])
                    model.loginLoad = nil
                end
            end
        end
    end
    if not parent.loginLoadingCover then
        local cover = CreateFrame("Frame", nil, parent)
        cover:SetAllPoints(parent)
        cover:SetFrameLevel(4)
        local texture = cover:CreateTexture(nil, "BACKGROUND")
        texture:SetAllPoints(cover)
        texture:SetTexture(0, 0, 0, 1)
        parent.loginLoadingCover = cover
    end
    if pending then parent.loginLoadingCover:Show() else parent.loginLoadingCover:Hide() end
end

