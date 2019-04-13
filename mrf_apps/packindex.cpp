/*
 * file: packindex.cpp
 *
 * Purpose:
 *
 * Packed Format:
 *
 * The MRF packed format consist of a header of size 32 * (1 + isize / 49152), followed
 * by the 512 byte blocks of the original MRF index that do hold value
 * The output index will be 1/1536 of the original size, plus the actual content blocks
 * 
 */

#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <cassert>
// #include <cinttypes>

using namespace std;

// Compare a substring of src with cmp, return true if same
// offset can be negative, in which case it is measured from the end of the src, python style
static bool substr_equal(const string &src, const string &cmp, int off = 0, size_t len = 0) {
    if (off < 0)
        off += static_cast<int>(src.size());
    if (off < 0 || off >= src.size())
        return false; // usage Error
    return cmp == (len ? src.substr(off, len) : src.substr(off));
}

inline bool check(const char *src, size_t len = 512) {
    assert(len % 8 == 0);
    len /= 8;
    const uint64_t *p = reinterpret_cast<const uint64_t *>(src);
    uint64_t accumulator = 0;
    while (len--)
        accumulator |= *p++;
    return 0 == accumulator;
}


int main(int argc, char **argv)
{
    assert(argc > 2);
    string in_idx_name(argv[1]);
    string out_idx_name(argv[2]);
    assert(substr_equal(in_idx_name, ".idx", -4));
    assert(substr_equal(out_idx_name, ".ix", -3));

    ifstream in_idx(in_idx_name, fstream::binary);
    ofstream out_idx(out_idx_name, fstream::binary);

    if (!in_idx.is_open() || !out_idx.is_open()) {
        cerr << "Can't open " << (in_idx.is_open() ? out_idx_name: in_idx_name) << endl;
        return 1;
    }

    in_idx.seekg(0, fstream::end);
    auto in_size = in_idx.tellg();
    in_idx.seekg(0);
    assert(in_size % 16 == 0);

    uint64_t header_size = 32 * (1 + in_size / 49152);
    cout << "Header will be " << header_size << " bytes" << endl;

    // Get space for the header and reserve space on disk,
    // Header will be written at the end
    vector<uint64_t> header(header_size / sizeof(uint64_t));
    out_idx.seekp(header_size, fstream::beg);
    
    size_t out_block_count = 0;
    size_t in_block_count = 1 + in_size / 512;
    // Block buffer
    char buffer[512];

    // Check all full blocks, transferring them as needed
    while (--in_block_count) {
        in_idx.read(buffer, 512);
        if (!check(buffer)) {
            out_idx.write(buffer, 512);
            out_block_count++;
        }
    }

    // Last block can be partial
    if (in_size % 512) {
        auto extras = in_size % 512 / 8;
        in_idx.read(reinterpret_cast<char *>(buffer), extras * 8);
        for (auto i = extras ; i < 512 / 8 ; i++)
            buffer[i] = 0;
        if (!check(buffer)) {
            out_idx.write(buffer, 512);
            out_block_count++;
        }
    }

    cout << "Packed from " << in_size << " to " << out_idx.tellp() << endl;

    // End, write the header
    in_idx.close();
    out_idx.seekp(0);
    out_idx.write(reinterpret_cast<char *>(header.data()), header.size() * sizeof(uint64_t));
    out_idx.close();
    return 0;
}
