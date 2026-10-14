"""Exercise the real scene-switch Lua and lossless Sirus filename relocation."""

import struct
import unittest

from lupa import LuaRuntime
from wotlkconv.m2 import parse_m2

import login_screen_pack as pack


class LoginScreenTests(unittest.TestCase):
    def test_embedded_camera_preserves_existing_model_bytes(self):
        path = pack.WORK / "raw-sirus/interface/glues/models/ui_mainmenu_sirusdefault/humanmalefarmer.m2"
        payload = path.read_bytes()
        expected = pack.sirus_camera()
        result = pack.embed_login_camera(payload, expected)
        self.assertEqual(result[:0x110], payload[:0x110])
        self.assertEqual(result[0x120:len(payload)], payload[0x120:])
        parsed = parse_m2(result)
        camera = parsed.cameras[0]
        self.assertEqual(parsed.camera_lookup, [0])
        for field in ("fov", "far_clip", "near_clip", "position_base", "target_position_base"):
            self.assertEqual(camera[field], expected[field])
        for field in ("positions", "target_position", "roll"):
            self.assertEqual(camera[field].timestamps, expected[field].timestamps)
            self.assertEqual(camera[field].values, expected[field].values)

    def test_sirus_relocation_preserves_geometry_and_tracks(self):
        path = pack.WORK / "raw-sirus/interface/glues/models/ui_mainmenu_sirusdefault/ui_mainmenu_sirusdefault.m2"
        payload = path.read_bytes()
        original = parse_m2(payload)
        relocated = pack.namespace_model(payload, pack.SIRUS_PREFIX)
        model = parse_m2(relocated)
        self.assertEqual(model.vertices, original.vertices)
        self.assertEqual(model.sequences, original.sequences)
        self.assertEqual(model.bones, original.bones)
        self.assertEqual(model.cameras, original.cameras)
        allowed = set()
        count, offset = struct.unpack_from("<II", payload, 0x50)
        for i in range(count):
            allowed.update(range(offset + i * 16 + 8, offset + i * 16 + 16))
        count, offset = struct.unpack_from("<II", payload, 0x128)
        for i in range(count):
            allowed.update(range(offset + i * original.particle_schema.size + 24,
                                 offset + i * original.particle_schema.size + 40))
        self.assertTrue(all(a == b or i in allowed for i, (a, b) in enumerate(zip(payload, relocated))))
        self.assertTrue(all(t["filename"].startswith(pack.SIRUS_PREFIX) for t in model.textures))

    def test_scene_switch_restore_and_frame_reuse(self):
        text = (pack.WORK / "AccountLogin.lua").read_text(encoding="utf-8")
        lua = LuaRuntime()
        lua.execute('''
            unpack = table.unpack
            ModelManager = {models = {}, loginModels = {}}
            LoginState = {sceneTimer = 0, currentScene = 1}
            Config = {LOGIN_AMBIENCE = false, MODEL_UPDATE_INTERVAL = 0.1, MODEL_UPDATE_COUNT_REQUIRED = 2}
            LOGIN_MODEL_STRUCT = {SCENE_ID=1, POS_Y=2, POS_Z=3, POS_X=4, FACING=5,
                SCALE=6, ALPHA=7, LIGHT=8, SEQUENCE=9, WIDTH_SQUISH=10, HEIGHT_SQUISH=11, MODEL_PATH=12}
            function getModelFrameLevel() return 2 end
            function UpdateBackgroundAnimation() end
            created = 0
            frames = {}
            cache = {}
            function CreateFrame()
                created = created + 1
                local f = {shown = false, loads = {}, alpha = 1}
                function f:SetModel(path)
                    self.request = path
                    self.wait = cache[path] and 0 or 2
                    -- The real client reports the request before native render setup.
                    self.path = path
                    table.insert(self.loads, path)
                end
                function f:GetModel() return self.path end
                function f:SetScript(event, handler) self.update=handler end
                function f:SetCamera(camera)
                    self.camera=camera
                end
                function f:SetPosition(x,y,z) self.position={x,y,z} end
                function f:SetFacing(facing) self.facing=facing end
                function f:SetModelScale(scale) self.scale=scale end
                function f:SetSequence(sequence) self.sequence=sequence end
                function f:SetLight(...) self.light={...} end
                function f:Show() self.shown=true end
                function f:Hide() self.shown=false end
                function f:SetSize() end
                function f:SetPoint() end
                function f:SetFogNear() end
                function f:SetFogFar() end
                function f:SetAlpha(alpha) self.alpha=alpha end
                function f:SetFrameLevel() end
                function f:SetAllPoints() end
                function f:CreateTexture()
                    return {SetAllPoints=function() end, SetTexture=function() end}
                end
                table.insert(frames, f)
                return f
            end
            function tick()
                LoginModels_Update(AccountLogin, 0.05)
                for _, f in ipairs(frames) do
                    if f.shown and f.update then f.update(f) end
                    if f.shown and f.alpha > 0 and f.wait and f.wait > 0 then
                        f.wait = f.wait - 1
                        if f.wait == 0 then
                            f.path = f.request
                            cache[f.path] = true
                            f.position = {0,0,0}
                            f.scale = 1
                        end
                    end
                end
            end
            function settle() for i=1,12 do tick() end end
            AccountLoginModel1 = CreateFrame()
            AccountLoginModel2 = CreateFrame()
            AccountLogin = {Models={AccountLoginModel1,AccountLoginModel2}}
            function AccountLogin:GetSize() return 1920,1080 end
        ''')
        helper = "local function SetLoginModelFile" + text.split("local function SetLoginModelFile", 1)[1].split(
            "local function InitializeLoginScene", 1)[0]
        picker = "local SIRUS_LOGIN_PATH" + text.split("local SIRUS_LOGIN_PATH", 1)[1].split(
            "local function LoginScenePicker_RefreshRows", 1)[0]
        update = "function LoginScene_OnUpdate" + text.split("function LoginScene_OnUpdate", 1)[1].split(
            "local function isBackgroundModel", 1)[0]
        lua.execute(helper + "\n" + picker + "\n" + update)
        lua.execute('''
            assert(LoginScenePicker_Apply("ww") and #AccountLogin.Models == 2)
            settle()
            assert(LoginScenePicker_Apply("mi") and #AccountLogin.Models == 2)
            assert(AccountLogin.Models[1].alpha == 1 and AccountLogin.Models[1].loginLoad)
            assert(AccountLogin.Models[1]:GetModel())
            tick()
            assert(AccountLogin.Models[1].loginLoad and AccountLogin.loginLoadingCover.shown)
            settle()
            assert(AccountLogin.Models[1].alpha == 1 and not AccountLogin.Models[1].loginLoad)
            assert(not AccountLogin.loginLoadingCover.shown)
            assert(string.find(AccountLogin.Models[1].path, "midnight_02.m2", 1, true))
            assert(LoginScenePicker_Apply("si") and #AccountLogin.Models == 74)
            assert(AccountLogin.Models[2].alpha == 1 and AccountLogin.Models[2].loginLoad)
            settle()
            sirusModels = {table.unpack(AccountLogin.Models)}
            assert(AccountLogin.Models[2].camera == 1 and #AccountLogin.Models[2].light == 13)
            assert(AccountLogin.Models[2].scale == 0.35 and AccountLogin.Models[2].position[1] == -12.7)
            local kidFound = false
            for _, model in ipairs(AccountLogin.Models) do
                if string.find(model.path, "humanmalekid.m2", 1, true) then
                    assert(model.sequence == 134)
                    kidFound = true
                end
            end
            assert(kidFound)
            AccountLogin.modelsInitialized = false
            AccountLogin.modelUpdateTimer = 0
            AccountLogin.modelUpdateCount = 0
            LoginScene_OnUpdate(AccountLogin, 0.11)
            settle()
            assert(AccountLogin.Models[2].camera == 1)
            assert(LoginScenePicker_Apply("cl") and #AccountLogin.Models == 1)
            settle()
            for _, model in ipairs(sirusModels) do
                if model ~= AccountLogin.Models[1] then assert(not model.shown) end
            end
            local frameCount = created
            for i=1,5 do
                assert(LoginScenePicker_Apply("ww") and #AccountLogin.Models == 2)
                settle()
                assert(LoginScenePicker_Apply("si") and #AccountLogin.Models == 74)
                settle()
                assert(AccountLogin.Models[2] == sirusModels[2])
            end
            assert(created == frameCount)
            for _, frame in ipairs(frames) do
                assert(not frame.update)
            end
            LOGIN_SCENE_PICKER_COMMITTED = "mi"
            LoginScenePicker_Cancel(false)
            settle()
            assert(LOGIN_SCENE_PICKER_CURRENT == "mi" and #AccountLogin.Models == 2)
            local current = AccountLogin.Models[1]
            assert(not LoginScenePicker_Apply("invalid") and AccountLogin.Models[1] == current)
            assert(LoginScenePicker_Apply("si"))
            assert(LoginScenePicker_Apply("cl"))
            settle()
            for _, model in ipairs(sirusModels) do
                if model ~= AccountLogin.Models[1] then
                    assert(not model.shown and not model.loginLoad)
                end
            end
        ''')


if __name__ == "__main__":
    unittest.main()
