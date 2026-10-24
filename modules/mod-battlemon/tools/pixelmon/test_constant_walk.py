import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from m2 import build_model
from source_motion import constant_walk_proof,validate_constant_walk
from test_skin_sections import fixture
from validate import read_model


class ConstantWalkTests(unittest.TestCase):
    def test_authored_constant_walk_does_not_freeze_idle(self):
        mesh=fixture()
        for s in mesh['sequences'][1:]: s['translations'][:]=0
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.m2';model,skin=build_model(mesh,'model','model.blp')
            p.write_bytes(model);p.with_name('model00.skin').write_bytes(skin)
            with self.assertRaisesRegex(ValueError,'Walk sequence is static'):read_model(p)
            decoded=read_model(p,source_motion='source_constant_walk')
            self.assertGreater(np.ptp(decoded['poses'][0],axis=0).max(),.005)
            self.assertEqual(np.ptp(decoded['poses'][1],axis=0).max(),0)

    def test_moving_export_cannot_use_constant_walk_policy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.m2';model,skin=build_model(fixture(),'model','model.blp')
            p.write_bytes(model);p.with_name('model00.skin').write_bytes(skin)
            with self.assertRaisesRegex(ValueError,'gained motion'):
                read_model(p,source_motion='source_constant_walk')

    def test_source_proof_rejects_changed_bytes_motion_or_unmatched_rigs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'model').write_bytes(b'model');(p/'walk').write_bytes(b'walk')
            appearance=dict(model=str(p/'model'),animations=dict(walk=str(p/'walk')))
            model=dict(bones=[('root',-1)],weights=[[(0,1.)]])
            animation=dict(bones=[('root',-1)],frames=np.zeros((2,1,6)))
            with patch('source_motion.read_bmd',side_effect=[model,animation]):
                proof=constant_walk_proof(appearance)
            (p/'walk').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):validate_constant_walk(proof)
            (p/'walk').write_bytes(b'walk');animation['frames'][1,0,0]=1
            with patch('source_motion.read_bmd',side_effect=[model,animation]):
                with self.assertRaisesRegex(ValueError,'actual motion'):validate_constant_walk(proof)
            animation['frames'][:]=0;animation['bones']=[('unrelated',-1)]
            with patch('source_motion.read_bmd',side_effect=[model,animation]):
                with self.assertRaisesRegex(ValueError,'weighted model bones'):validate_constant_walk(proof)

if __name__=='__main__':unittest.main()
