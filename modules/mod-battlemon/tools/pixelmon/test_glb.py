"""Meaningful malformed-file and material regressions for the isolated GLB candidate."""
import json,struct,tempfile,unittest
from pathlib import Path
import numpy as np
from glb_source import GLB,decompose
from validate import read_model,array
MODULE = next(p for p in Path(__file__).resolve().parents if (p/'PIXELMON-RECOVERY.md').is_file())
ROOT = MODULE/'generated/grouped-glb'
SOURCE=Path(r'F:/_d-bak/_other/Pixelmon-1.21.1-9.4.0-universal/assets/pixelmon/textures/pokemon/491_darkrai/all/mega/none/megadarkrai.glb')

class GLBTests(unittest.TestCase):
    def test_real_shear_rejected(self):
        transform=np.eye(4);transform[0,1]=.05
        with self.assertRaisesRegex(ValueError,'shear'):decompose(transform)

    def test_nonuniform_scale_retained(self):
        transform=np.eye(4);transform[:3,:3]=np.diag([.11,2.57,1.4])
        _,_,scale=decompose(transform)
        np.testing.assert_allclose(scale,[.11,2.57,1.4])

    def test_source_step_channel_preserved(self):
        g=GLB(SOURCE);a=next(a for a in g.data['animations'] if a['name']=='idle')
        c=next(c for c in a['channels'] if c['target']=={'node':103,'path':'translation'})
        sampler=a['samplers'][c['sampler']]
        self.assertEqual(sampler['interpolation'],'STEP')
        times=g.accessor(sampler['input']).ravel();values=g.accessor(sampler['output'])
        for i in [0,len(times)//2,len(times)-2]:
            np.testing.assert_allclose(g.local_trs(a,float((times[i]+times[i+1])/2))[0][103],values[i],atol=0,rtol=0)

    def mutated_model(self,edit):
        source=ROOT/'candidate/megadarkrai_none.m2'
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory)/source.name;data=bytearray(source.read_bytes());edit(data)
            target.write_bytes(data)
            target.with_name(target.stem+'00.skin').write_bytes(source.with_name(source.stem+'00.skin').read_bytes())
            return read_model(target,texture_policy='source_alpha_emissive_twosided',skeleton_policy='glb_hierarchical_trs')

    def test_parent_cycle_rejected(self):
        def edit(data):
            _,off=array(data,0x2c,88);struct.pack_into('<h',data,off+8,0)
        with self.assertRaisesRegex(ValueError,'parent'):self.mutated_model(edit)

    def test_one_sided_material_rejected(self):
        def edit(data):
            _,off=array(data,0x70,4);struct.pack_into('<H',data,off,0)
        with self.assertRaisesRegex(ValueError,'materials'):self.mutated_model(edit)

    def test_missing_scale_track_rejected(self):
        def edit(data):
            _,off=array(data,0x2c,88);struct.pack_into('<II',data,off+60,0,0)
        with self.assertRaisesRegex(ValueError,'scale'):self.mutated_model(edit)

if __name__=='__main__':unittest.main()
