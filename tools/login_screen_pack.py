"""Stage and install Midnight/Sirus scenes without replacing other client content."""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from luaparser import ast
from wotlkconv.m2 import parse_m2, parse_skin

from cars_mount_pack import DLL_DEFAULT, Storm
from wod_model_migration import rebuild_archive_streaming

REPO = Path(__file__).resolve().parents[1]
WORK = Path("G:/RetroPorterWork/login-screens")
CLIENT = Path("G:/3.3.5a - Dev")
GLUE = "Interface\\GlueXML\\AccountLogin.lua"
ARCHIVES = ("Data/patch-Z.MPQ", "Data/enUS/patch-enUS-Z.MPQ", "Data/Patch-Zzz.mpq")
SIRUS_PREFIX = "custom\\esteria_login\\sirus\\"
MIDNIGHT_PREFIX = "custom\\esteria_login\\midnight\\"
SCENES = REPO / "tools/login_ui/LoginScenes.lua"


class LoginStorm(Storm):
    def ensure_capacity(self, archive, extra):
        # Replacing the existing login entry needs no new hash slots.
        if extra != 1:
            raise ValueError("Login writer requires exactly one existing entry")
        self.read(archive, GLUE)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def namespace_model(payload, prefix):
    """Append path strings and change their spans; retain every original track offset."""
    model = parse_m2(payload)
    if payload[:4] != b"MD20" or model.version != 264:
        raise ValueError("Sirus input must already be flat Wrath M2")
    result = bytearray(payload)

    def relocate(at):
        count, offset = struct.unpack_from("<II", payload, at)
        if not count:
            return
        if offset + count > len(payload):
            raise ValueError("Invalid filename span")
        name = payload[offset:offset + count].rstrip(b"\0").decode("ascii")
        name = name.replace("/", "\\").lower()
        if name.endswith(".mdx"):
            name = name[:-4] + ".m2"
        if not name:
            return
        if name.startswith("\\") or ".." in name.split("\\"):
            raise ValueError("Unsafe model dependency path")
        encoded = (prefix + name).encode("ascii") + b"\0"
        if len(encoded) > 260:
            raise ValueError("Namespaced path exceeds the client limit")
        struct.pack_into("<II", result, at, len(encoded), len(result))
        result.extend(encoded)

    count, offset = struct.unpack_from("<II", payload, 0x50)
    for index in range(count):
        relocate(offset + index * 16 + 8)
    count, offset = struct.unpack_from("<II", payload, 0x128)
    for index in range(count):
        for field in (24, 32):
            relocate(offset + index * model.particle_schema.size + field)
    parse_m2(bytes(result))
    return bytes(result)


def embed_login_camera(payload, camera):
    """Append the static Human portrait camera, preserving all existing model data."""
    out = bytearray(payload)

    def append(data):
        out.extend(b"\0" * (-len(out) % 4))
        offset = len(out)
        out.extend(data)
        return offset

    at = append(b"\0" * 100)
    struct.pack_into("<i3f", out, at, 0, camera["fov"], camera["far_clip"], camera["near_clip"])
    for field, offset, base, width in (("positions", 16, "position_base", 9),
                                       ("target_position", 48, "target_position_base", 9),
                                       ("roll", 80, None, 3)):
        track = camera[field]
        if track.timestamps != [[0]] or any(track.values[0][0]) or track.global_sequence != -1:
            raise ValueError("Expected the verified static Human portrait camera")
        times = append(struct.pack("<I", 0))
        values = append(struct.pack("<" + "f" * width, *track.values[0][0]))
        times_outer = append(struct.pack("<II", 1, times))
        values_outer = append(struct.pack("<II", 1, values))
        struct.pack_into("<Hh4I", out, at + offset, track.interpolation, -1,
                         1, times_outer, 1, values_outer)
        if base:
            struct.pack_into("<3f", out, at + offset + 20, *camera[base])
    lookup = append(struct.pack("<H", 0))
    struct.pack_into("<4I", out, 0x110, 1, at, 1, lookup)
    parsed = parse_m2(bytes(out))
    assert len(parsed.cameras) == 1 and parsed.camera_lookup == [0]
    return bytes(out)


