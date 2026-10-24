import unittest
from bone_binding import check_duplicate_names


class DuplicateBoneTests(unittest.TestCase):
    def test_unused_duplicate_leaf_does_not_change_weighted_binding(self):
        self.assertEqual(check_duplicate_names([('root',-1),('Hat',0),('Hat',0)],
                         [('root',-1),('Hat',0)],[[(1,1.)]]),['unweighted_duplicate_leaf_or_branch:Hat'])

    def test_duplicate_ancestor_of_weighted_bone_is_ambiguous(self):
        with self.assertRaisesRegex(ValueError,'weighted'):
            check_duplicate_names([('root',-1),('Hat',0),('Hat',0),('child',2)],
                                  [('root',-1),('Hat',0),('child',1)],[[(1,.8),(3,.2)]])

    def test_duplicate_animation_channels_always_remain_ambiguous(self):
        with self.assertRaisesRegex(ValueError,'animation'):
            check_duplicate_names([('root',-1)],[('root',-1),('root',-1)],[[(0,1.)]])

if __name__=='__main__':unittest.main()
