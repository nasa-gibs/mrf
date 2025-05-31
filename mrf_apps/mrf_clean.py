#!/usr/bin/env python3

#-------------------------------------------------------------------------------
# Name:        mrf_clean
# Purpose:
# Copy the tile data and index files of an MRF, ignoring the unused parts
#
# Author:      lucian plesea
#
# Created:     05/10/2016
# Updated:     07/07/2017 Creates index files with holes if possible
# Updated:     11/09/2018 Use typed arrays instead of struct
#                         Process index file block at a time
# Updated:     12/09/2020 Updated to python3
# Updated:     05/31/2025 Added trim mode to remove unused space in place
# Updated:     05/31/2025 Added command line parser
#
# Copyright:   (c) lucian 2016 - 2025
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
#-------------------------------------------------------------------------------

import os
import os.path
import sys
import argparse
from array import array

# Get the 64 bit unsigned integer type 
try:
    TYPEL = 'Q'
    idx = array('Q')
except ValueError: # likely Python 2
    TYPEL = 'L'
    idx = array('L')
if not idx.itemsize == 8:
    raise ValueError("Platform does not support unsigned 8 byte long type")
del idx

def index_name(mrf_name):
    bname, ext = os.path.splitext(mrf_name)
    return bname + os.extsep + "idx"

def mrf_trim(args):
    '''
    Cleans the MRF in place, overwriting it, not safe while reading.
    If anything goes wrong, the original file may be corrupted.
    Should only be used when the MRF is not in use and the disk space is tight.
    '''
    # TODO: Add option to deal with padded tiles, i.e. tiles prefixed by a number of bytes
    # Read the whole index file
    with open(index_name(args.source), "rb") as sidx:
        full_idx = array(TYPEL)
        full_idx.fromfile(sidx, os.path.getsize(index_name(args.source)) // full_idx.itemsize)
    if sys.byteorder != 'big':
        full_idx.byteswap()
    # Create a list of tuples (offset, size, index) 
    idx_list = []
    for i in range(0, len(full_idx), 2):
        idx_list.append((full_idx[i], full_idx[i + 1], i // 2))
    offset = int(args.empty_file) if args.empty_file else 0
    # See if the file has any slack space
    full_size = sum(size for _, size, _ in idx_list) + offset
    old_size = os.path.getsize(args.source)
    if full_size == old_size:
        print("No unused space in the MRF, nothing to do")
        return 0
    if full_size > os.path.getsize(args.source):
        raise ValueError("The MRF file is smaller than the sum of tiles, cannot trim")
    print(f"Trimming MRF file, current size: {old_size}, new size: {full_size}")

    # Sort by offset
    idx_list.sort(key=lambda x: x[0])

    with open(args.source, "r+b") as mrf_file:
        for tile in idx_list:
            o, s, i = tile
            if s == 0:
                continue
            if o < offset: # Borken MRF
                raise ValueError("MRF is corrupted, tile offset {} is under the current offset {}".format(o, offset))
            if o == offset: # Tile is already at the current offset
                offset += s
                continue
            # Move the tile to the current offset
            mrf_file.seek(o)
            data = mrf_file.read(s)
            mrf_file.seek(offset)
            mrf_file.write(data)
            # Update the index
            full_idx[i * 2] = offset
            assert full_idx[i * 2 + 1] == s, "Tile size mismatch in index"
            offset += s
        # Truncate the data file to new size
        mrf_file.truncate(offset)
    # Write the new index file
    with open(index_name(args.source), "wb") as idx_file:
        if sys.byteorder != 'big':
            full_idx.byteswap()  # To big endian

        # Write the index file in block of 512 bytes, skipping holes
        for i in range(0, len(full_idx), 512 // full_idx.itemsize):
            block = full_idx[i:i + 512 // full_idx.itemsize]
            block = block.tobytes()
            if block != b'\x00' * len(block):  # Skip empty blocks
                idx_file.write(block)
            else:
                idx_file.seek(len(block), os.SEEK_CUR)  # Skip empty block
        idx_file.truncate() # In case there is a hole at the end

    return 0

# empty_file content is used to initialize the data file
def mrf_clean(source, destination, empty_file = None):
    '''Copies the active tile from a source to a destination MRF'''

    with open(index_name(source), "rb") as sidx:
        with open(source, "rb") as sfile:
            with open(index_name(destination), "wb") as didx:
                with open(destination, "wb") as dfile:
                    if empty_file:
                        dfile.write(open(empty_file, "rb").read())
                    doffset = dfile.tell()

                    while True:
                        idx = array(TYPEL)
                        try:
                            idx.fromfile(sidx, 512 // idx.itemsize)
                        except EOFError:  # Could be incomplete last block or EOF
                            if len(idx) == 0:
                                break  # Normal exit

                        # Don't write empty blocks
                        if idx.count(0) == len(idx):
                            didx.seek(len(idx) * idx.itemsize, os.SEEK_CUR)
                            continue

                        if sys.byteorder != 'big':
                            idx.byteswap()  # To native

                        # copy tiles in this block, adjust the offsets
                        for i in range(0, len(idx), 2):
                            if idx[i + 1] != 0:  # size of tile
                                sfile.seek(idx[i], os.SEEK_SET)
                                idx[i] = doffset
                                doffset += idx[i + 1]
                                dfile.write(sfile.read(idx[i+1]))

                        if sys.byteorder != 'big':
                            idx.byteswap()  # Back to big before writing
                        idx.tofile(didx)

                didx.truncate()  # In case last block is empty


def main():
    # Get the arguments, add copy if first argument is not copy or trim
    cmdargs = sys.argv[1:]
        
    if len(cmdargs) == 0 or cmdargs[0] in ('-h', '--help'):
        if len(cmdargs) == 0:
            cmdargs.append('-h') # Show help if no arguments are given
    else:
        if cmdargs[0] not in ('copy', 'trim'):
            cmdargs.insert(0, 'copy')

    parser = argparse.ArgumentParser(description='Clean an MRF file')
    # Two modes, in-place and copy
    subparsers = parser.add_subparsers(dest = 'mode')

    parser_copy = subparsers.add_parser('copy', 
                                        help='Copy the MRF data to a new file, ignoring unused space')
    parser_copy.add_argument('source', help='Source MRF file')
    parser_copy.add_argument('destination', help='Destination MRF file')
    parser_copy.add_argument('empty', nargs='?' , help='File to initialize the destination MRF data file', default=None)

    parser_trim = subparsers.add_parser('trim',
                                        help='Trim the MRF in place, removing unused space. Unsafe while reading')
    parser_trim.add_argument('source', help='Source MRF file to trim')
    parser_trim.add_argument('-e', '--empty', type = int, default = 0,
                             help='Size of empty tile located at the start of the file')

    args = parser.parse_args(cmdargs)

    if args.mode == 'copy':
        return mrf_clean(args.source, args.destination, args.empty)
    
    # For in-place, the empty file can be either None or a number
    empty_file = args.empty if args.empty else None
    try:
        args.empty_file = int(empty_file) if empty_file else None
    except ValueError:
        raise ValueError("If present in the in-place mode, the empty " \
        "file argument must be the number of bytes at the start of the data file")

    return mrf_trim(args)

if __name__ == '__main__':
    main()