def make_scenes(rows):
    midnight = "interface\\glues\\models\\ui_mainmenu_midnight\\"
    lines = [
        "-- Sirus foreground models carry the Human camera with their authored placement and sequence.",
        "local SIRUS_LOGIN_PATH = [[" + SIRUS_PREFIX + "]]",
        "local MIDNIGHT_LOGIN_PATH = [[" + MIDNIGHT_PREFIX + midnight + "]]",
        "local ESTERIA_LOGIN_SCENES = {",
        '{ id = "mi", label = "Retail Midnight", layers = {',
        '    { model = MIDNIGHT_LOGIN_PATH .. [[ui_mainmenu_midnight_02.m2]] },',
        '    { model = MIDNIGHT_LOGIN_PATH .. [[ui_mainmenu_midnight.m2]] },',
        "} },",
        '{ id = "si", label = "Sirus WoW", layers = {',
    ]
    for row in rows:
        name = row["model"]
        lines.append("    { model = SIRUS_LOGIN_PATH ..")
        if row["camera"] == 0:
            lines.append("        [[" + name + "]] },")
            continue
        x, y, z = row["position"]
        light = ", ".join(str(v) for v in row["light"])
        values = f"1, {y}, {z}, {x}, {row['facing']}, {row['scale']}, 1,"
        lines.append("        [[" + name + "]],")
        lines.append("        data = {" + values)
        lines.append("            {" + light + "}, " + str(row["sequence"]) + ", 1, 1, camera = 1} },")
    lines.extend(["} },", "}"])
    return "\n".join(lines) + "\n"


def sirus_camera():
    return parse_m2((WORK / "sirus-camera-donor.m2").read_bytes()).cameras[1]


def camera_stage():
    source = json.loads((WORK / "sirus-source.json").read_text())
    camera = sirus_camera()
    foreground = {row["model"] for row in source["rows"] if row["camera"] == 1}
    storm = Storm(DLL_DEFAULT)
    assets = {}
    asset_archive = CLIENT / ARCHIVES[2]
    for name in sorted(foreground):
        raw = (WORK / "raw-sirus" / name.replace("\\", "/")).read_bytes()
        original = namespace_model(raw, SIRUS_PREFIX)
        prior_camera = embed_login_camera(original, camera)
        packed = original
        entry = SIRUS_PREFIX + name
        current = read(storm, asset_archive, entry)
        if current not in (original, prior_camera):
            raise ValueError("Sirus model changed outside this camera repair: " + name)
        assets[entry] = packed
    output = WORK / "camera-fix"
    report = {"baseline": {}, "staged": {}, "updates": {}, "live_acceptance": "pending",
              "camera_models": len(assets), "camera_source_sha256": sha(WORK / "sirus-camera-donor.m2")}
    for relative in ARCHIVES:
        live = CLIENT / relative
        print("Staging camera repair:", relative, flush=True)
        baseline = sha(live)
        if relative == ARCHIVES[2]:
            updates = assets
            writer = storm
        else:
            text = read(storm, live, GLUE).decode("utf-8").split("\nfunction LoginSceneDebugInit()", 1)[0]
            payload = patch_initialization(text).encode("utf-8")
            if relative == ARCHIVES[0]:
                (WORK / "AccountLogin.lua").write_bytes(payload)
            elif payload != (WORK / "AccountLogin.lua").read_bytes():
                raise ValueError("Root and locale scripts differ")
            updates = {GLUE: payload}
            writer = LoginStorm(DLL_DEFAULT)
        staged = output / relative
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, staged)
        if sha(staged) != baseline or sha(live) != baseline:
            raise ValueError("Baseline changed: " + relative)
        writer.replace_archive_entries(staged, updates)
        original_handle = storm.open_archive(live)
        staged_handle = storm.open_archive(staged)
        preserved = 0
        changed_names = {n.lower() for n in updates}
        try:
            for name, *_ in storm.list_files(original_handle):
                if name.lower() in {"(listfile)", "(attributes)"} or name.lower() in changed_names:
                    continue
                if storm.read(original_handle, name) != storm.read(staged_handle, name):
                    raise ValueError("Unrelated entry changed: " + name)
                preserved += 1
            for name, expected in updates.items():
                if storm.read(staged_handle, name) != expected:
                    raise ValueError("Packed readback mismatch: " + name)
        finally:
            storm.dll.SFileCloseArchive(original_handle)
            storm.dll.SFileCloseArchive(staged_handle)
        if staged.stat().st_size >= 2**31:
            raise ValueError("Archive crossed the classic client boundary")
        report["baseline"][relative] = baseline
        report["staged"][relative] = sha(staged)
        report["updates"][relative] = {"changed": len(updates), "preserved": preserved}
        print(relative, report["updates"][relative], flush=True)
    (output / "stage.json").write_text(json.dumps(report, indent=2) + "\n")


