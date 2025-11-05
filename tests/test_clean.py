# tests/test_clean.py

import os
from tests.helpers import MRFTestCase
from mrf_apps import mrf_clean

class TestMRFClean(MRFTestCase):
    def test_mrf_clean_copy(self):
        """Test the 'copy' mode of mrf_clean.py."""
        source_base = os.path.join(self.test_dir, "source")
        dest_base = os.path.join(self.test_dir, "dest")
        
        tile1, tile2 = b'\x01' * 10, b'\x02' * 20
        self.create_mock_data(source_base + ".dat", [tile1, b'\x00' * 5, tile2])
        self.create_mock_idx(source_base + ".idx", [(0, 10), (15, 20)])
        
        mrf_clean.mrf_clean(source_base + ".dat", dest_base + ".dat")
        
        self.assertEqual(os.path.getsize(dest_base + ".dat"), 30)
        with open(dest_base + ".dat", "rb") as f:
            self.assertEqual(f.read(), tile1 + tile2)
            
        new_idx = self.read_idx_file(dest_base + ".idx")
        self.assertEqual(new_idx, [(0, 10), (10, 20)])

    def test_mrf_clean_trim(self):
        """Test the 'trim' in-place mode of mrf_clean.py."""
        source_base = os.path.join(self.test_dir, "source")
        
        self.create_mock_data(source_base + ".dat", [b'\x01' * 10, b'\x00' * 5, b'\x02' * 20])
        self.create_mock_idx(source_base + ".idx", [(0, 10), (15, 20)])
        
        class Args:
            source = source_base + ".dat"
            empty_file = 0
        
        mrf_clean.mrf_trim(Args())
        
        self.assertEqual(os.path.getsize(source_base + ".dat"), 30)
        new_idx = self.read_idx_file(source_base + ".idx")
        self.assertEqual(new_idx, [(0, 10), (10, 20)])
