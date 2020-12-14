#!/usr/bin/env python3
#
# Name: mrf_join
# Purpose:

'''Joins multiple MRF files with the same structure into a single one'''

# Created: 11/08/2018
# Updated: 12/14/2018 - Added Z dimension append mode
# Updated: 12/09/2020 - Updated to python3
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
import argparse
import glob

# hexversion >> 16 >= 0x306 (for 3.6 or later)
assert sys.hexversion >> 24 >= 0x3, "Python 3 required"

def appendfile(srcname, dstname):
    with open(dstname, 'ab') as ofile:
        with open(srcname, 'rb') as ifile:
            for chunk in iter(lambda : ifile.read(1024 * 1024), b""):
                ofile.write(chunk)

def mrf_join(argv, forceoffset = None):
    '''Input file given as list, the last one is the output
 Given the data file names, including the extension, which should be the same 
 for all files, the .idx and the .mrf extensions are assumed.
 The last file name is the otput, it will be created in case it doesn't exist.
 Tile from inputs are added in the order in which they appear on the command line, 
 except the output file, if it exists, which ends up first.
    '''
    assert len(argv) >= 2,\
       "Takes a list of input mrf data files to be concatenated, the last is the output, which will be created if needed"
    ofname, ext = os.path.splitext(argv[-1])
    assert ext not in ('.mrf', '.idx'),\
       "Takes data file names as input, not the .mrf or .idx"
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
        # Only create the data file if forceoffset is not given
        if forceoffset is None:
            with open(ofname + ext, "wb") as data_file:
                pass

    idxsize = os.path.getsize(ofname + '.idx')
    for f in input_list:
        assert os.path.getsize(os.path.splitext(f)[0] + '.idx') == idxsize,\
            "All input index files should have the same size {}, {} does not".format(idxsize, f)

    # At this point the output exist, loop over the inputs
    for input_file in argv[:-1]:
        print("Processing {}".format(input_file))
        fname = os.path.splitext(input_file)[0]
        offset = forceoffset
        if offset is None:
            # Offset to adjust start of tiles in this input
            offset = os.path.getsize(ofname + ext)
            # Copy the data file at the end of the current file, in 1MB chunks
            appendfile(input_file, ofname + ext)

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

                    # If the input block is all zeros, no need to write it
                    if inidx.count(0) == len(outidx):
                        continue

                    # Got some input content, there is work to do
                    if sys.byteorder != 'big': # MRF index is always big endian
                        inidx.byteswap()
                        outidx.byteswap()

                    for i in range(0, len(inidx), 2):
                        if inidx[i + 1] != 0: # Copy existing tiles indices
                            outidx[i] = inidx[i] + offset # Add the starting offset to every tile
                            outidx[i + 1] = inidx[i + 1]

                    if sys.byteorder != 'big':
                        outidx.byteswap()

                    # Write it where it was read from
                    ofile.seek(- len(outidx) * outidx.itemsize, io.SEEK_CUR)
                    outidx.tofile(ofile)

# Integer division of x/y, rounded up
def rupdiv(x, y):
    return 1 + (x - 1) // y

def getpcount(size, pagesize):
    return rupdiv(size['x'], pagesize['x'])\
         * rupdiv(size['y'], pagesize['y'])\
         * rupdiv(size['c'], pagesize['c'])

def getmrfinfo(fname):
    import xml.etree.ElementTree as ET
    tree = ET.parse(fname)
    root = tree.getroot()
    assert root.tag == "MRF_META", "{} is not an MRF".format(fname)
    info = {}
    info['size'] = { key : int(val) for (key, val) in 
                    root.find("./Raster/Size").attrib.items() }

    if root.find("./Raster/PageSize"):
        info['pagesize'] = { key : int(val) for (key, val) in 
                        root.find("./Raster/PageSize").attrib.items() }
    else:
        info['pagesize'] = {
            'x' : 512,
            'y' : 512,
            'c' : info['size']['c'] if 'c' in info['size'] else 1
        }

    if root.find("./Rsets") is not None:
        assert root.find("./Rsets").get('model') == 'uniform', "Only uniform model rsets are supported"
        try:
            info['scale'] = int(root.find("./Rsets").get('scale'))
        except:
            info['scale'] = 2

    # compute the pagecount per level, level 0 always exists
    sz = info['size']
    info['pages'] = [getpcount(sz, info['pagesize'])]

    if 'scale' in info:
        scale = info['scale']
        # This is either 1 or the number of bands
        bandpages = rupdiv(info['size']['c'], info['pagesize']['c'])
        while info['pages'][-1] != bandpages:
            sz['x'] = rupdiv(sz['x'], scale)
            sz['y'] = rupdiv(sz['y'], scale)
            info['pages'].append(getpcount(sz, info['pagesize']))
    info['totalpages'] = sum(info['pages'])

    return info, tree

