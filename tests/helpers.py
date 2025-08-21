# tests/helpers.py

import unittest
import os
import shutil
import struct
from xml.etree import ElementTree as ET

class MRFTestCase(unittest.TestCase):
    """
    A base class for MRF utility tests that handles temporary directory
    creation and provides helper methods for creating mock MRF files.
    """
    def setUp(self):
        """Set up a temporary directory for test files."""
        self.test_dir = "mrf_test_temp_dir"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Assume C++ utilities are compiled and in the system PATH
        self.can_executable = "can"
        self.mrf_insert_executable = "mrf_insert"

    def tearDown(self):
        """Clean up the temporary directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_mock_mrf_xml(self, path, xsize=512, ysize=512, channels=1, pagesize=512, data_ext="dat"):
        """Creates a minimal MRF metadata file."""
        root = ET.Element("MRF_META")
        raster = ET.SubElement(root, "Raster")
        ET.SubElement(raster, "Size", x=str(xsize), y=str(ysize), c=str(channels))
        ET.SubElement(raster, "PageSize", x=str(pagesize), y=str(pagesize), c=str(channels))
        data_file = ET.SubElement(raster, "DataFile")
        base_name = os.path.basename(path).replace('.mrf', '')
        data_file.text = f"{base_name}.{data_ext}"
        
        tree = ET.ElementTree(root)
        tree.write(path)

    def create_mock_idx(self, path, tiles):
        """Creates a mock index file from a list of (offset, size) tuples."""
        with open(path, "wb") as f:
            for offset, size in tiles:
                f.write(struct.pack('>QQ', offset, size))

    def create_mock_data(self, path, content_list):
        """Creates a mock data file from a list of byte strings."""
        with open(path, "wb") as f:
            for content in content_list:
                f.write(content)
                
    def read_idx_file(self, path):
        """Reads an index file and returns a list of (offset, size) tuples."""
        tiles = []
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(16)
                if not chunk:
                    break
                tiles.append(struct.unpack('>QQ', chunk))
        return tiles
