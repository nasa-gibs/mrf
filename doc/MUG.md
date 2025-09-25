# Meta Raster Format (MRF) User Guide

For MRF Version 1.x

# MRF: Definition, Context and Introduction

MRF, short for Meta Raster Format, is a technology that combines raster storage with tile web services and cloud computing.
While the main target domain is cloud GIS, the MRF technology can also be used in other areas such as medical imaging and scientific data processing.

MRF is:

- A raster storage format
- A tile cache format for web services
- A dynamic tile cache for another raster

For the purpose of this document, a raster is defined as a two dimensional array of values. In information technology, a raster most commonly 
represents an image, in which case the array elements are known as pixels, short for picture elements. An image can be grayscale or color.
In the latter case multiple values are associated with each pixel, usually one for each of the red, green and blue components. In scientific 
applications, rasters are commonly used to represent sampled scalar fields or matrices, where each array value is the numeric value of the 
scalar field at a specific point.  In geographic information science (GIS), a raster can be either a map image or an array of values.
A raster is a very compact and efficient way of storing uniformly sampled data, since the set of coordinates does not have to be stored with 
each of the data values.  Instead, the coordinates are calculated by knowing the raster projection, one or more reference points and resolution.

There are many raster formats in use today. Most of them have started as image formats intended for disk storage or archiving. JPEG, PNG and TIFF 
are some of the best known examples. As image formats, they usually support grayscale and color images of reasonable size, and employ various 
compression algorithms for reducing the amount of storage needed. Most of these formats have been designed before the advent of the internet, 
and have continued to be used since they serve their purpose very well. Yet these formats have significant limitations, for example when used 
to store extremely large images, or non-image data.

MRF was designed to leverage existing image formats while addressing some of their shortcomings, without adding unnecessary complexity. In the 
simplest form, MRF explicitly provides tiling, spatial indexing and multiple resolutions (aka overviews, pyramid, or resolution-sets) support.
This is an extremely common approach in GIS, allowing data for a specific area to be read without having to read the complete raster. It also 
allows for raster sizes well beyond what is feasible with traditional image formats. Since the tiles in an MRF file may themselves be stored in a 
raster format, the MRF is suitable as the tile storage format for web services. MRF can also be used as a cloud raster cache format, to improve 
the performance of web applications. MRF segregates the data, index and metadata in different files, which allows different classes of storage to be 
used for the different components as needed, enhancing efficiency, even on a single system.

There are of course other technologies that try to address the same areas. For example the naive approach of leaving the image tiles in 
folders and imposing a known folder and file naming strategy. This has the advantage that no special tools or applications are needed to explore 
and curate the larger dataset. This approach is somewhat fragile and does not scale as well as it seems at first glance, since the file and 
operating system overhead is increasing significantly with dataset size. A slightly better approach is to use a database for storing the tiles.
In general a database has less overhead than a file system and thus scales slightly better than the file in folder approach. The disadvantage 
is that a full database engine is needed while most of the database functionality (tables, queries, transactions) are not useful or applicable 
to raster tile storage. In addition, databases expect and are optimized for smaller records than the normal raster tile size. The two dimensional 
grid intrinsic to a raster is not a common database construct, and tools for populating a database of rasters are scarce, non-standard or have 
to be written from scratch.

MRF takes the middle road between these two approaches. It provides excelent scalability by providing only the needed database functionality parts.
It does not rely heavily on the file system for tile management. It acts as a raster itself, so it can be read and written using raster aware 
applications. Performance and scalability have been the main design goals for the MRF, closely followed by simplicity, usability and flexibility.
The MRF is implemented as a GDAL driver (Geospatial Data Abstraction Layer), which allows the MRF to be immediately leveraged in many GIS 
applications, and providing access to well documented tools and workflows. As with most technologies, understanding the features and limitations 
by MRF is important if good results are to be expected. This document contains the detailed MRF documentation.

# MRF File Structure

An MRF dataset has three components, metadata, index and data. While normally each component is stored in a separate file, alternative 
configurations exist.

- The metadata contains high level information about the raster itself. It is stored as an XML formatted file, which improves readability and 
  extensibility. The metadata file is the starting point in any operation on an MRF dataset. In GDAL, the XML content of this file can be used
  instead of a file name, so in some cases the metadata component can be just a text string. The metadata file uses the .mrf extension by 
  convention, any other file extension can also be used.
- The index is concerned with the two dimensional organization of the raster tiles on a grid. It contains one or more two dimensional array of 
  records, where each record holds the size and offset of a raster tile. The index file size is proportional to the number of tiles that may 
  reside in an MRF. The organization of the index file depends on which MRF features are being used, but for a single raster they are stored 
  in a top-left aligned, row major array. The index file name is by default the same as the metadata file name with the .idx extension.
- The data component contains the raster tiles forming the MRF, which themselves contain data values for each pixel. As opposed to the index,
  there is no guaranteed order of the data tiles within the data file. The data file is modified only by appending at the end of the file, 
  all existing content will continue to take space on disk, even if it was replaced and is no longer accessible via the MRF driver.
  The data file name may have a variety of extensions (e.g. ".ppg" for PNG tiles or ".pjg" for JPEG tiles).

Note that there is no redundancy of information, neither of the components contain any information which exist in a different component 
of the same MRF. All three components are required for accessing the MRF content. It is not usually possible to fully recover the dataset from 
only one or two of the components.

# Referring to an MRF

The normal reference to a specific MRF raster is to use to the metadata file name. The metadata file can have any extension, the file format 
detection in GDAL is done by matching the first ten characters in the file, which have the value `"<MRF_META>"`. For example this command 
will work if the test.mrf is an MRF metadata file.

`gdalinfo test.mrf`

Another way to reference an MRF is to use the XML content of the metadata as a string. In this case the data and index file names have to be 
explicitly identified in the metadata string itself, since it is not possible to derive them based on the metadata file name. When this method 
is used from the command line, shell special characters have to be escaped, so that a correctly formed XML string is passed to the GDAL open 
command.

# MRF Operations

When a MRF is created, all three component files are usually created on disk in the same folder. One of the MRF format features is that the 
dataset can be read as soon as the files are created, even before any data is actually written. It is also possible to read from an MRF file 
while it is being written into. Regions of an MRF that have not been written to automatically return the NoData value if the NoData value is 
defined for the dataset, or zero otherwise. This is also true for the overviews, data can be read as soon as the MRF file is flagged as 
containing overviews.

## Overview Generation

An MRF can have either no overviews or all the overviews for a specific overview scale progression, until all the raster fits into a single 
tile. There is no MRF support for individual overviews, so it is not possible to only have a selected few! If the overviews have not been 
populated with data, they will return NoData value or zero.  
The MRF driver contains optimized code to generate overviews using averaging or nearest value interpolation, for overview scale of 
powers of 2. The generic GDAL overview generation code can also be used, in which case overviews with various resampling methods or at 
other scale factor (3, 4 …) can be generated. The same rule applies; all levels have to exist until all raster fits in one tile. If the MRF 
is not already marked as having overviews, the scale between overviews will be the first value passed to gdaladdo utility. The first 
overview to be generated and populated has to be the largest one. It is also mandatory to generate all necessary overviews in sequence, 
since they are generated recursively, from the previous one. Usually the list of levels passed to gdaladdo should be all the needed 
powers of the scale factor, like this:

