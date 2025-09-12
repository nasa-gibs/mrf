## **MRF Utilities Test Suite**

This document outlines the unit tests for the Meta Raster Format (MRF) utilities. The tests are written in Python using the `unittest` framework and are designed to be run with a test runner like `pytest`. The suite is structured into separate files for each utility to ensure maintainability and clarity.

A shared test helper, `tests/helpers.py`, provides a base class that handles the setup and teardown of a temporary testing directory and includes methods for creating mock MRF files (`.mrf`, `.idx`, `.dat`). This approach minimizes code duplication and standardizes test environments.


### Docker-Based Testing Environment

Using Docker is the recommended method for running this test suite. It creates an environment with all the necessary C++, GDAL, and Python dependencies pre-installed, resolving any platform-specific issues and ensuring the tests run in this isolated environment. This workflow uses a two stage building approach: first creating a base application image, and then building a lightweight test runner image from it.

#### Prerequisites

Ensure Docker installed and running on your system.

#### Building and Running the Tests

**Step 1: Build the Base Application Image**
Navigate to the project's root directory and run the following command. This builds the main application image, compiling all C++ utilities and installing dependencies. It is tagged as `mrf-app:latest`.

```bash
docker build --platform linux/amd64 -t mrf-app:latest -f Dockerfile .
```

> **Note**: The `--platform linux/amd64` flag is required if you are building on an ARM-based machine (like an Apple Silicon Mac) to ensure compatibility with the pre-compiled `x86_64` GDAL RPM used in the build.

**Step 2: Build the Test Suite Image**
Next, build the dedicated test runner image. This build uses the `mrf-app` image from the previous step as its base.

```bash
docker build --platform linux/amd64 -t mrf-test-suite -f tests/Dockerfile .
```

**Step 3: Run the Test Suite**
Finally, run the tests using the `mrf-test-suite` image. This command starts a container, executes `pytest`, and automatically removes the container (`--rm`) when finished.

```bash
docker run --rm mrf-test-suite
```

You should see output from `pytest`, culminating in a summary showing tests passing or failing or skipping.


### `can` Utility Tests

**File**: `tests/test_can.py`

These tests validate the `can` C++ command-line utility, which is used for compressing and decompressing sparse MRF index files.

  * **`test_can_uncan_cycle`**: Verifies the round-trip integrity of the canning process. It creates a large, sparse mock index file (`.idx`), runs `can` to compress it to a canned index (`.ix`), and then runs it with the `-u` flag to decompress it back to an `.idx` file. The test passes if the final index file is identical to the original.


### `jxl` Utility Tests

**File**: `tests/test_jxl.py`

These tests validate the `jxl` C++ utility, which converts MRF data files and single images between JPEG (JFIF) and JPEG XL (Brunsli) formats.

  * **`test_jxl_mrf_round_trip`**: Verifies the primary MRF conversion. It converts a mock MRF data file (`.pjg`) and its index to JXL format and then back to JPEG, confirming the final files are identical to the originals and that the JXL file is smaller.
  * **`test_jxl_single_file_round_trip`**: Validates the single-file mode (`-s`). It performs a round-trip conversion on a standalone JPEG file and confirms data integrity.
  * **`test_jxl_bundle_mode` (Placeholder)**: A placeholder test for Esri bundle mode (`-b`) that is skipped, as creating a valid mock bundle file is non-trivial.


### `mrf_clean.py` Tests

**File**: `tests/test_clean.py`

These tests validate `mrf_clean.py`, a script used to optimize MRF storage by removing unused space.

  * **`test_mrf_clean_copy`**: Checks the default "copy" mode. It verifies that the script creates a new, smaller data file with slack space removed and that the new index file has correctly updated, contiguous tile offsets.
  * **`test_mrf_clean_trim`**: Validates the in-place "trim" mode. It confirms that the original data file is truncated to the correct size and its index file is overwritten with updated offsets.


### `mrf_insert` Utility Tests

**File**: `tests/test_mrf_insert.py`

