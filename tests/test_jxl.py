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
        jpeg_content = (
    	   b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
           b'\xff\xdb\x00C\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
     	   b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
    	   b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
           b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
           b'\x01\x01\x01\x01\x01\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03'
           b'\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01'
           b'\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00'
           b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10'
           b'\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}'
           b'\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81'
           b'\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18'
           b'\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
           b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98'
           b'\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5'
           b'\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2'
           b'\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7'
           b'\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda'
           b'\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfd\xc3\xff\xd9'
        )
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
        jpeg_content = (
           b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
           b'\xff\xdb\x00C\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
           b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
           b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
           b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
           b'\x01\x01\x01\x01\x01\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03'
           b'\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01'
           b'\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00'
           b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10'
           b'\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}'
           b'\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81'
           b'\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18'
           b'\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
           b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98'
           b'\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5'
           b'\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2'
           b'\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7'
           b'\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda'
           b'\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfd\xc3\xff\xd9'
        )

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