`gdaladdo -r avg Test.mrf 2 4 8 16 32 64 128`  
Or for powers of 3:  
`gdaladdo Test.mrf 3 9 27 81`

For convenience, unnecessary levels (the large values) generate a warning but not an error. It is not possible to change MRF overviews 
from one scale factor to another. It is however possible to generate the overviews multiple times, which will not reclaim the space used
by the older overviews.

While not recommended, it is possible to generate MRF external overviews in GDAL, which are usually not in MRF format and are not subject
to the MRF limitations.

## Overview sampling:

The MRF driver contains its own optimized resampling code, using either averaging or nearest neighbor algorithms. The internal code has 
less overhead than the GDAL averaging and is usually faster. It is also optimized for MRFs with large areas of NoData. Use `–r avg` or 
`-r nnb` as the sampling option to gdaladdo with 2 as a scale factor to trigger the use of the MRF specific overview generation. Only scale 
2 works for the internal sampler! The MRF sampler pads to the right and bottom of the image when needed, keeping the scale factor an exact 2. 
In contrast, the GDAL sampler stretches the input when needed by repeating rows and/or columns, which keeps the bounding box for all the 
overviews identical but the ratio between two successive overviews may not be exactly 2. Since for the internal resampler the scale factor is 
exactly 2, the `avg` algorithm can also be considered a bilinear interpolation. Both `avg` and `nbb` samplers do take the NoData into account.
The GDAL average or near neighbor sampling can be selected by using `–r average` or `-r near`. As described above, the results 
may differ slightly from the MRF internal sampler, due to the different padding.

GDAL resampling takes into consideration both the NoData value and the alpha band when it exists, setting to zero pixels where the alpha 
band is zero. To force gdal to preserve the data values even for pixels where the alpha value is zero, set the MRF create option 
`PHOTOMETRIC=MULTISPECTRAL`. The downside of this workaround is that it will set the photometric interpretation of all bands to unknown, 
which may create other problems. The MRF `avg` or `nnb` resampling methods are not subject to this behavior, it will keep the the data 
values even if the alpha band is zero.

## Reading a single overview

In case of an MRF file with overviews, it is possible to open a single specific overview level, usually to check the overview in isolation.
The overviews are identified by their numeral and not by the relative scale, with 0 being the largest overview. 
The syntax used for this is `<filename>:MRF:L<n>`

For example, this command will explicitly open the first overview level:

`gdalinfo test.mrf:MRF:L0`

## Inserting data in an existing MRF

Using an MRF specific utility `mrf_insert`, it is possible to replace or modify a part of an MRF and generate only the affected portions 
of the overviews. This facility makes it possible to build very large datasets efficiently, operating on small areas at a time. This functionality 
relies on the internal MRF resampling, so it will only work with avg or nnb resampling mode and powers of two between levels.  
Set create option `APPEND_SUBDATASET` to true avoid deleting the MRF header file.  
Since a Caching or Cloning MRF may be used at the same time by different processes, the MRF driver contains code that allows it to be written 
by multiple processes on the same machine safely, as long as the MRF resides on a local disk. This feature might be useful for other types of 
MRF, for example when mrf_insert is used to update different areas of the same file, or when multiple third dimension MRF Z-Slices can be written 
to at the same time. To turn on this feature, manually add a boolean attribute called mp_safe with the value **on** to the Raster node of the 
MRF metadata. This feature is not on by default since it slows down the write operations somewhat. This feature has been tested on Windows and 
Linux, and it may fail on specific operating and file system implementations. It does not work on shared, network file systems like CIFS and NFS, 
because these file systems do not implement the file append mode correctly.

# Tile compression modes supported by MRF

Tiles in an MRF are stored using one of the multiple supported packing or compression formats. Some of the formats are themselves standard 
raster formats like JPEG, TIFF or PNG, while others are only compression formats. The choice of the tile format is passed to the MRF driver 
using the GDAL create option `COMPRESS`.

