# Test Suite: `mrf_insert`

This document outlines the test suite for the `mrf_insert` C++ utility. The purpose of this suite is to provide comprehensive **integration testing** that validates the end-to-end functionality of the tool.

The tests use the `osgeo.gdal` and `numpy` Python libraries to dynamically create georeferenced test rasters. The `mrf_insert` executable is called as a `subprocess`, and the results are verified by reading the output MRF's pixel data back into memory.

---

## Setup and Helpers

All tests in this suite inherit from `MRFTestCase`, a base class that automatically handles the creation and cleanup of a temporary directory for each test, ensuring complete isolation.

A helper method, `_create_geotiff`, is used to reduce code duplication by providing a simple interface for generating TIFF files with specific dimensions, fill values, and georeferencing.

---

## Test Cases

### `test_mrf_insert_simple_patch()`

* **Purpose:** This test validates the most basic functionality of `mrf_insert`: patching a source image into a target MRF at the base resolution level.
* **Scenario:**
    1.  A large target GeoTIFF (1024x1024) is created and filled with a background value of **0**.
    2.  This target is converted into a base MRF.
    3.  A smaller source GeoTIFF (512x512) is created, filled with a patch value of **255**, and georeferenced to the top-left corner of the target.
* **Assertions:**
    1.  It asserts that the top-left 512x512 region of the modified MRF now contains the patch value (**255**).
    2.  It asserts that a region outside the patch area remains unchanged, still containing the background value (**0**).

### `test_mrf_insert_with_overviews()`

* **Purpose:** This is a critical test that validates the utility's most powerful feature: the intelligent and efficient regeneration of **overviews** (pyramids) after an insert. 
* **Scenario:**
    1.  A large target MRF (2048x2048) is created with pre-built overview levels using the `UNIFORM_SCALE` creation option. The MRF is filled with a background value of **0**.
    2.  A 512x512 source image filled with **255** is inserted into the target using the `-r Avg` command-line flag, which triggers the overview update logic.
* **Assertions:**
    1.  It verifies that the **base resolution** is correctly patched.
    2.  It then reads the first overview level (which is 2x downsampled) and asserts that the corresponding, smaller region in the overview has been correctly updated to the new average value (**255**).
    3.  It also checks an unpatched area in the overview to ensure it was not modified.

### `test_mrf_insert_partial_tile_overlap()`

* **Purpose:** This test targets an important **edge case**: inserting a source image that only partially covers a tile in the target MRF. This validates the `ClippedRasterIO` logic within the C++ code, which must correctly merge old and new data within a single tile.
* **Scenario:**
    1.  A target MRF is created with a single 512x512 tile, filled with a background value of **100**.
    2.  A smaller 256x256 source image, filled with a patch value of **255**, is georeferenced to cover only the top-left quadrant of the target's single tile.
* **Assertions:**
    1.  It reads the entire 512x512 tile from the modified MRF.
    2.  It asserts that the top-left quadrant of the tile now contains the patch value (**255**).
    3.  It asserts that the other three quadrants of the tile were not affected and still contain the original background value (**100**).
