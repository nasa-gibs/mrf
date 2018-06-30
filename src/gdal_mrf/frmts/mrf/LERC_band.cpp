/*
Copyright 2013-2015 Esri
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
A local copy of the license and additional notices are located with the
source distribution at:
http://github.com/Esri/lerc/

LERC band implementation
LERC page compression and decompression functions

Contributors:  Lucian Plesea
*/

#include "marfa.h"
#include <algorithm>
#include <limits>
#include "Lerc.h"
#include "Lerc_types.h"

CPL_CVSID("$Id: LERC_band.cpp 39464 2017-07-04 13:42:10Z rouault $")

USING_NAMESPACE_LERC

NAMESPACE_MRF_START

static GDALDataType GetL2DataType(Lerc::DataType L2type) {
    GDALDataType dt;
    switch (L2type) {
    case Lerc::DT_Byte:  dt = GDT_Byte; break;
    case Lerc::DT_Short: dt = GDT_Int16; break;
    case Lerc::DT_UShort: dt = GDT_UInt16; break;
    case Lerc::DT_Int: dt = GDT_Int32; break;
    case Lerc::DT_UInt: dt = GDT_UInt32; break;
    case Lerc::DT_Float: dt = GDT_Float32; break;
    case Lerc::DT_Double: dt = GDT_Float64; break;
    default: dt = GDT_Unknown;
    }
    return dt;
}
static Lerc::DataType GetGDALDataType(GDALDataType gdtype) {
    Lerc::DataType dt;
    switch (gdtype) {
    case GDT_Byte:  dt = Lerc::DT_Byte; break;
    case GDT_Int16: dt = Lerc::DT_Short; break;
    case GDT_UInt16: dt = Lerc::DT_UShort; break;
    case GDT_Int32: dt = Lerc::DT_Int; break;
    case GDT_UInt32: dt = Lerc::DT_UInt; break;
    case GDT_Float32: dt = Lerc::DT_Float; break;
    case GDT_Float64: dt = Lerc::DT_Double; break;
    default: dt = Lerc::DT_Float;
    }
    return dt;
}

// Populate a bitmask based on comparison with the image no data value
template <typename T> static void UnMask(BitMask &bitMask, T *arr, const ILImage &img)
{
    int w = img.pagesize.x;
    int h = img.pagesize.y;
    if (w * h == bitMask.CountValidBits())
        return;
    T *ptr = arr;
    T ndv = T(img.NoDataValue);

    // fixme ??
    // It doesn't get called when img doesn't have NoDataValue
    // "0" may also be used to define valid values in the raster dataset
    if (!img.hasNoData) ndv = 0;
    for (int i = 0; i < h; i++)
        for (int j = 0; j < w; j++, ptr++)
            if (!bitMask.IsValid(i, j))
                *ptr = ndv;
    return;
}

// Populate a bitmask based on comparison with the image no data value
// Returns the number of NoData values found
template <typename T> static int MaskFill(BitMask &bitMask, T *src, const ILImage &img)
{
    int w = img.pagesize.x;
    int h = img.pagesize.y;
    int count = 0;

    bitMask.SetSize(w, h);
    bitMask.SetAllValid();

    // No data value
    T ndv = static_cast<T>(img.NoDataValue);
    // It really doesn't get called when img doesn't have NoDataValue
    if (!img.hasNoData) ndv = 0;

    for (int i = 0; i < h; i++)
        for (int j = 0; j < w; j++)
            if (ndv == *src++) {
                bitMask.SetInvalid(i, j);
                count++;
            }

    return count;
}