def patch_login(text, scenes):
    def replace(old, new, count=1):
        nonlocal text
        if text.count(old) != count:
            raise ValueError("Login baseline changed: " + old[:90])
        text = text.replace(old, new)

    if 'label = "Retail Midnight"' in text:
        raise ValueError("Scenes already installed; use the original baseline to restage")
    anchor = "local LOGIN_SCENE_PICKER_SCENES = {\n"
    replace(anchor, scenes + "\n" + anchor + "    ESTERIA_LOGIN_SCENES[1],\n    ESTERIA_LOGIN_SCENES[2],\n")
    helper = '''local function SetLoginModelFile(model, data)
    -- Sirus doodads inherit Human camera 1 because they have no authored camera.
    if data.camera then
        model:SetModel("Character/Human/Male/HumanMale.mdx")
        model:SetCamera(data.camera)
    end
    model:SetModel(data[LOGIN_MODEL_STRUCT.MODEL_PATH])
    if not data.camera then
        model:SetCamera(0)
    end
end

'''
    replace("local function CreateLoginModel(parent, modelData)\n",
            helper + "local function CreateLoginModel(parent, modelData)\n")
    replace('    model:SetModel(modelData[LOGIN_MODEL_STRUCT.MODEL_PATH])\n    model:SetCamera(0)',
            "    SetLoginModelFile(model, modelData)")
    replace('                        model:SetModel(data[LOGIN_MODEL_STRUCT.MODEL_PATH])\n'
            '                        model:SetCamera(0)', '                        SetLoginModelFile(model, data)')
    replace("        local scenes = { scene }", "        local scenes = scene.layers or { scene }")
    replace("            local data = { 1, 0, 0, 0, 0, 1, 1, nil, 0, 1, 1, selectedScene.model }\n"
            '            local model = previousModels[index] or _G["AccountLoginModel"..index]',
            "            local data = selectedScene.data or "
            "{ 1, 0, 0, 0, 0, 1, 1, nil, 0, 1, 1, selectedScene.model }\n"
            "            data[LOGIN_MODEL_STRUCT.MODEL_PATH] = selectedScene.model\n"
            '            local poolKey = data.camera and ("sirus"..index) or index\n'
            '            local model = ModelManager.models[poolKey]\n'
            '            if not model and not data.camera then\n'
            '                model = _G["AccountLoginModel"..index]\n'
            '            end')
    replace("                model = CreateLoginModel(AccountLogin, data)\n            end",
            "                model = CreateLoginModel(AccountLogin, data)\n            end\n"
            "            ModelManager.models[poolKey] = model")
    replace('            model:SetModel(selectedScene.model)\n            model:SetCamera(0)',
            "            SetLoginModelFile(model, data)")
    replace("            model:SetAlpha(data[LOGIN_MODEL_STRUCT.ALPHA])\n",
            "            model:SetAlpha(data[LOGIN_MODEL_STRUCT.ALPHA])\n"
            "            if data[LOGIN_MODEL_STRUCT.LIGHT] then\n"
            "                model:SetLight(unpack(data[LOGIN_MODEL_STRUCT.LIGHT]))\n"
            "            end\n")
    # The camera-specific pool may choose a different frame at the same index.
    replace("        for index = #scenes + 1, #previousModels do\n"
            "            previousModels[index]:Hide()\n        end",
            "        for index, previousModel in ipairs(previousModels) do\n"
            "            if previousModel ~= models[index] then\n"
            "                previousModel:Hide()\n"
            "            end\n"
            "        end")
    ast.parse(text)
    return patch_initialization(text)


