#-------------------------------------------------------------------------------
# Name:        mrf_clean
# Purpose:
# Copy the tile data and index files of an MRF, ignoring the unused parts
#
# Author:      lucian
#
# Created:     05/10/2016
# Updated:     07/07/2017 Creates index files with holes if possible
#
# Copyright:   (c) lucian 2016 - 2017
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

import struct
import os
import os.path
import sys

def index_name(mrf_name):
    bname, ext = os.path.splitext(mrf_name)
    return bname + os.extsep + "idx"


def write_idx(didx, lidx):
    'Write a chunk of the index file or just extend the file'
    if sum(i[1] for i in lidx):
        didx.write(struct.pack(">{0}Q".format(len(lidx)), *sum(lidx, ())))
    else:
        didx.seek(16 * len(lidx), os.SEEK_CUR)

def main(source, destination, empty_file = None):
    '''Copies the active tile from a source to a destination MRF'''
    sidx = open(index_name(source), "rb")
    sfile = open(source, "rb")
    # Create the output files
    didx = open(index_name(destination),"wb")
    dfile = open(destination, "wb")
    doffset = dfile.tell()
    if empty_file:
        dfile.write(open(empty_file,"rb").read())
        doffset = dfile.tell()

    lidx = []
    # Copy every tile in sequence
    # Not the fastest, but the simplest
    for tile in iter(lambda: sidx.read(16), ''):
        offset, size = struct.unpack(">2Q", tile)
        if size:
            sfile.seek(offset, os.SEEK_SET)
            dfile.write(sfile.read(size))
            offset = doffset
            doffset += size
        else:
            offset = 0
        lidx.append((offset, size))
        if 32 == len(lidx): # 32 tile records, 512 bytes
            write_idx(didx, lidx)
            lidx = []

    # Write the remaining index chunk and mark the file end
    if len(lidx):
        write_idx(didx, lidx)
    didx.truncate()

if __name__ == '__main__':
    main(*sys.argv[1:])

