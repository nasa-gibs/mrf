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

int bundle_to_jxl(const string &inname, const string &outname) {

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
    double min_rat = 1; // Should be 1, but just in case
    double max_rat = 0;
    for (auto &v : idx) {
        if (!v.size)
            continue;
        tilebuf.clear();
        if (!EncodeBrunsli(v.size, &input[v.offset], &tilebuf, (DecodeBrunsliSink)out_fun)) {
            cerr << "Location " << hex << v.offset << " size " << v.size << endl;
            return Usage("Error encoding JXL");
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
        // Collect some stats
        double rat = 1 - double(tilesz) / v.size;

        if (rat < min_rat) {
            cerr << "Min " << rat << endl;
            min_rat = rat;
        }
        if (rat > max_rat) {
            cerr << "Max " << rat << endl;
            max_rat = rat;
        }

        // Modify the index in place
        v.offset = ooff + 4; // Points to first byte of tile data, not the size prefix
        v.size = tilesz;
        ooff += 4 + tilesz;
        maxsz = max(maxsz, static_cast<size_t>(tilesz));
    }
    // Done with the input
    munmap((void *)input, insize);

    // Go back, write the new header and index
    fseek(out, 0, SEEK_SET);
    // TODO: Figure out the header stuff
    // Modify maxtilesize and file size
    memcpy(header + 8, &maxsz, sizeof(maxsz));
    memcpy(header + 24, &ooff, sizeof(ooff));
    fwrite(header, HDRSZ, 1, out);

    fwrite(idx.data(), IDXSZ, 1, out);
    fclose(out);
    cerr << "Used to be " << insize << " now " << ooff << ", saved " << (1 - double(ooff)/insize) * 100 << "%\n";
    cerr << "Individual tile saving between " << min_rat * 100 << " and " << max_rat * 100 << endl;
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2)
        return Usage("Needs input file name");
    return bundle_to_jxl(argv[1], string(argv[1]) + ".jxl");
}