def patch_initialization(text):
    start = text.index("local function SetLoginModelFile(model, data)\n")
    end = text.index("local function CreateLoginModel", start)
    loader = (SCENES.parent / "LoginModelLoader.lua").read_text(encoding="utf-8")
    text = text[:start] + loader + "\n" + text[end:]
    text = text.replace('    model:SetModel("Character/Human/Male/HumanMale.mdx")\n'
                        '    model:SetCamera(0)\n    SetLoginModelFile(model, modelData)',
                        '    SetLoginModelFile(model, modelData)')
    # A zero-alpha Model can skip the native render initialization we need.
    text = text.replace("    model:SetAlpha(modelData[LOGIN_MODEL_STRUCT.ALPHA])",
                        "    model:SetAlpha(1)")
    text = text.replace("            model:SetAlpha(data[LOGIN_MODEL_STRUCT.ALPHA])",
                        "            model:SetAlpha(1)")
    text = text.replace("model:SetAlpha(0.001)", "model:SetAlpha(1)")
    text = text.replace("model:SetAlpha(0)", "model:SetAlpha(1)")
    text = text.replace('previousModel:SetScript("OnUpdate", nil)', 'previousModel.loginLoad = nil')
    if 'previousModel.loginLoad = nil' not in text:
        text = text.replace("                previousModel:Hide()",
                            '                previousModel.loginLoad = nil\n'
                            '                previousModel:Hide()')
    text = text.replace("camera = 0} },", "camera = 1} },")
    anchor = "function LoginScene_OnUpdate(self, elapsed)\n"
    if "    LoginModels_Update(self, elapsed)\n" not in text:
        text = text.replace(anchor, anchor + "    LoginModels_Update(self, elapsed)\n")
    ast.parse(text)
    return text


def repair_stage():
    storm = LoginStorm(DLL_DEFAULT)
    report = {"baseline": {}, "staged": {}, "updates": {}, "live_acceptance": "pending"}
    output = WORK / "initialization-fix"
    for relative in ARCHIVES[:2]:
        live = CLIENT / relative
        print("Staging initialization fix:", relative, flush=True)
        baseline = sha(live)
        text = read(storm, live, GLUE).decode("utf-8")
        patched = patch_initialization(text).encode("utf-8")
        if relative == ARCHIVES[0]:
            (WORK / "AccountLogin.lua").write_bytes(patched)
        elif patched != (WORK / "AccountLogin.lua").read_bytes():
            raise ValueError("Root and locale login scripts differ")
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        if sha(target) != baseline or sha(live) != baseline:
            raise ValueError("Baseline changed during copy")
        storm.replace_archive_entries(target, {GLUE: patched})
        original = storm.open_archive(live)
        staged = storm.open_archive(target)
        preserved = 0
        try:
            for name, *_ in storm.list_files(original):
                if name.lower() in {"(listfile)", "(attributes)", GLUE.lower()}:
                    continue
                if storm.read(original, name) != storm.read(staged, name):
                    raise ValueError("Unrelated entry changed: " + name)
                preserved += 1
            if storm.read(staged, GLUE) != patched:
                raise ValueError("Login readback mismatch")
        finally:
            storm.dll.SFileCloseArchive(original)
            storm.dll.SFileCloseArchive(staged)
        report["baseline"][relative] = baseline
        report["staged"][relative] = sha(target)
        report["updates"][relative] = {"changed": 1, "preserved": preserved}
        print(relative, report["updates"][relative], flush=True)
    (output / "stage.json").write_text(json.dumps(report, indent=2) + "\n")


