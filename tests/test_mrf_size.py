import os
import subprocess
import sys
from xml.etree import ElementTree as ET
from tests.helpers import MRFTestCase
# Import the script to test its functions directly
from mrf_apps import mrf_size

class TestMRFSize(MRFTestCase):
    """
    Tests for the mrf_size.py script, which generates a VRT to visualize tile sizes.
    """

    def _create_full_mrf_xml(self, path, xsize=512, ysize=512, channels=1, pagesize=512, include_pagesize_tag=True):
        """Creates a more complete MRF metadata file with GeoTags for testing."""
        root = ET.Element("MRF_META")
        raster = ET.SubElement(root, "Raster")
        ET.SubElement(raster, "Size", x=str(xsize), y=str(ysize), c=str(channels))
        if include_pagesize_tag:
            ET.SubElement(raster, "PageSize", x=str(pagesize), y=str(pagesize), c=str(channels))
        
        geotags = ET.SubElement(root, "GeoTags")
        # Define a simple BoundingBox and Projection for testing GeoTransform
        ET.SubElement(geotags, "BoundingBox", minx="0", miny="0", maxx=str(xsize), maxy=str(ysize))
        ET.SubElement(geotags, "Projection").text = "LOCAL_CS[\"Pseudo-Mercator\",UNIT[\"metre\",1]]"

        tree = ET.ElementTree(root)
        tree.write(path)

    def test_vrt_creation_single_band(self):
        """Test VRT generation for a single-band 2x1 tile MRF."""
        # ARRANGE: Create a mock MRF file for a 1024x512 image (2x1 tiles)
        mrf_path = os.path.join(self.test_dir, "test.mrf")
        vrt_path = os.path.join(self.test_dir, "test_size.vrt")
        self._create_full_mrf_xml(mrf_path, xsize=1024, ysize=512, pagesize=512)

        # ACT: Run the script's main function
        sys.argv = ["mrf_size.py", mrf_path]
        mrf_size.main()

        # ASSERT
        self.assertTrue(os.path.exists(vrt_path))
        tree = ET.parse(vrt_path)
        root = tree.getroot()

        # 1. Check VRT dimensions (should be 2x1 pixels, one for each tile)
        self.assertEqual(root.tag, "VRTDataset")
        self.assertEqual(root.get("rasterXSize"), "2")
        self.assertEqual(root.get("rasterYSize"), "1")

        # 2. Check GeoTransform (should be scaled by pagesize)
        # Original pixel res: x=1, y=-1. Scaled by 512 -> x=512, y=-512
        geotransform = root.find("GeoTransform").text
        self.assertEqual(geotransform, "0.0,512.0,0,512.0,0,-512.0")

        # 3. Check VRTRasterBand properties
        band = root.find("VRTRasterBand")
        self.assertIsNotNone(band)
        self.assertEqual(band.get("dataType"), "UInt32")
        self.assertEqual(band.find("SourceFilename").text, "test.idx")
        
        # ImageOffset should be 12 to read the lower 4 bytes of the 8-byte size field
        self.assertEqual(band.find("ImageOffset").text, "12") 
        # PixelOffset is 16 bytes (size of one index record)
        self.assertEqual(band.find("PixelOffset").text, "16")
        # LineOffset is 16 * rasterXSize * num_bands = 16 * 2 * 1 = 32
        self.assertEqual(band.find("LineOffset").text, "32")
        self.assertEqual(band.find("ByteOrder").text, "MSB")

    def test_vrt_creation_multi_band(self):
        """Test VRT generation for a 3-band, single-tile MRF."""
        # ARRANGE
        mrf_path = os.path.join(self.test_dir, "multiband.mrf")
        vrt_path = os.path.join(self.test_dir, "multiband_size.vrt")
        self._create_full_mrf_xml(mrf_path, xsize=512, ysize=512, channels=3, pagesize=512)

        # ACT
        sys.argv = ["mrf_size.py", mrf_path]
        mrf_size.main()
        
        # ASSERT
        self.assertTrue(os.path.exists(vrt_path))
        tree = ET.parse(vrt_path)
        root = tree.getroot()
        
        # 1. VRT should be 1x1 pixels
        self.assertEqual(root.get("rasterXSize"), "1")
        self.assertEqual(root.get("rasterYSize"), "1")

        # 2. There should be 1 raster band (for the single pixel-interleaved tile)
        bands = root.findall("VRTRasterBand")
        self.assertEqual(len(bands), 1)

        # 3. Check offsets for the single band
        # VRT is 1x1, so xsz=1. bands=1.
        # PixelOffset and LineOffset are 16 * num_bands = 16
        self.assertEqual(bands[0].find("ImageOffset").text, "12")
        self.assertEqual(bands[0].find("PixelOffset").text, "16")
        self.assertEqual(bands[0].find("LineOffset").text, "16")

    def test_vrt_default_pagesize(self):
        """Test that a default PageSize of 512 is used when the tag is absent."""
        # ARRANGE: Create a 1024x1024 MRF without a <PageSize> tag
        mrf_path = os.path.join(self.test_dir, "default.mrf")
        vrt_path = os.path.join(self.test_dir, "default_size.vrt")
        self._create_full_mrf_xml(mrf_path, xsize=1024, ysize=1024, include_pagesize_tag=False)

        # ACT
        sys.argv = ["mrf_size.py", mrf_path]
        mrf_size.main()

        # ASSERT: The VRT should be 2x2, based on the default 512x512 page size
        self.assertTrue(os.path.exists(vrt_path))
        tree = ET.parse(vrt_path)
        root = tree.getroot()
        self.assertEqual(root.get("rasterXSize"), "2")
        self.assertEqual(root.get("rasterYSize"), "2")