These tests validate the `mrf_insert` C++ utility, which is used to patch a smaller raster into a larger MRF.

  * **`test_mrf_insert_simple_patch`**: Validates the core functionality. It creates an empty target MRF and a smaller source raster, executes `mrf_insert`, and uses GDAL to verify the patched region was written correctly while unpatched regions remain unaffected.
  * **`test_mrf_insert_with_overviews`**: Tests that inserting a patch with the `-r` flag correctly regenerates the affected overview tiles.
  * **`test_mrf_insert_partial_tile_overlap`**: Confirms that inserting a source that only partially covers a target tile correctly merges the new data while preserving the uncovered portions of the original tile.


### `mrf_join.py` Tests

**File**: `tests/test_join.py`

These tests validate `mrf_join.py`, a script that merges or appends multiple MRF files.

  * **`test_mrf_join_simple_merge`**: Checks the script's ability to merge two sparse MRFs, verifying that the final data file is a concatenation of inputs and the final index correctly combines entries with updated offsets.
  * **`test_mrf_join_overwrite`**: Confirms the "last-one-wins" logic by joining two MRFs that provide data for the same tile and verifying that the final index points to the data from the last-processed input.
  * **`test_mrf_append_z_dimension`**: Validates the ability to stack 2D MRFs into a single 3D MRF, checking that the Z dimension is correctly set in the metadata and that the index layout is correct for multiple slices.
  * **`test_mrf_append_with_overviews`**: Tests the scenario of appending MRFs that contain overviews, ensuring the final interleaved index structure is correctly assembled.

### `mrf_read_data.py` Tests

**File**: `tests/test_read_data.py`

These tests validate `mrf_read_data.py`, which extracts a specific tile or data segment from an MRF data file.

  * **`test_read_with_offset_and_size`**: Validates the direct read mode by using `--offset` and `--size` to extract a specific data segment and confirming the output is correct.
  * **`test_read_with_index_and_tile`**: Validates the index-based read mode by using `--index` and `--tile` to retrieve a specific tile and verifying its content.
  * **`test_read_with_little_endian_index`**: Ensures the `--little-endian` flag functions correctly by reading from an index file with a different byte order.


### `mrf_read_idx.py` Tests

**File**: `tests/test_read_idx.py`

These tests validate `mrf_read_idx.py`, which converts a binary MRF index file into a CSV.

  * **`test_read_simple_index`**: Validates the script's core functionality with a standard, big-endian index file, verifying the output CSV has the correct headers and data.
  * **`test_read_little_endian_index`**: Confirms that the `--little-endian` flag works by parsing an index with a different byte order and checking for correctly interpreted values.
  * **`test_read_empty_index`**: Handles the edge case of an empty input file, ensuring the script produces a CSV with only the header row.


### `mrf_size.py` Tests

**File**: `tests/test_mrf_size.py`

These tests validate `mrf_size.py`, which generates a GDAL VRT to visualize the tile sizes from an MRF index.

  * **`test_vrt_creation_single_band`**: Checks VRT generation for a single-band MRF, verifying the VRT's dimensions, GeoTransform, and raw band parameters.
  * **`test_vrt_creation_multi_band`**: Validates handling of multi-band MRFs, ensuring the VRT contains the correct number of bands with correctly calculated offsets.
  * **`test_vrt_default_pagesize`**: Ensures the script correctly applies a default 512x512 page size when it's not specified in the MRF metadata.


### `tiles2mrf.py` Tests

**File**: `tests/test_tiles2mrf.py`

These tests validate `tiles2mrf.py`, which assembles an MRF from a directory of individual tiles.

  * **`test_simple_conversion`**: Validates basic functionality by assembling a 2x2 grid of tiles and verifying the concatenated data file and sequential index offsets.
  * **`test_with_overviews_and_padding`**: Checks the creation of a multi-level pyramid, ensuring the script correctly processes all levels and adds necessary padding records to the index.
  * **`test_blank_tile_handling`**: Validates the `--blank-tile` feature, confirming that blank tiles are omitted from the data file and are represented by a zero-record in the index.


### Conditional Test Skipping

The test suite is designed to be run primarily within the provided Docker container, where all dependencies are guaranteed to be met. However, the tests include conditional skipping logic to fail gracefully if run in a local environment that is not fully configured.

  * **C++ Executable Tests**: The tests for **`can`**, **`jxl`**, and **`mrf_insert`** will be skipped if their respective compiled executables are not found in the system's PATH.
  * **GDAL Python Dependency**: The test for `mrf_insert` requires the GDAL Python bindings to create test files. It will be skipped if the `osgeo.gdal` library cannot be imported.
