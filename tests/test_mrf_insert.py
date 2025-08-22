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
    def test_mrf_insert_simple_patch(self):
        """Test patching a small image into a larger MRF."""
        if not gdal:
            self.skipTest("GDAL Python bindings are not available.")
            
        if not shutil.which(self.mrf_insert_executable):
            self.skipTest(f"'{self.mrf_insert_executable}' executable not found in PATH.")

        # Define file paths
        target_tiff_path = os.path.join(self.test_dir, "target.tif")
        source_tiff_path = os.path.join(self.test_dir, "source.tif")
        target_mrf_path = os.path.join(self.test_dir, "target.mrf")
        
        # Create a large target raster (1024x1024) filled with zeros
        driver = gdal.GetDriverByName('GTiff')
        target_ds = driver.Create(target_tiff_path, 1024, 1024, 1, gdal.GDT_Byte)
        target_band = target_ds.GetRasterBand(1)
        target_band.WriteArray(np.zeros((1024, 1024), dtype=np.uint8))
        target_ds.SetGeoTransform([0, 1, 0, 1024, 0, -1]) # Set geotransform for positioning
        target_ds = None # Close and save file

        # Create a smaller source raster (512x512) filled with 255
        source_ds = driver.Create(source_tiff_path, 512, 512, 1, gdal.GDT_Byte)
        source_band = source_ds.GetRasterBand(1)
        source_band.WriteArray(np.full((512, 512), 255, dtype=np.uint8))
        # Place it in the top-left corner of the target
        source_ds.SetGeoTransform([0, 1, 0, 1024, 0, -1]) 
        source_ds = None

        # Convert the target TIFF to an MRF
        gdal.Translate(target_mrf_path, target_tiff_path, options='-f MRF -co BLOCKSIZE=512')
        
        # Run the mrf_insert utility
        subprocess.run([self.mrf_insert_executable, source_tiff_path, target_mrf_path], check=True)
        
        # Verify the result
        # Open the modified MRF and read the patched area
        result_ds = gdal.Open(target_mrf_path)
        result_band = result_ds.GetRasterBand(1)
        # Read the top-left 512x512 block where the source was inserted
        data = result_band.ReadAsArray(0, 0, 512, 512)
        
        # All values in the patched area should be 255
        self.assertTrue(np.all(data == 255))
        
        # Check an un-patched area to ensure it's still zero
        data_unpatched = result_band.ReadAsArray(513, 513, 10, 10)
        self.assertTrue(np.all(data_unpatched == 0))
        
        result_ds = None
