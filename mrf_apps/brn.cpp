#include <brunsli/encode.h>
#include <brunsli/decode.h>
#include <string>
#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <sys/stat.h>
#include <cstdlib>
#include <fcntl.h>
#include <sys/types.h>

#if defined(_WIN32)
#if !defined(_WIN64)
#error "Need 64bit support"
#endif
#include <Windows.h>
#include <io.h>

#define FSEEK _fseeki64
#define FTELL _ftelli64

// Windows is always little endian, supply functions to swap bytes
// These are defined in <cstdlib>
#define htobe64 _byteswap_uint64
#define be64toh _byteswap_uint64

#else // Linux

#include <unistd.h>
#include <endian.h>
// Check that we can seek large files
static_assert(sizeof(off_t) == 8);
#define FSEEK fseeko
#define FTELL ftello
#endif

using namespace std;

int Usage(const string &s) {
    std::cerr << s << endl << endl
        << "Synopsis: brn [OPTIONS] <source-file>\n"
        << "\t-r\tReverse, convert BRUNSLI input to JFIF\n"
        << "\t-b\tBundle (esri v2) input, default is MRF\n"
        << "\t-s\tSingle image, input is a JFIF or BRUNSLI (with -r)\n";
    return 1;
}

static size_t out_fun(vector<uint8_t> *output, const uint8_t *data, size_t size) {
    copy(data, data+size, back_inserter(*output));
    return size;
}

// Big Endian native
struct tinfo {
    uint64_t offset;
    uint64_t size;
    void toh() {
        offset = be64toh(offset);
        size = be64toh(size);
    }
    void tonative() {
        offset = htobe64(offset);
        size = htobe64(size);
    }
};

// Single file, either BRUNSLI or JFIF
int single_to_brn(const string &inname, bool reverse = false) {
    auto outname = inname + (reverse ? ".jfif" : ".brn");
    auto fin = fopen(inname.c_str(), "rb");
    if (!fin) return Usage("Can't open input file");
    FSEEK(fin, 0, SEEK_END);
    auto insize = ftell(fin);
    rewind(fin);
    // Check a max size of 128MB
    if (insize > (1ull << 27)) return Usage("Input file too large, limit is 128MB");
    vector<uint8_t> input(insize);
    fread(input.data(), insize, 1, fin);
    fclose(fin);
    auto fout = fopen(outname.c_str(), "wb");
    if (!fout) return Usage("Can't open output file");
    // Convert
    vector<uint8_t> tilebuf;
    int result = reverse ?
        DecodeBrunsli(insize, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun)
        : EncodeBrunsli(insize, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun);
    if (!result) return Usage(reverse ? "Error decoding BRUNSLI" : "Error encoding BRUNSLI");
    fwrite(tilebuf.data(), tilebuf.size(), 1, fout);
    fclose(fout);
    return 0;
}

// From MRF, separate files, inname is the data file
int mrf_to_brn(const string &inname, const string &outname, bool reverse = false) {
    // Assume three letter data file extension
    if ('.' != inname[inname.size() - 4])
        return Usage("Expect mrf data file with three letter file name extension");

    struct stat statb;
    if (stat(inname.c_str(), &statb)) 
        return Usage("Can't stat input file");
    auto insize = statb.st_size;

    // Indes should be same file with extension changed
    string inidxname(inname);
    inidxname.resize(inidxname.size() - 3);
    inidxname += "idx";
    // cout << "Opening " << inname << " and " << inidxname << endl;
    auto finidx = fopen(inidxname.c_str(), "rb");
    auto fin = fopen(inname.c_str(), "rb");
    if (!finidx || !fin)
        return Usage("Can't open input data or index file");
    
    string outidxname(outname.substr(0, outname.size() - 4) + ".idx");
    // cout << "Opening " << outname << " and " << outidxname << endl;
    auto fout = fopen(outname.c_str(), "wb");
    auto foutidx = fopen(outidxname.c_str(), "wb");
    tinfo tile;
    vector<uint8_t> input;
    vector<uint8_t> tilebuf;
    uint64_t ooff = 0;

    // Stats, saving ratio
    double min_rat = 1;
    double max_rat = -100;
    while (fread(&tile, sizeof(tile), 1, finidx)) {
        if (0 == tile.size) continue;
        tile.toh();
        FSEEK(fin, tile.offset, SEEK_SET);
        input.resize(tile.size);
        if (!fread(input.data(), tile.size, 1, fin)) {
            std::cerr << "Location " << hex << tile.offset << " size " << tile.size << dec << endl;
            return Usage("Failed to read input tile");
        }
        tilebuf.clear();

        int result = reverse ?
            DecodeBrunsli(tile.size, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun)
            : EncodeBrunsli(tile.size, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun);
        if (!result) {
            std::cerr << "Location " << hex << tile.offset << " size " << tile.size << dec << endl;
            return Usage(reverse ? "Error decoding BRUNSLI" : "Error encoding BRUNSLI");
        }

        double rat = 1 - double(tilebuf.size()) / tile.size;
        min_rat = min(rat, min_rat);
        max_rat = max(rat, max_rat);

        // Prepare the output tinfo
        tile.offset = ooff;
        tile.size = tilebuf.size();
        ooff += tile.size;
        if (!fwrite(tilebuf.data(), tilebuf.size(), 1, fout))
            return Usage("Error writing data");
        tile.tonative();
        fwrite(&tile, sizeof(tile), 1, foutidx);
    }
    fclose(fin);
    fclose(finidx);
    fclose(fout);
    fclose(foutidx);

    std::cerr << "Used to be " << insize << " now " << ooff << ", saved " << (1 - double(ooff)/insize) * 100 << "%\n";
    std::cerr << "Individual tile saving between " << min_rat * 100 << "% and " << max_rat * 100 << "%\n";

    return 0;
}

