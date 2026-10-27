"""Prints a NIF's version and block list (types + sizes) - enough to locate geometry blocks."""
import struct
import sys


def read_header(path):
    d = open(path, 'rb').read()
    nl = d.index(b'\n')
    head = d[:nl].decode('latin-1')
    p = nl + 1
    ver, = struct.unpack_from('<I', d, p); p += 4
    endian = d[p]; p += 1
    user, nblocks = struct.unpack_from('<II', d, p); p += 8
    bs_ver, = struct.unpack_from('<I', d, p); p += 4
    for _ in range(2 if bs_ver <= 130 else 3):  # author, process script (+ export script)
        n = d[p]; p += 1 + n
    if bs_ver >= 130: pass
    n = d[p]; p += 1 + n  # export info 3
    ntypes, = struct.unpack_from('<H', d, p); p += 2
    types = []
    for _ in range(ntypes):
        n, = struct.unpack_from('<I', d, p); p += 4
        types.append(d[p:p + n].decode('latin-1')); p += n
    idx = struct.unpack_from(f'<{nblocks}H', d, p); p += 2 * nblocks
    sizes = struct.unpack_from(f'<{nblocks}I', d, p); p += 4 * nblocks
    nstr, maxlen = struct.unpack_from('<II', d, p); p += 8
    strings = []
    for _ in range(nstr):
        n, = struct.unpack_from('<I', d, p); p += 4
        strings.append(d[p:p + n].decode('latin-1')); p += n
    ngroups, = struct.unpack_from('<I', d, p); p += 4 + 4 * ngroups
    return dict(head=head, ver=hex(ver), user=user, bs=bs_ver, blocks=[(types[i], s) for i, s in zip(idx, sizes)],
                strings=strings, data_start=p, raw=d)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        h = read_header(path)
        print(path.split('/')[-1], h['head'], h['ver'], 'user', h['user'], 'bs', h['bs'])
        print('  strings:', h['strings'][:12])
        from collections import Counter
        print('  blocks:', Counter(t for t, _ in h['blocks']).most_common())
