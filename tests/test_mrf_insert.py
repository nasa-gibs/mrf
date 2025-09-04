# tests/test_mrf_insert.py

import os
import shutil
import subprocess
import numpy as np
from tests.helpers import MRFTestCase

# The osgeo library is available inside the Docker container
try:
    from osgeo import gdal
except ImportError:
    gdal = None

class TestMRFInsert(MRFTestCase):
    """
    Test the mrf_insert utility, including base level patching,
    overview regeneration, and partial tile updates.
    """

    def _create_geotiff(self, path, width, height, bands, fill_value, geo_transform):
        """Helper function to create a georeferenced TIFF file."""
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(path, width, height, bands, gdal.GDT_Byte)
        dataset.SetGeoTransform(geo_transform)
        
        fill_array = np.full((height, width), fill_value, dtype=np.uint8)
        for i in range(1, bands + 1):
            band = dataset.GetRasterBand(i)
            band.WriteArray(fill_array)
        
        dataset = None # Close and save

    def setUp(self):
        """Extend setUp to skip all tests if dependencies are missing."""
        super().setUp()
        if not gdal:
            self.skipTest("GDAL Python bindings are not available.")
        if not shutil.which(self.mrf_insert_executable):
            self.skipTest(f"'{self.mrf_insert_executable}' executable not found in PATH.")

    def test_mrf_insert_simple_patch(self):
        """Test patching a small image into a larger MRF at the base resolution."""
        # Define file paths
        target_tiff_path = os.path.join(self.test_dir, "target.tif")
        source_tiff_path = os.path.join(self.test_dir, "source.tif")
        target_mrf_path = os.path.join(self.test_dir, "target.mrf")

        # Create a large target raster (1024x1024) filled with zeros
        self._create_geotiff(target_tiff_path, 1024, 1024, 1, 0, [0, 1, 0, 1024, 0, -1])

        # Create a smaller source raster (512x512) filled with 255
        # Place it in the top-left corner of the target
        self._create_geotiff(source_tiff_path, 512, 512, 1, 255, [0, 1, 0, 1024, 0, -1])

        # Convert the target TIFF to an MRF
        gdal.Translate(target_mrf_path, target_tiff_path, options='-f MRF -co BLOCKSIZE=512')
        
        # Run the mrf_insert utility
        subprocess.run([self.mrf_insert_executable, source_tiff_path, target_mrf_path], check=True)
        
        # Verify the result
        result_ds = gdal.Open(target_mrf_path)
        result_band = result_ds.GetRasterBand(1)
        
        # All values in the patched area should be 255
        data_patched = result_band.ReadAsArray(0, 0, 512, 512)
        self.assertTrue(np.all(data_patched == 255))
        
        # Check an un-patched area to ensure it's still zero
        data_unpatched = result_band.ReadAsArray(513, 513, 10, 10)
        self.assertTrue(np.all(data_unpatched == 0))
        
        result_ds = None

    def test_mrf_insert_with_overviews(self):
        """Test that inserting a patch correctly updates the MRF's overviews."""
        # ARRANGE: Create a large target MRF with pre-built overviews
        target_tiff_path = os.path.join(self.test_dir, "target_ov.tif")
        source_tiff_path = os.path.join(self.test_dir, "source_ov.tif")
        target_mrf_path = os.path.join(self.test_dir, "target_ov.mrf")

        self._create_geotiff(target_tiff_path, 2048, 2048, 1, 0, [0, 1, 0, 2048, 0, -1])
        # Insert a 512x512 patch of 255 into the second tile column, first row
        self._create_geotiff(source_tiff_path, 512, 512, 1, 255, [512, 1, 0, 2048, 0, -1])

        # Create an MRF with UNIFORM_SCALE to generate overview levels
        gdal.Translate(target_mrf_path, target_tiff_path, options='-f MRF -co BLOCKSIZE=512 -co UNIFORM_SCALE=2')

        # ACT: Run mrf_insert with the '-r' flag to trigger overview regeneration
        subprocess.run([self.mrf_insert_executable, "-r", "Avg", source_tiff_path, target_mrf_path], check=True)

        # ASSERT: Verify both the base level and the first overview level
        result_ds = gdal.Open(target_mrf_path)
        
        # 1. Verify base level (as in the simple test)
        base_band = result_ds.GetRasterBand(1)
        patched_base_data = base_band.ReadAsArray(512, 0, 512, 512)
        self.assertTrue(np.all(patched_base_data == 255), "Base level was not patched correctly.")

        # 2. Verify overview level
        self.assertEqual(base_band.GetOverviewCount(), 2, "MRF should have overviews.")
        ov_band = base_band.GetOverview(0) # First overview (2x downsampled)
        self.assertEqual(ov_band.XSize, 1024, "Overview width is incorrect.")
        
        # The 512x512 patch at (512,0) on the base becomes a 256x256 patch at (256,0) on the overview
        patched_ov_data = ov_band.ReadAsArray(256, 0, 256, 256)
        self.assertTrue(np.all(patched_ov_data == 255), "Overview level was not updated correctly.")

        unpatched_ov_data = ov_band.ReadAsArray(0, 0, 10, 10)
        self.assertTrue(np.all(unpatched_ov_data == 0), "Unpatched overview area was modified.")
        
        result_ds = None

    def test_mrf_insert_partial_tile_overlap(self):
        """Test inserting a source that only partially covers a target tile."""
        # ARRANGE: Create a target with one 512x512 tile filled with value 100
        target_tiff_path = os.path.join(self.test_dir, "target_partial.tif")
        source_tiff_path = os.path.join(self.test_dir, "source_partial.tif")
        target_mrf_path = os.path.join(self.test_dir, "target_partial.mrf")

        self._create_geotiff(target_tiff_path, 512, 512, 1, 100, [0, 1, 0, 512, 0, -1])
        
        # Create a 256x256 source to patch over the top-left quadrant of the target tile
        self._create_geotiff(source_tiff_path, 256, 256, 1, 255, [0, 1, 0, 512, 0, -1])

        gdal.Translate(target_mrf_path, target_tiff_path, options='-f MRF -co BLOCKSIZE=512')

        # ACT: Run mrf_insert
        subprocess.run([self.mrf_insert_executable, source_tiff_path, target_mrf_path], check=True)

        # ASSERT: Check that the single tile is a mix of old and new data
        result_ds = gdal.Open(target_mrf_path)
        result_band = result_ds.GetRasterBand(1)
        final_tile_data = result_band.ReadAsArray()
        
        # Top-left quadrant should be the new value (255)
        top_left = final_tile_data[0:256, 0:256]
        self.assertTrue(np.all(top_left == 255), "Top-left quadrant was not patched.")

        # Top-right quadrant should be the original value (100)
        top_right = final_tile_data[0:256, 256:512]
        self.assertTrue(np.all(top_right == 100), "Top-right quadrant was incorrectly modified.")
        
        # Bottom-left quadrant should be the original value (100)
        bottom_left = final_tile_data[256:512, 0:256]
        self.assertTrue(np.all(bottom_left == 100), "Bottom-left quadrant was incorrectly modified.")

        result_ds = None
