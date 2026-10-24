"""Restore one companion addon installation, refusing modified or unrelated files."""
import argparse
import json
import shutil
from pathlib import Path
from install_addon import digest


def child(root, relative):
    path = (root / relative).resolve()
    if path == root or root not in path.parents:
        raise ValueError("Receipt path escaped its folder")
    return path


def restore(addons, backup):
    addons, backup = addons.resolve(), backup.resolve()
    receipt = json.loads((backup / "receipt.json").read_text(encoding="utf-8"))
    net = addons / "Battlemon/Core/Net.lua"
    target = (addons / "BattlemonBattles").resolve()
    if digest(net) != receipt["net_after"] or digest(backup / "Net.lua") != receipt["net_before"]:
        raise ValueError("Net.lua or its backup changed; nothing restored")
    changes = []
    for relative, expected in receipt["files"].items():
        dst = child(addons, relative)
        if target not in dst.parents or not dst.is_file() or digest(dst) != expected:
            raise ValueError("Companion file changed or escaped its folder; nothing restored")
        changes.append(dst)
    previous = []
    for relative, expected in receipt.get("previous", {}).items():
        src = child((backup / "BattlemonBattles").resolve(), relative)
        dst = child(target, relative)
        if not src.is_file() or digest(src) != expected:
            raise ValueError("Previous addon backup changed; nothing restored")
        if str(dst.relative_to(addons)) not in receipt["files"] and dst.exists() and digest(dst) != expected:
            raise ValueError("Unowned companion file changed; nothing restored")
        previous.append((src, dst))
    # All hashes and paths have passed before any mutation; no recursive deletion.
    shutil.copy2(backup / "Net.lua", net)
    previous_paths = {dst for _, dst in previous}
    for dst in changes:
        if dst not in previous_paths:
            dst.unlink()
    for src, dst in previous:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return {"restored": str(backup), "net_sha256": digest(net)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addons", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.addons, args.backup), indent=2))
