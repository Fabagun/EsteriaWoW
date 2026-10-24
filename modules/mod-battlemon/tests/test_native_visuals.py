"""Guard visual-only delivery against broken or incompatible native DBC references."""
import copy,importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native',ROOT/'tools/native_visuals.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
class NativeVisualValidation(unittest.TestCase):
 def setUp(self):
  spell=[0]*234;spell[0]=133;spell[131]=67;spell[136]=1
  visual=[0]*32;visual[0]=67;visual[2]=38;visual[3]=286
  self.config={'spells':{'Fireball':133}}
  self.tables=[{133:(tuple(spell),b'\0Fireball\0','fixture')},{67:(tuple(visual),b'','fixture')},
   {38:((38,),b'','fixture'),286:((286,),b'','fixture')},{}]
 def run_validation(self,client=None,server=None):
  with patch.object(native,'table',side_effect=(client or self.tables)+(server or copy.deepcopy(self.tables))):
   return native.validate(self.config,Path('client'),Path('server'))
 def test_valid_visual(self):self.assertEqual(self.run_validation()[0]['kits'],[38,286])
 def test_missing_impact_kit(self):
  changed=copy.deepcopy(self.tables);del changed[2][286]
  with self.assertRaises(KeyError):self.run_validation(client=changed)
 def test_mismatched_client_server_visual(self):
  changed=copy.deepcopy(self.tables);r=list(changed[1][67][0]);r[3]=38;changed[1][67]=(tuple(r),b'','fixture')
  with self.assertRaisesRegex(ValueError,'visual mismatch'):self.run_validation(server=changed)
 def test_channel_requires_cleanup(self):
  changed=copy.deepcopy(self.tables);r=list(changed[0][133][0]);r[5]=4;changed[0][133]=(tuple(r),b'\0Fireball\0','fixture')
  with self.assertRaisesRegex(ValueError,'Channeled'):self.run_validation(client=changed)
 def test_generated_header_matches_reviewed_config(self):
  import json
  config=json.loads((ROOT/'data/native-visuals.json').read_text(encoding='utf-8'))
  self.assertEqual(native.header(config),(ROOT/'src/BattlemonNativeEffects.h').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
