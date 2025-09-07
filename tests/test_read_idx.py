import os
import subprocess
import struct
from tests.helpers import MRFTestCase

class TestMRFReadIdx(MRFTestCase):
    """
    Tests for the mrf_read_idx.py script, which converts a binary .idx file to CSV.
    """

    def test_read_simple_index(self):
        """Test reading a standard (big-endian) index file."""
        # ARRANGE: Create a mock index file with a few records
        idx_path = os.path.join(self.test_dir, "test.idx")
        output_path = os.path.join(self.test_dir, "output.csv")
        
        # Three records: (offset, size)
        idx_layout = [
            (0, 100),
            (100, 250),
            (350, 12345)
        ]
        self.create_mock_idx(idx_path, idx_layout)

        # ACT: Run the script
        cmd = [
            "python3", "mrf_apps/mrf_read_idx.py",
            "--index", idx_path,
            "--output", output_path
        ]
        # Hide the script's version printout for cleaner test logs
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)

        # ASSERT: The output CSV should have the correct header and content
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, 'r') as f:
            lines = f.readlines()
        
        expected_lines = [
            "idx_offset,data_offset,data_size\n",
            "0,0,100\n",
            "16,100,250\n",
            "32,350,12345\n"
        ]
        self.assertEqual(lines, expected_lines)

    def test_read_little_endian_index(self):
        """Test reading an index file with little-endian byte order."""
        # ARRANGE
        idx_path = os.path.join(self.test_dir, "test_le.idx")
        output_path = os.path.join(self.test_dir, "output_le.csv")

        # Create the index file using little-endian byte order ('<q')
        with open(idx_path, "wb") as f:
            # Note: The script uses 'q' (signed long long), not 'Q' (unsigned)
            f.write(struct.pack('<qq', 1000, 2000))

        # ACT: Run the script with the -l (--little-endian) flag
        cmd = [
            "python3", "mrf_apps/mrf_read_idx.py",
            "--index", idx_path,
            "--output", output_path,
            "--little-endian"
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)

        # ASSERT: The output CSV should contain the correctly interpreted values
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, 'r') as f:
            lines = f.readlines()

        expected_lines = [
            "idx_offset,data_offset,data_size\n",
            "0,1000,2000\n"
        ]
        self.assertEqual(lines, expected_lines)
        
    def test_read_empty_index(self):
        """Test the script's behavior with an empty index file."""
        # ARRANGE: Create an empty index file
        idx_path = os.path.join(self.test_dir, "empty.idx")
        output_path = os.path.join(self.test_dir, "empty.csv")
        open(idx_path, 'w').close() # Create empty file

        # ACT: Run the script
        cmd = [
            "python3", "mrf_apps/mrf_read_idx.py",
            "--index", idx_path,
            "--output", output_path
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)

        # ASSERT: The output CSV should contain only the header
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, 'r') as f:
            lines = f.readlines()
        
        expected_lines = ["idx_offset,data_offset,data_size\n"]
        self.assertEqual(lines, expected_lines)
