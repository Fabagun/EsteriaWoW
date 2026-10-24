import unittest
import numpy as np
from source_skinning import shader_weights, source_positions
from m2 import skin_positions


class SourceSkinningTests(unittest.TestCase):
    def test_four_strongest_stable_ties(self):
        self.assertEqual([b for b,w in shader_weights([(5,.1),(4,.2),(3,.2),(2,.2),(1,.2),(0,.1)])], [4,3,2,1])

    def test_threshold_and_empty_default(self):
        self.assertEqual(shader_weights([]), [(0,1.)])
        self.assertAlmostEqual(float(shader_weights([(0,.97)])[0][1]),1.,places=6)
        self.assertAlmostEqual(float(shader_weights([(0,.98)])[0][1]),.98,places=6)
        for links in [[(0,0)],[(0,-1)],[(0,float('nan'))]]:
            with self.assertRaises(ValueError):shader_weights(links)

    def test_homogeneous_projection_matches_normalized_four(self):
        vertices=np.array([[1.,2.,3.]])
        matrices=np.tile(np.eye(4),(2,5,1,1))
        matrices[1,:,0,3]=[0.,1.,2.,3.,100.]
        raw=[[(0,.3),(1,.3),(2,.2),(3,.18),(4,.02)]]
        expected=skin_positions(vertices,[[(b,w/.98) for b,w in raw[0][:4]]],matrices)
        actual=source_positions(vertices,raw,matrices)
        np.testing.assert_allclose(actual,expected,atol=1e-6)
        unlimited=skin_positions(vertices,raw,matrices)
        self.assertGreater(np.abs(unlimited-actual).max(),1.)

    def test_reference_detects_wrong_exported_influences(self):
        vertices=np.array([[0.,0.,0.]])
        matrices=np.tile(np.eye(4),(1,5,1,1));matrices[0,4,2,3]=20
        raw=[[(0,.3),(1,.3),(2,.2),(3,.15),(4,.05)]]
        wrong=skin_positions(vertices,[[(4,1.)]],matrices)
        self.assertGreater(np.abs(source_positions(vertices,raw,matrices)-wrong).max(),10)

if __name__=='__main__':unittest.main()
