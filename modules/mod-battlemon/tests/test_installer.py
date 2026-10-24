"""Exercise the real deploy/restore tools on temporary addon trees."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from install_addon import NEW, digest
from restore_addon import restore

with tempfile.TemporaryDirectory(prefix="battlemon-addon-test-") as tmp:
    addons = Path(tmp) / "Interface/AddOns"
    net = addons / "Battlemon/Core/Net.lua"
    net.parent.mkdir(parents=True)
    original = b"-- original\n    run(handlers[cmd])\n"
    net.write_bytes(original)
    def install():
        output = subprocess.check_output([sys.executable, str(ROOT / "tools/install_addon.py"), str(addons)], text=True)
        return json.loads(output)
    first = install()
    assert NEW in net.read_text(encoding="utf-8")
    assert (Path(first["backup"]) / "Net.lua").read_bytes() == original
    second = install()
    assert first["net_after"] == second["net_after"]
    assert len(second["previous"]) == len(second["files"])
    restore(addons, Path(second["backup"]))
    texture = next((addons / "BattlemonBattles/Textures").glob("*.tga"))
    intact = texture.read_bytes()
    texture.write_bytes(b"modified")
    try:
        restore(addons, Path(first["backup"]))
    except ValueError:
        pass
    else:
        raise AssertionError("Modified texture was overwritten")
    assert digest(net) == first["net_after"]
    texture.write_bytes(intact)
    restore(addons, Path(first["backup"]))
    assert net.read_bytes() == original
    assert not (addons / "BattlemonBattles/BattlemonBattles.toc").exists()
    net.write_text("unrecognized routing", encoding="utf-8")
    failed = subprocess.run([sys.executable, str(ROOT / "tools/install_addon.py"), str(addons)], capture_output=True)
    assert failed.returncode != 0
    assert net.read_text(encoding="utf-8") == "unrecognized routing"
print("PASS: backup, idempotent install, owned restore, tamper refusal, unknown base rejection")
