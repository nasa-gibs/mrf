/*
 * Copyright (c) 2002-2015, California Institute of Technology.
 * All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
 * Redistribution and use in source and binary forms, with or without modification, are permitted provided
 * that the following conditions are met:
 *   1. Redistributions of source code must retain the above copyright notice, this list of conditions and
 *      the following disclaimer.
 *   2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
 *      the following disclaimer in the documentation and/or other materials provided with the distribution.
 *   3. Neither the name of the California Institute of Technology (Caltech), its operating division the
 *      Jet Propulsion Laboratory (JPL), the National Aeronautics and Space Administration (NASA),
 *      nor the names of its contributors may be used to endorse or promote products derived from this software
 *      without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Copyright 2015 Esri
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "mrf_insert.h"

using namespace std;
USING_NAMESPACE_MRF

// Size and location from handle
img_info::img_info(GDALDatasetH hDS)
{
    double adfGT[6];
    GDALGetGeoTransform(hDS, adfGT);

    size.x = GDALGetRasterXSize(hDS);
    size.y = GDALGetRasterYSize(hDS);

    bbox.lx = adfGT[0];
    bbox.uy = adfGT[3];
    bbox.ux = adfGT[1] * size.x + bbox.lx;
    bbox.ly = adfGT[5] * size.y + bbox.uy;

    res.x = adfGT[1];
    res.y = adfGT[5];
}

static bool outside_bounds(const Bounds &inside, const Bounds &outside, XY tolerance)
{
    return (
        inside.lx + tolerance.x < outside.lx ||
        inside.ux - tolerance.x > outside.ux ||
        inside.ly + tolerance.y < outside.ly ||
        inside.uy - tolerance.y > outside.uy);
}

//
// Works like RasterIO, except that it trims the request as needed for the input image
// Only works with read currently
//
CPLErr ClippedRasterIO(GDALRasterBand *band, GDALRWFlag eRWFlag,
                       int nXOff, int nYOff,
                       int nXSize, int nYSize,
                       void *pData,
                       GDALDataType eBufType,
                       int nPixelSpace,
                       int nLineSpace)
{
    CPLAssert(GF_Read == eRWFlag);
    auto pcData = reinterpret_cast<char *>(pData);

    if (nXOff < 0)
    {
        // Adjust the start of the line
        // nXoff is negative, so this is addition
        pcData -= nXOff * nPixelSpace;
        nXSize += nXOff; // XOff is negative, so this is a subtraction
        nXOff = 0;
    }
    if (nXOff + nXSize > band->GetXSize())
    {
        // Clip end of lines
        nXSize = band->GetXSize() - nXOff;
    }

    if (nYOff < 0)
    {
        // Adjust the start of the column
        // nYoff is negative, so this is addition
        pcData -= nYOff * nLineSpace;
        nYSize += nYOff; // YOff is negative, so this is a subtraction
        nYOff = 0;
    }
    if (nYOff + nYSize > band->GetYSize())
    {
        // Clip end of columns
        nYSize = band->GetYSize() - nYOff;
    }

    // Call the raster band read with the trimmed values
    return band->RasterIO(GF_Read, nXOff, nYOff, nXSize, nYSize,
                          pcData, nXSize, nYSize, eBufType, nPixelSpace, nLineSpace, NULL);
}

// Insert the target in the base level
bool state::patch()
{
    if (TargetName.empty())
    {
        return false;
    }

    // These are the same thing, the handle for the C functions, the dataset class for C++
    union
    {
        GDALDatasetH hDataset;
        GDALDataset *pTDS;
        MRFDataset *pTarg;
    };

    union
    {
        GDALDatasetH hPatch;
        GDALDataset *pSDS;
    };

    CPLPushErrorHandler(CPLQuietErrorHandler);
    hDataset = GDALOpen(TargetName.c_str(), GA_Update);
    CPLPopErrorHandler();

    if (hDataset == NULL)
    {
        CPLError(CE_Failure, CPLE_AppDefined, "Can't open file %s for update", TargetName.c_str());
        return false;
    }

    try
    {
        // GetDescription is the driver name, uppercase
        if (!EQUAL(pTDS->GetDriver()->GetDescription(), "MRF"))
        {
            CPLError(CE_Failure, CPLE_AppDefined, "Target file is not an MRF");
            throw 1;
        }

        CPLPushErrorHandler(CPLQuietErrorHandler);
        hPatch = GDALOpen(SourceName.c_str(), GA_ReadOnly);
        CPLPopErrorHandler();

        if (hPatch == NULL)
        {
            CPLError(CE_Failure, CPLE_AppDefined, "Can't open file %s", SourceName.c_str());
            throw 1;
        }
    }
    catch (int e)
    {
        if (e > 0)
            GDALClose(hDataset);
        return false;
    }

    Bounds blocks_bbox;
    Bounds pix_bbox;
    int overview_count = 0;
    void *buffer = NULL;

    try
    {

        img_info in_img(hPatch);
        img_info out_img(hDataset);

        if (verbose != 0)
        {
            cerr << "Out " << out_img.bbox << endl
                 << "In " << in_img.bbox << endl;
        }

        // Tolerance of 1/2 of an output pixel
        XY tolerance;
        tolerance.x = fabs(out_img.res.x / 2);
        tolerance.y = fabs(out_img.res.y / 2);
        XY factor;
        factor.x = in_img.res.x / out_img.res.x;
        factor.y = in_img.res.y / out_img.res.y;

        if (!CPLIsEqual(factor.x, factor.y))
        {
            CPLError(CE_Failure, CPLE_AppDefined, "Scaling factor for X and Y are not the same");
            throw 2;
        }

        if (outside_bounds(in_img.bbox, out_img.bbox, tolerance))
        {
            CPLError(CE_Failure, CPLE_AppDefined, "Input patch outside of target");
            throw 2;
        }

        // tolerance of 1/1000 of the resolution
        if ((fabs(in_img.res.x - out_img.res.x) * 1000 > fabs(out_img.res.x)) ||
            (fabs(in_img.res.y - out_img.res.y) * 1000 > fabs(out_img.res.y)))
        {
            CPLError(CE_Failure, CPLE_AppDefined, "Source and target resolutions don't match");
            throw 2;
        }

        // Get the first band from the output MRF, which always exists, use it to
        // collect band count and block size
        GDALRasterBand *b0 = pTDS->GetRasterBand(1);
        int bands = pTDS->GetRasterCount();
        int tsz_x, tsz_y;
        b0->GetBlockSize(&tsz_x, &tsz_y);

        GDALDataType eDataType = b0->GetRasterDataType();
        overview_count = b0->GetOverviewCount();

        int pixel_size = GDALGetDataTypeSize(eDataType) / 8; // Bytes per pixel per band
        int line_size = tsz_x * pixel_size;                  // A line has this many bytes
        int buffer_size = line_size * tsz_y;                 // A block size in bytes

        //
        // Location in target (output MRF) pixels
        pix_bbox.lx = int((in_img.bbox.lx - out_img.bbox.lx) / in_img.res.x + 0.5);
        pix_bbox.ux = int((in_img.bbox.ux - out_img.bbox.lx) / in_img.res.x + 0.5);
        // note that uy < ly
        pix_bbox.uy = int((in_img.bbox.uy - out_img.bbox.uy) / in_img.res.y + 0.5);
        pix_bbox.ly = int((in_img.bbox.ly - out_img.bbox.uy) / in_img.res.y + 0.5);

        if (verbose != 0)
        {
            cerr << "Pixel location " << pix_bbox << endl
                 << "Factor " << factor.x << "," << factor.y << endl;
        }

        // First blocks to consider
        blocks_bbox.lx = int(pix_bbox.lx / tsz_x);
        blocks_bbox.ly = int(pix_bbox.ly / tsz_y);

        // Last block to consider
        blocks_bbox.ux = int(pix_bbox.ux / tsz_x);
        blocks_bbox.uy = int(pix_bbox.uy / tsz_y);

        if (verbose != 0)
        {
            cerr << "Blocks location " << blocks_bbox << endl;
        }

        // Build a vector of output bands
        vector<GDALRasterBand *> src_b;
        vector<GDALRasterBand *> dst_b;

        for (int band = 1; band <= bands; band++)
        {
            src_b.push_back(pSDS->GetRasterBand(band));
            dst_b.push_back(pTDS->GetRasterBand(band));
        }

        buffer = CPLMalloc(buffer_size); // Enough for one block

        //
        // Use the innner loop for bands, helps if output is interleaved
        //
        // Using the factor enables scaling of input
        // However, the input coverage still has to be exactly on
        // ouput block boundaries
        //
        if (start_level == 0) // Skip if start level is not zero
        {
            for (int y = static_cast<int>(blocks_bbox.uy); y <= static_cast<int>(blocks_bbox.ly); y++)
            {
                // Source offset relative to this block on y
                int src_offset_y = static_cast<int>(factor.y * tsz_y * y - pix_bbox.uy);

                for (int x = static_cast<int>(blocks_bbox.lx); x <= static_cast<int>(blocks_bbox.ux); x++)
                {
                    // Source offset relative to this block on x
                    int src_offset_x = static_cast<int>(factor.x * tsz_x * x - pix_bbox.lx);

                    for (int band = 0; band < bands; band++) // Counting from zero in a vector
                    {
                        if (verbose != 0)
                        {
                            cerr << "src_offset_x = " << src_offset_x << " src_offset_y = " << src_offset_y << endl;
                            cerr << " Y block " << y << " X block " << x << endl;
                        }
                        // READ

                        CPLErr eErr = CE_None;
                        // If input needs padding, initialize the buffer with destination content
                        if (src_offset_x < 0 || src_offset_x + tsz_x > src_b[band]->GetXSize() || src_offset_y < 0 || src_offset_y + tsz_y > src_b[band]->GetYSize())
                        {
                            // Clunky solution to this problem, but GDAL API does not support padding
                            if (x * tsz_x == dst_b[band]->GetXSize() || y * tsz_y == dst_b[band]->GetYSize())
                            {
                                continue;
                            }
                            eErr = dst_b[band]->RasterIO(GF_Read,
                                                         x * tsz_x, y * tsz_y,  // offset in output image
                                                         tsz_x, tsz_y,          // Size in output image
                                                         buffer, tsz_x, tsz_y,  // Buffer and size in buffer
                                                         eDataType,             // Requested type
                                                         pixel_size, line_size, // Pixel and line space
                                                         NULL                   // ExtraIO arguments
                            );
                            if (CE_None != eErr)
                            {
                                cerr << "Fill data read error" << endl;
                                throw static_cast<int>(eErr);
                            }
                        }

                        // Works just like RasterIO, except that it only reads the
                        // valid parts of the input band and has no scaling
                        eErr = ClippedRasterIO(src_b[band], GF_Read,
                                               src_offset_x, src_offset_y, // offset in input image
                                               tsz_x, tsz_y,               // Size in input image
                                               buffer,                     // buffer
                                               eDataType,                  // Requested type
                                               pixel_size, line_size);     // Pixel and line space
                        if (CE_None != eErr)
                        {
                            cerr << "Clipped rasterio read error" << endl;
                            throw static_cast<int>(eErr);
                        }

                        // WRITE
                        eErr = dst_b[band]->RasterIO(GF_Write,
                                                     x * tsz_x, y * tsz_y,  // offset in output image
                                                     tsz_x, tsz_y,          // Size in output image
                                                     buffer, tsz_x, tsz_y,  // Buffer and size in buffer
                                                     eDataType,             // Requested type
                                                     pixel_size, line_size, // Pixel and line space
                                                     NULL                   // ExtraIO arguments
                        );
                        if (CE_None != eErr)
                        {
                            cerr << "Read error" << endl;
                            throw static_cast<int>(eErr);
                        }
                    }
                }
            }
        }
        CPLFree(buffer);
    }
    catch (int e)
    {
        if (e > 0)
            GDALClose(hDataset);
        CPLFree(buffer);
        return false;
    }

    // Close input, flush output, then worry about overviews
    GDALClose(hPatch);
    GDALFlushCache(hDataset);

    // Call the PatchOverview for the MRF
    if (overlays)
    {
        // Initialize BlockX, BlockY, Width, and Height based on the bounding box
        auto BlockX = static_cast<int>(blocks_bbox.lx);
        auto BlockY = static_cast<int>(blocks_bbox.uy);
        auto Width = static_cast<int>(blocks_bbox.ux - blocks_bbox.lx);
        auto Height = static_cast<int>(blocks_bbox.ly - blocks_bbox.uy);

        // If stop_level is not set, process all levels
        if (stop_level == -1)
            stop_level = overview_count;

        // Convert level limits to source levels
        start_level--;

        // Loop through each source level
        for (int sl = 0; sl < overview_count; sl++)
        {
            if (sl >= start_level && sl < stop_level)
            {
                pTarg->PatchOverview(BlockX, BlockY, Width, Height,
                                     sl, false, Resampling);
                GDALFlushCache(hDataset);
            }

            // Update BlockX and BlockY for the next level (round down)
            int BlockXOut = BlockX / 2;
            int BlockYOut = BlockY / 2;

            // Adjust Width and Height before division
            Width += (BlockX & 1);  // Increment width if BlockX was rounded down
            Height += (BlockY & 1); // Increment height if BlockY was rounded down

            // Compute WidthOut and HeightOut for the next level (round up)
            int WidthOut = Width / 2 + (Width & 1);
            int HeightOut = Height / 2 + (Height & 1);

            // Prepare for the next iteration
            BlockX = BlockXOut;
            BlockY = BlockYOut;
            Width = WidthOut;
            Height = HeightOut;
        }
    }

    // Now for the upper levels
    GDALFlushCache(hDataset);
    GDALClose(hDataset);
    return true;
}

/************************************************************************/
/*                               Usage()                                */
/************************************************************************/

