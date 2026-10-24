"""Exercise installation ownership, ID collision, tamper and partial-copy rollback."""
import importlib.util,json,tempfile,struct,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'tools/install_effects.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.package=self.root/'package';self.dest=self.root/'data/patch-z.mpq';m.PACKAGE=self.package
  paths=['client/Creature/BattlemonEffects/test.m2','client/DBFilesClient/CreatureDisplayInfo.dbc9-battlemon-effects']
  for name in paths:
   p=self.package/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture' if name.endswith('.m2') else b'WDBC'+struct.pack('<4I',1,1,4,1)+struct.pack('<I',310000)+b'\0')
  (self.package/'manifest.json').write_text(json.dumps(dict(files={n:m.sha(self.package/n) for n in paths},effects=[dict(id=310000)])))
 def tearDown(self):self.tmp.cleanup()
 def test_repeat_and_tamper(self):
  m.install(self.dest,'client');m.install(self.dest,'client');(self.dest/'Creature/BattlemonEffects/test.m2').write_bytes(b'tamper')
  with self.assertRaises(ValueError):m.install(self.dest,'client')
 def test_unowned(self):
  p=self.dest/'Creature/BattlemonEffects/test.m2';p.parent.mkdir(parents=True);p.write_bytes(b'fixture')
  with self.assertRaises(ValueError):m.install(self.dest,'client')
 def test_other_patch_collision(self):
  p=self.dest.parent/'patch-w.mpq/DBFilesClient/CreatureDisplayInfo.dbc9-else';p.parent.mkdir(parents=True);p.write_bytes((self.package/'client/DBFilesClient/CreatureDisplayInfo.dbc9-battlemon-effects').read_bytes())
  with self.assertRaises(ValueError):m.install(self.dest,'client')
 def test_partial_copy_rollback(self):
  original=m.shutil.copyfile;calls=[]
  def copy(a,b):
   calls.append(b)
   if len(calls)==2:raise OSError('simulated interruption')
   return original(a,b)
  with patch.object(m.shutil,'copyfile',copy):
   with self.assertRaises(OSError):m.install(self.dest,'client')
  self.assertFalse((self.dest/'Creature/BattlemonEffects/test.m2').exists())
  self.assertFalse((self.dest/'battlemon-effects-client-receipt.json').exists())
if __name__=='__main__':unittest.main()
