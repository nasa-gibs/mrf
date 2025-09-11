# Test Suite: `mrf_join.py`

This is documentation of the test suite for the `mrf_join.py` utility. The purpose of this suite is to provide comprehensive testing for the script's two primary modes of operation:
1.  **Join Mode:** Merging multiple 2D MRFs into a single composite 2D MRF.
2.  **Append Mode:** Stacking multiple 2D MRFs to create a single 3D MRF with multiple Z-slices.

The tests are designed to verify data integrity, the correctness of complex index file manipulations, and proper metadata updates.

---

## Test Setup and Helpers

All tests in this suite inherit from `MRFTestCase`, a base class defined in `tests/helpers.py`. This class provides:
* Automatic creation and cleanup of a temporary directory for each test, ensuring **test isolation**.
* Helper functions (`create_mock_mrf_xml`, `create_mock_data`, `create_mock_idx`) for generating the necessary MRF component files for each test scenario.

The tests directly import and call the functions from the `mrf_join.py` script, allowing for fast and focused unit testing without relying on command-line subprocesses.

---

## Test Cases

### `test_mrf_join_simple_merge()`

* **Purpose:** This test validates the behavior of the **join mode**, where two MRFs containing data for different tiles are merged into one.
* **Scenario:**
    1.  An MRF (`in1.mrf`) is created with space for two tiles, but only the **first** tile contains data.
    2.  A second MRF (`in2.mrf`) is created with the same structure, but only the **second** tile contains data.
* **Assertions:**
    1.  It verifies that the output data file (`out.dat`) contains the simple concatenation of the tile data from both inputs.
    2.  It asserts that the output index file (`out.idx`) has been correctly merged, with the tile from `in1` at the beginning and the tile from `in2` following it, with its data offset correctly recalculated.

### `test_mrf_join_overwrite()`

* **Purpose:** This test validates the "last-in-wins" overwrite logic of the **join mode**.
* **Scenario:**
    1.  An MRF (`in1_overwrite.mrf`) is created with data for a single tile (version A).
    2.  A second MRF (`in2_overwrite.mrf`) is created with different data for the **same** tile (version B).
* **Assertions:**
    1.  It verifies that the output data file contains the data from both inputs concatenated. The data from the first input becomes inaccessible "slack space."
    2.  It asserts that the final index record correctly points to the data from the **second** input (`in2_overwrite.mrf`), confirming that it overwrote the entry from the first input.

### `test_mrf_append_z_dimension()`

* **Purpose:** This test validates the core functionality of the **append mode**—stacking 2D MRFs into a 3D MRF.
* **Scenario:**
    1.  Two simple 2D MRFs (`in_z1.mrf` and `in_z2.mrf`) are created, each containing a single tile.
    2.  The `mrf_append` function is called to stack these into a new 3D MRF with a Z-size of 2.
* **Assertions:**
    1.  It verifies that the output data file contains the concatenated tile data from both inputs.
    2.  It asserts that the output index file contains two records, one for each Z-slice, with correctly calculated offsets.
    3.  It parses the output metadata file (`out_3d.mrf`) and confirms that the `<Size>` element has been correctly updated with the `z="2"` attribute.

### `test_mrf_append_with_overviews()`

* **Purpose:** This test is designed to validate the **append mode**'s handling of MRFs that contain overviews (pyramids). It verifies the script's ability to correctly calculate the complex interleaved index structure for a 3D MRF with multiple levels.
* **Scenario:**
    1.  Two identical MRFs are created, each having a structure that produces one overview level (e.g., a base resolution of 2x1 tiles and an overview of 1x1 tiles).
    2.  The `mrf_append` function is called to stack these into a 2-slice, 3D MRF.
* **Assertions:**
    1.  It verifies that the final index file has the correct total number of records (2 slices * 3 records/slice = 6 records).
    2.  It asserts that the records are interleaved in the correct order as required by the MRF specification for 3D pyramids: **[L0S0T0, L0S0T1, L0S1T0, L0S1T1, L1S0T0, L1S1T0]**, where `L` is level, `S` is slice, and `T` is tile.
    3.  It confirms that the data offsets for each record have been correctly recalculated to point to the right location in the final concatenated data file.