# Creates the file if it doesn't exist, then truncates it to the given size
def ftruncate(fname, size = 0):
    try:
        with open(fname, "r+b") as f:
            assert os.path.getsize(fname) <= size, "Output index file exists and has the wrong size"
            f.truncate(size)
    except:
        with open(fname, "wb") as f:
            f.truncate(size)

def write_mrf(tree, zsz, fname):
    root = tree.getroot()
    assert root.tag == "MRF_META", "Invalid tree, not an mrf"
    size = root.find("./Raster/Size")
    size.set('z', str(zsz))
    tree.write(fname)

def mrf_append(inputs, output, outsize, startidx = 0):
    ofname, ext = os.path.splitext(output)
    assert ext not in ('.mrf', '.idx'),\
       "Takes data file names as arguments"
    for f in inputs:
        assert os.path.splitext(f)[1] == ext,\
            "All input files should have the same extension as the output"
    # Get the template mrf information from the first input
    mrfinfo, tree = getmrfinfo(os.path.splitext(inputs[1])[0] + ".mrf", ofname + ".mrf")

    # Create the output .mrf if it doesn't exist
    if not os.path.isfile(ofname + ".mrf"):
        write_mrf(tree, outsize, ofname + ".mrf")

    inidxsize = 16 * mrfinfo['totalpages']
    outidxsize = outsize * inidxsize
    # Make sure the output is the right size
    ftruncate(ofname + ".idx", outidxsize)
    if not os.path.isfile(output):
        # Try to create it
        with open(output, "wb") as o:
            pass

    for fn in inputs:
        # Create the output file if not there and get its current size
        with open(output, "a+b") as o:
            dataoffset = os.path.getsize(output)

        fname, iext = os.path.splitext(fn)
        assert iext == ext, \
            "File {} should have extension {}".format(fn, ext)
        assert os.path.getsize(fname + ".idx") == inidxsize, \
            "Index for file {} has invalid size, expected {}".format(fn, inidxsize)
        appendfile(fn, output)
        with open(fname + ".idx", "rb") as inidx:
            with open(ofname + ".idx", "r+b") as outidx:
                for level in range(len(mrfinfo['pages'])):
                    outidxoffset = startidx * mrfinfo['pages'][level]
                    if level > 0:
                        outidxoffset += sum(mrfinfo['pages'][0:level]) * outsize
                    outidx.seek(16 * outidxoffset, io.SEEK_SET)
                    # Copy tile by tile, don't write zeros
                    for tnum in range(mrfinfo['pages'][level]):
                        tinfo = array.array('Q')
                        tinfo.fromfile(inidx, 2)
                        # If the input block is all zeros, no need to write it
                        if tinfo.count(0) == len(tinfo):
                            outidx.seek(16, io.SEEK_CUR)
                            continue
                        if sys.byteorder != 'big':
                            tinfo.byteswap()
                        tinfo[0] += dataoffset
                        if sys.byteorder != 'big':
                            tinfo.byteswap()
                        tinfo.tofile(outidx)
        startidx += 1

def main():
    def auto_int(x):
        return int(x, 0)

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output",
                        help = "Output file name, otherwise the last file name is the output")
    parser.add_argument("-z", "--zsize", type = auto_int,
                        help = "The output is a 3rd dimension MRF into which inputs are inserted as slices")
    parser.add_argument("-s", "--slice", type = auto_int,
                        help = "Used only with -z, which is the first target slice, defaults to 0")
    parser.add_argument("-f", "--forceoffset", type = auto_int,
                        help = "Provide an offset to be used when adding one input index to the output. Data files are ignored")

    parser.add_argument("fnames", nargs='+')
    args = parser.parse_args()
    fnames = args.fnames
    # On windows, call the glob expliticly
    if not isinstance(fnames, (list, tuple)):
        fnames = glob.glob(fnames)

    if args.zsize is not None:
        assert args.output is not None, "-z option requires an explicit output file name"
        assert args.forceoffset is None, "-z option can't use a forced offset"
        slice = args.slice if args.slice is not None else 0
        return mrf_append(fnames, args.output, args.zsize, slice)

    # Default action is mrf_join, takes the output as the last argument
    if args.output is not None:
        fnames.append(args.output)
    if args.forceoffset is not None:
        assert len(fnames) == 2, "Forced offset works only with one input"
    mrf_join(fnames, forceoffset = args.forceoffset)

if __name__ == "__main__":
    main()
