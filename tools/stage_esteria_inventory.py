"""Stage the digital inventory addon, migration, config and manifest; optionally install loose addon files.

This does not build, change SQL data, enable the server feature or replace any executable.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "client-customization/EsteriaInventory"
MIGRATION = ROOT / "data/sql/updates/pending_db_characters/rev_20261018030000000_digital_inventory.sql"
CONFIG = ROOT / "conf/dist/digital_inventory.conf.dist"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(out: Path, client: Path | None = None) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    staged = out / "client/Interface/AddOns/EsteriaInventory"
    shutil.copytree(ADDON, staged)
    shutil.copy2(MIGRATION, out / MIGRATION.name)
    shutil.copy2(CONFIG, out / CONFIG.name)
    report = {
        "status": "staged source payload; consult validation.json for native checks; in-game acceptance pending",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "server_feature_enabled": False,
        "executables_replaced": False,
        "database_changed": False,
        "source_core": str(ROOT),
        "source_client_extension": str(ROOT.parent / "wowdecomp/Extensions/DigitalInventory"),
        "files": {str(p.relative_to(out)): digest(p) for p in out.rglob("*") if p.is_file()},
    }
    if client is not None:
        client = client.resolve(strict=True)
        addons = (client / "Interface/AddOns").resolve(strict=True)
        if not addons.is_relative_to(client):
            raise ValueError("Addon path must remain within the requested client")
        target = addons / "EsteriaInventory"
        if not target.resolve().is_relative_to(addons):
            raise ValueError("Addon target must remain within the requested AddOns directory")
        if target.exists():
            backup = client / "_backups" / ("digital-inventory-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
            if not backup.resolve().is_relative_to(client):
                raise ValueError("Backup path must remain within the requested client")
            backup.mkdir(parents=True, exist_ok=False)
            shutil.copytree(target, backup / "EsteriaInventory")
            report["addon_backup"] = str(backup)
        target.mkdir(exist_ok=True)
        for source in staged.iterdir():
            shutil.copy2(source, target / source.name)
            if digest(source) != digest(target / source.name):
                raise RuntimeError(f"Addon verification failed: {source.name}")
        report["installed_addon"] = str(target)
        report["installed_files"] = {p.name: digest(p) for p in target.iterdir() if p.is_file()}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--install-addon", type=Path, metavar="CLIENT_ROOT")
    args = parser.parse_args()
    report = stage(args.out, args.install_addon)
    print(json.dumps({"stage": str(args.out.resolve()), "status": report["status"],
                      "installed_addon": report.get("installed_addon")}, indent=2))