static int Usage()

{
    printf(
        "Usage: mrf_insert [-r {Avg, NNb}]\n"
        "\t\t[-q] [--help-general] source_file(s) target_file\n"
        "\n"
        "\t-start_level <N> : first level to insert into (0)\n"
        "\t-end_level <N> : last level to insert into (last)\n"
        "\t-r : choice of resampling method (default: average)\n"
        "\t-q : turn off progress display\n");

    return 1;
}

int main(int nArgc, char **papszArgv)
{
    state State;
    int ret = 0;

    std::vector<std::string> fnames;

    /* Check that we are running against at least GDAL 3.x */
    /* Note to developers : if using newer API, please change the requirement */
    if (atoi(GDALVersionInfo("VERSION_NUM")) < 3000)
    {
        fprintf(stderr, "At least, GDAL >= 3.0.0 is required for this version of %s, "
                        "which was compiled against GDAL %s\n",
                papszArgv[0], GDAL_RELEASE_NAME);
        exit(1);
    }

    GDALAllRegister();

    //
    // Set up a reasonable large cache size, say 256MB
    GDALSetCacheMax(256 * 1024 * 1024);
    //
    // Done before the CmdLineProcessor has looked at options, so it can be overriden by the user
    // by setting the GDAL_CACHEMAX env, or passing it as a --config option
    //
    // See http://trac.osgeo.org/gdal/wiki/ConfigOptions
    //

    // Pick up the GDAL options
    nArgc = GDALGeneralCmdLineProcessor(nArgc, &papszArgv, 0);
    if (nArgc < 1)
        exit(-nArgc);

    /* -------------------------------------------------------------------- */
    /*      Parse commandline, set up state                                 */
    /* -------------------------------------------------------------------- */

    for (int iArg = 1; iArg < nArgc; iArg++)
    {
        if (EQUAL(papszArgv[iArg], "--utility_version"))
        {
            printf("%s was compiled against GDAL %s and is running against GDAL %s\n",
                   papszArgv[0], GDAL_RELEASE_NAME, GDALVersionInfo("RELEASE_NAME"));
            return 0;
        }
        else if (EQUAL(papszArgv[iArg], "-start_level") && iArg < nArgc - 1)
        {
            State.setStart(strtol(papszArgv[++iArg], 0, 0));
        }
        else if (EQUAL(papszArgv[iArg], "-stop_level") && iArg < nArgc - 1)
        {
            State.setStop(strtol(papszArgv[++iArg], 0, 0));
        }
        else if (EQUAL(papszArgv[iArg], "-r") && iArg < nArgc - 1)
        {
            // R is required for building overviews
            State.setResampling(papszArgv[++iArg]);
            State.setOverlays();
        }
        else if (EQUAL(papszArgv[iArg], "-q") || EQUAL(papszArgv[iArg], "-quiet"))
        {
            State.setProgress(GDALDummyProgress);
        }
        else if (EQUAL(papszArgv[iArg], "-v"))
        {
            State.setDebug(1);
        }
        else
        {
            fnames.push_back(papszArgv[iArg]);
        }
    }

    // Need at least a target and a source
    if (fnames.size() > 0)
    {
        State.setTarget(fnames[fnames.size() - 1]);
        fnames.pop_back();
    }

    if (fnames.empty())
    {
        return Usage();
    }

    try
    {
        // Each input file in sequence, as they were passed as arguments
        for (int i = 0; i < fnames.size(); i++)
        {
            State.setSource(fnames[i]);

            // false return means error was detected and printed, just exit
            if (!State.patch())
            {
                throw 2;
            }
        }
    } // Try, all execution
    catch (int err_ret)
    {
        ret = err_ret;
    };

    // General cleanup
    CSLDestroy(papszArgv);
    GDALDestroyDriverManager();
    return ret;
}
