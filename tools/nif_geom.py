"""Minimal Skyrim SE (NIF 20.2.0.7, BS stream 100) geometry reader: positions, UVs and triangles of BSTriShape
blocks, including skinned shapes whose vertex data lives in NiSkinPartition. Enough to bake UV maps from BodySlide
reference meshes without a Blender NIF add-on.

python tools/nif_geom.py <in.nif> <out.npz> [shape name]   -> verts (N,3) float32, uvs (N,2) float32, tris (M,3) int32
Positions are in the shape's own space with its local transform applied; UV v stays as stored (top-down)."""
import struct
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from nif_header import read_header  # noqa: E402

VF_UV, VF_FULLPREC = 1 << 1, 1 << 10


class R:
    def __init__(self, d, p):
        self.d, self.p = d, p

    def u(self, fmt):
        v = struct.unpack_from('<' + fmt, self.d, self.p)
        self.p += struct.calcsize('<' + fmt)
        return v if len(v) > 1 else v[0]


def decode_vertices(raw, desc, count, sse=True):
    size = (desc & 0xF) * 4
    flags = desc >> 44
    uv_off = ((desc >> 8) & 0xF) * 4
    a = np.frombuffer(raw, np.uint8, size * count).reshape(count, size)
    if flags & VF_FULLPREC or sse:  # SSE stores positions as float32 whatever the flag says (32-bit position + bitangent x)
        pos = a[:, 0:12].copy().view(np.float32).reshape(count, 3)
    else:
        pos = a[:, 0:6].copy().view(np.float16).reshape(count, 3).astype(np.float32)
    if not flags & VF_UV:
        raise ValueError('shape has no UVs')
    uv = a[:, uv_off:uv_off + 4].copy().view(np.float16).reshape(count, 2).astype(np.float32)
    return pos, uv


def parse_shape(h, i):
    d, starts = h['raw'], h['starts']
    r = R(d, starts[i])
    name_idx = r.u('i')
    nextra = r.u('I'); r.p += 4 * nextra
    r.u('i')  # controller
    r.u('I')  # flags
    trans = np.array(r.u('3f'), np.float32)
    rot = np.array(r.u('9f'), np.float32).reshape(3, 3)
    scale = r.u('f')
    r.u('i')  # collision
    r.u('4f')  # bounding sphere
    skin, _shader, _alpha = r.u('3i')
    desc = r.u('Q')
    ntris = r.u('I')  # uint32 in SSE (BS stream 100), ushort only in older streams
    nverts = r.u('H')
    dsize = r.u('I')
    shape = dict(name=h['strings'][name_idx] if name_idx >= 0 else '', trans=trans, rot=rot, scale=scale,
                 skin=skin, desc=desc, ntris=ntris, nverts=nverts)
    if dsize:
        vsize = (desc & 0xF) * 4
        assert dsize == vsize * nverts + 6 * ntris, 'BSTriShape size check failed'
        raw = d[r.p:r.p + vsize * nverts]
        r.p += vsize * nverts
        tris = np.frombuffer(d, np.uint16, 3 * ntris, r.p).reshape(ntris, 3).astype(np.int32)
        shape['pos'], shape['uv'] = decode_vertices(raw, desc, nverts)
        shape['tris'] = tris
    return shape


def skin_partition_geometry(h, skin_idx, nverts):
    """SSE keeps a skinned shape's vertex buffer and triangles in the NiSkinPartition its skin instance points to."""
    d, starts, blocks = h['raw'], h['starts'], h['blocks']
    r = R(d, starts[skin_idx])
    r.u('i')  # skin data ref
    part_idx = r.u('i')
    assert blocks[part_idx][0] == 'NiSkinPartition', blocks[part_idx]
    r = R(d, starts[part_idx])
    nparts = r.u('I')
    dsize, vsize = r.u('2I')
    desc = r.u('Q')
    count = dsize // vsize if vsize else 0
    assert count and (nverts in (0, count)), (count, nverts)  # skinned SSE shapes may report 0 vertices themselves
    raw = d[r.p:r.p + dsize]
    r.p += dsize
    pos, uv = decode_vertices(raw, desc, count)
    tris = []
    for _ in range(nparts):
        nv, nt, nb, ns, nw = r.u('5H')
        r.p += 2 * nb
        vmap = None
        if r.u('B'):
            vmap = np.frombuffer(d, np.uint16, nv, r.p).astype(np.int32); r.p += 2 * nv
        if r.u('B'):
            r.p += 4 * nv * nw
        r.p += 2 * ns  # strip lengths
        if r.u('B'):
            assert ns == 0, 'strips are not supported'
            t = np.frombuffer(d, np.uint16, 3 * nt, r.p).reshape(nt, 3).astype(np.int32); r.p += 6 * nt
        if r.u('B'):
            r.p += nv * nw
        r.u('2B')  # LOD level, global VB
        r.u('Q')  # vertex desc
        copy = np.frombuffer(d, np.uint16, 3 * nt, r.p).reshape(nt, 3).astype(np.int32); r.p += 6 * nt
        tris.append(copy)  # SSE keeps a copy with indices into the shared vertex buffer
    return pos, uv, np.concatenate(tris)


def read_shapes(path):
    h = read_header(path)
    starts, p = [], h['data_start']
    for _t, size in h['blocks']:
        starts.append(p)
        p += size
    h['starts'] = starts
    out = []
    for i, (t, _s) in enumerate(h['blocks']):
        if t != 'BSTriShape':
            continue
        s = parse_shape(h, i)
        if 'pos' not in s:
            s['pos'], s['uv'], s['tris'] = skin_partition_geometry(h, s['skin'], s['nverts'])
        s['pos'] = (s['pos'] @ s['rot'].T) * s['scale'] + s['trans']
        out.append(s)
    return out


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    want = sys.argv[3] if len(sys.argv) > 3 else None
    shapes = read_shapes(src)
    for s in shapes:
        print(f"  {s['name']:28s} verts {len(s['pos']):6d} tris {len(s['tris']):6d} "
              f"bbox {s['pos'].min(0).round(2)} .. {s['pos'].max(0).round(2)} uv {s['uv'].min(0).round(3)} .. {s['uv'].max(0).round(3)}")
    pick = next((s for s in shapes if s['name'] == want), None) if want else max(shapes, key=lambda s: len(s['tris']))
    np.savez(dst, verts=pick['pos'].astype(np.float32), uvs=pick['uv'].astype(np.float32), tris=pick['tris'])
    print('saved', pick['name'], '->', dst)
