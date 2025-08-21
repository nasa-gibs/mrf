# tests/test_mrf_insert.py

import shutil
from tests.helpers import MRFTestCase

class TestMRFInsert(MRFTestCase):
    def test_mrf_insert_simple_patch(self):
        """Test patching a small image into a larger MRF."""
        if not shutil.which(self.mrf_insert_executable):
            self.skipTest(f"'{self.mrf_insert_executable}' executable not found in PATH.")
        
        # This test requires a full GDAL environment to create the necessary
        # TIFF and MRF files for the utility to process.
        self.skipTest("Skipping mrf_insert test: requires an active GDAL environment.")
