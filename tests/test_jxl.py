import os
import shutil
import subprocess
import filecmp
from tests.helpers import MRFTestCase

class TestJXLUtility(MRFTestCase):
    """
    Tests for the jxl utility which converts between JFIF-JPEG and JPEG-XL (brunsli).
    """

    def setUp(self):
        """Extend setUp to define the jxl executable path."""
        super().setUp()
        self.jxl_executable = "jxl"

    def test_jxl_mrf_round_trip(self):
        """Test round-trip conversion for an MRF data/index file pair."""
        if not shutil.which(self.jxl_executable):
            self.skipTest(f"'{self.jxl_executable}' executable not found in PATH.")

        # ARRANGE: Create mock MRF files and a path for a backup of the original
        data_path = os.path.join(self.test_dir, "test.pjg")
        idx_path = os.path.join(self.test_dir, "test.idx")
        jxl_data_path = data_path + ".jxl"
        original_data_backup_path = os.path.join(self.test_dir, "original.pjg")

        # Generate the initial JPEG file and its index
        self.create_mock_jpeg(data_path, size=(32, 32), color='blue')
        jpeg_size = os.path.getsize(data_path)
        self.create_mock_idx(idx_path, [(0, jpeg_size)])

        # Back up the original file for the final comparison
        shutil.copy(data_path, original_data_backup_path)

        # ACT: Convert MRF to JXL
        subprocess.run([self.jxl_executable, data_path], check=True)

        # ASSERT: Check that the JXL file was created and is smaller
        self.assertTrue(os.path.exists(jxl_data_path))
        self.assertLess(os.path.getsize(jxl_data_path), jpeg_size,
                        "JXL file should be smaller than the original JPEG MRF data.")

        # ACT: Convert back to MRF/JFIF. This will overwrite the original data_path file.
        subprocess.run([self.jxl_executable, "-r", jxl_data_path], check=True)

        # ASSERT: The overwritten data file should be identical to our backup of the original
        self.assertTrue(filecmp.cmp(original_data_backup_path, data_path, shallow=False),
                        "Round-trip conversion of MRF data file failed.")

    def test_jxl_single_file_round_trip(self):
        """Test round-trip conversion for a single JPEG file using the -s flag."""
        if not shutil.which(self.jxl_executable):
            self.skipTest(f"'{self.jxl_executable}' executable not found in PATH.")

        # ARRANGE: Create a mock single JPEG file
        jpeg_path = os.path.join(self.test_dir, "single.jpg")
        jxl_path = jpeg_path + ".jxl"
        final_jpeg_path = os.path.join(self.test_dir, "final_single.jpg")
        self.create_mock_jpeg(jpeg_path)

        # ACT: Convert JPEG to JXL in single file mode
        subprocess.run([self.jxl_executable, "-s", jpeg_path], check=True)

        # ASSERT: Check that the JXL file exists
        self.assertTrue(os.path.exists(jxl_path))

        # ACT: Convert back to JPEG
        subprocess.run([self.jxl_executable, "-s", "-r", jxl_path], check=True)
        os.rename(jxl_path + ".jfif", final_jpeg_path)

        # ASSERT: The final file should be identical to the original
        self.assertTrue(filecmp.cmp(jpeg_path, final_jpeg_path, shallow=False),
                        "Round-trip conversion of single JPEG file failed.")
    def test_jxl_bundle_mode(self):
        """Placeholder test for Esri bundle conversion."""
        self.skipTest("Skipping bundle test: Creating a mock Esri bundle is not yet implemented.")
