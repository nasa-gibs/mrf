#!/usr/bin/env python3
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


import errno
import hashlib
import struct
from optparse import OptionParser
import os
import sys
from functools import reduce

prog = os.path.basename(sys.argv[0])

def help(parser):
    parser.print_help()
    print("""
Arguments:
  path_template   Path to the image tiles using {x}, {y}, and {z} to
                  denote the column, row, and zoom level number. Example:
                       tiles/{z}/{x}/{y}.png
  output_base     Base name of the output MRF files without the file
                  extension.
""")

def option_error(parser, msg):
    print("{0}: ERROR: {1}\n".format(prog, msg), file=sys.stderr)
    help(parser)
    sys.exit(1)

def half(val):
    'Divide by two with roundup, returns integer value at least 1'
    return 1 + (val - 1 ) // 2

def hash_tile(tile):
    h = hashlib.sha256()
    h.update(tile)
    return h.digest()

def update_status(last_status, status):
    counter = last_status
    while counter <= status:
        if counter % 10 == 0:
            print(int(counter), end="")
            sys.stdout.flush()
        else:
            print(".", end="")
            sys.stdout.flush()
        counter += 2.5
    return counter

def process_tiles(options, args, fout, fidx):
    template = args[0]
    offset = 0
    tiles = 0
    count = 0
    last_status = 0
    blank = 0

    notile = struct.pack('!QQ', 0, 0)
    sz = [ options.width, options.height]
    sizes = []
    for level in range(options.levels):
        sizes += [sz]
        sz = [half(v) for v in sz]

#   Reverse because level 0 is the lowest resolution

    sizes.reverse()
    tiles = reduce(lambda total, s: total + s[0] * s[1], sizes, 0)
    print("Input tile count: {0}".format(tiles))

    if options.blank_tile:
        with open(options.blank_tile, "rb") as fblank:
            blank_tile = fblank.read()
        blank_hash = hash_tile(blank_tile)

    for z in range(options.levels -1, -1, -1):
        w,h = sizes[z]
        for y in range(0, h):
            for x in range(0, w):
                tile_name = template.format(x=x, y=y, z=z)
                bytes = open(tile_name, "rb").read()
                to_write = True
                if options.blank_tile:
                    hash_value = hash_tile(bytes)
                    if hash_value == blank_hash:
                        fidx.write(notile)
                        to_write = False
                        blank += 1
                if to_write:
                    fout.write(bytes)
                    tile_length = len(bytes)
                    fidx.write(struct.pack('!QQ', offset, tile_length))
                    offset += tile_length
                count += 1
                status = (float(count) / tiles) * 100
                last_status = update_status(last_status, status)

    # If the final level isn't exactly 1x1, pad until there
    sz = sizes[0]
    pads = 0
    while sz[0]*sz[1] != 1:
        pads += sz[0]*sz[1]
        sz = [half(v) for v in sz]
    for i in range(pads):
        fidx.write(notile)

    print(" - done.")

    if blank > 0:
        print("{0} blank tile(s)".format(blank))
    if pads > 0:
        print("{0} padding tile(s)".format(pads))

def main():
    usage = "Usage: %prog [options] path_template output_base"
    parser = OptionParser(usage=usage, add_help_option=False)
    parser.add_option("-b", "--blank-tile", type="string",
                      metavar="file",
                      help="Tiles that match the checksum of this file "
                      "will be omitted and marked as a blank tile")
    parser.add_option("-d", "--debug", default=False, action="store_true",
                      help="Rethrow exceptions to see backtraces")
    parser.add_option("-l", "--levels", default=1,
                      type="int", metavar="count",
                      help="Number of zoom levels. Default is one.")
    parser.add_option("-f", "--format", default="ppg", metavar="{ppg,pjg}",
                      help="Output format. Default is ppg.")
    parser.add_option("-h", "--height", default=1,
                      type="int", metavar="tile_count",
                      help="Number of tiles in the y direction at the "
                      "highest resolution. Default is one.")
    parser.add_option("-w", "--width", default=1,
                      type="int", metavar="tile_count",
                      help="Number of tiles in the x direction at the "
                      "highest resolution. Default is one.")
    parser.add_option("--help", action="store_true",
                      help="Shows this help message")
    (options, args) = parser.parse_args()


    if options.help:
        help(parser)
        sys.exit(0)

    if len(args) != 2:
        option_error(parser, "Invalid number of arguments")
    if options.levels < 0:
        option_error(parser, "Invalid levels: {0}".format(options.levels))
    if options.width < 1:
        option_error(parser, "Invalid width: {0}".format(options.width))
    if options.height < 1:
        option_error(parser, "Invalid height: {0}".format(options.height))
    if options.format not in ("ppg", "pjg"):
        option_error(parser, "Invalid format: {0}".format(options.format))

    output_base = args[1]
    tiles_file = output_base + "." + options.format
    index_file = output_base + ".idx"

    try:
        with open(tiles_file, "wb") as fout:
            with open(index_file, "wb") as fidx:
                process_tiles(options, args, fout, fidx)
    except Exception as e:
        print("\n{0}: ERROR: {1}".format(prog, str(e)), file=sys.stderr)
        if options.debug:
            raise
        sys.exit(1)

if __name__ == "__main__":
    main()
