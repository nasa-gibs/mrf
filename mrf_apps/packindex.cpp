/*
 * file: packindex.cpp
 *
 * Purpose:
 *
 * Packed Format:
 *
 * The MRF packed format consist of a header of size 16 * ((49151 + isize) / 49152), followed
 * by the 512 byte blocks of the original MRF index that do hold value
 * The output index will be a few bytes over 1:3072 (0.03255%) of the original virtual size, 
 * plus the actual content blocks.
 *
 * This is because the header is formed of 96 bit masks for every 96 blocks of 512 bytes each, 
 * plus a 32 bit running count of previously existing blocks. Thus, every 96 input blocks will 
 * use 16 bytes.  Since the size of the header can be calculated based on the MRF size
 * it is used as a check that the header is correct.  Also the total number of set bits in the 
 * header has to be equal to the number of blocks in the file, which results in another check
 * 
 */

#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <cassert>
// #include <cinttypes>

using namespace std;

// Block size used, do not modify
const int BSZ = 512;

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
    string in_idx_name;
    string out_idx_name;
    string error; // Empty if parsing went fine
    bool unpack; // Pack by default
    bool quiet;  // Verbose by default
};

static options parse(int argc, char **argv) {
    options opt;
    for (int i = 1; i < argc; i++) {
        string arg(argv[i]);
        if (0 == arg.find_first_of("-")) {
            if (arg == "-q") {
                opt.quiet = true;
                continue;
            }
            else
            if (arg == "-u") {
                opt.unpack = true;
                continue;
            }
            else {
                opt.error = string("Unknown option ") + arg;
                return opt;
            }
        }
        else { // file names
            if (opt.in_idx_name.empty()) {
                opt.in_idx_name = argv[i];
                if (!substr_equal(opt.in_idx_name, ".idx", -4)) {
                    opt.error = "Input file name should end in .idx";
                    return opt;
                }
            }
            else {
                if (!opt.out_idx_name.empty()) {
                    opt.error = "Too many files names";
                    return opt;
                }
                opt.out_idx_name = argv[i];
                if (!substr_equal(opt.out_idx_name, ".ix", -3)) {
                    opt.error = "Input file name should end in .ix";
                    return opt;
                }
            }
        }
    }

    // Final checks
    if (opt.in_idx_name.empty() || opt.out_idx_name.empty())
        opt.error = "Need input and output file names";

    return opt;
}

enum ERRORS { NO_ERR = 0, USAGE_ERR, IO_ERR, INTERNAL_ERR };

int Usage(const string &error) {
    cerr << error << endl;
    return USAGE_ERR;
}

int pack(const options &opt) {
    string in_idx_name(opt.in_idx_name);
    string out_idx_name(opt.out_idx_name);

    ifstream in_idx(in_idx_name, fstream::binary);
    ofstream out_idx(out_idx_name, fstream::binary);

    if (!in_idx.is_open() || !out_idx.is_open()) {
        cerr << "Can't open " << (in_idx.is_open() ? out_idx_name : in_idx_name) << endl;
        return IO_ERR;
    }

    in_idx.seekg(0, fstream::end);
    auto in_size = in_idx.tellg();
    in_idx.seekg(0);

    // Input has to be an index, which is always a multiple of 16 bytes
    if (in_size % 16) {
        cerr << "Input file is not an index file, size is not a multiple of 16\n";
        return USAGE_ERR;
    }

    // Output has a 16 bit reserved line plus the line array
    uint64_t header_size = 16 * ((96 * BSZ - 1 + in_size) / (96 * BSZ));
    if (!opt.quiet)
        cout << "Header will be " << header_size << " bytes" << endl;

    // Get space for the header and reserve space on disk,
    // Header will be written at the end
    vector<uint32_t> header(header_size / sizeof(uint32_t));

    // Reserve space for the header
    out_idx.seekp(header_size, fstream::beg);

    // Running count of output blocks
    size_t count = 0;
    size_t in_block_count = (BSZ - 1 + in_size) / BSZ;
    // Block buffer
    char buffer[BSZ];

    // Current line start within header as a 32bit int index
    // always a multiple of 4, since there are 4 ints per line
    int line = 0;
    // and current bit position within that line
    int bit_pos = 0;

    // Check all full blocks, transferring them as needed
    while (--in_block_count) {
        in_idx.read(buffer, BSZ);

        if (!check(buffer)) {
            out_idx.write(buffer, BSZ);
            // Flip the bit that represents this value
            header[line + 1 + bit_pos / 32] |= 1 << (bit_pos % 32);
            count++;
        }

        bit_pos++;
        if (bit_pos % 96 == 0) {
            // Start a new line, store the running count
            bit_pos = 0;
            line += 4;
            // If there is another line, initialize running count
            if (line < header.size())
                header[line] = static_cast<uint32_t>(count);
        }
    }

    // The very last block may be partial
    if (in_size % BSZ) {
        auto extra_bytes = in_size % BSZ;
        in_idx.read(reinterpret_cast<char *>(buffer), extra_bytes);
        // The buffer is in int64_t, so we divide by 8
        for (auto i = extra_bytes; i < BSZ; i++)
            buffer[i] = 0;

        if (!check(buffer)) {
            out_idx.write(buffer, BSZ);
            // Flip the bit in the header
            header[line + 1 + bit_pos / 32] |= 1 << (bit_pos % 32);
        }
    }

    if (!opt.quiet)
        cout << "Index packed from " << in_size << " to " << out_idx.tellp() << endl;

    // Done, write the header at the begining of the file
    in_idx.close();
    out_idx.seekp(0);
    out_idx.write(reinterpret_cast<char *>(header.data()), header_size);
    out_idx.close();
    return NO_ERR;
}

int unpack(const options &opt) {
    cerr << "Unpack not yet implemented\n";
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
