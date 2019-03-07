## MRF Apps

A set of tools for working with MRF.

## mrf_clean.py

Copies the tile data and index files of an MRF, ignoring the unused parts.

## mrf_insert

Tool for inserting tiles into an existing MRF.

## mrf_join.py

Joins multiple MRF files with the same structure into a single one.

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

Generates an MRF from a set of tiles.