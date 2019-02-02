## Meta Raster Format

MRF is a raster format implemented as a [GDAL](http://github.com/OSGeo/GDAL).  The [MRF driver](https://github.com/OSGeo/gdal/tree/master/gdal/frmts/mrf) itself is maintained within GDAL since GDAL version 2.1.  This repository contains MRF documentation and MRF related utilities.

MRF is used by the [OnEarth](https://github.com/nasa-gibs/onearth) web server software.  OnEarth consists of image formatting and serving modules which facilitate the deployment of a web service capable of efficiently serving standards-based requests for georeferenced raster imagery at multiple spatial resolutions including, but not limited to, full spatial resolution.  The Meta Raster Format and OnEarth software were originally developed at the Jet Propulsion Laboratory (JPL) to serve Landsat imagery and global daily composites of MODIS imagery.  Since then, it has been deployed and repurposed in other installations, including at the Physical Oceanography Distributed Active Archive Center ([PO.DAAC](http://podaac.jpl.nasa.gov/)) in support of the State of the Oceans ([SOTO](http://podaac-tools.jpl.nasa.gov/soto-2d/)) visualization tool, the Lunar Mapping and Modeling Project (now [MoonTrek](https://moontrek.jpl.nasa.gov/)), and [Worldview](https://earthdata.nasa.gov/labs/worldview/).

For the documentation of the MRF format and the MRF GDAL driver see
[Meta Raster Format User Guide](src/gdal_mrf/frmts/mrf/MUG.md)

For more information, visit [NASA GIBS](https://earthdata.nasa.gov/gibs)
