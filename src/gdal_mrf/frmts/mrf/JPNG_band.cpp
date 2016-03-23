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

CPLErr JPNG_Band::Decompress(buf_mgr &dst, buf_mgr &src)
{
    return CE_Failure;
}

// The PNG internal palette is set on first band write
CPLErr JPNG_Band::Compress(buf_mgr &dst, buf_mgr &src)
{
    return CE_Failure;
}

/**
* \Brief For PPNG, builds the data structures needed to write the palette
* The presence of the PNGColors and PNGAlpha is used as a flag for PPNG only
*/

JPNG_Band::JPNG_Band(GDALMRFDataset *pDS, const ILImage &image, int b, int level) :
GDALMRFRasterBand(pDS, image, b, level)

{   // Check error conditions
    if (image.dt != GDT_Byte) {
	CPLError(CE_Failure, CPLE_NotSupported, "Data type not supported by MRF JPNG");
	return;
    }
    if (image.pagesize.c != 4 && image.pagesize.c != 2) {
	CPLError(CE_Failure, CPLE_NotSupported, "MRF PNG can only handle up to 4 bands per page");
	return;
    }

    // PNGs can be larger than the source, especially for small page size
    poDS->SetPBufferSize(image.pageSizeBytes + 100);
}

JPNG_Band::~JPNG_Band() {
}


NAMESPACE_MRF_END