def validate_assets(entries):
    for name, payload in entries.items():
        if name.endswith(".m2"):
            model = parse_m2(payload, name)
            if payload[:4] != b"MD20" or model.version != 264:
                raise ValueError("Incompatible model: " + name)
            dependencies = [t["filename"].lower() for t in model.textures if t["type"] == 0]
            for emitter in model.particles:
                dependencies.extend(emitter[f].lower() for f in
                                    ("geometry_model_filename", "recursion_model_filename") if emitter[f])
            dependencies.extend(name[:-3] + f"{i:02d}.skin" for i in range(model.num_skin_profiles))
            dependencies.extend(name[:-3] + f"{s['id']:04d}-{s['variation_index']:02d}.anim"
                                for s in model.sequences if not s["flags"] & 0x170)
            for dependency in dependencies:
                if dependency not in entries:
                    raise ValueError(f"Missing dependency: {name} -> {dependency}")
        elif name.endswith(".skin"):
            skin = parse_skin(payload, name)
            if any(struct.unpack_from("<H", s, 12)[0] > 75 for s in skin.submeshes):
                raise ValueError("Submesh exceeds Wrath bone palette: " + name)


def read(storm, archive, name):
    handle = storm.open_archive(archive)
    try:
        return storm.read(handle, name)
    finally:
        storm.dll.SFileCloseArchive(handle)


def stage():
    source = json.loads((WORK / "sirus-source.json").read_text())
    scenes = make_scenes(source["rows"])
    SCENES.parent.mkdir(exist_ok=True)
    SCENES.write_text(scenes, encoding="utf-8", newline="\n")
    ast.parse(scenes)
    entries = {}
    foreground = {row["model"] for row in source["rows"] if row["camera"] == 1}
    camera = sirus_camera()
    for name, info in source["files"].items():
        payload = (WORK / "raw-sirus" / name.replace("\\", "/")).read_bytes()
        if hashlib.sha256(payload).hexdigest() != info["sha256"]:
            raise ValueError("Source changed: " + name)
        entries[SIRUS_PREFIX + name] = namespace_model(payload, SIRUS_PREFIX) if name.endswith(".m2") else payload
    for path in (WORK / "converted-midnight").rglob("*"):
        if path.is_file():
            name = MIDNIGHT_PREFIX + str(path.relative_to(WORK / "converted-midnight")).replace("/", "\\").lower()
            entries[name] = path.read_bytes()
    validate_assets(entries)
    storm = Storm(DLL_DEFAULT)
    report = {"baseline": {}, "staged": {}, "updates": {}, "assets": len(entries),
              "sirus_placements": len(source["rows"]), "live_acceptance": "pending"}
    for relative in ARCHIVES:
        live = CLIENT / relative
        print("Staging:", relative, flush=True)
        baseline = sha(live)
        updates = entries if relative == ARCHIVES[2] else {
            GLUE: patch_login(read(storm, live, GLUE).decode("utf-8"), scenes).encode("utf-8")}
        if relative == ARCHIVES[0]:
            (WORK / "AccountLogin.lua").write_bytes(updates[GLUE])
        staged = WORK / "stage" / relative
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, staged)
        if sha(staged) != baseline or sha(live) != baseline:
            raise ValueError("Baseline changed while staging: " + relative)
        storm.replace_archive_entries(staged, updates)
        if relative == ARCHIVES[2]:
            compressed = staged.with_suffix(".compressed")
            rebuild_archive_streaming(storm, staged, compressed, compress=True)
            os.replace(compressed, staged)
        print("Checking preserved entries:", relative, flush=True)
        if staged.stat().st_size >= 2**31:
            raise ValueError("Classic archive crossed 2 GiB boundary")
        original_handle = storm.open_archive(live)
        staged_handle = storm.open_archive(staged)
        preserved = 0
        changed_names = {n.lower() for n in updates}
        try:
            for name, *_ in storm.list_files(original_handle):
                if name.lower() in {"(listfile)", "(attributes)"} or name.lower() in changed_names:
                    continue
                if storm.read(original_handle, name) != storm.read(staged_handle, name):
                    raise ValueError("Unrelated entry changed: " + name)
                preserved += 1
            for name, expected in updates.items():
                if storm.read(staged_handle, name) != expected:
                    raise ValueError("Packed readback mismatch: " + name)
        finally:
            storm.dll.SFileCloseArchive(original_handle)
            storm.dll.SFileCloseArchive(staged_handle)
        report["baseline"][relative] = baseline
        report["staged"][relative] = sha(staged)
        report["updates"][relative] = {"changed": len(updates), "preserved": preserved}
        print(relative, report["updates"][relative], flush=True)
    (WORK / "stage.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Stage:", WORK / "stage.json")


