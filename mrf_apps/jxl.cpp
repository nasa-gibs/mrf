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
#include <sys/mman.h>
#include <unistd.h>

// For Linux
#include <endian.h>

using namespace std;

const static int BSZ(128);
const static int BSZ2(BSZ*BSZ);
const static int BUFSZ(1024*1024); // 1MB, kinda small

int Usage(const string &s) {
    cerr << s << endl;
    return 1;
}

struct bundle_index {
    uint64_t offset : 40;
    uint64_t size : 24;
    bool operator<(const bundle_index &other) {
        return offset < other.offset;
    }
};

// It's really a pair, so we can sort by offset or by rank
struct ranked_index {
    ranked_index(bundle_index idx, uint64_t rank) : idx (idx), rank(rank) {}
    bundle_index idx;
    uint64_t rank;
    bool operator<(const ranked_index &other) {
        return idx < other.idx;
    }
};

static_assert(sizeof(bundle_index) == sizeof(uint64_t));

static const int HDRSZ = 64;
static const int IDXSZ = BSZ2 * sizeof(bundle_index);

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
    void ton() {
        offset = htobe64(offset);
        size = htobe64(size);
    }
};

// From MRF, separate files, inname is the data file
int mrf_to_jxl(const string &inname, const string &outname, bool reverse = false) {
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
        tile.toh();
        if (tile.size) {
            fseek(fin, tile.offset, SEEK_SET);
            input.resize(tile.size);
            if (!fread(input.data(), tile.size, 1, fin)) {
                cerr << "Location " << hex << tile.offset << " size " << tile.size << endl;
                return Usage("Failed to read input tile");
            }
            tilebuf.clear();

            int result = reverse ?
                DecodeBrunsli(tile.size, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun)
                : EncodeBrunsli(tile.size, input.data(), &tilebuf, (DecodeBrunsliSink)out_fun);
            if (!result) {
                cerr << "Location " << hex << tile.offset << " size " << tile.size << endl;
                return Usage(reverse ? "Error decoding JXL" : "Error encoding JXL");
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
        }
        tile.ton();
        fwrite(&tile, sizeof(tile), 1, foutidx);
    }
    fclose(fin);
    fclose(finidx);
    fclose(fout);
    fclose(foutidx);

    cerr << "Used to be " << insize << " now " << ooff << ", saved " << (1 - double(ooff)/insize) * 100 << "%\n";
    cerr << "Individual tile saving between " << min_rat * 100 << "% and " << max_rat * 100 << "%\n";

    return 0;
}

int bundle_to_jxl(const string &inname, const string &outname, bool reverse = false) {

    struct stat statb;
    if (stat(inname.c_str(), &statb)) 
        return Usage("Can't stat input file");
    auto insize = statb.st_size;
    if (insize < (HDRSZ + IDXSZ))
        return Usage("Input file too small, can't be a bundle");
    // cerr << "Size is " << insize << endl;
    int infd = open(inname.c_str(), O_RDONLY);
    if (infd < 0) return Usage("Can't open input file");
    auto input = reinterpret_cast<const unsigned char *>(
        mmap(nullptr, insize, PROT_READ, MAP_SHARED, infd, 0));
    close(infd);
    if (MAP_FAILED == input) {
        cerr << "ERROR: " << strerror(errno) << endl;
        return Usage("Can't mmap input file");
    }

    // TODO: define header as struct
    char header[64];
    memcpy(header, input, HDRSZ);

    // Read index
    vector<bundle_index> idx(BSZ2);
    memcpy(idx.data(), input + HDRSZ, IDXSZ);

    // TODO: Swap after reading if not little endian

    // Check for out of bounds
    for (auto &v : idx) 
        if ((v.offset + v.size) > insize)
            return Usage("Corrupt index");

    // Prepare output
    FILE *out = fopen(outname.c_str(), "wb");
    if (!out) return Usage("Can't open output file");
    // Write the input header + index, to have the right placement
    size_t ooff = HDRSZ + IDXSZ;
    fwrite(input, ooff, 1, out);

    // Convert, writing output as we go, reusing the index
    vector<uint8_t> tilebuf; // output holder
    size_t maxsz = 0;
    // Stats, saving ratio
    double min_rat = 1;
    double max_rat = -100;

    for (auto &v : idx) {
        if (!v.size) continue;
        tilebuf.clear();
        int result = reverse ?
            DecodeBrunsli(v.size, &input[v.offset], &tilebuf, (DecodeBrunsliSink)out_fun)
            : EncodeBrunsli(v.size, &input[v.offset], &tilebuf, (DecodeBrunsliSink)out_fun);
        if (!result) {
            cerr << "Location " << hex << v.offset << " size " << v.size << endl;
            return Usage(reverse ? "Error decoding JXL" : "Error encoding JXL");
        }

        // This has to be 3 bytes or smaller, check anyhow
        uint32_t tilesz = tilebuf.size();
        if (tilesz >= (1 << 24) || static_cast<size_t>(tilesz) != tilebuf.size()) {
            cerr << "Location " << hex << v.offset << " size " << v.size << 
                " converted to " << tilebuf.size() << endl;
            return Usage("Output tile size too big");
        }
        // Looks good, write the output tile, prefixed by size
        fwrite(&tilesz, 4, 1, out);
        fwrite(tilebuf.data(), tilesz, 1, out);

        // Collect stats
        maxsz = max(maxsz, static_cast<size_t>(tilesz));
        double rat = 1 - double(tilesz) / v.size;
        min_rat = min(rat, min_rat);
        max_rat = max(rat, max_rat);

        // Modify the index in place
        v.offset = ooff + 4; // Points to first byte of tile data, not the size prefix
        v.size = tilesz;
        ooff += 4 + tilesz;
    }
    // Done with the input
    munmap((void *)input, insize);

    // Go back, write the new header and index
    fseek(out, 0, SEEK_SET);
    
    // TODO: Figure out the header stuff
    // Modify maxtilesize and file size
    memcpy(header + 8, &maxsz, 4); // Assume little endian
    memcpy(header + 24, &ooff, sizeof(ooff));
    fwrite(header, HDRSZ, 1, out);

    fwrite(idx.data(), IDXSZ, 1, out);
    fclose(out);
    cerr << "Used to be " << insize << " now " << ooff << ", saved " << (1 - double(ooff)/insize) * 100 << "%\n";
    cerr << "Individual tile saving between " << min_rat * 100 << "% and " << max_rat * 100 << "%\n";
    cerr << "Maxtile " << maxsz << endl;
    return 0;
}

int main(int argc, char **argv)
{
    bool reverse = false; // default to JPEG -> JXL
    bool bundle = false;  // default to MRF
    string input_name;
    while(--argc) {
        string this_arg(argv[argc]);
        if (this_arg == "-r") {
            reverse = true;
        } else if (this_arg == "-b") {
            bundle = true;
        } else {
            input_name = this_arg;
        }
    }

    if (input_name.empty())
        return Usage("Needs input file name");
    
    if (bundle)
        return bundle_to_jxl(input_name, input_name + ".jxl", reverse);
    return mrf_to_jxl(input_name, input_name + ".jxl", reverse);
}