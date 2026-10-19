"""Install a verified matched satchel package after explicitly authorized native builds.

Replace the worldserver binary in its existing container to preserve its environment,
mounts, container identity and shared-network sidecars. The built image remains the
Compose master image for future recreations. Never roll back after players create
satchels without first handling their stored items.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tarfile

from cars_mount_pack import DLL_DEFAULT, Storm
from esteria_satchel import ARCHIVE, ITEM, effective

ROOT = Path(__file__).resolve().parents[1]
CLIENT = Path("G:/3.3.5a - Dev")
DECOMP = ROOT.parent / "wowdecomp"
SERVER_BIN = "/azerothcore/env/dist/bin/worldserver"


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace", **kwargs).strip()


def sql(query, database="world"):
    return subprocess.run(["docker", "exec", "-i", "ac-database", "sh", "-c",
                           'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --skip-column-names '
                           + "acore_" + database], input=query, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout.strip()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def atomic_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".satchel-next")
    if temporary.exists():
        raise FileExistsError(temporary)
    shutil.copy2(source, temporary)
    assert digest(temporary) == digest(source)
    os.replace(temporary, target)


def copy_server_binary(source):
    # tar preserves executable permissions and ownership across the Windows host.
    archive = source.with_suffix(".install.tar")
    def permissions(info):
        info.mode, info.uid, info.gid = 0o755, 1000, 1000
        info.uname = info.gname = "acore"
        return info
    with tarfile.open(archive, "w") as output:
        output.add(source, arcname="worldserver", filter=permissions)
    with archive.open("rb") as stream:
        subprocess.run(["docker", "cp", "-", "ac-worldserver:/azerothcore/env/dist/bin"],
                       stdin=stream, check=True, capture_output=True)
    archive.unlink()


def install(stage):
    report = json.loads((stage / "report.json").read_text())
    builds = json.loads((stage / "build-receipt.json").read_text())
    baseline = json.loads((stage / "server-baseline.json").read_text())
    assert builds["client_exit"] == builds["server_exit"] == 0
    assert baseline["updates_disabled"]
    current_container = json.loads(command("docker", "inspect", "ac-worldserver"))[0]
    assert current_container["Image"] == baseline["image"]
    assert "AC_UPDATES_ENABLE_DATABASES=0" in current_container["Config"]["Env"]
    assert command("docker", "image", "inspect", "acore/ac-wotlk-worldserver:master", "--format", "{{.Id}}") \
        == builds["server_image"]
    assert digest(CLIENT / "WowClientRetailVulkan.exe") == report["client_executable_baseline_sha256"]
    processes = command("powershell", "-NoProfile", "-Command",
                        "Get-Process -ErrorAction SilentlyContinue | Where-Object { "
                        "$_.ProcessName -match '^(Wow|WowClientRetail.*)$' } | Select-Object -ExpandProperty Path")
    assert not any(line.startswith(str(CLIENT)) for line in processes.splitlines()), "Close the game client first"
    assert sql(f"SELECT entry FROM item_template WHERE entry={ITEM};") == "", "Item allocation changed"
    assert sql(f"SELECT ID FROM item_dbc WHERE ID={ITEM};") == "", "DBC allocation changed"
    migration = stage / report["migration"]
    assert migration.read_bytes() == (ROOT / "data/sql/updates/pending_db_world" / migration.name).read_bytes()
    assert sql(f"SELECT name FROM updates WHERE name='{migration.name}';") == ""
    storm = Storm(DLL_DEFAULT)
    data, _, _ = effective(storm, CLIENT, "DBFilesClient/Item.dbc")
    assert hashlib.sha256(data).hexdigest() == report["item_baseline"]["sha256"]
    for entry in report["dragonui"]:
        assert digest(CLIENT / entry["relative"]) == entry["baseline_sha256"]
    assert digest(stage / ARCHIVE) == report["archive_sha256"]
    expected_interface = {name.replace("\\", "/"): expected for name, expected in report["entries"].items()
                          if name.replace("\\", "/").startswith("Interface/")}
    actual_interface = {str(path.relative_to(stage / "client")).replace("\\", "/"): digest(path)
                        for path in (stage / "client/Interface").rglob("*") if path.is_file()}
    assert actual_interface == expected_interface, "Loose addon files differ from the verified package"
    binary = stage / "worldserver"
    assert digest(binary) == builds["server_binary_sha256"]
    exe = Path(builds["client_executable"])
    assert digest(exe) == builds["client_sha256"]
    layout = json.loads((DECOMP / "build/retail-satchel/generated/limits/limits.json").read_text())
    assert (layout["container_dwords"], layout["quest_slots"], layout["max_class_id"]) == (574, 25, 32)
    # Preserve every service identity; only worldserver is stopped/restarted.
    service_ids = dict(line.split("\t") for line in command("docker", "ps", "--format",
                                                            "{{.Names}}\t{{.ID}}").splitlines())
    sources = {str(p.relative_to(stage / "client")).replace("\\", "/"): p
               for p in (stage / "client/Interface").rglob("*") if p.is_file()}
    sources["Data/" + ARCHIVE] = stage / ARCHIVE
    sources["WowClientRetailVulkan.exe"] = exe
    backup = CLIENT / "_backups" / ("satchel-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    backup.mkdir(parents=True)
    plan = {"backup": str(backup), "before": {}, "after": {}, "prior_image": baseline["image"],
            "server_image": builds["server_image"], "service_ids": service_ids, "migration": migration.name}
    for relative, source in sources.items():
        target = CLIENT / relative
        plan["before"][relative] = digest(target) if target.exists() else None
        plan["after"][relative] = digest(source)
        if target.exists():
            saved = backup / "client" / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            assert digest(saved) == plan["before"][relative]
    manifest = CLIENT / "WowClientRetailVulkan.build.json"
    shutil.copy2(manifest, backup / manifest.name)
    command("docker", "cp", "ac-worldserver:" + SERVER_BIN, str(backup / "worldserver"))
    plan["prior_server_sha256"] = digest(backup / "worldserver")
    save(stage / "install-plan.json", plan)
    save(backup / "install-plan.json", plan)
    print("Verified backups:", backup, flush=True)
    committed = False
    migration_attempted = False
    receipt = hashlib.sha1(migration.read_bytes()).hexdigest().upper()
    try:
        print("Stopping only ac-worldserver", flush=True)
        command("docker", "stop", "--time", "60", "ac-worldserver")
        for relative, source in sources.items():
            atomic_copy(source, CLIENT / relative)
        copy_server_binary(binary)
        migration_attempted = True
        sql("START TRANSACTION;\n" + migration.read_text() +
            f"\nINSERT INTO updates (name,hash,state) VALUES ('{migration.name}','{receipt}','PENDING');\nCOMMIT;")
        committed = True
        metadata = json.loads(manifest.read_text())
        metadata.update(source_executable=str(exe), extended_limits=True, container_slots=254,
                        quest_log_slots=25, max_classes=32, satchel_slots=237, satchel_item=ITEM,
                        sha256=builds["client_sha256"], previous_sha256=plan["before"]["WowClientRetailVulkan.exe"],
                        staged_at_utc=datetime.now(timezone.utc).isoformat(), backup=str(backup),
                        build_log=str(DECOMP / "build/retail-satchel-build.log"),
                        verification=("Matched native client/core builds; layout and archive read-back verified; "
                                      "live acceptance pending"))
        save(manifest, metadata)
        command("docker", "start", "ac-worldserver")
        print("Installed matched binaries, UI, artwork and item; worldserver starting", flush=True)
    except Exception:
        # No game session can have created satchels while the worldserver was stopped.
        running = command("docker", "inspect", "ac-worldserver", "--format", "{{.State.Running}}")
        if running == "true":
            command("docker", "stop", "--time", "60", "ac-worldserver")
        if migration_attempted:
            # Reconcile a lost COMMIT response before restoring the smaller old runtime.
            stored_receipt = sql(f"SELECT hash FROM updates WHERE name='{migration.name}';")
            assert stored_receipt in ("", receipt), "Unexpected migration receipt; keep worldserver stopped"
            committed = stored_receipt == receipt
        if committed:
            assert sql(f"SELECT COUNT(*) FROM item_instance WHERE itemEntry={ITEM};", "characters") == "0"
            sql(f"START TRANSACTION; DELETE FROM item_template WHERE entry={ITEM}; "
                f"DELETE FROM item_dbc WHERE ID={ITEM}; DELETE FROM updates WHERE name='{migration.name}'; COMMIT;")
        for relative, prior in plan["before"].items():
            target = CLIENT / relative
            if prior is not None:
                atomic_copy(backup / "client" / relative, target)
            elif target.exists():
                assert target.is_relative_to(CLIENT)
                target.unlink()
        atomic_copy(backup / manifest.name, manifest)
        copy_server_binary(backup / "worldserver")
        command("docker", "tag", plan["prior_image"], "acore/ac-wotlk-worldserver:master")
        command("docker", "start", "ac-worldserver")
        plan["status"] = "installation_failed_rolled_back_files_sql_binary"
        save(stage / "last-install.json", plan)
        raise
    plan.update(status="installed_starting", client_sha256=builds["client_sha256"],
                server_binary_sha256=builds["server_binary_sha256"], migration_hash=receipt, live_accepted=False)
    save(stage / "last-install.json", plan)
    save(backup / "install-report.json", plan)


def verify(stage):
    report = json.loads((stage / "report.json").read_text())
    plan = json.loads((stage / "last-install.json").read_text())
    for relative, expected in plan["after"].items():
        assert digest(CLIENT / relative) == expected, relative
    assert command("docker", "exec", "ac-worldserver", "sha256sum", SERVER_BIN).split()[0] \
        == plan["server_binary_sha256"]
    current = json.loads(command("docker", "inspect", "ac-worldserver"))[0]
    assert current["State"]["Running"]
    assert "AC_UPDATES_ENABLE_DATABASES=0" in current["Config"]["Env"]
    ids = dict(line.split("\t") for line in command("docker", "ps", "--format", "{{.Names}}\t{{.ID}}").splitlines())
    assert all(ids.get(name) == identifier for name, identifier in plan["service_ids"].items())
    assert sql(f"SELECT name,ContainerSlots,displayid,InventoryType FROM item_template WHERE entry={ITEM};") \
        == "Esteria Grand Satchel\t237\t64151\t18"
    assert sql(f"SELECT ClassID,DisplayInfoID,InventoryType FROM item_dbc WHERE ID={ITEM};") == "1\t64151\t18"
    assert sql(f"SELECT hash FROM updates WHERE name='{plan['migration']}';") == plan["migration_hash"]
    with socket.create_connection(("127.0.0.1", 8085), timeout=5) as connection:
        header = b""
        while len(header) < 4:
            block = connection.recv(4 - len(header))
            assert block
            header += block
        assert struct.unpack_from("<H", header, 2)[0] == 0x1EC
    plan["status"] = "installed_and_worldserver_ready_live_acceptance_pending"
    report.update(status=plan["status"], installed=True, client_built=True, server_built=True,
                  live_accepted=False, backup=plan["backup"])
    save(stage / "last-install.json", plan)
    save(stage / "report.json", report)
    save(Path(plan["backup"]) / "install-report.json", plan)
    print("Verified file/binary hashes, item237, DBC metadata, update receipt, unchanged service IDs, game handshake")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "verify"))
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    (install if args.action == "install" else verify)(args.stage)
