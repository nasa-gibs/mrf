/*
 * file: packindex.cpp
 *
 * Purpose:
 *
 * canned Format:
 *
 * The MRF packed format consist of a header of size 16 + 16 * ((49151 + isize) / 49152)
 * followed by the 512 byte blocks of the original MRF index that do hold non-zero values
 * The output index will be 1:3072 (0.03255%) of the original virtual size, rounded up to 16,
 * plus the actual content blocks.
 *
 * This is because the canned file header contains a bitmask that holds presence info for every
 * 512 byte block of the input, stored in 96 block groups, stored as a 96 bit line prefixed 
 * by a 32 bit running count of previously existing blocks. Thus, each line will use 16 bytes.
 * The canned file starts with a 16 byte canned index metadata that describes it's structure
 * followed by the bitmap, followed by the data blocks.

 * Since the size of the header can be calculated from the input MRF index size
 * it can be used as a check that the header is correct. Also the total number of set bits 
 * in the header has to be equal to the number of blocks in the file
 * 
 * The canned index file metadata line contains two 32bit integers and one 64bit int
 * all in big endian
 * | "MRF\0" | size of bitmap in 16 byte units | original index size in 16 byte units | 
 *
 * The bitmap structure has 4 32bit unsigned integers, in big endian format
 * |start_count | bits 0 to 32 | bits 33 to 63 | bits 64 to 95 |
 * Where start_count is the total count of the bits set in the previous lines
 * 
 */

#if defined(_WIN32)
#include <Windows.h>
#include <io.h>

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
#include <unistd.h>
#include <endian.h>
#define FSEEK fseek
#define FTELL ftell

#define SETSPARSE(f) true
#endif

#include <string>
#include <vector>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <cassert>
#include <cstdio>
#include <cstdlib>

 // For memset only
#include <cstring>

using namespace std;

// Block size used, do not modify
const int BSZ = 512;

// 4 byte length signature string
const char *SIG = "IDX";

// Make file end at current offset, return true on success
static bool MARK_END(FILE *f) {
#if defined(_WIN32)
    HANDLE h = (HANDLE) _get_osfhandle(_fileno(f));
    if (h == INVALID_HANDLE_VALUE)
        return false; // Possibly not a seekable file
    return 0 != SetEndOfFile(h);
#else
    return !ftruncate(fileno(f), ftell(f));
#endif
}

#if defined(_WIN32)
// Set file as sparse, returns true if all went fine
static bool SETSPARSE(FILE *f) {
    DWORD dw;
    HANDLE h = (HANDLE)_get_osfhandle(_fileno(f));
    if (h = INVALID_HANDLE_VALUE)
        return false;
    return 0 != DeviceIoControl(h, FSCTL_SET_SPARSE, nullptr, 0, nullptr, 0, &dw, nullptr);
}
#endif

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
    options() : un(false), quiet(false) {}
    vector<string> file_names;
    string error; // Empty if parsing went fine
    bool un; // reverse
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
                opt.un = true;
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

static int Usage(const string &error) {
    cerr << error << endl;
    return USAGE_ERR;
}

// Output has a 16 bit reserved line plus the counted bitmap
static inline uint64_t canned_size(uint64_t in_size) {
    return 16 + 16 * ((96 * BSZ - 1 + in_size) / (96 * BSZ));
}

// transfer len bytes from in to out, prints an error and returns false if it erred
// len has to be under or equal to BSZ
inline int transfer(FILE *in_file, FILE *out_file, size_t len = BSZ) {
    assert(len <= BSZ);
    static char buffer[BSZ];

    if (len != fread(buffer, 1, len, in_file)) {
        cerr << "Read error\n";
        return false;
    }

    if (len != fwrite(buffer, 1, len, out_file)) {
        cerr << "Write error\n";
        return false;
    }

    return true;
}

// The bit state at a given position in a line, assumes native endianess
inline bool is_on(uint32_t *values, int bit) {
    return 0 != (values[1 + bit / 32] & (static_cast<uint32_t>(1) << bit % 32));
}

