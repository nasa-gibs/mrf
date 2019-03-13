#!/usr/bin/env python

# Copyright (c) 2002-2015, California Institute of Technology.
# All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
#     the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
#     endorse or promote products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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

from optparse import OptionParser
import os
import shutil
import struct
import traceback

versionNumber = '1.0'
   
def write_idx(didx, lidx):
   'Write a chunk of the index file or just extend the file'
   
   if sum(i[1] for i in lidx):
      didx.write(struct.pack(">{0}Q".format(2 * len(lidx)), *sum(lidx, ())))
   else:
      didx.seek(16 * len(lidx), os.SEEK_CUR)


#-------------------------------------------------------------------------------   

print 'mrf_condense.py v' + versionNumber

usageText = 'mrf_condense.py --input [mrf_file] --empty_tile [empty_tile_file] (--output [output_dir] --remove_orig --verbose)'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-i', '--input',
              action='store', type='string', dest='input',
              help='Full path of the MRF data file')
parser.add_option('-e', '--empty_tile',
              action='store', type='string', dest='empty_tile',
              help='Full path of the empty tile file')
parser.add_option('-o', '--output',
              action='store', type='string', dest='output',
              help='Full path of output directory, if different from input file')
parser.add_option("-k", "--remove_orig", action="store_true", dest="remove", 
              default=False, help="Remove the original MRF data and index files. .orig extension added if co-located with output")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
              default=False, help="Verbose mode")


# Read command line args.
(options, args) = parser.parse_args()

if not options.input:
   parser.error('input filename not provided. --input must be specified.')
else:
   inputDataFile = os.path.realpath(options.input)

if not options.empty_tile:
   parser.error('empty tile filename not provided. --empty_tile must be specified.')
else:
   emptyTileFile = os.path.realpath(options.empty_tile)

if not options.output:
   outputDir = os.path.dirname(inputDataFile)
else:
   outputDir = os.path.realpath(options.output)


if not os.path.exists(inputDataFile):
   print "\nInput MRF data file does not exist, exiting."
   exit(-1)

if not os.path.exists(emptyTileFile):
   print "\nEmpty tile file does not exist, exiting."
   exit(-1)
   
if not os.path.exists(outputDir):
   try:
      os.makedirs(outputDir)
   except:
      print "\nUnable to create output directory, exiting."
      if options.verbose: print(traceback.format_exc())
      exit(-1)


bname, ext = os.path.splitext(inputDataFile)

inputIdxFile   = bname + os.extsep + "idx"   
inputMrfFile   = bname + os.extsep + "mrf"   

tmpDataFile    = os.path.join(outputDir, os.path.basename(inputDataFile) + ".new")
tmpIdxFile     = inputIdxFile + ".new"
tmpMrfFile     = inputMrfFile + ".new"

outputDataFile = os.path.join(outputDir, os.path.basename(inputDataFile))
outputIdxFile  = os.path.join(outputDir, os.path.basename(inputIdxFile))
outputMrfFile  = os.path.join(outputDir, os.path.basename(inputMrfFile))


# Remove the temporary files if they already exist
if os.path.exists(tmpDataFile):
   os.remove(tmpDataFile)
if os.path.exists(tmpIdxFile):
   os.remove(tmpIdxFile)


# Print out the original file size
if options.verbose:
   fileSizeMB = float(os.stat(inputDataFile).st_size / (1024 * 1024))
   if fileSizeMB > 1024.0:
      fileSizeGB = float(fileSizeMB/1024.0)
      print "\nOriginal File Size: " + str(int(fileSizeGB)) + " GB"
   else:
      print "\nOriginal File Size: " + str(int(fileSizeMB)) + " MB"
   

# Condense!
print ("\nCondensing data file: " + inputDataFile)

shutil.copy(inputMrfFile, tmpMrfFile)

