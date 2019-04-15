/*
 * file: packindex.cpp
 *
 * Purpose:
 *
 * Packed Format:
 *
 * The MRF packed format consist of a header of size 16 * ((49151 + isize) / 49152), followed
 * by the 512 byte blocks of the original MRF index that do hold value
 * The output index will be 1:3072 (0.03255%) of the original virtual size, rounded up to 16,
 * plus the actual content blocks.
 *
 * This is because the header is formed of 96 bit masks for every 96 blocks of 512 bytes of input, 
 * plus a 32 bit running count of previously existing blocks. Thus, every 96 input blocks will 
 * use 16 bytes.  Since the size of the header can be calculated based on the MRF size
 * it is used as a check that the header is correct.  Also the total number of set bits in the 
 * header has to be equal to the number of blocks in the file, which results in another check
 * 
 * The header line structure has 4 32bit unsigned integers, in big endian format
 * |start_count | bits 0 to 32 | bits 33 to 63 | bits 64 to 95 |
 * Where start_count is the total count of the bits set in the previous lines
 * 
 */

#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <cassert>
#include <cstdio>
#include <cstdlib>

// For memset only
#include <cstring>

#if defined(_WIN32)
#define FSEEK _fseeki64
#define FTELL _ftelli64

// Windows is always little endian, supply functions to swap bytes
// These are defined in <cstdlib>
#define htobe16 _byteswap_ushort
#define be16toh _byteswap_ushort
#define htobe32 _byteswap_ulong
#define be32toh _byteswap_ulong
#define htobe64 _byteswap_uint64
#define be64toh _byteswap_uint64

#else
#include <endian.h>
#define FSEEK fseek
#define FTELL ftell
#endif

using namespace std;

// Block size used, do not modify
const int BSZ = 512;

// 4 byte length signature string
const char *SIG = "IDX";

// Compare a substring of src with cmp, return true if same
// offset can be negative, in which case it is measured from the end of the src, python style
static bool substr_equal(const string &src, const string &cmp, int off = 0, size_t len = 0) {
    if (off < 0)
        off += static_cast<int>(src.size());
    if (off < 0 || off >= src.size())
        return false; // usage Error
    return cmp == (len ? src.substr(off, len) : src.substr(off));
}

// Returns true if the block is filled with zeros
inline bool check(const char *src, size_t len = BSZ) {
    assert(len % 8 == 0); // So we can use uint64_t
    len /= 8;
    const uint64_t *p = reinterpret_cast<const uint64_t *>(src);
    uint64_t accumulator = 0;
    while (len--)
        accumulator |= *p++;
    return 0 == accumulator;
}

// Program options
struct options {
    options() : unpack(false), quiet(false) {}
    vector<string> file_names;
    string error; // Empty if parsing went fine
    bool unpack; // Pack by default
    bool quiet;  // Verbose by default
};

static options parse(int argc, char **argv) {
    options opt;
    bool optend = false;
    for (int i = 1; i < argc; i++) {
        string arg(argv[i]);
        if (!optend && 0 == arg.find_first_of("-")) {
            if (arg == "-q") {
                opt.quiet = true;
                continue;
            }
            else if (arg == "-u") {
                opt.unpack = true;
                continue;
            }
            else if (arg == "-") { // Could be stdin or stdout file name
                opt.file_names.push_back(arg);
            }
            else if (arg == "--") { // End of options
                optend = true;
            }
            else {
                opt.error = string("Unknown option ") + arg;
                return opt;
            }
        }
        else { // File names, accumulate
            opt.file_names.push_back(arg);
        }
    }

    return opt;
}

enum ERRORS { NO_ERR = 0, USAGE_ERR, IO_ERR, INTERNAL_ERR };

int Usage(const string &error) {
    cerr << error << endl;
    return USAGE_ERR;
}

