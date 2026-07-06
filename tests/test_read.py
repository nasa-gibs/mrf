import os
import shutil
import struct
import subprocess
import sys
from xml.etree import ElementTree as ET
from tests.helpers import MRFTestCase

# Signature of a brunsli (ZenJPEG) packed tile
BRUNSLI_SIGNATURE = b'\x0a\x04\x42\xd2\xd5\x4e'

def yarn_encode(data, code=0xC3):
    """Minimal valid encoding of the MRF RLE (yarn) stream: a marker code
    byte followed by the data as literals, escaping the marker code."""
    out = bytearray([code])
    for b in data:
        out.append(b)
        if b == code:
            out.append(0)
    return bytes(out)

def insert_zen_chunk(jpeg, mask_payload):
    """Insert a Zen APP3 chunk right after the JPEG SOI marker.
    An empty mask_payload means all pixels are non-zero."""
    payload = b'Zen\x00' + mask_payload
    segment = b'\xff\xe3' + struct.pack('>H', len(payload) + 2) + payload
    return jpeg[:2] + segment + jpeg[2:]

class TestMRFRead(MRFTestCase):
    """
    Tests for the mrf_read.py script, which extracts a tile from an MRF,
    converting brunsli (ZenJPEG) tiles to JFIF-JPEG on output.
    """

    def setUp(self):
        """Extend setUp to define the brn executable path."""
        super().setUp()
        self.brn_executable = "brn"

    def create_mrf_meta(self, path, xsize=16, ysize=16, compression="JPEG"):
        """Creates a minimal MRF metadata file with a Compression element,
        as expected by mrf_read.py."""
        root = ET.Element("MRF_META")
        raster = ET.SubElement(root, "Raster")
        ET.SubElement(raster, "Size", x=str(xsize), y=str(ysize), c="3")
        comp = ET.SubElement(raster, "Compression")
        comp.text = compression
        ET.ElementTree(root).write(path)

    def make_jpeg_mrf(self, tile_content):
        """Creates a JPEG MRF (mrf/idx/pjg) holding a single tile with the
        given content, returns the path of the .mrf file."""
        mrf_path = os.path.join(self.test_dir, "test.mrf")
        self.create_mrf_meta(mrf_path)
        self.create_mock_data(os.path.join(self.test_dir, "test.pjg"), [tile_content])
        self.create_mock_idx(os.path.join(self.test_dir, "test.idx"), [(0, len(tile_content))])
        return mrf_path

    def read_tile(self, mrf_path, output_path, extra_args=[]):
        """Runs mrf_read.py for the first tile and returns the output bytes."""
        cmd = [
            sys.executable, "mrf_apps/mrf_read.py",
            "--input", mrf_path,
            "--output", output_path,
            "--tile", "1"
        ] + extra_args
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue("Wrote" in result.stdout)
        self.assertNotIn("Warning", result.stdout)
        with open(output_path, 'rb') as f:
            return f.read()

    def test_read_jfif_tile(self):
        """A plain JFIF-JPEG tile should be written out unmodified."""
        # ARRANGE: Build an MRF holding a single JPEG tile
        jpeg_path = os.path.join(self.test_dir, "tile.jpg")
        self.create_mock_jpeg(jpeg_path)
        with open(jpeg_path, 'rb') as f:
            jpeg_content = f.read()
        mrf_path = self.make_jpeg_mrf(jpeg_content)

        # ACT
        output_path = os.path.join(self.test_dir, "output.jpg")
        content = self.read_tile(mrf_path, output_path)

        # ASSERT: The output is the stored tile, byte for byte
        self.assertEqual(content, jpeg_content)

    def test_read_brunsli_tile_converts_to_jfif(self):
        """A brunsli (ZenJPEG) tile should be converted to JFIF-JPEG on output."""
        if not shutil.which(self.brn_executable):
            self.skipTest(f"'{self.brn_executable}' executable not found in PATH.")

        # ARRANGE: Encode a JPEG to brunsli and store it as the MRF tile
        jpeg_path = os.path.join(self.test_dir, "tile.jpg")
        self.create_mock_jpeg(jpeg_path)
        with open(jpeg_path, 'rb') as f:
            jpeg_content = f.read()
        subprocess.run([self.brn_executable, "-s", jpeg_path], check=True)
        with open(jpeg_path + ".brn", 'rb') as f:
            brn_content = f.read()
        self.assertTrue(brn_content.startswith(BRUNSLI_SIGNATURE))
        mrf_path = self.make_jpeg_mrf(brn_content)

        # ACT
        output_path = os.path.join(self.test_dir, "output.jpg")
        content = self.read_tile(mrf_path, output_path)

        # ASSERT: The output is a JFIF-JPEG identical to the original
        self.assertEqual(content, jpeg_content)

    def test_zen_mask_full(self):
        """With --mask, an empty Zen chunk should force all pixels to non-zero."""
        from PIL import Image

        # ARRANGE: A black JPEG with an empty Zen chunk (all pixels non-zero)
        jpeg_path = os.path.join(self.test_dir, "tile.jpg")
        self.create_mock_jpeg(jpeg_path, size=(16, 16), color='black')
        with open(jpeg_path, 'rb') as f:
            zen_jpeg = insert_zen_chunk(f.read(), b'')
        mrf_path = self.make_jpeg_mrf(zen_jpeg)

        # ACT
        output_path = os.path.join(self.test_dir, "output.png")
        self.read_tile(mrf_path, output_path, extra_args=["--mask"])

        # ASSERT: Every decoded zero was lifted to one
        with Image.open(output_path) as img:
            self.assertEqual(img.size, (16, 16))
            values = set(img.tobytes())
        self.assertNotIn(0, values)
        self.assertIn(1, values)

    def test_zen_mask_partial(self):
        """With --mask, masked-as-zero pixels should be zeroed on all bands."""
        from PIL import Image

        # ARRANGE: A white JPEG with a Zen mask marking the top-left
        # 8x8 block as zero. The 16x16 mask holds 2x2 blocks, one 64bit
        # little endian unit each, in row major order.
        jpeg_path = os.path.join(self.test_dir, "tile.jpg")
        self.create_mock_jpeg(jpeg_path, size=(16, 16), color='white')
        all_set = (1 << 64) - 1
        mask = struct.pack('<4Q', 0, all_set, all_set, all_set)
        with open(jpeg_path, 'rb') as f:
            zen_jpeg = insert_zen_chunk(f.read(), yarn_encode(mask))
        mrf_path = self.make_jpeg_mrf(zen_jpeg)

        # ACT
        output_path = os.path.join(self.test_dir, "output.png")
        self.read_tile(mrf_path, output_path, extra_args=["--mask"])

        # ASSERT: Top-left 8x8 block is zero, everything else is untouched white
        with Image.open(output_path) as img:
            for y in range(16):
                for x in range(16):
                    expected = (0, 0, 0) if x < 8 and y < 8 else (255, 255, 255)
                    self.assertEqual(img.getpixel((x, y)), expected,
                                     f"wrong pixel at {x},{y}")

    def test_read_brunsli_tile_raw(self):
        """With --raw, a brunsli tile should be written out unmodified."""
        if not shutil.which(self.brn_executable):
            self.skipTest(f"'{self.brn_executable}' executable not found in PATH.")

        # ARRANGE
        jpeg_path = os.path.join(self.test_dir, "tile.jpg")
        self.create_mock_jpeg(jpeg_path)
        subprocess.run([self.brn_executable, "-s", jpeg_path], check=True)
        with open(jpeg_path + ".brn", 'rb') as f:
            brn_content = f.read()
        mrf_path = self.make_jpeg_mrf(brn_content)

        # ACT
        output_path = os.path.join(self.test_dir, "output.brn")
        content = self.read_tile(mrf_path, output_path, extra_args=["--raw"])

        # ASSERT: The output is the stored brunsli tile, byte for byte
        self.assertEqual(content, brn_content)
