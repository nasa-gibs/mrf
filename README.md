### NASA Global Imagery Browse Services (GIBS)

**This software was originally developed at the Jet Propulsion Laboratory as Tiled WMS (https://github.com/nasajpl/tiledwms).  OnEarth is now the latest actively developed version (https://github.com/nasa-gibs/onearth).  The Meta Raster Format driver for GDAL source code was split off into this repository.**

## Meta Raster Format

The source code contains the Meta Raster Format (MRF) specification and plugin for GDAL, which is a part of the OnEarth software package.  OnEarth consists of image formatting and serving modules which facilitate the deployment of a web service capable of efficiently serving standards-based requests for georeferenced raster imagery at multiple spatial resolutions including, but not limited to, full spatial resolution.  The Meta Raster Format and OnEarth software were originally developed at the Jet Propulsion Laboratory (JPL) to serve global daily composites of MODIS imagery.  Since then, it has been deployed and repurposed in other installations, including at the Physical Oceanography Distributed Active Archive Center (PO.DAAC) in support of the State of the Oceans (SOTO) visualization tool, the Lunar Mapping and Modeling Project (LMMP), and GIBS.

### [Meta Raster Format Specification] (spec/mrf_spec.md)

For more information, visit https://earthdata.nasa.gov/gibs

## Preconditions

The MRF driver for GDAL requires the use of GDAL (version 1.11.1 recommended).  GDAL is included with the RPM release.

## RPM Installation

Download the latest [MRF release](https://github.com/nasa-gibs/mrf/releases).

Unpackage the release .tar.gz file:
```
tar -zxvf mrf-*.tar.gz
```

Install GIBS GDAL with the MRF driver:
```
sudo yum -y install gibs-gdal-1.*
```

Alternatively: The GDAL plugin for MRF is available if using the included version of GDAL is not desired (note: Python bindings are not supported with the plugin).
```
sudo yum -y install gibs-gdal-plugin-mrf-*
```

## Installing from Source
 
The MRF driver links with the rest of GDAL and has to be compiled with the same compiler, libraries, and options by which GDAL was compiled.

Download GDAL source:
```
wget http://download.osgeo.org/gdal/1.11.1/gdal1111.zip
```

Unpack GDAL source:
```
mkdir src
mv gdal1111.zip src/
cd src/
unzip gdal1111.zip
```
 
Go to the GDAL source directory:
```
cd gdal-1.11.1/
``` 

Configure GDAL source install:
```
set LD_LIBRARY_PATH "<gdal install location>/lib:$LD_LIBRARY_PATH"
./configure --prefix=<gdal install location>
```
The ```<gdal install location>``` should be different from where you build the source code for gdal.

Make gdal:
```
make
```

Install gdal:
```
make install
```

Download the source for the latest [MRF release](https://github.com/nasa-gibs/mrf/releases) or checkout from git:
```
git clone https://github.com/nasa-gibs/mrf.git
```

Copy the MRF GDAL driver to the GDAL source tree (the plugin must be compiled here):
```
cp -R mrf/src/gdal-mrf/frmts/mrf <gdal source directory>/frmts/
```

Go to the mrf driver source directory:
```
cd <gdal source directory>/frmts/mrf
```
 
Make the driver:
```
make clean
make plugin
```

Install the driver:
```
mkdir -p <gdal install location>/lib/gdalplugins
cp gdal_mrf.so.1 <gdal install location>/lib/gdalplugins
```
 
Create soft link:
```
cd <gdal install location>/lib/gdalplugins
ln -s gdal_mrf.so.1 gdal_mrf.so
```
 
Verify that the MRF driver is recognized by GDAL:
```
gdalinfo --format MRF

Format Details:
  Short Name: MRF
  Long Name: Meta Raster Format
  Help Topic: frmt_marfa.html
  Supports: CreateCopy() - Create dataset by copying another.
  Creation Datatypes: Byte UInt16 Int16 Int32 UInt32 Float32 Float64

<CreationOptionList>
  <Option name="COMPRESS" type="string-select" default="PNG" description="PPNG = Palette PNG; DEFLATE = zlib ">
    <Value>JPEG</Value>
    <Value>PNG</Value>
    <Value>PPNG</Value>
    <Value>TIF</Value>
    <Value>DEFLATE</Value>
    <Value>NONE</Value>
  </Option>
  <Option name="INTERLEAVE" type="string-select" default="PIXEL">
    <Value>PIXEL</Value>
    <Value>BAND</Value>
  </Option>
  <Option name="QUALITY" type="int" description="best=99, bad=0, default=85" />
  <Option name="OPTIONS" type="string" description="Freeform dataset parameters" />
  <Option name="BLOCKSIZE" type="int" description="Block size, both x and y, default 512" />
  <Option name="BLOCKXSIZE" type="int" description="Page x size, default=512" />
  <Option name="BLOCKYSIZE" type="int" description="Page y size, default=512" />
  <Option name="NETBYTEORDER" type="boolean" description="Force endian for certain compress options, default is host order" />
  <Option name="CACHEDSOURCE" type="string" description="The source raster, if this is a cache" />
  <Option name="UNIFORM_SCALE" type="int" description="Uniform overlays in MRF, only 2 is tested" />
  <Option name="NOCOPY" type="boolean" description="Leave created MRF empty, default=no" />
</CreationOptionList>
```

## Sample Usage

Use gdal_translate to convert into MRF:
```
gdal_translate -of MRF -co COMPRESS=PPNG -co BLOCKSIZE=512 -outsize 20480 10240 input.vrt output.mrf
```
Note: "PPNG" is used for a paletted PNG color profile, whereas "PNG" is used for RGBA.

Use gdaladdo to add overview levels:
```
gdaladdo output.mrf -r nearest 2 4 8 16
```

See the [Meta Raster Format Specification](spec/mrf_spec.md) for more information.

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)