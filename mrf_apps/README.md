## MRF Apps

MRF Tools for working with MRF files.

## mrf_insert

Tool for inserting data into an existing MRF. Partial overviews can be  generated, for the regions affected by the new data. Location of the inserted data is controlled by the georegistration.

## can
Transforms an MRF index file between the normal format and a compact, **canned** format, which does not store the sparse regions. This allows for efficient storage of very large MRFs on storage media that doesn't support sparse files, such as object stores. This is the recommended way to transfer MRF files with large, sparse index files between systems. The canned format has to be un-canned on a file system with sparse file support before use by GDAL. The MRF tile server **mod_mrf** is able to use the canned index as is, for reading the tiles.

## jxl

MRF tile convertor between JFIF-JPEG and JPEG-XL (brunsli), works for MRF and for esri bundles. When used with MRF, it takes a single argument, the data file (default extension .pjg). The output is written to the same location, with .jxl extension added (also .jxl.idx). Add -r to reverse the conversion, ie from JPEG-XL to JFIF-JPEG. To compile, the brunsli library and public header has to be installed

## mrf_clean.py

Copies the active tile data and index files of an MRF, ignoring the potential unused parts. It preserves the sparseness of the index file, it is the recommended way to transfer an MRF from one file system to another.

## mrf_join.py

Joins two or more MRF files with similar structure into a single one. It can be used to combine MRF content in 2D, or to stack 2D MRFs in a 3-rd dimension MRF.

## mrf\_read_data.py

The mrf_read_data.py tool reads an MRF data file from a specified index and offset and outputs the contents as an image.

```Shell
Usage: mrf_read_data.py --input [mrf_data_file] --output [output_file] (--offset INT --size INT) OR (--index [index_file] --tile INT)

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -i INPUT, --input=INPUT
                        Full path of the MRF data file
  -f OFFSET, --offset=OFFSET
                        data offset
  -l, --little_endian   Use little endian instead of big endian (default)
  -n INDEX, --index=INDEX
                        Full path of the MRF index file
  -o OUTPUT, --output=OUTPUT
                        Full path of output image file
  -s SIZE, --size=SIZE  data size
  -t TILE, --tile=TILE  tile within index file
  -v, --verbose         Verbose mode
```

## mrf\_read_idx.py

The mrf_read_idx.py tool reads an MRF index file and outputs the contents to a CSV file.

```Shell
Usage: mrf_read_idx.py --index [index_file] --output [output_file]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -i INDEX, --index=INDEX
                        Full path of the MRF index file
  -l, --little_endian   Use little endian instead of big endian (default)
  -o OUTPUT, --output=OUTPUT
                        Full path of output CSV file
  -v, --verbose         Verbose mode
```

## mrf_read.py

The mrf_read.py tool reads MRF files and outputs the contents as an image.

```Shell
Usage: mrf_read.py --input [mrf_file] --output [output_file] (--tilematrix INT --tilecol INT --tilerow INT) OR (--offset INT --size INT) OR (--tile INT)

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -i INPUT, --input=INPUT
                        Full path of the MRF data file
  -f OFFSET, --offset=OFFSET
                        data offset
  -l, --little_endian   Use little endian instead of big endian (default)
  -o OUTPUT, --output=OUTPUT
                        Full path of output image file
  -s SIZE, --size=SIZE  data size
  -t TILE, --tile=TILE  tile within index file
  -v, --verbose         Verbose mode
  -w TILEMATRIX, --tilematrix=TILEMATRIX
                        Tilematrix (zoom level) of tile
  -x TILECOL, --tilecol=TILECOL
                        The column of tile
  -y TILEROW, --tilerow=TILEROW
                        The row of tile
  -z ZLEVEL, --zlevel=ZLEVEL
                        the z-level of the data
```

## mrf_size.py

Builds a GDAL VRT that visualizes the size of tiles in an MRF index.

## tiles2mrf.py

Assembles an MRF from a set of tiles on disk.