CPLErr LERC_Band::Decompress(buf_mgr &dst, buf_mgr &src)
{
    const Byte *ptr = reinterpret_cast<Byte *>(src.buffer);
    Lerc::LercInfo lercInfo;

    if (ErrCode::Ok != Lerc::GetLercInfo(ptr, static_cast<unsigned int>(src.size), lercInfo)) {
    	CPLError(CE_Failure, CPLE_AppDefined, "MRF_LERC: get lerc info failure");
    	return CE_Failure;
    }

    CPLDebug("MRF_LERC", "lerc info, version: %d, dt: %d, cols: %d, rows: %d, nBands: %d,"
        "precision: %f, blobSize: %d, zMax: %f, zMin: %f\n",
        lercInfo.version, lercInfo.dt, lercInfo.nCols, lercInfo.nRows, lercInfo.nBands,
        lercInfo.maxZError,
        lercInfo.blobSize, lercInfo.zMax, lercInfo.zMin);

    if (static_cast<size_t>(lercInfo.blobSize) > src.size) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF: Lerc2 object too large");
        return CE_Failure;
    }

    if (img.pagesize.x != lercInfo.nCols
        || img.pagesize.y != lercInfo.nRows
        || img.dt != GetL2DataType(lercInfo.dt)
        || dst.size < static_cast<size_t>(lercInfo.nCols * lercInfo.nRows * GDALGetDataTypeSizeBytes(img.dt))) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF: Lerc2 format error");
        return CE_Failure;
    }

    // we need to add the padding bytes so that out-of-buffer-access checksum
    // don't false-positively trigger.
    size_t nRemaingBytes = src.size + PADDING_BYTES;
    BitMask bitMask(img.pagesize.x, img.pagesize.y);
    // first try Lerc2, then try Lerc1
    if (ErrCode::Ok != Lerc::Decode(ptr,
    	static_cast<unsigned int>(nRemaingBytes),
    	&bitMask,
    	lercInfo.nCols, lercInfo.nRows, 1,
    	lercInfo.dt,
    	dst.buffer)
    ) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF: Error during LERC2 decompression");
        return CE_Failure;
    }
    if (!img.hasNoData)
        return CE_None;

    // Fill in no data values
    switch (img.dt) {
#define UNMASK(T) UnMask(bitMask, reinterpret_cast<T *>(dst.buffer), img)
    case GDT_Byte:      UNMASK(GByte);      break;
    case GDT_UInt16:    UNMASK(GUInt16);    break;
    case GDT_Int16:     UNMASK(GInt16);     break;
    case GDT_Int32:     UNMASK(GInt32);     break;
    case GDT_UInt32:    UNMASK(GUInt32);    break;
    case GDT_Float32:   UNMASK(float);      break;
    case GDT_Float64:   UNMASK(double);     break;
    default:            CPLAssert(false);   break;
#undef UNMASK
    }

    bitMask.Clear();
    return CE_None;
}

CPLErr LERC_Band::Compress(buf_mgr &dst, buf_mgr &src)
{
    if (version < 2) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF_LERC: Version 1 is not supported");
        return CE_Failure;
    }

    int nBands = 1;
    int w = img.pagesize.x;
    int h = img.pagesize.y;

    unsigned int sz = 0;
    unsigned int numBytesWritten = 0;

    Lerc::DataType outDt = GetGDALDataType(eDataType);

    if (src.size > (std::numeric_limits<size_t>::max)() ) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF: src object too large");
        return CE_Failure;
    }

    int ndv_count = 0;
    BitMask bitMask;
    bitMask.SetSize(w, h);
    bitMask.SetAllValid();

    if (img.hasNoData) { // Only build a bitmask if no data value is defined
        switch (img.dt) {
#define MASK(T) ndv_count = MaskFill(bitMask, reinterpret_cast<T *>(src.buffer), img)
        case GDT_Byte:          MASK(GByte);    break;
        case GDT_UInt16:        MASK(GUInt16);  break;
        case GDT_Int16:         MASK(GInt16);   break;
        case GDT_Int32:         MASK(GInt32);   break;
        case GDT_UInt32:        MASK(GUInt32);  break;
        case GDT_Float32:       MASK(float);    break;
        case GDT_Float64:       MASK(double);   break;
        default:                CPLAssert(false); break;
#undef MASK
        }
    }

    if (ErrCode::Ok != Lerc::ComputeCompressedSize((Byte *)src.buffer,
        outDt,
        w, h, nBands,
        ndv_count == 0 ? NULL : &bitMask, precision, sz)) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF_LERC: compute compressed size failure");
        bitMask.Clear();
        return CE_Failure;
    }

    if (sz > dst.size) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF: Lerc2 object too large");
        bitMask.Clear();
        return CE_Failure;
    }
    CPLDebug("MRF_LERC", "src size: %ld, width: %d, height: %d, precision: %f, src type: %d, out type: %d, ComputeCompressedSize %ld\n",
        src.size, w, h, precision, eDataType, outDt, dst.size
        );

    if (ErrCode::Ok != Lerc::Encode((Byte *)src.buffer,
        outDt,
        w, h, nBands,
        ndv_count == 0 ? NULL : &bitMask,
        precision,
        (Byte *)dst.buffer,
        (unsigned int)dst.size, // buffer size
        numBytesWritten) // num bytes written to buffer
    ) {
        CPLError(CE_Failure, CPLE_OutOfMemory, "MRF_LERC: encode failure");
        bitMask.Clear();
        return CE_Failure;
    }

    dst.size = numBytesWritten;
    bitMask.Clear();
    return CE_None;
}

