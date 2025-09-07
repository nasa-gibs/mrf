import os
import subprocess
import struct
from tests.helpers import MRFTestCase

class TestMRFReadData(MRFTestCase):
    """
    Tests for the mrf_read_data.py script, which extracts tile data.
    """

    def test_read_with_offset_and_size(self):
        """Test reading a data segment using direct offset and size."""
        # ARRANGE: Create a mock data file with three distinct parts
        data_path = os.path.join(self.test_dir, "test.dat")
        output_path = os.path.join(self.test_dir, "output.dat")
        
        part1 = b'START'
        part2 = b'MIDDLE_CHUNK'
        part3 = b'END'
        self.create_mock_data(data_path, [part1, part2, part3])

        # ACT: Run the script to extract the middle part
        offset = len(part1)
        size = len(part2)
        
        cmd = [
            "python3", "mrf_apps/mrf_read_data.py",
            "--input", data_path,
            "--output", output_path,
            "--offset", str(offset),
            "--size", str(size)
        ]
        # Hide the script's version printout for cleaner test logs
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)

        # ASSERT: The output file should contain only the middle part
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, 'rb') as f:
            content = f.read()
        self.assertEqual(content, part2)

    def test_read_with_index_and_tile(self):
        """Test reading a tile using an index file."""
        # ARRANGE: Create a data file and an index file pointing to tiles within it
        data_path = os.path.join(self.test_dir, "test.dat")
        idx_path = os.path.join(self.test_dir, "test.idx")
        output_path = os.path.join(self.test_dir, "output.dat")

        tile1_content = b'TILE_ONE_DATA'
        tile2_content = b'TILE_TWO_DATA'
        self.create_mock_data(data_path, [tile1_content, tile2_content])

        # Index records: (offset, size)
        # Tile 1 starts at offset 0
        # Tile 2 starts after tile 1
        idx_layout = [
            (0, len(tile1_content)),
            (len(tile1_content), len(tile2_content))
        ]
        self.create_mock_idx(idx_path, idx_layout)

        # ACT: Run the script to read the second tile (tile number is 1-based)
        cmd = [
            "python3", "mrf_apps/mrf_read_data.py",
            "--input", data_path,
            "--output", output_path,
            "--index", idx_path,
            "--tile", "2"
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)

        # ASSERT: The output file should contain the content of the second tile
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, 'rb') as f:
            content = f.read()
        self.assertEqual(content, tile2_content)

    def test_read_with_little_endian_index(self):
        """Test reading with a little-endian formatted index file."""
        # ARRANGE
        data_path = os.path.join(self.test_dir, "test.dat")
        idx_path = os.path.join(self.test_dir, "test.idx")
        output_path = os.path.join(self.test_dir, "output.dat")

        tile_content = b'LITTLE_ENDIAN_TEST'
        self.create_mock_data(data_path, [tile_content])
        
        # Create the index file using little-endian byte order ('<QQ')
        with open(idx_path, "wb") as f:
            f.write(struct.pack('<QQ', 0, len(tile_content)))

        # ACT: Run the script with the -l (--little-endian) flag
        cmd = [
            "python3", "mrf_apps/mrf_read_data.py",
            "--input", data_path,
            "--output", output_path,
            "--index", idx_path,
            "--tile", "1",
            "--little-endian"
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)

        # ASSERT: The output should correctly contain the tile data
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, 'rb') as f:
            content = f.read()
        self.assertEqual(content, tile_content)
