# tests/test_can.py

import os
import shutil
import subprocess
import struct
import filecmp
from tests.helpers import MRFTestCase

class TestCanUtility(MRFTestCase):
    def test_can_uncan_cycle(self):
        """Test that canning and uncanning an index file restores it perfectly."""
        if not shutil.which(self.can_executable):
            self.skipTest(f"'{self.can_executable}' executable not found in PATH.")

        idx_path = os.path.join(self.test_dir, "test.idx")
        can_path = os.path.join(self.test_dir, "test.ix")
        out_idx_path = os.path.join(self.test_dir, "test.out.idx")
        
        # Create a sparse index with data in the first and last blocks
        empty_block = b'\x00' * 512
        data_block = struct.pack('>QQ', 123, 456) * (512 // 16)
        with open(idx_path, 'wb') as f:
            f.write(data_block)
            for _ in range(94):
                f.write(empty_block)
            f.write(data_block)
            
        subprocess.run([self.can_executable, "-g", idx_path, can_path], check=True)
        self.assertLess(os.path.getsize(can_path), os.path.getsize(idx_path))
        
        subprocess.run([self.can_executable, "-u", "-g", can_path, out_idx_path], check=True)
        self.assertTrue(filecmp.cmp(idx_path, out_idx_path, shallow=False))
