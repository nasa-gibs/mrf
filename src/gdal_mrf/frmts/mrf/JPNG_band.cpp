/*
* Copyright 2016 Esri
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

/*
* JPNG band, uses JPEG or PNG encoding, depending on the input data
*/

#include "marfa.h"
#include <cassert>

CPL_C_START
#include <jpeglib.h>

#ifdef INTERNAL_PNG
#include "../png/libpng/png.h"
#else
#include <png.h>
#endif
CPL_C_END

NAMESPACE_MRF_START

// Are all pixels in the tile opaque?
static bool opaque(const buf_mgr &src, const ILImage &img) {
int stride = img.pagesize.c;
    char *s = src.buffer + img.pagesize.c - 1;
    char *stop = src.buffer + img.pageSizeBytes;
    while (s < stop && 255 == static_cast<unsigned char>(*s))
        s += stride;
    return (s >= stop);
}

// Strip the alpha from an RGBA buffer
static void RGBA2RGB(const char *start, const char *stop, char *target) {
    while (start < stop) {
        *target++ = *start++;
        *target++ = *start++;
        *target++ = *start++;
        start++; // Skip the alpha
    }
}

// Strip the alpha from an Luma Alpha buffer
static void LA2L(const char *start, const char *stop, char *target) {
    while (start < stop) {
        *target++ = *start++;
        start++; // Skip the alpha
    }
}

CPLErr JPNG_Band::Decompress(buf_mgr &dst, buf_mgr &src)
{
    return CE_Failure;
}

// The PNG internal palette is set on first band write
CPLErr JPNG_Band::Compress(buf_mgr &dst, buf_mgr &src)
{
    ILImage image(img);
    CPLErr retval = CE_None;

    buf_mgr temp;
    temp.size = img.pageSizeBytes; // No need for a larger buffer
    temp.buffer = (char *)(CPLMalloc(temp.size));
    if (temp.buffer == NULL) {
        CPLError(CE_Failure, CPLE_OutOfMemory, "Allocating temporary JPNG buffer");
        return CE_Failure;
    }

    try {
        if (opaque(src, image)) { // If all pixels are opaque, compress as JPEG
            if (image.pagesize.c == 4)
                RGBA2RGB(src.buffer, src.buffer + src.size, temp.buffer);
            else
                LA2L(src.buffer, src.buffer + src.size, temp.buffer);

            image.pagesize.c -= 1; // RGB or Grayscale only for JPEG
            JPEG_Codec codec(image);
            codec.rgb = rgb;
            codec.optimize = optimize;
            codec.sameres = sameres;
            retval = codec.CompressJPEG(dst, temp);
        }
        else {
            PNG_Codec codec(image);
            retval = codec.CompressPNG(dst, src);
        }
    }
    catch (CPLErr err) {
        retval = err;
    }

    CPLFree(temp.buffer);
    return retval;
}

/**
* \Brief For PPNG, builds the data structures needed to write the palette
* The presence of the PNGColors and PNGAlpha is used as a flag for PPNG only
*/

JPNG_Band::JPNG_Band(GDALMRFDataset *pDS, const ILImage &image, int b, int level) :
GDALMRFRasterBand(pDS, image, b, level), 
sameres(FALSE), rgb(FALSE), optimize(false)

{   // Check error conditions
    if (image.dt != GDT_Byte) {
	CPLError(CE_Failure, CPLE_NotSupported, "Data type not supported by MRF JPNG");
	return;
    }
    if (image.order != IL_Interleaved || image.pagesize.c != 4 && image.pagesize.c != 2) {
	CPLError(CE_Failure, CPLE_NotSupported, "MRF JPNG can only handle 2 or 4 interleaved bands");
	return;
    }

    if (img.pagesize.c == 4) { // RGBA can have storage flavors
        CPLString const &pm = pDS->GetPhotometricInterpretation();
        if (pm == "RGB" || pm == "MULTISPECTRAL") { // Explicit RGB or MS
            rgb = TRUE;
            sameres = TRUE;
        }
        if (pm == "YCC")
            sameres = TRUE;
    }

    optimize = GetOptlist().FetchBoolean("OPTIMIZE", FALSE) != FALSE;

    // PNGs and JPGs can be larger than the source, especially for small page size
    poDS->SetPBufferSize(image.pageSizeBytes + 100);
}

JPNG_Band::~JPNG_Band() {
}

NAMESPACE_MRF_END
