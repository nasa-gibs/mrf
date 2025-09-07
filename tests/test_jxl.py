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

        # ARRANGE: Create mock MRF data and index files
        data_path = os.path.join(self.test_dir, "test.pjg")
        idx_path = os.path.join(self.test_dir, "test.idx")
        jxl_data_path = data_path + ".jxl"
        final_data_path = os.path.join(self.test_dir, "final.pjg")

        # Create some mock JPEG content and a simple index
        # A minimal valid JPEG file (1x1 pixel, grayscale)
        jpeg_content = b'\xff\xd8\xff\xdb\x00\x43\x00\x03\x02\x02\x02\x02\x02\x03\x02\x02\x02\x03\x03\x03\x03\x04\x06\x04\x04\x04\x04\x04\x08\x06\x06\x05\x06\x09\x08\x0a\x0a\x09\x08\x09\x09\x0a\x0c\x0f\x0c\x0a\x0b\x0e\x0b\x09\x09\x0d\x11\x0d\x0e\x0f\x10\x10\x11\x10\x0a\x0c\x12\x13\x12\x10\x13\x0f\x10\x10\x10\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x10\xff\xd9'
        self.create_mock_data(data_path, [jpeg_content])
        self.create_mock_idx(idx_path, [(0, len(jpeg_content))])

        # ACT: Convert MRF to JXL
        subprocess.run([self.jxl_executable, data_path], check=True)

        # ASSERT: Check that the JXL file was created and is smaller
        self.assertTrue(os.path.exists(jxl_data_path))
        self.assertLess(os.path.getsize(jxl_data_path), os.path.getsize(data_path),
                        "JXL file should be smaller than the original JPEG MRF data.")

        # ACT: Convert back to MRF/JFIF
        # The utility writes to <input>.jxl.jfif, so we need to rename
        subprocess.run([self.jxl_executable, "-r", jxl_data_path], check=True)
        os.rename(jxl_data_path + ".jfif", final_data_path)

        # ASSERT: The final data file should be identical to the original
        self.assertTrue(filecmp.cmp(data_path, final_data_path, shallow=False),
                        "Round-trip conversion of MRF data file failed.")

    def test_jxl_single_file_round_trip(self):
        """Test round-trip conversion for a single JPEG file using the -s flag."""
        if not shutil.which(self.jxl_executable):
            self.skipTest(f"'{self.jxl_executable}' executable not found in PATH.")

        # ARRANGE: Create a mock single JPEG file
        jpeg_path = os.path.join(self.test_dir, "single.jpg")
        jxl_path = jpeg_path + ".jxl"
        final_jpeg_path = os.path.join(self.test_dir, "final_single.jpg")

        jpeg_content = b'\xff\xd8\xff\xdb\x00\x43\x00\x03\x02\x02\x02\x02\x02\x03\x02\x02\x02\x03\x03\x03\x03\x04\x06\x04\x04\x04\x04\x04\x08\x06\x06\x05\x06\x09\x08\x0a\x0a\x09\x08\x09\x09\x0a\x0c\x0f\x0c\x0a\x0b\x0e\x0b\x09\x09\x0d\x11\x0d\x0e\x0f\x10\x10\x11\x10\x0a\x0c\x12\x13\x12\x10\x13\x0f\x10\x10\x10\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x10\xff\xd9'
        with open(jpeg_path, 'wb') as f:
            f.write(jpeg_content)

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
        self.skipTest("Skipping bundle test: Creating a mock Esri bundle is non-trivial and not yet implemented.")
