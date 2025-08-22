## **MRF Utilities Test Suite**

This document outlines the unit tests for the Meta Raster Format (MRF) utilities. The tests are written in Python using the `unittest` framework and are designed to be run with a test runner like `pytest`. The suite is structured into separate files for each utility to ensure maintainability and clarity.

A shared test helper, `tests/helpers.py`, provides a base class that handles the setup and teardown of a temporary testing directory and includes methods for creating mock MRF files (`.mrf`, `.idx`, `.dat`). This approach minimizes code duplication and standardizes test environments.


### \#\# Docker-Based Testing Environment

Using Docker is the recommended method for running this test suite. It creates a consistent, isolated environment with all the necessary C++, GDAL, and Python dependencies pre-installed, resolving any platform-specific issues and ensuring the tests run reliably.

#### \#\#\# Prerequisites

Ensure you have Docker installed and running on your system.

#### \#\#\# Building and Running the Tests

1.  **Build the Docker Image**
    Navigate to the project's root directory (the one containing the `Dockerfile`) and run the following command. This will build the Docker image and tag it as `mrf-test-suite`.

    ```bash
    docker build --platform linux/amd64 -t mrf-test-suite .
    ```

    > **Note**: The `--platform linux/amd64` flag is required if you are building on an ARM-based machine (like an Apple Silicon Mac) to ensure compatibility with the pre-compiled `x86_64` GDAL RPM used in the build.

2.  **Run the Test Suite**
    Once the image is built, run the tests using this command. It will start a container from the image, execute `pytest`, and automatically remove the container (`--rm`) when finished.

    ```bash
    docker run --rm mrf-test-suite
    ```

You should see output from `pytest`, culminating in a summary like `5 passed`.


### \#\# `mrf_clean.py` Tests

**File**: `tests/test_clean.py`

These tests validate the functionality of the `mrf_clean.py` script, which is used to optimize MRF storage by removing unused space.

  * **`test_mrf_clean_copy`**: This test checks the default "copy" mode. It creates a mock MRF data file containing slack space (unused bytes) between valid data tiles. It verifies that the script creates a new, smaller data file with the slack space removed and that the corresponding new index file has correctly updated, contiguous tile offsets.

  * **`test_mrf_clean_trim`**: This test validates the in-place "trim" mode. It uses a source MRF with slack space and confirms that after the script runs, the original data file is truncated to the correct, smaller size and that its index file is correctly overwritten with the updated tile offsets.


### \#\# `mrf_join.py` Tests

**File**: `tests/test_join.py`

This test validates the `mrf_join.py` script, which merges multiple MRF files.

  * **`test_mrf_join_simple`**: This test checks the script's ability to merge two sparse MRF files. It creates two mock MRFs, each containing data for a different tile in a two-tile raster. It verifies that the final data file is a concatenation of the input tile data and that the final index file correctly combines the index entries from both sources, applying the proper offsets. This test specifically validates the script's "last-one-wins" merge logic for sparse datasets.


### \#\# `can` Utility Tests

**File**: `tests/test_can.py`

These tests validate the `can` C++ command-line utility, which is used for compressing and decompressing sparse MRF index files.

  * **`test_can_uncan_cycle`**: This test verifies the round-trip integrity of the canning process. It creates a large, sparse mock index file (`.idx`), runs the `can` utility to compress it into a canned index (`.ix`), and then runs the utility again with the `-u` flag to decompress it back to an `.idx` file. The test passes if the final, decompressed index file is identical to the original, confirming a lossless process.


### \#\# `mrf_insert` Utility Tests

**File**: `tests/test_mrf_insert.py`

These tests validate the `mrf_insert` C++ command-line utility, which is used to patch a smaller raster into a larger MRF.

  * **`test_mrf_insert_simple_patch`**: This test validates the core functionality of the utility. It programmatically creates a large, empty target MRF and a smaller source raster filled with data. It then executes the `mrf_insert` command to patch the source into the target. Finally, it uses the GDAL library to read back the patched region and an unpatched region to verify that the data was inserted correctly and that other areas of the file were not affected.


### \#\# Conditional Test Skipping

The test suite is designed to be run primarily within the provided Docker container, where all dependencies are guaranteed to be met. However, the tests include conditional skipping logic to fail gracefully if run in a local environment that is not fully configured.

  * **C++ Executable Tests**: The tests for `can` and `mrf_insert` will be skipped if their respective compiled executables are not found in the system's PATH.

  * **GDAL Python Dependency**: The test for `mrf_insert` requires the GDAL Python bindings to create test files. It will be skipped if the `osgeo.gdal` library cannot be imported.