int pack(const options &opt) {
    if (opt.file_names.size() != 2)
        return Usage("Need an input and an output name");

    string in_idx_name(opt.file_names[0]);
    string out_idx_name(opt.file_names[1]);

    if (!substr_equal(in_idx_name, ".idx", -4))
        return Usage("Input file should have an .idx extension");

    if (!substr_equal(out_idx_name, ".ix", -3))
        return Usage("Output file should have an .idx extension");

    FILE *in_idx = fopen(in_idx_name.c_str(), "rb");
    FILE *out_idx = fopen(out_idx_name.c_str(), "wb");

    if (!in_idx || !out_idx) {
        cerr << "Can't open " << (in_idx ? out_idx_name : in_idx_name) << endl;
        return IO_ERR;
    }

    FSEEK(in_idx, 0, SEEK_END);
    uint64_t in_size = static_cast<uint64_t>(FTELL(in_idx));
    FSEEK(in_idx, 0, SEEK_SET);

    // Input has to be an index, which is always a multiple of 16 bytes
    if (in_size % 16) {
        cerr << "Input file is not an index file, size is not a multiple of 16\n";
        return USAGE_ERR;
    }

    // Output has a 16 bit reserved line plus the counted bitmap
    uint64_t header_size = 16 + 16 * ((96 * BSZ - 1 + in_size) / (96 * BSZ));
    if (!opt.quiet)
        cout << "Header will be " << header_size << " bytes" << endl;

    // Get space for the header and reserve space on disk,
    // Header will be written at the end
    vector<uint32_t> header(header_size / sizeof(uint32_t));

    // Reserve space for the header
    FSEEK(out_idx, header_size, SEEK_SET);

    // Running count of output blocks
    size_t count = 0;
    size_t in_block_count = (BSZ - 1 + in_size) / BSZ;
    // Block buffer
    char buffer[BSZ];

    // Current line start within header as a 32bit int index
    // always a multiple of 4, since there are 4 ints per line
    // Skip the reserved line
    int line = 4;
    // and current bit position within that line
    int bit_pos = 0;

#define BIT_SET(line, i) header[line + 1 + i / 32] |= 1 << (i % 32)

    // Check all full blocks, transferring them as needed
    while (--in_block_count) {
        if (BSZ != fread(buffer, 1, BSZ, in_idx)) {
            cerr << "Error reading block from input file\n";
            return IO_ERR;
        }

        if (!check(buffer)) {
            if (BSZ != fwrite(buffer, 1, BSZ, out_idx)) {
                cerr << "Error writing to output file\n";
                return IO_ERR;
            }
            BIT_SET(line, bit_pos);
            count++;
        }

        bit_pos++;
        if (96 == bit_pos) {
            // Start a new line, store the running count
            bit_pos = 0;
            line += 4;
            // If there is another line, initialize running count
            if (line < header.size())
                header[line] = static_cast<uint32_t>(count);
        }
    }

    auto extra_bytes = in_size % BSZ;

    // The very last block may be partial
    if (extra_bytes) {
        memset(buffer, 0, BSZ);
        if (extra_bytes != fread(buffer, 1, extra_bytes, in_idx)) {
            cerr << "Error reading block from input file\n";
            return IO_ERR;
        }

        if (!check(buffer)) {
            if (extra_bytes != fwrite(buffer, 1, extra_bytes, out_idx)) {
                cerr << "Error writing to output file\n";
                return IO_ERR;
            }
            BIT_SET(line, bit_pos);
        }
        line += 4; // Points right at the end of the header
    }

#undef BIT_SET

    if (!opt.quiet)
        cout << "Index packed from " << in_size << " to " << FTELL(out_idx) << endl;

    // line should point to the last line or the one after the last
    if (!(header.size() == line))
        cerr << "Something is wrong, line is " << line << " header is " << header.size() << endl;

    // swap all header values to big endian
    for (auto &v : header)
        v = htobe32(v);

    // Write the header line, the signature is not dependent of endianess
    header[0] = *reinterpret_cast<const uint32_t *>(SIG);

    // The initial index size, in 16byte units, big endian
    in_size = htobe64(in_size / 16);
    header[1] = static_cast<uint32_t>(in_size >> 32);
    header[2] = static_cast<uint32_t>(in_size);

    // Last part of the header line, the size of the header itself, in 16 byte units
    // This imposes a size limit of 64GB for the header, which translates into 
    // 192PB for the source index, unlikely to be ever reached
    header[3] = static_cast<uint32_t>(htobe64(header.size() / 4));

    // Done, write the header at the begining of the file
    fclose(in_idx);
    FSEEK(out_idx, 0, SEEK_SET);
    if (header.size() != fwrite(header.data(), sizeof(uint32_t), header.size(), out_idx)) {
        cerr << "Error writing output header\n";
        return IO_ERR;
    }
    fclose(out_idx);

    return NO_ERR;
}

int unpack(const options &opt) {
    string in_idx_name(opt.file_names[0]);
    string out_idx_name(opt.file_names[1]);

    FILE *in_idx = fopen(in_idx_name.c_str(), "rb");
    FILE *out_idx = fopen(out_idx_name.c_str(), "wb");

    if (!in_idx || !out_idx) {
        cerr << "Can't open " << (in_idx ? out_idx_name : in_idx_name) << endl;
        return IO_ERR;
    }

    return INTERNAL_ERR;
}

int main(int argc, char **argv)
{
    options opt(parse(argc, argv));
    if (!opt.error.empty())
        return Usage(opt.error);

    if (opt.unpack)
        return unpack(opt);
    return pack(opt);
}
