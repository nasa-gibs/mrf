### NASA Global Imagery Browse Services (GIBS)

**This software was originally developed at the Jet Propulsion Laboratory as part of [Tiled WMS](https://github.com/nasajpl/tiledwms). The Meta Raster Format driver for GDAL source code was split off into this repository.**

## Meta Raster Format

The MRF driver is included and maintained within the standard GDAL source since GDAL version 2.1.  This repository usually lags the GDAL trunk.  It is maintained in support of the NASA GIBS and as a source of MRF documentation.

The source code contains the Meta Raster Format (MRF) specification and driver for GDAL, which is used by the OnEarth software package.  OnEarth consists of image formatting and serving modules which facilitate the deployment of a web service capable of efficiently serving standards-based requests for georeferenced raster imagery at multiple spatial resolutions including, but not limited to, full spatial resolution.  The Meta Raster Format and OnEarth software were originally developed at the Jet Propulsion Laboratory (JPL) to serve global daily composites of MODIS imagery.  Since then, it has been deployed and repurposed in other installations, including at the Physical Oceanography Distributed Active Archive Center ([PO.DAAC](http://podaac.jpl.nasa.gov/)) in support of the State of the Oceans ([SOTO](http://podaac-tools.jpl.nasa.gov/soto-2d/)) visualization tool, the Lunar Mapping and Modeling Project (now [MoonTrek](https://moontrek.jpl.nasa.gov/)), and [Worldview](https://earthdata.nasa.gov/labs/worldview/).

The full documentation for the MRF format and the GDAL driver see
[Meta Raster Format User Guide](src/gdal_mrf/frmts/mrf/MUG.md)

For more information, visit https://earthdata.nasa.gov/gibs