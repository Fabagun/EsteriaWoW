from pathlib import Path
import tempfile
import unittest

from tools.stage_esteria_inventory import ADDON, digest, stage


class StageInventory(unittest.TestCase):
    def test_additive_install_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = root / "client"
            (client / "Interface/AddOns").mkdir(parents=True)
            unrelated = client / "WowClientRetailVulkan.exe"
            unrelated.write_bytes(b"executable must remain unchanged")
            report = stage(root / "stage-one", client)
            target = Path(report["installed_addon"])
            self.assertFalse(report["executables_replaced"])
            self.assertFalse(report["database_changed"])
            self.assertEqual(unrelated.read_bytes(), b"executable must remain unchanged")
            self.assertEqual(digest(target / "EsteriaInventory.lua"), digest(ADDON / "EsteriaInventory.lua"))
            (target / "EsteriaInventory.lua").write_text("previous version", encoding="utf-8")
            report = stage(root / "stage-two", client)
            previous = Path(report["addon_backup"]) / "EsteriaInventory/EsteriaInventory.lua"
            self.assertEqual(previous.read_text(), "previous version")
            self.assertEqual(digest(target / "EsteriaInventory.lua"), digest(ADDON / "EsteriaInventory.lua"))

    def test_stage_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "stage"
            stage(out)
            with self.assertRaises(FileExistsError):
                stage(out)


if __name__ == "__main__":
    unittest.main()
