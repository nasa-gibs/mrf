# tests/test_join.py

import os
import shutil
from xml.etree import ElementTree as ET
from tests.helpers import MRFTestCase
from mrf_apps import mrf_join # Import the script to test its functions directly

class TestMRFJoin(MRFTestCase):

    def setUp(self):
        """Set up test environment by calling parent setUp."""
        super().setUp()
        # Mock class to simulate argparse Namespace object for direct function calls
        class MockArgs:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        self.MockArgs = MockArgs

    # Helper function to create MRFs for append tests
    def create_append_input(self, base_name, tile_data, index_layout, xsize=512):
        """Helper to create a single MRF for append tests."""
        self.create_mock_mrf_xml(base_name + ".mrf", xsize=xsize)
        self.create_mock_data(base_name + ".dat", tile_data)
        self.create_mock_idx(base_name + ".idx", index_layout)

    def test_mrf_join_simple_merge(self):
        """Test simple merge where inputs provide data for different tiles."""
        input1_base = os.path.join(self.test_dir, "in1")
        input2_base = os.path.join(self.test_dir, "in2")
        output_base = os.path.join(self.test_dir, "out")

        # Create two simple MRFs for a 2-tile image (xsize=1024, pagesize=512)
        # Input 1 provides data for the FIRST tile and leaves the second empty.
        tile1_data = [b'A' * 10]
        tile1_index = [(0, 10), (0, 0)] # Tile 1 has data, Tile 2 is empty
        self.create_mock_mrf_xml(input1_base + ".mrf", xsize=1024)
        self.create_mock_data(input1_base + ".dat", tile1_data)
        self.create_mock_idx(input1_base + ".idx", tile1_index)

        # Input 2 provides data for the SECOND tile and leaves the first empty.
        tile2_data = [b'B' * 20]
        tile2_index = [(0, 0), (0, 20)] # Tile 1 is empty, Tile 2 has data
        self.create_mock_mrf_xml(input2_base + ".mrf", xsize=1024)
        self.create_mock_data(input2_base + ".dat", tile2_data)
        self.create_mock_idx(input2_base + ".idx", tile2_index)

        # Run the join script in default mode
        argv = [input1_base + ".dat", input2_base + ".dat", output_base + ".dat"]
        mrf_join.mrf_join(argv)

        # Verify the results
        # 1. Data file should contain the concatenated tile data from both inputs
        with open(output_base + ".dat", "rb") as f:
            self.assertEqual(f.read(), b'A' * 10 + b'B' * 20)

        # 2. Final index should merge tile info from both inputs, updating offsets
        final_idx = self.read_idx_file(output_base + ".idx")
        # Tile 1 from input1: (offset=0, size=10)
        # Tile 2 from input2: offset_of_input2_data + tile2_offset = 10 + 0 = 10
        self.assertEqual(final_idx, [(0, 10), (10, 20)])

    def test_mrf_join_overwrite(self):
        """Test that later inputs overwrite tiles from earlier inputs."""
        input1_base = os.path.join(self.test_dir, "in1_overwrite")
        input2_base = os.path.join(self.test_dir, "in2_overwrite")
        output_base = os.path.join(self.test_dir, "out_overwrite")

        # Input 1 has data for tile 1: version 'A'
        tile_v1_data = [b'A_v1' * 10]
        tile_v1_index = [(0, 6)]
        self.create_mock_mrf_xml(input1_base + ".mrf", xsize=512)
        self.create_mock_data(input1_base + ".dat", tile_v1_data)
        self.create_mock_idx(input1_base + ".idx", tile_v1_index)

        # Input 2 also has data for tile 1: version 'B'
        tile_v2_data = [b'B_v2' * 20]
        tile_v2_index = [(0, 6)]
        self.create_mock_mrf_xml(input2_base + ".mrf", xsize=512)
        self.create_mock_data(input2_base + ".dat", tile_v2_data)
        self.create_mock_idx(input2_base + ".idx", tile_v2_index)

        # Run the join script in default mode
        argv = [input1_base + ".dat", input2_base + ".dat", output_base + ".dat"]
        mrf_join.mrf_join(argv)

        # Verify the results
        # 1. Data file contains data from both inputs. The data from input1 is now slack space.
        with open(output_base + ".dat", "rb") as f:
            self.assertEqual(f.read(), tile_v1_data[0] + tile_v2_data[0])

        # 2. Final index should point to the data from input2 (the last one processed)
        final_idx = self.read_idx_file(output_base + ".idx")
        # Offset calculation: len(input1_data) + offset_from_input2 = len(b'A_v1' * 10) + 0 = 6
        expected_offset = len(tile_v1_data[0])
        self.assertEqual(final_idx, [(expected_offset, 6)])

    def test_mrf_append_z_dimension(self):
        """Test stacking two 2D MRFs into one 3D MRF using append mode."""
        input1_base = os.path.join(self.test_dir, "in_z1")
        input2_base = os.path.join(self.test_dir, "in_z2")
        output_data_path = os.path.join(self.test_dir, "out_3d.dat")

        # Create input 1 (for slice 0)
        self.create_append_input(input1_base, [b'Slice1Data'], [(0, 10)])
        
        # Create input 2 (for slice 1)
        self.create_append_input(input2_base, [b'Slice2Data'], [(0, 10)])

        # Run mrf_append via main function simulation
        args = self.MockArgs(
            zsize=2,
            output=output_data_path,
            forceoffset=None,
            slice=0,
            fnames=[input1_base + ".dat", input2_base + ".dat"]
        )
        mrf_join.mrf_append(args.fnames, args.output, args.zsize, args.slice)

        # Verify results
        # 1. Data file check
        with open(output_data_path, "rb") as f:
            self.assertEqual(f.read(), b'Slice1Data' + b'Slice2Data')

        # 2. Index check: The index for a 2-slice MRF with 1 tile per slice
        #    should contain two records.
        final_idx = self.read_idx_file(os.path.join(self.test_dir, "out_3d.idx"))
        self.assertEqual(len(final_idx), 2)
        # Slice 0 (from input 1) offset = 0. Data size = 10.
        self.assertEqual(final_idx[0], (0, 10))
        # Slice 1 (from input 2) offset = len(Slice1Data) = 10. Data size = 10.
        self.assertEqual(final_idx[1], (10, 10))

        # 3. Metadata check: Verify the zsize attribute was added to the MRF XML.
        tree = ET.parse(os.path.join(self.test_dir, "out_3d.mrf"))
        size_node = tree.find("./Raster/Size")
        self.assertEqual(size_node.get('z'), '2')

    def test_mrf_append_with_overviews(self):
        """Test stacking MRFs that contain overviews to verify complex index layout."""
        # Setup: Create MRFs with overviews.
        # Image size: 1024x512 pixels. Tile size: 512x512 pixels.
        # Level 0 (base resolution) dimensions: 2x1 tiles = 2 tiles.
        # Overview Level 1 dimensions: ceil(2/2)xceil(1/2) = 1x1 tiles = 1 tile.
        # Total index records per slice = 2 + 1 = 3.
        
        input1_base = os.path.join(self.test_dir, "in_ov1")
        input2_base = os.path.join(self.test_dir, "in_ov2")
        output_data_path = os.path.join(self.test_dir, "out_3d_ov.dat")

        # Input 1 data: [L0T0, L0T1, L1T0] data. Offsets are 0, 10, 20. Sizes are 10, 10, 5.
        data1 = [b'A' * 10, b'B' * 10, b'C' * 5]
        index1 = [(0, 10), (10, 10), (20, 5)]
        self.create_append_input(input1_base, data1, index1, xsize=1024)

        # Input 2 data: [L0T0, L0T1, L1T0] data. Offsets are 0, 8, 16. Sizes are 8, 8, 4.
        data2 = [b'X' * 8, b'Y' * 8, b'Z' * 4]
        index2 = [(0, 8), (8, 8), (16, 4)]
        self.create_append_input(input2_base, data2, index2, xsize=1024)
        
        # Run append for 2 slices
        args = self.MockArgs(
            zsize=2,
            output=output_data_path,
            forceoffset=None,
            slice=0,
            fnames=[input1_base + ".dat", input2_base + ".dat"]
        )
        # Need to mock getmrfinfo to return correct overview structure
        # mrfinfo['pages'] = [pagecount_level_0, pagecount_level_1] = [2, 1]
        original_getmrfinfo = mrf_join.getmrfinfo
        def mock_getmrfinfo(fname, *args_):
            info, tree = original_getmrfinfo(fname)
            info['pages'] = [2, 1] # Override page count calculation: [L0 count, L1 count]
            info['totalpages'] = 3
            return info, tree
        mrf_join.getmrfinfo = mock_getmrfinfo

        mrf_join.mrf_append(args.fnames, args.output, args.zsize, args.slice)
        
        # Restore original function
        mrf_join.getmrfinfo = original_getmrfinfo

        # ASSERT: Verify interleaved index structure for 2 slices, 3 records per slice.
        final_idx = self.read_idx_file(os.path.join(self.test_dir, "out_3d_ov.idx"))
        self.assertEqual(len(final_idx), 6) # 2 slices * 3 records/slice

        # Expected index layout trace: [L0S0T0, L0S0T1, L0S1T0, L0S1T1, L1S0T0, L1S1T0]
        # Data offsets: Input 1 starts at 0. Input 2 starts at len(data1) = 10+10+5 = 25.
        
        # Slice 0 records (from input 1) with offsets relative to 0:
        expected_s0_l0t0 = index1[0] # (0, 10)
        expected_s0_l0t1 = index1[1] # (10, 10)
        expected_s0_l1t0 = index1[2] # (20, 5)

        # Slice 1 records (from input 2) with offsets relative to 25:
        data2_start_offset = sum(len(d) for d in data1) # 25
        expected_s1_l0t0 = (index2[0][0] + data2_start_offset, index2[0][1]) # (25, 8)
        expected_s1_l0t1 = (index2[1][0] + data2_start_offset, index2[1][1]) # (33, 8)
        expected_s1_l1t0 = (index2[2][0] + data2_start_offset, index2[2][1]) # (41, 4)

        # Verify interleaved records based on trace logic from mrf_join code review
        self.assertEqual(final_idx[0], expected_s0_l0t0) # L0S0T0
        self.assertEqual(final_idx[1], expected_s0_l0t1) # L0S0T1
        self.assertEqual(final_idx[2], expected_s1_l0t0) # L0S1T0
        self.assertEqual(final_idx[3], expected_s1_l0t1) # L0S1T1
        self.assertEqual(final_idx[4], expected_s0_l1t0) # L1S0T0
        self.assertEqual(final_idx[5], expected_s1_l1t0) # L1S1T0