CPLXMLNode *LERC_Band::GetMRFConfig(GDALOpenInfo *poOpenInfo)
{
    // Should have enough data pre-read
    // if(poOpenInfo->nHeaderBytes <
    //     static_cast<int>(CntZImage::computeNumBytesNeededToWriteVoidImage()))
    // {
    //     return NULL;
    // }
    if (poOpenInfo->eAccess != GA_ReadOnly
        || poOpenInfo->pszFilename == NULL
        || poOpenInfo->pabyHeader == NULL
        || strlen(poOpenInfo->pszFilename) < 2)
        return NULL;

    // Check the header too
    char *psz = reinterpret_cast<char *>(poOpenInfo->pabyHeader);
    CPLString sHeader;
    sHeader.assign(psz, psz + poOpenInfo->nHeaderBytes);
    if (!IsLerc(sHeader))
        return NULL;

    // Get the desired type
    const char *pszDataType = CSLFetchNameValue(poOpenInfo->papszOpenOptions, "DATATYPE");
    GDALDataType dt = GDT_Unknown; // Use this as a validity flag
    if (pszDataType)
        dt = GDALGetDataTypeByName(pszDataType);


    // Use this structure to fetch width and height
    ILSize size(-1, -1, 1, 1, 1);


    Lerc::LercInfo lercInfo;
    if (0 != (int)Lerc::GetLercInfo(reinterpret_cast<Byte *>(psz), poOpenInfo->nHeaderBytes, lercInfo)) {
        CPLError(CE_Failure, CPLE_AppDefined, "MRF_LERC: get lerc info failure");
        return NULL;
    }

    size.x = lercInfo.nCols;
    size.y = lercInfo.nRows;
    dt = GetL2DataType(lercInfo.dt);

    if (size.x <=0 || size.y <=0 || dt == GDT_Unknown)
        return NULL;

    // Build and return the MRF configuration for a single tile reader
    CPLXMLNode *config = CPLCreateXMLNode(NULL, CXT_Element, "MRF_META");
    CPLXMLNode *raster = CPLCreateXMLNode(config, CXT_Element, "Raster");
    XMLSetAttributeVal(raster, "Size", size, "%.0f");
    XMLSetAttributeVal(raster, "PageSize", size, "%.0f");
    CPLCreateXMLElementAndValue(raster, "Compression", CompName(IL_LERC));
    CPLCreateXMLElementAndValue(raster, "DataType", GDALGetDataTypeName(dt));
    CPLCreateXMLElementAndValue(raster, "DataFile", poOpenInfo->pszFilename);
    // Set a magic index file name to prevent the driver from attempting to open itd
    CPLCreateXMLElementAndValue(raster, "IndexFile", "(null)");

    return config;
}

LERC_Band::LERC_Band(GDALMRFDataset *pDS, const ILImage &image,
                      int b, int level ) :
    GDALMRFRasterBand(pDS, image, b, level)
{
    // Pick 1/1000 for floats and 0.5 losless for integers.
    if (eDataType == GDT_Float32 || eDataType == GDT_Float64 )
        precision = strtod(GetOptionValue( "LERC_PREC" , ".001" ),NULL);
    else
        precision =
            std::max(0.5, strtod(GetOptionValue("LERC_PREC", ".5"), NULL));

    // Encode in V2 by default.
    version = GetOptlist().FetchBoolean("V1", FALSE) ? 1 : 2;

    if( image.pageSizeBytes > INT_MAX / 2 )
    {
        CPLError(CE_Failure, CPLE_AppDefined, "Integer overflow");
        return;
    }
    // Enlarge the page buffer in this case, LERC may expand data.
    pDS->SetPBufferSize( 2 * image.pageSizeBytes);
}

LERC_Band::~LERC_Band() {}

NAMESPACE_MRF_END
