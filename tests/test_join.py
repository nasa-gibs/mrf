# tests/test_join.py

import os
from tests.helpers import MRFTestCase
from mrf_apps import mrf_join

class TestMRFJoin(MRFTestCase):
    def test_mrf_join_simple(self):
        """Test simple concatenation of two MRFs with mrf_join.py."""
        input1_base = os.path.join(self.test_dir, "in1")
        input2_base = os.path.join(self.test_dir, "in2")
        output_base = os.path.join(self.test_dir, "out")
        
        # Create two simple MRFs
        # Note: We are creating an MRF with space for TWO tiles.
        
        # Input 1 provides data for the FIRST tile and leaves the second empty.
        self.create_mock_mrf_xml(input1_base + ".mrf", xsize=1024) # 2 tiles wide
        self.create_mock_data(input1_base + ".dat", [b'A'*10])
        self.create_mock_idx(input1_base + ".idx", [(0, 10), (0, 0)]) # Tile 1 has data, Tile 2 is empty

        # Input 2 provides data for the SECOND tile and leaves the first empty.
        self.create_mock_mrf_xml(input2_base + ".mrf", xsize=1024) # 2 tiles wide
        self.create_mock_data(input2_base + ".dat", [b'B'*20])
        self.create_mock_idx(input2_base + ".idx", [(0, 0), (0, 20)]) # Tile 1 is empty, Tile 2 has data
        
        # Run the join script
        argv = [input1_base + ".dat", input2_base + ".dat", output_base + ".dat"]
        mrf_join.mrf_join(argv)
        
        # Verify the results
        # The data file should contain the concatenated tile data
        with open(output_base + ".dat", "rb") as f:
            self.assertEqual(f.read(), b'A'*10 + b'B'*20)
            
        # The final index should now correctly contain both tile entries
        final_idx = self.read_idx_file(output_base + ".idx")
        self.assertEqual(final_idx, [(0, 10), (10, 20)])