struct bundle_index {
    uint64_t offset : 40;
    uint64_t size : 24;
    //bool operator<(const bundle_index& other) {
    //    return offset < other.offset;
    //}
};

static_assert(sizeof(bundle_index) == 8);

constexpr size_t BSZ = 128;
constexpr size_t BSZ2 = BSZ * BSZ;
constexpr size_t HDRSZ = 64;
constexpr size_t IDXSZ = BSZ2 * sizeof(bundle_index);

int bundle_to_brn(const string &inname, const string &outname, bool reverse = false)
{
    struct stat statb;
    if (stat(inname.c_str(), &statb)) 
        return Usage("Can't stat input file");
    auto insize = statb.st_size;
    if (insize < (HDRSZ + IDXSZ))
        return Usage("Input file too small, can't be a bundle");

    auto fin = fopen(inname.c_str(), "rb");
    if (!fin) return Usage("Can't open input file");

    // TODO: define header as struct
    char header[64];
    if (1 != fread(header, sizeof(header), 1, fin))
        return Usage("Can't read from input bundle file");

    // Read compact bundle index
    vector<bundle_index> idx(BSZ2);
    if (BSZ2 != fread(idx.data(), sizeof(bundle_index), BSZ2, fin))
        return Usage("Can't read bundle index");

    // TODO: Swap after reading if not little endian

    // Check for out of bounds
    for (auto &v : idx) 
        if ((v.offset + v.size) > insize)
            return Usage("Corrupt bundle, index points past the end of the file");

    // Prepare output
    FILE *fout = fopen(outname.c_str(), "wb");
    if (!fout)
        return Usage("Can't open output file");
    // Write the input header + index, to have the right placement
    size_t ooff = HDRSZ + IDXSZ;
    FSEEK(fout, ooff, SEEK_SET);

    // Convert, writing output as we go, reusing the index
    vector<uint8_t> input;
    vector<uint8_t> tilebuf;
    size_t maxsz = 0;
    // Stats, saving ratio
    double min_rat = 1;
    double max_rat = -100;

    for (auto &tile : idx) {
        if (0 == tile.size) continue;
        tilebuf.clear();

        FSEEK(fin, tile.offset, SEEK_SET);
        input.resize(tile.size);
        if (!fread(input.data(), tile.size, 1, fin)) {
            std::cerr << "Location " << hex << tile.offset << " size " << tile.size << dec << endl;
            return Usage("Failed to read input tile");
        }

        int result = reverse ?
            DecodeBrunsli(tile.size, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun)
            : EncodeBrunsli(tile.size, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun);
        if (!result) {
            cerr << "Location " << hex << tile.offset << " size " << tile.size << endl;
            return Usage(reverse ? "Error decoding BRUNSLI" : "Error encoding BRUNSLI");
        }

        // Check that the output tile size fits on 24bits
        uint32_t tilesz = uint32_t(tilebuf.size());
        if (tilesz >= (1 << 24) || static_cast<size_t>(tilesz) != tilebuf.size()) {
            cerr << "Location " << hex << tile.offset << " size " << tile.size << 
                " converted to " << tilebuf.size() << endl;
            return Usage("Output tile size too big");
        }

        double rat = 1 - double(tilesz) / tile.size;
        min_rat = min(rat, min_rat);
        max_rat = max(rat, max_rat);
        tile.offset = ooff + 4;
        tile.size = tilebuf.size();
        ooff += tile.size + 4;

        // Looks good, write the output tile, prefixed by size
        uint32_t size_prefix = tile.size;
        if (!fwrite(&size_prefix, sizeof(size_prefix), 1, fout) ||
            !fwrite(tilebuf.data(), tilebuf.size(), 1, fout))
            return Usage("Failed to write output data");

        // Collect stats
        maxsz = max(maxsz, static_cast<size_t>(tile.size));
    }
    // Done with the input
    fclose(fin);

    // Update header and index at the start of the output bundle
    rewind(fout);
    // Modify maxtilesize and file size only
    memcpy(header + 8, &maxsz, 4); // Assume little endian
    memcpy(header + 24, &ooff, sizeof(ooff));
    fwrite(header, sizeof(header), 1, fout);
    fwrite(idx.data(), IDXSZ, 1, fout);
    fclose(fout);

    std::cerr << "Used to be " << insize << " now " << ooff 
        << ", saved " << (1 - double(ooff)/insize) * 100 << "%\n";
    std::cerr << "Individual tile saving between " << min_rat * 100 
        << "% and " << max_rat * 100 << "%\n";
    std::cerr << "Maxtile " << maxsz << endl;
    return 0;
}

int main(int argc, char **argv)
{
    bool reverse = false; // defaults to JPEG -> BRUNSLI
    bool bundle = false;  // defaults to MRF
    bool single = false;  // single jpeg
    string input_name;
    while(--argc) {
        string this_arg(argv[argc]);
        if (this_arg == "-r") {
            reverse = true;
        } else if (this_arg == "-b") {
            bundle = true;
        } else if (this_arg == "-s") {
            single = true;
        } else {
            input_name = this_arg;
        }
    }

    if (input_name.empty())
        return Usage("Needs input file name");
    
    if (single)
        return single_to_brn(input_name, reverse);
    if (bundle)
        return bundle_to_brn(input_name, input_name + ".brn", reverse);
    return mrf_to_brn(input_name, input_name + ".brn", reverse);
}