try:
   with open(inputIdxFile, "rb") as srcIdx:
      with open(inputDataFile, "rb") as srcData:
         with open(tmpIdxFile,"wb") as destIdx:
            with open(tmpDataFile, "wb") as destData:

               # Extend or create the output files
               destIdx.seek(0, os.SEEK_END)
               
               destData.seek(0, os.SEEK_END)
               destOffset = destData.tell()
               
               destData.write(open(emptyTileFile,"rb").read())
               destOffset = destData.tell()
   
               tempIdx = []
                        
               # Copy every tile in sequence
               # Not the fastest, but the simplest
               for tile in iter(lambda: srcIdx.read(16), ''):
                  srcOffset, size = struct.unpack(">QQ", tile)
                  if size:
                     srcData.seek(srcOffset, os.SEEK_SET)
                     destData.write(srcData.read(size))
                     srcOffset = destOffset
                     destOffset += size
                  else:
                     srcOffset = 0
                  
                  tempIdx.append((srcOffset, size))
                  
                  if 32 == len(tempIdx): # 32 tile records, 512 bytes
                     write_idx(destIdx, tempIdx)
                     tempIdx = []
        
               # Write the remaining index chunk and mark the file end
               if len(tempIdx):
                  write_idx(destIdx, tempIdx)
               destIdx.truncate()

   # Set the permissions/mod times no the new files to match
   shutil.copystat(inputIdxFile, tmpIdxFile)
   shutil.copystat(inputDataFile, tmpDataFile)
   shutil.copystat(inputMrfFile, tmpMrfFile)
   
               
   # If keeping the original...
   if not options.remove:

      # If input and output directories are the same, rename the input 
      # files with an .orig extension
      if os.path.dirname(outputIdxFile) == os.path.dirname(inputIdxFile):
         
         if os.path.exists(inputDataFile + ".orig"):
            os.remove(inputDataFile + ".orig")
         if os.path.exists(inputIdxFile + ".orig"):
            os.remove(inputIdxFile + ".orig")
         if os.path.exists(inputMrfFile + ".orig"):
            os.remove(inputMrfFile + ".orig")
                     
         shutil.move(inputDataFile, inputDataFile + ".orig")
         shutil.move(inputIdxFile, inputIdxFile + ".orig")
         shutil.move(inputMrfFile, inputMrfFile + ".orig")
      
         if options.verbose:
            print ("\nOriginal data file renamed: " + inputDataFile + ".orig")
            print ("Original index file renamed: " + inputIdxFile + ".orig")
            print ("Original mrf file renamed: " + inputMrfFile + ".orig")
      
      # Else input and output directories are different, no need to rename the input files

   # Else remove the input files
   else:
      os.remove(inputDataFile)
      os.remove(inputIdxFile)
      os.remove(inputMrfFile)
      
      if options.verbose:
            print ("\nOriginal data file removed: " + inputDataFile + ".orig")
            print ("Original index file removed: " + inputIdxFile + ".orig")
            print ("Original mrf file removed: " + inputMrfFile + ".orig")

   
   # Now move the temp files into their final resting place
   shutil.move(tmpDataFile, outputDataFile)
   shutil.move(tmpIdxFile, outputIdxFile)
   shutil.move(tmpMrfFile, outputMrfFile)
   
   if options.verbose:
      fileSizeMB = float(os.stat(outputDataFile).st_size / (1024 * 1024))
      if fileSizeMB > 1024.0:
         fileSizeGB = float(fileSizeMB/1024.0)
         print "\nCondensed File Size: " + str(int(fileSizeGB)) + " GB"
      else:
         print "\nCondensed File Size: " + str(int(fileSizeMB)) + " MB"

   print "\nMRF successfully condensed into " + outputDir

except:
   print "\nError condensing MRF, exiting."
   print(traceback.format_exc())

   # Cleanup the output files if they were created
   if os.path.exists(tmpDataFile):
      os.remove(tmpDataFile)
   if os.path.exists(tmpIdxFile):
      os.remove(tmpIdxFile)
   if os.path.exists(tmpMrfFile):
      os.remove(tmpMrfFile)

   exit(-1)