def install(repair=False, camera=False):
    processes = subprocess.check_output(["tasklist", "/FO", "CSV"], text=True).lower()
    if any(f'"{name}"' in processes for name in ("wow.exe", "run.exe", "eclipse.exe", "mpqeditor.exe")):
        raise ValueError("Close the WoW client and archive editor before installing")
    stage_root = WORK / "camera-fix" if camera else (WORK / "initialization-fix" if repair else WORK)
    report = json.loads((stage_root / "stage.json").read_text())
    archives = ARCHIVES[:2] if repair else ARCHIVES
    source_root = stage_root if repair or camera else WORK / "stage"
    for relative in archives:
        print("Verifying install hashes:", relative, flush=True)
        if sha(CLIENT / relative) != report["baseline"][relative]:
            raise ValueError("Client changed since staging: " + relative)
        if sha(source_root / relative) != report["staged"][relative]:
            raise ValueError("Stage changed: " + relative)
    backup = Path("G:/ClientBackups/login-screens") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for relative in archives:
        print("Backing up:", relative, flush=True)
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if camera:
            # Atomic replacement leaves this same-volume snapshot on the original file's storage.
            os.link(CLIENT / relative, target)
        else:
            shutil.copy2(CLIENT / relative, target)
        if sha(target) != report["baseline"][relative]:
            raise ValueError("Backup mismatch: " + relative)
    changed = []
    try:
        for relative in (archives if repair else (ARCHIVES[2], ARCHIVES[0], ARCHIVES[1])):
            print("Installing:", relative, flush=True)
            live = CLIENT / relative
            staged = source_root / relative
            if sha(staged) != report["staged"][relative] or sha(live) != report["baseline"][relative]:
                raise ValueError("Install precondition changed: " + relative)
            # Same-volume replacement consumes the validated stage without another multi-GB copy.
            os.replace(staged, live)
            changed.append(relative)
            if sha(live) != report["staged"][relative]:
                raise ValueError("Installed hash mismatch: " + relative)
    except BaseException:
        for relative in reversed(changed):
            shutil.copy2(backup / relative, CLIENT / relative)
        raise
    report["backup"] = str(backup)
    (stage_root / "installed.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Installed with verified backup:", backup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("stage", "install", "repair-stage", "repair-install",
                                           "camera-stage", "camera-install"))
    {"stage": stage, "install": install, "repair-stage": repair_stage,
     "repair-install": lambda: install(repair=True), "camera-stage": camera_stage,
     "camera-install": lambda: install(camera=True)}[parser.parse_args().action]()
