#!/usr/bin/env python
#
# Name: mrf_join
# Purpose:

'''Joins multiple MRF files with the same structure into a single one'''

# Created: 11/08/2018
# Updated: 
#
# Author: Lucian Plesea
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import io
import sys
import array

# hexversion >> 16 >= 0x306 (for 3.6 or later)
assert sys.hexversion >> 24 >= 0x3, "Python 3 required"

def mrf_join(argv):
    '''Input file given as list, the last one is the output
 Given the data file names, including the extension, which should be the same 
 for all files, the .idx and the .mrf extensions are assumed.
 The last file name is the otput, it will be created in case it doesn't exist.
 Tile from inputs are added in the order in which they appear on the command line, 
 except the output file, if it exists, which ends up first.
    '''
    assert len(argv) > 2,\
       "Takes a list of input mrf data files to be concatenated, the last is the output, which will be created if needed"
    ofname, ext = os.path.splitext(argv[-1])
    assert ext not in ('.mrf', '.idx'),\
       "Takes data file names as input"
    input_list = argv[:-1]
    for f in input_list:
        assert os.path.splitext(f)[1] == ext,\
            "All input files should have the same extension"

    if not os.path.isfile(ofname + ext): # Create the output using the first file info
        ffname = os.path.splitext(input_list[0])[0]
        # Copy the .mrf file content
        with open(ffname + '.mrf', "rb") as mrf_file:
            with open(ofname + '.mrf', "wb") as omrf_file:
                omrf_file.write(mrf_file.read())
        with open(ofname + '.idx', "wb") as idx_file:
            idx_file.truncate(os.path.getsize(ffname + '.idx'))
        with open(ofname + ext, "wb") as data_file:
            pass

    idxsize = os.path.getsize(ofname + '.idx')
    for f in input_list:
        assert os.path.getsize(os.path.splitext(f)[0] + '.idx') == idxsize,\
            "All input index files should have the same size {}, {} does not".format(idxsize, f)

    # At this point the output exist, loop over the inputs
    for input_file in argv[:-1]:
        fname = os.path.splitext(input_file)[0]
        # Offset to adjust start of tiles in this input
        offset = os.path.getsize(ofname + ext)

        # Copy the data file at the end of the current file, in 1MB chunks
        with open(ofname + ext, 'ab') as ofile:
            with open(fname + ext, 'rb') as ifile:
                for chunk in iter(lambda : ifile.read(1024 * 1024), b""):
                    ofile.write(chunk)

        # Now for the hard job, tile by tile, adjust the index and write it
        with open(ofname + '.idx', 'r+b') as ofile:
            with open(fname + '.idx', 'rb') as ifile:
                while True: # Process index files, block at a time
                    # Read as quads, to avoid individual conversions
                    outidx = array.array('Q')
                    inidx  = array.array('Q')

                    try: # Read a chunk of the output
                        outidx.fromfile(ofile, 512 // outidx.itemsize)
                    except EOFError:
                        if len(outidx) == 0:
                            break # This is the exit condition, reached the end of index

                    try:                     # Same for the input index
                        inidx.fromfile(ifile, 512 // outidx.itemsize)
                    except EOFError:
                        # This has to be the last non-zero chunk, size matches the output file read
                        assert len(inidx) == len(outidx), \
                            "Error reading from index file {}".format(fname + '.idx')

                    # If the input block has no tiles, no changes are needed
                    if inidx.count(0) == len(outidx):
                        continue

                    # Got some input content, there is work to do
                    if sys.byteorder is 'little': # MRF index is big endian
                        inidx.byteswap()
                        outidx.byteswap()

                    for i in range(0, len(inidx), 2):
                        if inidx[i + 1] is not 0: # Only modify tiles in input
                            outidx[i] = inidx[i] + offset # Add the starting offset to every tile
                            outidx[i + 1] = inidx[i + 1]  # Tile size

                    if sys.byteorder is 'little':
                        outidx.byteswap()

                    # Write it where it was read from
                    ofile.seek(- len(outidx) * outidx.itemsize, io.SEEK_CUR)
                    outidx.tofile(ofile)

if __name__ == "__main__":
    mrf_join(sys.argv[1:])
