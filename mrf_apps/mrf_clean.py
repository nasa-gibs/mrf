#-------------------------------------------------------------------------------
# Name:        mrf_clean
# Purpose:
# Copy the tile data and index files of an MRF, ignoring the unused parts
#
# Author:      lucian
#
# Created:     05/10/2016
# Updated:     07/07/2017 Creates index files with holes if possible
# Updated:     11/09/2018 Use typed arrays instead of struct
#                         Process index file block at a time
#
# Copyright:   (c) lucian 2016 - 2018
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
import array

# empty_file content is used to initialize the data file
def mrf_clean(source, destination, empty_file = None):
    '''Copies the active tile from a source to a destination MRF'''

    def index_name(mrf_name):
        bname, ext = os.path.splitext(mrf_name)
        return bname + os.extsep + "idx"

    with open(index_name(source), "rb") as sidx:
        with open(source, "rb") as sfile:
            with open(index_name(destination),"wb") as didx:
                with open(destination, "wb") as dfile:
                    if empty_file:
                        dfile.write(open(empty_file,"rb").read())
                    doffset = dfile.tell()

                    while True:
                        try:
                            idx = array.array('Q')
                        except ValueError: # likely Python 2.7 
                            idx = array.array('L')
                            
                            if not idx.itemsize == 8:
                                raise ValueError("Platform does not support unsigned 8 byte long type")
                        try:
                            idx.fromfile(sidx, 512 // idx.itemsize)
                        except: # Could be incomplete last block or EOF
                            if len(idx) == 0:
                                break # Normal exit

                        # Don't write empty blocks
                        if idx.count(0) == len(idx):
                            didx.seek(len(idx) * idx.itemsize, os.SEEK_CUR)
                            continue

                        if sys.byteorder != 'big':
                            idx.byteswap() # To native

                        # copy tiles in this block, adjust the offsets
                        for i in range(0, len(idx), 2):
                            if idx[i + 1] != 0: # size of tile
                                sfile.seek(idx[i], os.SEEK_SET)
                                idx[i] = doffset
                                doffset += idx[i + 1]
                                dfile.write(sfile.read(idx[i+1]))

                        if sys.byteorder != 'big':
                            idx.byteswap() # Back to big before writing

                        idx.tofile(didx)

                    didx.truncate() # In case last block is empty


if __name__ == '__main__':
    mrf_clean(*sys.argv[1:])