|Format|Data Type|Description|Usage|Lossy|Comments|
| --- | --- | --- | --- | --- | --- |
|[NONE](#none)|All|As is, no compression|Rarely|No|Very large and very fast|
|[QB3](#qb3)|Integer|[QB3](https://github.com/lucianpls/QB3) compression|Recommended|No|Small and very fast|
|[PNG](#png-and-ppng)|Byte, UInt16, Int16|Well known PNG format|Web Tiles|No|Small but very slow to create|
|[PPNG](#png-and-ppng)|Byte|PNG with per tile palette|Web Tiles|No|Small but very slow to create|
|[ZSTD](#zstd)|All|[ZSTD](https://github.com/facebook/zstd) compression|Recommended|No|Good compression, speed depends on QUALITY=[1-22]|
|[DEFLATE](#deflate)|All|[zlib](https://www.zlib.net/) compression|DEPRECATED|No|Use ZSTD instead, it is faster and better|
|[JPEG](#jpeg)|Byte, UInt16|JPEG (JFIF) format|Images, Web Tiles|Yes|Very small and fast. Up to 12bit per channel data. Includes zero mask (Zen)|
|[JPEG](#jpeg) brunsli|Byte|[Brunsli](https://github.com/google/brunsli) packed JPEG|Smaller than JPEG| Yes|Replaces COMPRESSION=JPEG when brunsli is available|
|[JPNG](#jpng)|Byte|Mix of JPEG and PNG|Web Tiles with transparency|Yes|Uses JPEG for tiles with no transparency, PNG otherwise. Use only when JPEG-Zen is not suitable|
|[TIFF](#tiff)|All|TIFF with LZW compression|Web Tiles|No|Mostly for web clients with TIFF support|
|[LERC](#lerc)|All|[LERC](https://github.com/Esri/lerc) compression||Choice|Fast compression with fixed quantization step|

## NONE

The NONE format directly stores the tile array in a row major pixel order. PIXEL and BAND interleave modes are supported, 
as well as all the GDAL supported data types. The NONE format has no other options or features, all the common MRF functionality applies. 
If a NoData value is defined per band, tiles consisting only in NoData values are not stored on disk. If the NoData value is not defined, 
tiles which only contain zeros are not stored. As with any other tile format, the MRF does not guarantee any specific order of the tiles in 
the data file. For multiple byte data types, the order of the bytes is machine dependent, except if the NETBYTEORDER option is set, in which
case the bytes are written in big endian. This rule applies to most of the other formats that do not explicitly control the data values (JPEG, PNG, TIF).

## QB3

The [QB3](https://github.com/lucianpls/QB3) compression is a raster specific lossless integer compression algorithm. It is very fast for both 
compression and decompression and it produces great compression for natural images. In MRF it supports all integer types, signed 
or unsigned. Multiple bands per tile are supported (INTERLEAVE=PIXEL), with a default inter-band decorrelation for RGB(A) data which can 
improve the compression ratio. The decorrelation can be disabled by using PHOTOMETRIC=MULTI create option. A custom band decorrelation
can be used by setting the free form option QB3_BAND_MAP to a comma separated list of indices. The list is positional, if the index is equal
with the position then the respective band is a core band, kept as such. If the index is different from the position, it indicates the core
band that will have its values subtracted from the current band before the current band is compressed.
QB3 has an optional extra compression step which in some cases can result in additional compression while still being lossless. Since this step
slows down the compression and is usually ineffective for Byte data, it is not enabled by default. To enable it, use QUALITY settings above 95.  
There is also a faster mode, triggered by setting QUALITY under 5, which also loses a bit of the compression.
The QB3 is highly recommended as a format for lossless data. It achieves better compression that PNG, DEFLATE, ZSTD and LERC while being significantly
faster. The fast compression makes it especially valuable for use in a caching MRF or when MRF is a transient (work) format.  

## PNG and PPNG

PNG is a well known lossless compression image format. It uses a raster filter plus the DEFLATE algorithm internally. PNG is currently the 
default compression mechanism for MRF. PNG compression is slower than DEFLATE, but results in smaller data files which are also suitable as 
tiled web services. PPNG is an MRF specific compression name, it stands for Palette PNG. While both types can have an MRF level palette, 
PPNG also stores the palette inside each and every PNG tile. This mode should only be used if the individual tiles are to be served 
over the web as colorized images, otherwise the regular PNG compression results in smaller data files. The PNG format itself supports up 
to sixteen bit unsigned integer data types.
However, the MRF driver can treat a 16 bit PNG as containing either unsigned or signed data type (Int16), in which case the values stored in 
the PNG are interpreted as signed. The QUALITY setting controls the DEFLATE stage of the PNG, with the same behavior as the ones described in 
the DEFLATE compression. Similarly, the Z_STRATEGY band option controls the DEFLATE stage of PNG. Choosing Z_RLE or Z_HUFFMAN_ONLY as strategies 
will result in much faster compression at the expense of size, Z_HUFFMAN_ONLY being the fastest. Z_FIXED and Z_FILTERED have much less effect.
The effect of the strategy setting is much stronger than the QUALITY value setting.  
Example of gdal_translate to MRF/PNG:  
`gdal_translate -of MRF –co COMPRESS=PNG –co OPTIONS="Z_STRATEGY:Z_RLE" –co QUALITY=50 input.tif output.mrf`

## ZSTD

[ZSTD](https://github.com/facebook/zstd) is an open source generic lossless compression algorithm. It is considerably faster 
than DEFLATE at the same compression ratio and can achieve better compression. ZSTD in MRF can handle all the data types, both band 
and pixel interleave. The ZSTD compression level can be controled by providing a quality figure, an integer between 1 and 22. 
The default level in MRF is 9, where ZSTD is expected to achive a compression ratio similar to DEFLATE at level 6, while being much faster. 
In general the default ZSTD level should not be modified, it provides good compression and is fast. Lower figures 
will be faster but achieve less compression while higher ones will take more CPU time while compressing better. Note that large values
can take a massive amount of time and runtime memory and do not necessarily improve the compression over slighly lower levels. 
QUALITY values outside of the valid range will be silently ignored, the ZSTD compression level will stay the default 9. 
ZSTD at QUALITY=1 (lowest) is very fast while also providing reasonable compression, it should be used in most cases where the 
write speed is more important than the absolute storage size, for example in caching MRFs. 
The fact that ZSTD compression is lossless and that it works with all supported data types makes this choice even better.
MRF with ZSTD uses a data filter (see below), which improves the compression ratio considerably.  

ZSTD in MRF can be used in two ways, as a stand-alone tile packing mechanism or as a second pass compression when used with another format. 
The later mode is chosen by adding `ZSTD:ON` to the free form list `OPTIONS`.

### MRF ZSTD Optimization
ZSTD is a lossless byte stream compression. The compression achieved can be improved if the input data is taken into 
consideration by filtering the input to increase redundancy. MRF implements a byte-rank reorder followed a byte delta filter on the 
tile data before ZSTD compression. This filter improves the raster compression considerably in most cases, especially for multi byte 
data types and for pixel interleaved data. The filter has a negligible computation cost, especially when compared with the ZSTD 
compression itself, so it is always applied. This filter is not used when ZSTD is applied as a second stage compression, except when 
the main compression is `NONE`.

## DEFLATE
### DEPRECATED, **ZSTD is recommended instead**

DEFLATE is a well known generic compression algorithm, implemented in the open source zlib library. In MRF it can be used in two ways, as a 
stand-alone tile packing mechanism and also as a second compression step to other compression formats. The second meaning is activated by 
adding `DEFLATE:on` to the free form list `OPTIONS`. `NONE` compression with the `DEFLATE:on` option is equivalent to the DEFLATE as 
compression format, even though the content of the metadata file is different. The following two commands should generate MRFs with identical 
size data files, although the tile order may differ.
```
gdal_translate –of MRF –co COMPRESS=DEFLATE input.tif deflate.mrf
gdal_translate –of MRF –co COMPRESS=NONE -co OPTIONS="DEFLATE:on" input.tif raw_and_deflate.mrf
```
The DEFLATE compression level is calculated from the QUALITY setting as level = floor(Quality/10). The default is 8, which produces very good 
compression albeit slow. A quality setting of 60 is recommended as a tradeoff between compression speed and size. Quality of zero, 
corresponding to quality values under 10, means no compression.  
The DEFLATE compression can use different tile headers. The default should be used in general, since the speed and size difference 
between these options is insignificant. By default, zlib compatible tile headers are generated. Gzip or no tile headers can be used instead, 
by setting the boolean free form `OPTIONS` GZ and RAWZ. If both are set, the headers will be gzip. The zlib header is 6 bytes and 
includes a checksum calculated with the zlib specific ADLER32 algorithm. The gzip header is slightly larger and uses a CRC32 as a 
checksum, which is very slightly slower than the zlib one. Raw deflate does not have a checksum nor a header and is slightly faster 
than either the gzip or zip headers. 

The following command will generate an MRF in which every tile is a gzip stream:

`gdal_translate –of MRF –co COMPRESS=DEFLATE -co OPTIONS="GZ:on" input.tif gzipped.mrf`

This feature can be useful when tiles are served via http, which mandates support for GZIP decoding.  
Zlib supports slightly different compression strategies, and MRF allows control of these strategies. The compression speed and the size 
of the output will change significantly if these options are used. This options only affect the compression algorithm, so the generated 
tiles can always be decompressed. For exact details on the strategy flags refer to the zlib documentation. The free form option to use 
is `Z_STRATEGY`, and the valid values are:

- `Z_FILTERED`: Skips the optional filtering of the input stream
- `Z_HUFFMAN_ONLY`: Only the Huffman encoding part of DEFLATE is performed
- `Z_RLE`: Somewhat like an RLE, within the limits of DEFLATE
- `Z_FIXED`: Fixed Huffman tables as opposed to addaptive ones

Example which will generate an RLE compressed tile with gzip style headers:  
`gdal_translate –of MRF –co COMPRESS=DEFLATE -co OPTIONS="GZ:on Z_STRATEGY:Z_RLE" input.tif gzipped.mrf`

## JPEG

The JPEG compression is a well know lossless image compression, tuned for good visual quality combined with good 
compression. Since JPEG is a well known format, the MRF tiles compressed as JPEG are suitable for serving as web 
tiles. Depending on how the GDAL MRF was built, the MRF/JPEG format can handle 8 and sometimes 12 bit data.
MRF with JPEG can handle up to 10 bands in pixel interleave mode. Note that only 8 bit JPEGs with 1 or 3 bands are 
suitable as web tile services in most cases. The MRF `QUALITY` output option value is directly passed to JPEG 
library as the Q (quantization) factor, with the default value being 85.
Note that the JPEG Q value does control the output quality and size, but it is not linear. For the exact interpretation 
of Q, please consult JPEG documentation. Values between 0 and 100 are supported, the reasonable range being between 
60 and 85, larger values producing visually better results at the cost of increased size.  
For three bands interleaved, a couple of encoding options are available, controlled via the `PHOTOMETRIC` setting. 
The default setting should be used most of the time.

The valid choices for the `PHOTOMETRIC` setting are:
- (DEFAULT): This is the most common JPEG style, it uses the YCbCr color space, and 4:2:0 sampling. This mode provides 
good compression and visual quality. The color space has significantly lower quality than the brightness, which
 matches the human vision charateristics.
- `YCC`: Uses the YCbCr colorspace with 4:4:4 sampling, i.e. it is not spatially resampled. This setting produces 
tiles with fewer color artifacts while being about a third larger than the default. The color conversion itself results 
in a slight loss of information, as well as the quantization.
- `RGB`: Compressed as RGB, not color converted and not spatially resampled. For the same Q setting, this mode produces 
 JPEG files much larger than the default, commonly two or three time larger. MRF with this setting can be decoded 
and re-encoded multiple times at the same Q without any data quality degradation.

Optimizing the Huffman encoding tables for each tile, as opposed to using a default table will improve the compression 
by a few percent in most cases, while taking slighly longer to compress. By default, MRF uses the default tables for 8 
bit data. For 12 bit JPEG optimize is always on since there are no predefined Huffman tables for that mode.
In MRF, optimized Huffman tables in JPEG can be enabled by adding the "OPTIMIZE:ON" to the OPTIONS list. Choosing this 
will increase encoding time somewhat and reduce the tile size, both changes are relatively small in most cases. It is
recommended to use custom tables when tiles will be stored for a while or when web tile services will operate from the MRF.  
To use the 12 bit JPEG, when available, set the data type to Int16 or UInt16.

### brunsli (JPEG XL)

While commonly refered to as a JPEG file, the normal file format used to stored JPEG compressed images
is actually [JFIF](https://en.wikipedia.org/wiki/JPEG_File_Interchange_Format). A newer format, which can be 
losslessly converted back and forth to JFIF exists, named [brunsli](https://github.com/google/brunsli). Brunsli 
format has the advantage that it can store the same exact information as the JFIF in a package 22% smaller on average. 
Since brunsli is only a better packing of a JPEG, the result is still JPEG compressed and the it has exactly the
same features and limitations. Brunsli supports all the standard JFIF/JPEG features, with the **notable 
exception** of 12bit per sample JPEGs.  
Using the brunsli format does have a small negative effect on the speed of reading and writing the tiles when compared 
with the JFIF format, because the brunsli adds a codec stage. Yet both reading and writing are still fast compared with 
DEFLATE or PNG.
When GDAL and MRF are compiled with brunsli support and JPEG compression is selected, the extra compression is very
beneficial, so MRF will store the data in the brunsli format bye default. In some cases it is useful to
force the older format, JFIF to be used. For example when the tiles are to be directly 
served over the web to a browser or when a legacy GDAL application, compiled without 
brunsli support may be used to to read the data. The OPTIONS flag `JFIF` can be set in those cases, forcing 
MRF to only generate JFIF compatible tiles:  
`gdal_translate -of MRF -co COMPRESS=JPEG -co OPTIONS=JFIF:on input.tif output.mrf`  
The command above can also be used to convert a brunsli input MRF to a JFIF output MRF.  
Serving JPEG (JFIF) tiles from an MRF which uses brunsli as the storage format is possible, using an Apache httpd filter 
module which converts the tiles on the fly to JFIF, see [mod_brunsli](https://github.com/lucianpls/mod_brunsli).

### JPEG Zero Enhanced (Zen) Extension

The JPEG tiles generated by MRF contain a mask of zero value pixels, which is stored in a JPEG Zen chunk, using APP3 "Zen" tag. 
If the size of the Zen chunk is zero, all pixels within the respective tile are known to be non-zero. When reading a JPEG that 
contains a Zen chunk, the MRF driver will ensure that the pixel positions that contain zero matches the mask. In essence, the 
pixels that contain zero are stored in a lossless way and can be used as a data mask, when read with the MRF driver. This 
eliminates the JPEG edge artifacts when the background is black, enabling a Zen JPEG encoded MRF to be used as an overlay on
top of other data, as long as black is made transparent.
Using MRF/JPEG-Zen for storing visual data can produce significant space savings over the next 
best option, which would generally be lossless JPNG, PNG or LERC. Since the Zen chunk is built 
in accordance to the JFIF standard, the mask will be ignored by legacy applications, which 
will still decode the JPEG image content. Since the mask is generated and applied at the MRF codec level, it is not 
accessible to GDAL. 
This Zen feature works with either 8 or 12 bit JPEG tiles, and works even when the brunsli tile 
format is used.  
The Zen bitmask is organized in a 8x8 2D bitmask, which is then compressed by run length encoding (RLE). For most inputs, 
the size of the Zen chunk containing the mask is negligible. The potential benefit of being able to treat black as transparent 
outweigh this size increase thus this feature cannot be turned off.

## JPNG

The JPNG compression uses PNG or JPEG tiles depending on the presence of non-opaque pixels in each tile. 
This format is intended to be used for generating web tiles which include a transparency channel
while minimizing the size of the tiles. If all the pixels within a tile are opaque the tile will be stored 
as JPEG, otherwise it is stored as PNG with an Alpha channel. It is presented to GDAL as a RGBA or 
Luma-Alpha image, it will always have 2 or 4 bands, and always PIXEL interleaved.
Most of the MRF options from PNG and from JPEG compression still apply, including the JFIF flag.
The data file will be smaller than when using only PNG if there are tiles that are fully 
opaque and can be stored as JPEG. Note that depending on the options used and the input 
data, the transition from PNG to JPEG may be visible. The JPEG with Zen mask format
should be used in most cases, except if 0 is not to be transparent or when gradual 
transparency is needed. Another advantage over MRF/JPEG-Zen is that legacy clients 
such as web browser applications do not usually need modification to be able to 
display the tiles as intended. The big disadvante of this format is that the data size is usually much larger
than what it would be using JPEG-Zen.

## TIFF

In this format every tile is a TIFF raster which itself uses the lossless LZW compression. 
Most data types are supported. Note that the tiles are not GeoTiffs, they do not contain geotags. 
This compression is mostly useful for web services for certain clients which support 
decoding TIFF.

## LERC

Limited Error Raster Compression [LERC](https://github.com/Esri/lerc) is an original Esri raster 
compression format. The benefit of using LERC is fast compression when compared with PNG, 
DEFLATE and even with JPEG, as well as great compression for data types larger than eight bit.
LERC compression can be lossy or lossless. The lossy part is due to an initial quantization stage, 
which is controled by the LERC maximum error value (LERC_PREC), which is a floating point number. 
LERC may alter the values during compression, but the change will always be less or equal to this 
LERC maximum error value. The quanta or precision of the output data values will thus be twice the 
LERC_PREC value. If the LERC maximum error is zero or too small for any space savings to be obtained 
by quantization, the input data values are not modified, and LERC becomes a lossless format.
Output compression may still occur in this case, as long as it can be lossless.  
LERC contains an explicit data mask, which in MRF is always enabled. This mask is obtained from the 
NoData value if defined, otherwise the value zero is used.
The NoData values are not stored in the compressed tile, which makes LERC a good choice 
for storing sparse data.  
In MRF, for integer types the default LERC_PREC value is 0.5, corresponding to lossless compression. 
In MRF, floating point types LERC precision defaults to 0.001 (.002 data resolution). The compression 
achieved by LERC heavily depends on the LERC_PREC value, which should be carefully selected for each 
particular dataset.  
To set a custom LERC precision value for a new MRF file, use the free form MRF OPTIONS mechanism: 
`-co OPTIONS="LERC_PREC:0.005"`  

There are two different styles of LERC compression supported in MRF, LERC (default) and LERC1.

- LERC1 is the original LERC algorithm, which implements a single band compression for floating point. 
MRF can make use of it for integer data by conversion to floating point before invoking LERC1. 
This means that LERC1 integer precision is limited to 24 bits. MRF also simulates pixel interleaved 
with LERC1 compression by concatenating the results for each individual band. While there is no size 
advantage to using LERC1 pixel interleaved in MRF, there might be a performance advantage in some environments
since data for all bands is read in a single operation. LERC1 is the format used by Esri terrain tiles.  
To choose LERC1 instead of the default LERC, add V1=ON to the options string:  
`-co OPTIONS="LERC_PREC=0.01 V1=ON"`

- LERC (Lerc2, not to be confused with Lerc version 2) supports different data types explicitly and is usually faster than LERC1. 
LERC development continues independent of MRF, new features may be added.
The LERC format includes different compression algorithms in addition to the original LERC1 one, methods 
that may result in better compression. For byte input data specifically, Huffman compression is used 
since Lerc version 2, which usually results in better compression. LERC also handles pixel interleaved data, 
introduced at LERC version 4.
By default, MRF writes LERC tiles using LERC version 2 for single band per tile, or the latest version
supported by the LERC library otherwise. MRF files created using a more recent LERC library 
may be unreadable by MRF using an older LERC version, it will generate LERC decoding errors. 
When writing to a MRF/LERC, it is possible to choose a specific LERC version using the free OPTION L2_VER. 
This option is used by the MRF driver to request that LERC encoding does not use any features not available 
in the selected version.
For example, to choose LERC version 3 as the maximum, while specifying a value precision of 0.2, use 
`-co OPTIONS="L2_VER=3 LERC_PREC=0.2"`


MRF tiles compressed by LERC can be further compressed with ZSTD or DEFLATE which in some cases can 
improve the overall compression, at the expense of speed. ZSTD and DEFLATE speed is asymmetric, with 
decompression being faster than compression, so it does not affect read speeds as much as it does writes.
To add ZSTD or DEFLATE to LERC, add "ZSTD:ON" or "DEFLATE:ON" to the list of free form options. This 
example sets the LERC precision, the LERC version and the extra ZSTD stage: `-co OPTIONS="LERC_PREC=0.01 ZSTD:ON L2_VER:2"`


# Functional Types of MRF

## Static MRF

This is the name for the basic storage format MRF, where all the three components are physically sitting in the same folder. In use it is similar 
to a TIFF or many other raster formats.

## Split MRF

The three component files of an MRF (metadata, index and data) are distributed across different storage systems. This is accomplished by having two 
XML nodes in the MRF metadata, each containing a GDAL accessible file names for the index or respectively for the data file, similar to hyperlinks.
These XML nodes are not usually created by the GDAL MRF driver, then need to be added by modifying the metadata file once the location of the component 
files is known. The two nodes to be added are `<IndexFile>` and `<DataFile>`. They are added as sub-nodes of the `<Raster>` node. The content 
is simply a GDAL readable path to where the data or the index file can be found. The Split MRF can be used for example to accelerate access to data 
on slow storage, by keeping the metadata files and possibly the index file on a fast storage (local SSD) while having the large data files on a HDD 
a NAS or even in a cloud storage by using the GDAL VSI (virtual storage interface). Other than the file location, there is no difference between 
the Static and the Split MRF. The IndexFile and DataFile nodes can also contain an optional attribute called **offset** , with a numerical value. 
This value will be added to the normal, calculated file offsets for all access to the respective files.

## Caching MRF

A caching MRF is used as a cache format for another raster file. The original raster is called the **source** raster, while the MRF used to cache 
becomes the **caching MRF**. Only reading from a caching MRF is possible in GDAL, the update of the caching MRF content occurs automatically. 
Opening a caching MRF for update is not supported. It is also not possible to write to the parent dataset through a caching MRF. Some of the GDAL 
functionality of the parent raster might not be available when accessing the data through an MRF. Only static rasters, including static/split 
MRFs should be cached. Chaining caching MRFs is possible but cache coherency may become an issue.
When the location of the caching MRF data file is on a local disk, the caching MRF can be used in parallel by multiple processes on the same machine.
For example, multiple gdal based GIS applications can be active at the same time, reading and sharing the same caching MRF data.

### Creating a MRF cache

#### CACHEDSOURCE create option

The basic way to create a caching MRF is using the gdal_translate command. In addition to the normal MRF create options, the creation of a caching 
MRF dataset requires the presence of the **CACHEDSOURCE** option, whose value is the file name of the raster dataset to be cached. Any raster 
format readable by GDAL can be used as the source, including properly quoted string GDAL specifiers. The file name should be absolute, except for 
the case where the parent raster file is located in the same exact folder as the caching MRF metadata file.

An example of creating a caching MRF:  
`gdal_translate –of MRF -co NOCOPY=True –co CACHEDSOURCE=H12003_MB_1m_MLLW_14of16.tif H12003_MB_1m_MLLW_14of16.tif tst.mrf`

In the command above, the presence of the CACHEDSOURCE option flags the file as a caching MRF and the value of the option gets stored in the MRF 
metadata file. Since the values used are the file name without an absolute path, the caching mrf metadata file will always reside in the same 
location as the parent dataset file. Absolute source path is also supported, and is the right choice in most cases.

The command above will create the caching MRF metadata, data and index files but will not copy the source data. The caching MRF has the same 
structure as a normal, static MRF, except that in the metadata it is flagged as a caching MRF. It is possible to erase the index and data files 
and then use the MRF for caching, the index and data files of a caching MRF dataset are created as empty when needed needed.  

**WARNING:**  Always remove the index and data files of a caching MRF together, otherwise errors will occur.

#### NOCOPY Create Option

As seen above, to initialize a caching MRF but not copy any data in it, use the boolean create option `NOCOPY=True`. For example:  
`gdal_translate -of MRF -co COMPRESS=LERC -co BLOCKSIZE=512 -co OPTIONS="LERC_PREC=0.01" -co NOCOPY=True -co CACHEDSOURCE=/data/LERC_test/H12003_MB_1m_MLLW_14of16.tif H12003_MB_1m_MLLW_14of16.tif caching.mrf`

The example above, in addition to the precedent one, sets the caching MRF compression to LERC, sets the blocksize to be used, sets the LERC max 
error via the freeform option and sets the NOCOPY to true. This will leave the caching MRF initialized but empty. When raster blocks are then read 
from the MRF, data is read from the CACHEDSOURCE raster and stored in the caching MRF. On subsequent reads, if the data already exists in the caching 
MRF the parent dataset is not longer accessed.  The caching MRF can be used to transcode data from any raster file format supported by GDAL.

The combined use of the `CACHEDSOURCE` and `NOCOPY` options should be the most common use pattern. Normally, the source raster as used on the 
gdal_translate command line and the value of the `CACHEDSOURCE` are the same. The difference is that the source raster is used as the source of 
metadata during the gdal_translate execution, while the `CACHEDSOURCE` raster is used while reading, when attempting to read from the caching MRF, 
if the data is not present in the MRF itself.  This syntax is required due to the structure of gdal_translate, and it also offers the possibility 
to initialize a caching MRF using a local file while caching a different, possibly remote raster. Since opening and reading the metadata from a remote
raster can take a while, this option can greatly speed up setting multiple caching MRFs without having to open each and every remote raster.

#### UNIFORM_SCALE Create Option

The MRF (caching or static) can be flagged at creation time as already having the full set of internal overlays. This is useful when creating a 
caching MRF, since it will then cache and offer access to overview tiles.  
This command creates a caching MRF with the normal, factor 2:  
`gdal_translate -of MRF -co COMPRESS=LERC -co BLOCKSIZE=512 -co OPTIONS="LERC_PREC:0.01" -co UNIFORM_SCALE=2 -co NOCOPY=True -co CACHEDSOURCE=/data/LERC_test/H12003_MB_1m_MLLW_14of16.tif H12003_MB_1m_MLLW_14of16.tif /data/LERC_test/test.mrf`

Note that data for the overlays of a caching MRF will be read at the corresponding scale by reading from the parent dataset, thus they might be different from 
the ones created on a static MRF. Do not use gdalado on a caching MRF.

#### Using a caching MRF

This is the easy part, simply use the caching MRF for reading data just as any other raster format in GDAL. When opened, the MRF driver will 
not open the source dataset. When reading, if the tile already exists in the caching MRF, then it will be read from it. Otherwise, the source file 
will be opened and the tile will be requested from the source. Then the MRF tile will be created and stored in the caching MRF before returning the data. 
Thus, the first time a tile is requested it will have the source performance, any subsequent writes will have local performance.  The delayed source 
dataset open provides additional performance.
The performance of the caching MRF depends on a multitude of factors, including the page sizes of both the caching MRF and the remote files. 
Good performance is usually achieved when the caching MRF and the remote file have the same page size and alignment. A particular case is when the 
remote is pixel interleaved but the caching MRF is band interleaved. In this case, the remote page may be read and decompressed multiple times, 
once for each and every output band. However, if the GDAL block cache is large enough to hold all the remote blocks this will not happen and the 
blocks will be reused. If the source page size is not efficient for the user application, it is recommended that the source data be reformatted 
ahead of time with a suitable page size, possibly as MRF.

#### Advanced use of caching MRF

The two extra features of a caching MRF over a static one, fetching content from a different source and storing content locally can be individually 
turned off. Turning them both off will transform the caching MRF into a static MRF, where only the content that already exists within the cache is 
accessible. The ability to turn these features off and then turn them on again is done via file access rights. The state of these features is set 
when the data and index files are opened, and they will persist for that process as long as those files are kept open.

Turning off the **local cache writes** while still reading data from the source still allows reading the cached content as well as source content. 
This feature is useful for example when the local cache should not be allowed to increase in size. To turn off local cache writing off, make the 
existing MRF **data file** read only.

Turning off the **new content fetch** is useful for reading only the local cache, or when the source is not available. It avoids the latency and 
penalty of trying and failing to access the source. To turn off the source fetching, make the existing MRF **index file** read only. 
Turning off the new content fetch will implicitly turn off local cache writes, since there is no new content to be written. If a caching MRF uses 
the same file for both data and index, this will be the behavior.  Data which does not exist in the local caching MRF will be returned as NoData 
or black.

Sometimes it is useful to temporarily stop the caching MRF from storing data locally while preserving data access to the remote data source, without
modifying the file access flags. This can be achieved by setting the environment variable **MRF_BYPASSCACHING** to **TRUE**. This variable can 
be set as a gdal configuration option. All caching and cloning MRF files opened while this variable is set to true are affected, it is not possible 
to selectively choose which caching MRFs are affected.


## Cloning MRF

As a further optimization of a caching MRF, if the source dataset of a caching MRF is itself an MRF, and the caching MRF has the identical structure 
with the source one (image size, projection, page size, compression …), the page transcoding is eliminated, and a copy of the already compressed pages 
from the source MRF into the cache. This type of MRF is a `Cloning MRF`, since its tiles are an identical copy of the source MRF ones, 
possibly in a different order. Creating a clone MRF cannot be done using gdal_translate, since it is not possible to insure that the source has the 
same properties as the caching MRF. Instead, a cloning MRF has to be created by copying the cloned MRF metadata file to where the cloning MRF should 
reside and adding the following lines to the top level node:

```
<CachedSource>
	<Source clone="true">/path/to/cloned.mrf</Source>
</CachedSource>
```

The data and the index files for a cloned MRF will also be created on read, as needed. Only static or split MRFs can be cloned, the cloning MRF read 
does not trigger the full GDAL block read to the source dataset. This characteristic has the added benefit of reduced GDAL block cache use, 
since the source blocks are not read in the block cache, being identical with the cloning MRF blocks.

## Versioned MRF

A versioned MRF is a special type of static MRF. It has to be created by hand, adding the "versioned" boolean attribute to the Raster node in the 
metadata file. Once set up as a versioned MRF, any tile overwrite will automatically create a new version within the same MRF set of files. 
There is no support for explicit version creation. Versions are counted, 1 being the oldest, 2 the second oldest ... Version 0 (default) is 
special, being the latest. Only the version 0 (latest) is being updated, all the other versions are read only. By using the normal file name 
as the MRF reference, the latest version is being used. To read from a previous version, use the ornate file name with a V prefix. This reference 
will open the oldest version of an versioned MRF:

`<filename>:MRF:V1`

The number of versions is unlimited. The index file will grow as versions are added. It is possible to have overviews in a versioned MRF. 
To make this work, create an empty MRF with reserved space for overviews, then modify the metadata to flag it as versioned and start writing into it.
Alternatively, once the initial version of the base resolution has been created, overviews should be generated, and only then the MRF be flagged 
as being versioned.

## Third dimension MRF

A raster is usually a 2D dataset, characterized by the size in the X and Y dimensions and the number of color bands or channels. MRF supports an 
optional third dimension, dimension Z. An MRF with the Z size N contains N 2D rasters, all with the same size in X and Y, same number of bands, 
stored with the same exact parameters. Each of the N 2D rasters is identified by the Z index, an integer from 0 to N-1. In GDAL only one of the 
2D rasters is available at a time, determined at the time of the file opening, with Z index zero being the default. In other words, a normal, 
2D MRF is a 3D MRF with the Z size of 1. The Z dimension is not visible in GDAL, other than the `ZSIZE` and `ZSLICE` metadata items in the 
`IMAGE_STRUCTURE` metadata domain.

While the third dimension MRF seems similar to the versioned MRF, the index file is structurally different, and there are other differences:  
- Similar to the X and Y sizes, the Z size is a constant that is set when the MRF file is created and cannot be modified later. In contrast, 
the number of versions is not limited and can change during use.
- Each 2D image in a 3rd-dimension MRF can be written to, in any order. In a versioned MRF, writes are possible to the latest version only.

#### Z Slice selection
	
To open a specific Z index from a 3rd dimensional MRF, the file name ornament Z has to be used. The syntax used for 
this is `<filename>:MRF:Z<n>`. If the Z index is not specified, zero is used.

For example, this command will explicitly open the 2D raster at Z index 1:

`gdalinfo TenSlice.mrf:MRF:Z1`

It is also possible to select a specific overview of a specific Z index, for example the second overview (scale 4 if powers of two are used) 
of the slice index five:

`gdalinfo TenSlice.mrf:MRF:Z5:L1`

It is also possible to create a metadatafile that explicitly refers to a specific `ZSlice`.

#### Creating and writing to a 3rd dimension MRF

To create an MRF with the Z size different from one, the ZSIZE create option has to be set at creation time. This gdal_translate command will 
create an MRF with the Z size of 10, getting the size and other parameters from the source.tif file and leaving the output MRF empty.

`gdal_translate –of MRF –co ZSIZE=10 –co NOCOPY=true source.tif TenSlice.mrf`

If the NOCOPY parameter is not set, the data from source.tif will also be copied in the slice index zero of the TenSlice.mrf. The UNIFORM_SCALE 
parameter can also be used, reserving space but not populating the overviews. Using the Z index selection names, gdaladdo can also be used to 
reserve the index space for the overviews and populate them, for any valid Z index value.
Once the 3rd dimension MRF exists, the full resolution image at a Z index different than one can be inserted using gdal_translate. 
Note that the create options have to be identical with the ones used to initially create the MRF. Also, if the input images have to have the 
same exact size and most of the other parameters, except for the ones explicitly overwritten by the create options. For example, content from a 
JPEG and a DEFLATE geotiff can be copied into the same 3rd dimension MRF, but the MRF compression has to be explicitly set in the gdal_translate 
command. If this condition is not met, the output MRF may be corrupted. This is because the MRF metadata file will be recreated by every 
gdal_translate command and no tests are done to insure that the content is the same.

The following commands will copy a source3.tif into the z index 3 of the mrf created above, followed by populating the overviews for the slice:

```
gdal_translate –of MRF –co ZSIZE=10 source3.tif TenSlice.mrf:MRF:Z3

gdaladdo –r avg TenSlice.mrf:MRF:Z3
```

# Notes on using MRF

## MRF in TAR

Many of the unique MRF applications rely on the separation of the MRF components in individual files. At times this can become 
a nuisance. As a convenience, it is possible to pack all the MRF component files in a single tar file and use the resulting 
tar as an MRF using GDAL. This feature is subject to the following requirements:

	- The MRF file names inside the tar do not include a path (basename only)  
	- The tar file includes all the MRF component files, with the metadata file (.mrf) being the first
	- The tar uses a UStar (Unix Standard TAR) header format, not pax
	- The file extension ends with .tar, with .mrf.tar being recommended

As long as the conditions above are met, the GDAL MRF driver will recognise the file as an MRF file and will be able to read from it. 
External overviews or external metadata (.mrf.aux.xml) will be used if included in the tar.

## MRF as a Web Tile Cache
One of the most common uses of MRF is to serve as a fast and easy to use tile cache for a web map tile server. 
Since far fewer files are used, adn MRF tile cache is much more efficient at using the disk than individual tiles would be,
while also offering better performance.
For example, the [NASA WorldView](https://worldview.earthdata.nasa.gov/) and [NASA-GIBS/OnEarth server](https://github.com/nasa-gibs/onearth) 
are using MRF as a web tile cache. An MRF can be updated at the same time as tiles are accessed by a tile server. 
The [mrf_insert](https://github.com/nasa-gibs/mrf/blob/master/mrf_apps/mrf_insert.cpp) utility allows a small region 
of an MRF to be updated efficiently, including the overview tiles affected, without distrubing the web server access 
to tiles in the same MRF.
For a simple web server solution using MRF and based on the Apache HTTPD server, use [mod_mrf](https://github.com/lucianpls/mod_mrf).

## Dealing with large MRF index files
MRF efficiently scales to very large areas. For example it is common to have MRFs that cover a whole planet at very high resolution, 
such as the [5m Mars CTX mosaic](http://astro.arcgis.com/CTX/index.html) or even larger.
MRF is also great for storing sparse datasets, where very few ares have actual data. The virtual size of the index file component of an
MRF does not depend on the amount on data stored but instead is proportional to the number of possible tiles. This is usually not a 
problem when the MRF is stored on a file system, since the MRF makes good use of file system holes, which are areas of a sparse file 
that contain no data. This means that the actual storage used may be much smaller than the virtual file size.
This feature can become a problem when transferring data to a different location, or on storage systems that do not support 
sparse files, AWS S3 for example. The recommended way to handle such sparse MRF index files is to use the [MRF can](https://github.com/nasa-gibs/mrf/blob/master/mrf_apps/can.cpp) utility. It can convert the sparse index into a dense form (canned) and then extract it back to a sparse file when needed.
The canned form of an index can be compressed further with any generic utility such as zip or gzip.
While the MRF GDAL driver itself cannot access an MRF with a canned index, the [mod_mrf](https://github.com/lucianpls/mod_mrf) 
tile handler does serve tiles from an MRF with a canned index.

## Single LERC data MRF
The MRF driver recognizes and reads a LERC and LERC1 compressed file. This type of file behaves as a read-only single tile MRF 
with LERC compression, without geo-reference. This feature is mostly intended to be used by the GDAL WMS driver. An open option, `DATATYPE`, 
can be used to set the data type when reading from LERC1 compressed data, since that information is not available in the LERC itself. 
The default data type for LERC1 is byte. LERC (V2) can only be read as the same data type it was encoded, the DATATYPE open option 
is ignored.

## Overwriting an MRF

When overwriting an MRF, GDAL normally tries to erase the files if they exist. To avoid having the data or the index file erased 
un-intentionally, the MRF driver does not do this. This means that if a file exists and is used repeatedly as a destination for 
gdal_translate, the data file will keep growing and the index file will keep its old content, which is the desired behavior. 
This can create problems in certain cases, for example when the same file name is reused for images of different size or structure, 
or when the MRF itself is corrupt. Crashes may occur in some of these situations. In these cases, the index and data file should 
be erased by hand, outside of the GDAL infrastructure.

# APPENDIX A, MRF specific environment variables

## MRF_BYPASSCACHING=FALSE|TRUE
Boolean, defaults to false. When set to TRUE and caching or cloning MRFs are in use, writes to the local MRF cache will not occur.
## CPL_DEBUG
This variable controls the [GDAL Logging](https://gdal.org/en/latest/user/configoptions.html#logging). In can hold
multiple concatenated control token strings, case insensitive. The presence of each recognized control token will turn
on logging of specific messages during gdal processing. MRF defines the following logging tokens:
* MRF : Top level MRF related operations
* MRF_TIMING : Accurate tile compression and decompression time is accumulated for each MRF dataset and are logged out when the
respective dataset is closed.
* MRF_IO : Details of MRF tile IO operations
* MRF_OVERLAY: Details of MRF overview building

# APPENDIX B, Index file format

The MRF index is a vector of tile records. A tile index record is sixteen bytes long and contains the tile offset and size, each 
stored as an eight byte unsigned integer in big endian order. In C, a tile index record is defined as

```
typedef struct {
 uint64_t offset;
 uint64_t size;
} tidx;
```

Example values in this document will be using the notation [Offset, Size] for a tile index. By convention the index for a tile 
which has no data written into it has the size of zero [R, 0].  This index record will generate a tile filled with zeros or 
NoData on read. The value for the offset is reserved and should be written as zero. An offset value of 1 and a size of 0 [1, 0] 
is used by the caching/cloning MRFs as a flag that a tile is zero or NoData in the source file. It will be read as zero without 
triggering a read from the source.

The order of the tile records in the index file depends on the type of MRF:
- Tile records are usually stored in top-left orientation, in row major order (Y, X).
- If the MRF contains multiple channels (Bands) and they are stored as band interleaved data, the band index changes first, then 
the spatial index (Y, X, C).
- If the MRF Z dimension is more than 1, each Z slice index is stored consecutively, thus Z varies after Y (Z, Y, X, C).
- If the MRF contains versions, the current version is stored at the start of the index file, immediately followed by version one 
and so on (V, Y, X, C) or (V, Z, Y, X, C).
- If there are overviews, the tile index vectors for the overviews immediately follow the index vector for the full resolution, in 
the decreasing order of resolution, (l;X,Y,C) or (l;Z,X,Y,C). Note that the vector for an overview level is smaller than the vector 
for the previous overview or base resolution.

- For cloning MRFs, the index of the local cache data is followed immediately by a copy of the cloned MRF index. The content of 
both may be updated during reads.

To print the content of the index in a human readable form, the following command can be used on UNIX. The first number is the offset, 
the second one the size of each tile
```
od -t u8 --endian big <input_file>
```
To check that the MRF data file does not have any slack, is to verify that the sum of the tile sizes equals the size 
of the data file. This can be done using:
```
od -td8 --endian=big TCI.idx |cut -c 40- | awk '{ sum += $1} END {print sum}'
```

# APPENDIX C, Create Options

In GDAL, a list of key-value string pairs can be used to pass various options to the target driver. Using the gdal_translate 
utility, these options are passed using the –co Key=Value syntax. Some of the names of the options supported by MRF have been 
chosen to match the ones used by TIFF. The create options supported by MRF are:

| Key | Default Value | Description |
| --- | --- | --- |
| BLOCKSIZE | 512 | The tile size in pixels for both X and Y axis |
| BLOCKXSIZE | 512 | Horizontal tile size |
| BLOCKYSIZE | 512 | Vertical tile size |
| INTERLEAVE | PIXEL or BAND, format dependent | PIXEL or BAND interleave |
| COMPRESS | PNG | Choses the tile packing algorithm |
| QUALITY | 85 | An integer value used to control the compression |
| INDEXNAME | | Filename to be used for the index |
| DATANAME | | Filename to be used for the data |
| ZSIZE | 1 | Specifies the third dimension size |
| NETBYTEORDER | FALSE | If true, for some packings, forces endianness dependent data to big endian when stored |
| PHOTOMETRIC |   | Sets the interpretation of the bands and controls some of the compression algorithms |
| SPACING | 0 | Reserve this many bytes before each tile data |
| NOCOPY | False | Create an empty MRF, do not copy input |
| UNIFORM_SCALE | | Flags the MRF as containing overviews, with a given numerical scale factor between successive overviews |
| CACHEDSOURCE | | GDAL raster reference to be cached in the caching MRF being created |
| OPTIONS | | A string that contains auxiliary create options, see appendix D |

# APPENDIX D, Free-form Create Options

In addition to the normal create options which are usually applicable to all supported tile packings 
and verified by the GDAL core, some MRF compressions accept a set of options that control features of 
only specific packing formats, or can be used to modify default behaviors. The main difference between 
the create options and free-form options is that the latter are saved in the MRF metadata file 
and may apply when a file is read, not only when it is written. The free form options are not 
part of the GDAL interface, and as such they are not checked for correctness when passed to the driver. 
If a free form option doesn't seem to have the expected effect, the exact spelling should be checked, 
they are case sensitive.

The free-form `OPTIONS` parameter takes a single string value. The value is a string containing white space separated 
key value pairs. GDAL list parsing is used when reading, either the equal sign `=` or the colon `:` 
may be used as the separator between key and value. Boolean flags default to `false`, they are treated as 
true only if the value is `Yes`, `True` or `1`.

For the gdal_translate utility, the free form option syntax is:  
 `-co OPTIONS="Key1:Value1 Key2:Value2 …"`

|Key|Default|Affected Format|Description|
| --- | --- | --- | --- |
| DEFLATE | False | Most | Apply zlib DEFLATE as a final compression stage |
| ZSTD | False | Most | Apply ZSTD as a final compression stage |
| GZ | False | DEFLATE | Generate gzip header style |
| RAWZ | False | DEFLATE | No zlib or gzip headers |
| Z_STRATEGY |  | PNG, DEFLATE | DEFLATE algorithmic choice: Z_HUFFMAN_ONLY, Z_FILTERED, Z_RLE, Z_FIXED |
| V1 | False | LERC | Uses LERC1 compression instead of LERC (V2) |
| LERC_PREC | 0.5 for integer types; 0.001  for floating point | LERC | Maximum value change allowed |
| L2_VER | 2 for single band, library default otherwise | LERC | Use features present in a specific Lerc library version |
| OPTIMIZE | False | JPEG, JPNG | Optimize the Huffman tables for each tile. Always true for JPEG12 |
| JFIF | False | JPEG, JPNG | When set, write JPEG tiles in JFIF format. By default, brunsli format is preferred |
| QB3_BAND_MAP || QB3 | A comma separated list of band indices for QB3 band decorrelation |

# APPENDIX E, Open Options

Starting with GDAL 2.x, a list of key-value string pairs can be used to pass various options to the target driver when reading. Using the 
gdal_translate utility, these options are passed using the –oo Key=Value syntax.

|Key|Default Value|Description|
| --- | --- | --- |
| ZSLICE | Integer | Sets the ZSlice to open in a 3rd dimension MRF|
| NOERRORS | False | If true, read errors will become warnings, allowing the read to continue past corrupt data|
| DATATYPE | Byte | Set the desired output datatype for single LERC1 chunk|

# APPENDIX F, Change Log

2025-06-05
* Add support for QB3_BAND_MAP free-form option, band decorrelation settings

2024-06-21
* Add support for 64 bit integer data type, signed and unsigned, for NONE, DEFLATE, ZSTD, QB3 and TIF tile format
* Add support for signed 8 bit integer

2024-06-30
* Add [mrf-in-tar](https://github.com/nasa-gibs/mrf/blob/master/doc/MUG.md#mrf-in-tar), a single file MRF format

2024-09-10
* QB3 encoding using the faster FTL mode when libQB3 has support for it and QUALITY setting is under 5
