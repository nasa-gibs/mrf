import os
import subprocess
from tests.helpers import MRFTestCase

class TestTiles2MRF(MRFTestCase):
    """
    Tests for the tiles2mrf.py script, which assembles an MRF from individual tiles.
    """

    def _create_tile_files(self, template_dir, levels, sizes, content_char='A'):
        """Helper to create a directory structure of mock tile files."""
        char_code = ord(content_char)
        for z in range(levels):
            width, height = sizes[z]
            level_dir = os.path.join(template_dir, str(z))
            os.makedirs(level_dir, exist_ok=True)
            for y in range(height):
                for x in range(width):
                    tile_path = os.path.join(level_dir, f"{x}_{y}.ppg")
                    with open(tile_path, 'wb') as f:
                        # Use variable content size to better test offsets
                        f.write(bytes([char_code]) * (char_code - ord('A') + 1))
                    char_code += 1

    def test_simple_conversion(self):
        """Test assembling a single-level 2x2 MRF."""
        # ARRANGE: Create a 2x2 grid of tiles for one level
        template_dir = os.path.join(self.test_dir, "tiles")
        output_base = os.path.join(self.test_dir, "output")
        self._create_tile_files(template_dir, 1, [(2, 2)])

        # The script's template format is slightly different from os.path.join
        template = os.path.join(template_dir, "{z}", "{x}_{y}.ppg")
        
        # ACT: Run the script
        cmd = [
            "python3", "mrf_apps/tiles2mrf.py",
            "--levels", "1",
            "--width", "2",
            "--height", "2",
            template,
            output_base
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # ASSERT
        data_path = output_base + ".ppg"
        idx_path = output_base + ".idx"
        self.assertTrue(os.path.exists(data_path))
        self.assertTrue(os.path.exists(idx_path))

        # 1. Verify data file content is the concatenation of all tiles
        # Tiles content: A (1 byte), B (2 bytes), C (3 bytes), D (4 bytes)
        with open(data_path, 'rb') as f:
            content = f.read()
            self.assertEqual(content, b'A' + b'B'*2 + b'C'*3 + b'D'*4)

        # 2. Verify index file records
        # Tiles are processed z, y, x (level 0, row 0, col 0 -> col 1, etc.)
        # z=0 is highest res level in script logic (reversed list)
        idx_records = self.read_idx_file(idx_path)
        expected_idx = [
            (0, 1),  # Tile 0,0 (A)
            (1, 2),  # Tile 0,1 (B)
            (3, 3),  # Tile 1,0 (C)
            (6, 4),  # Tile 1,1 (D)
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0)
        ]
        self.assertEqual(idx_records, expected_idx)

    def test_with_overviews_and_padding(self):
        """Test a 2-level pyramid that requires index padding."""
        # ARRANGE
        # Level 0 (overview, z=0): 2x1 tiles
        # Level 1 (highest res, z=1): 3x2 tiles
        template_dir = os.path.join(self.test_dir, "tiles_ov")
        output_base = os.path.join(self.test_dir, "output_ov")
        self._create_tile_files(template_dir, 2, [(2, 1), (3, 2)])

        template = os.path.join(template_dir, "{z}", "{x}_{y}.ppg")

        # ACT
        cmd = [
            "python3", "mrf_apps/tiles2mrf.py",
            "--levels", "2",
            "--width",  "3",
            "--height", "2",
            template,
            output_base
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # ASSERT
        # Total tiles: 6 (z=1) + 2 (z=0) = 8. Data file should contain 8 tiles' data.
        # Padding: Level 0 is 2x1. To get to 1x1, one more logical level is needed.
        # The script pads the index to fill out this 2x1 level. Total pads = 2.
        # Expected index records = 8 data records + 2 padding records = 10.
        idx_records = self.read_idx_file(output_base + ".idx")
        self.assertEqual(len(idx_records), 10, "Index should contain 8 data records and 2 padding records.")

        # Check the padding records at the end
        self.assertEqual(idx_records[-2], (0, 0))
        self.assertEqual(idx_records[-1], (0, 0))

        # Verify the offset and size of the last data tile.
        # The script processes z=1 then z=0, so the last data tile is the
        # last tile of level 0 (tile "B", which is the 2nd tile created).
        total_data_size = sum(range(1, 9)) # Sum of sizes A(1) through H(8)
        last_data_tile = idx_records[7]    # The 8th data record corresponds to tile "B"

        # The size of tile "B" is 2 bytes
        self.assertEqual(last_data_tile[1], 2)
        # Its offset should be the total size minus its own size
        self.assertEqual(last_data_tile[0], total_data_size - 2)

    def test_blank_tile_handling(self):
        """Test that blank tiles are correctly identified and skipped."""
        # ARRANGE
        template_dir = os.path.join(self.test_dir, "tiles_blank")
        output_base = os.path.join(self.test_dir, "output_blank")
        blank_tile_path = os.path.join(self.test_dir, "blank.ppg")

        # Create a 2x1 grid
        os.makedirs(os.path.join(template_dir, "0"))
        with open(os.path.join(template_dir, "0", "0_0.ppg"), 'wb') as f:
            f.write(b'DATATILE')
        with open(os.path.join(template_dir, "0", "1_0.ppg"), 'wb') as f:
            f.write(b'BLANK')
        with open(blank_tile_path, 'wb') as f:
            f.write(b'BLANK')

        template = os.path.join(template_dir, "{z}", "{x}_{y}.ppg")

        # ACT
        cmd = [
            "python3", "mrf_apps/tiles2mrf.py",
            "--levels", "1",
            "--width",  "2",
            "--height", "1",
            "--blank-tile", blank_tile_path,
            template,
            output_base
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # ASSERT
        data_path = output_base + ".ppg"
        idx_path = output_base + ".idx"

        # 1. Data file should only contain the non-blank tile's data
        self.assertEqual(os.path.getsize(data_path), 8)
        with open(data_path, 'rb') as f:
            self.assertEqual(f.read(), b'DATATILE')

        # 2. Index should have one data record and one blank record
        idx_records = self.read_idx_file(idx_path)
        expected_idx = [
            (0, 8),      # Data tile at offset 0, size 8
            (0, 0),      # Blank tile
            (0, 0),
            (0, 0)
        ]
        self.assertEqual(idx_records, expected_idx)