int can(const options &opt) {
    if (opt.file_names.size() != 2)
        return Usage("Need an input and an output name");

    string in_idx_name(opt.file_names[0]);
    string out_idx_name(opt.file_names[1]);

    if (!substr_equal(in_idx_name, ".idx", -4))
        return Usage("Input file should have an .idx extension");

    if (!substr_equal(out_idx_name, ".ix", -3))
        return Usage("Output file should have an .ix extension");

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

    uint64_t header_size = canned_size(in_size);
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

    // Last piece of the header line, the size of the header itself, in 16 byte units
    // This imposes a size limit of 64GB for the header, which translates into 
    // 192PB for the source index, unlikely to be ever reached
    header[1] = htobe32(static_cast<uint32_t>(header.size() / 4));

    // The initial index size, in 16byte units, big endian, this fills
    // header[2] and header[3]
    *reinterpret_cast<uint64_t *>(&header[2]) = htobe64(in_size / 16);

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


int uncan(const options &opt) {
    if (opt.file_names.size() != 2)
        return Usage("Need an input and an output name, use - to use stdin or stdout");

    string in_idx_name(opt.file_names[0]);
    string out_idx_name(opt.file_names[1]);

    // TODO: handle stdin as input
    if (!substr_equal(in_idx_name, ".ix", -3) && (in_idx_name != "-"))
        return Usage("Input file should have an .ix extension, or be -");

    if (!substr_equal(out_idx_name, ".idx", -4))
        return Usage("Output file should have an .idx extension");

    FILE *in_idx = stdin;
    if (in_idx_name != "-")
        in_idx = fopen(in_idx_name.c_str(), "rb");

    FILE *out_idx = fopen(out_idx_name.c_str(), "wb");
    SETSPARSE(out_idx);

    if (!in_idx || !out_idx) {
        cerr << "Can't open " << (in_idx ? out_idx_name : in_idx_name) << endl;
        return IO_ERR;
    }

    vector<uint32_t> header(4);
    if (4 != fread(header.data(), sizeof(uint32_t), 4, in_idx)) {
        cerr << "Error reading from input header\n";
        return IO_ERR;
    }

    // Verify and unpack the header line
    if (header[0] != *reinterpret_cast<const uint32_t *>(SIG))
        return Usage("Input is not a canned MRF index, wrong magick");
    // in 16 byte units, convert it to 4 byte units
    uint32_t header_size = 4 * be32toh(header[1]);

    // in bytes
    uint64_t out_size = 16 * be64toh(*reinterpret_cast<uint64_t *>(&header[2]));

    // Verify that the sizes make sense
    if (header_size * 4 != canned_size(out_size))
        return Usage("Input header is corrupt");

    if (!opt.quiet)
        cout << "Output size will be " << out_size << endl;

    header_size -= 4;

    // The bitmap part of the header
    vector<uint32_t> bitmap(header_size);

    if (header_size != fread(bitmap.data(), sizeof(uint32_t), header_size, in_idx)) {
        cerr << "Error reading input bitmap\n";
        return IO_ERR;
    }

    // Swap bitmap to host
    for (auto &it : bitmap)
        it = be32toh(it);

    // Full output blocks, there might be one more, partial
    uint64_t num_blocks = out_size / BSZ;

    uint32_t count = 0; // The running count of output blocks with data
    uint32_t line = 0; // increments by 4

    // How many output blocks are empty
    uint64_t empties = 0;

    // Loop over input lines
    while (num_blocks) {
        int bits = 96;
        if (num_blocks < 96)
            bits = static_cast<int>(num_blocks);

        // Check that the running count for the line agrees
        if (count != bitmap[line])
            return Usage("Input bitmap is corrupt\n");

        for (int bit= 0; bit < bits; bit++, num_blocks--) {

            if (!is_on(&bitmap[line], bit)) {
                empties++;
                continue;
            }

            // Flush
            if (empties)
                FSEEK(out_idx, empties * BSZ, SEEK_CUR);
            empties = 0;

            // Transfer the block from in to out
            if (!transfer(in_idx, out_idx))
                return IO_ERR;

            count++; // Transferred one more block
        }

        line += 4;
    }

    // Flush
    if (empties)
        FSEEK(out_idx, empties * BSZ, SEEK_CUR);

    // Might have a partial block at the end
    int extra_bytes = out_size % BSZ;
    if (extra_bytes) {
        // Which line we're on
        line = static_cast<uint32_t>((out_size / BSZ / 96) * 4);
        int bit = (out_size / BSZ) % 96;
        // Check the running count if the partial block is bit 0
        if ((bit == 0) && (count != bitmap[line]))
            return Usage("Input bitmap is corrupt\n");

        if (is_on(&bitmap[line], bit)) {
            // Transfer the partial block, we're done
            if (!transfer(in_idx, out_idx, extra_bytes))
                return IO_ERR;
        }
        else {
            FSEEK(out_idx, extra_bytes, SEEK_CUR);
        }
    }

    fclose(in_idx);
    // Need to end the file at the current position, to get the right size
    MARK_END(out_idx);
    fclose(out_idx);

    return NO_ERR;
}

int main(int argc, char **argv)
{
    options opt(parse(argc, argv));
    if (!opt.error.empty())
        return Usage(opt.error);

    if (opt.un)
        return uncan(opt);
    return can(opt);
}
