"""Conversion core between three female body UV layouts: 3BA / CBBE, UNP / BHUNP (both with the vanilla head) and
UBE (one body atlas + UBE head).

A coordinate map baked once from the body meshes (Grognak's StencilTool.blend; BHUNP added by tools/bake_unp.py) says,
for every texel of the target layout, where to read the source texture. Pixels are resampled with premultiplied
bilinear filtering, so colour and alpha stay as authored (no re-lighting, no gamma shift). The maps ship with the
app (maps/*.npz, 4096 px, built by tools/bake_maps.py + tools/pack_maps.py), so Blender is not needed at runtime.

DDS goes through Microsoft texconv (bundled): decoded to raw RGBA8 in the source's colour space and re-encoded."""
from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
MAPS_DIR = os.path.join(BASE, 'maps')
TEXCONV = os.path.join(BASE, 'bin', 'texconv.exe')
MAP_RES = 4096
NONE = 65535
CREATE_NO_WINDOW = 0x08000000

LAYOUTS = ('3ba', 'unp', 'ube')
LAYOUT_TAGS = {'3ba': '3BA', 'unp': 'UNP', 'ube': 'UBE'}  # output subfolder and short display name
TO_UBE, TO_3BA = ('3ba', 'ube'), ('ube', '3ba')  # a direction is a (source layout, target layout) pair
PARTS = ('body', 'hands', 'feet', 'head')
# maps that are not shipped: the coordinates are chained at load time through the 3BA layout
COMPOSED = {f'unp_{p}-ube': (f'3ba_{p}-ube', f'unp_{p}-3ba_{p}') for p in ('body', 'hands', 'feet')}
COMPOSED.update({f'ube-unp_{p}': (f'3ba_{p}-unp_{p}', f'ube-3ba_{p}') for p in ('body', 'hands', 'feet')})


class UserError(Exception):
    """A failure the GUI shows in the user's language: key into i18n.S plus its fields."""
    def __init__(self, key, **fields):
        super().__init__(key)
        self.key, self.fields = key, fields


class ExistsError(UserError):
    pass


def texture_id(layout, part):
    """Which texture layout a part lives in: UBE's body, hands and feet share one atlas, and 3BA and UNP both use
    the vanilla head."""
    if part == 'head':
        return 'ube_head' if layout == 'ube' else '3ba_head'
    return 'ube' if layout == 'ube' else f'{layout}_{part}'


def physical_texture(layout, part):
    """The texture file a part is painted on: 3BA and UNP keep the feet on the body texture."""
    tid = texture_id(layout, part)
    return tid.replace('_feet', '_body') if layout != 'ube' else tid


def map_name(direction, part):
    src, dst = direction
    return f'{texture_id(src, part)}-{texture_id(dst, part)}'


def is_identity(direction, part):
    """3BA <-> UNP faces: both are the vanilla head, nothing moves."""
    src, dst = direction
    return texture_id(src, part) == texture_id(dst, part)


def atlas_direction(direction):
    """Several 3BA / UNP textures can merge into the one UBE atlas."""
    return direction[1] == 'ube' and direction[0] != 'ube'


# ---------------------------------------------------------------- guessing what a file is

_PART_PATTERNS = [
    ('head', re.compile(r'(head|face|femalehead|malehead|_hd|lips|brow|eye|makeup|blush)', re.I)),
    ('hands', re.compile(r'(hand|finger|nail)', re.I)),
    ('feet', re.compile(r'(feet|foot|toe|sole)', re.I)),
]


def guess_part(path):
    """Part from the file name and its folders; body unless something says otherwise (SlaveTats areas included)."""
    low = path.replace('\\', '/').lower()
    stem = os.path.basename(low)
    for part, rx in _PART_PATTERNS:
        if rx.search(stem):
            return part
    for part, folder in (('head', '/face/'), ('hands', '/hands/'), ('feet', '/feet/')):
        if folder in low:
            return part
    return 'body'


def texture_kind(path, fourcc):
    """'normal' / 'specular' / 'color' — normal maps carry directions, which a UV remap does not rotate."""
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    if stem.endswith(('_n', '_msn', '_normal')) or fourcc in ('ATI2', 'BC5U'):
        return 'normal'
    if stem.endswith(('_s', '_sk', '_spec')):
        return 'specular'
    return 'color'


# ---------------------------------------------------------------- DDS header

DXGI_NAMES = {2: 'R32G32B32A32_FLOAT', 10: 'R16G16B16A16_FLOAT', 28: 'R8G8B8A8_UNORM', 29: 'R8G8B8A8_UNORM_SRGB',
              71: 'BC1_UNORM', 72: 'BC1_UNORM_SRGB', 74: 'BC2_UNORM', 75: 'BC2_UNORM_SRGB', 77: 'BC3_UNORM',
              78: 'BC3_UNORM_SRGB', 80: 'BC4_UNORM', 83: 'BC5_UNORM', 87: 'B8G8R8A8_UNORM', 91: 'B8G8R8A8_UNORM_SRGB',
              95: 'BC6H_UF16', 98: 'BC7_UNORM', 99: 'BC7_UNORM_SRGB'}
FOURCC_FORMATS = {'DXT1': 'BC1_UNORM', 'DXT2': 'BC2_UNORM', 'DXT3': 'BC2_UNORM', 'DXT4': 'BC3_UNORM',
                  'DXT5': 'BC3_UNORM', 'ATI1': 'BC4_UNORM', 'BC4U': 'BC4_UNORM', 'ATI2': 'BC5_UNORM',
                  'BC5U': 'BC5_UNORM'}


@dataclass
class TexInfo:
    width: int
    height: int
    fmt: str        # DXGI-style name, e.g. BC7_UNORM_SRGB; 'PNG' etc. for plain images
    fourcc: str
    mips: int

    @property
    def srgb(self):
        return self.fmt.endswith('_SRGB')


def read_info(path) -> TexInfo:
    if not path.lower().endswith('.dds'):
        with Image.open(path) as im:
            return TexInfo(im.width, im.height, im.format or 'IMAGE', '', 1)
    with open(path, 'rb') as f:
        d = f.read(148)
    if d[:4] != b'DDS ':
        raise UserError('err_not_dds')
    h, w = struct.unpack('<II', d[12:20])
    mips = max(1, struct.unpack('<I', d[28:32])[0])
    pf_flags = struct.unpack('<I', d[80:84])[0]
    fourcc = d[84:88].decode('latin-1') if pf_flags & 0x4 else ''
    if fourcc == 'DX10':
        fmt = DXGI_NAMES.get(struct.unpack('<I', d[128:132])[0], f'DXGI_{struct.unpack("<I", d[128:132])[0]}')
    elif fourcc:
        fmt = FOURCC_FORMATS.get(fourcc, fourcc)
    else:
        bits = struct.unpack('<I', d[88:92])[0]
        fmt = 'B8G8R8A8_UNORM' if bits == 32 else f'RGB{bits}'
    return TexInfo(w, h, fmt, fourcc, mips)


# ---------------------------------------------------------------- texconv / raw DDS i/o

def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        raise RuntimeError('texconv: ' + ' | '.join(tail))
    return r.stdout


def _write_raw_dds(path, rgba8, srgb):
    """Uncompressed DX10 DDS (R8G8B8A8, one mip) — texconv's input, avoids WIC guessing the colour space."""
    h, w = rgba8.shape[:2]
    hdr = bytearray(148)
    hdr[0:4] = b'DDS '
    struct.pack_into('<7I', hdr, 4, 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x8, h, w, w * 4, 0, 1)
    struct.pack_into('<2I4s', hdr, 76, 32, 0x4, b'DX10')
    struct.pack_into('<I', hdr, 108, 0x1000)
    struct.pack_into('<5I', hdr, 128, 29 if srgb else 28, 3, 0, 1, 0)
    with open(path, 'wb') as f:
        f.write(hdr)
        f.write(np.ascontiguousarray(rgba8, dtype=np.uint8).tobytes())


def _read_raw_dds(path):
    with open(path, 'rb') as f:
        d = f.read()
    h, w = struct.unpack('<II', d[12:20])
    off = 148 if d[84:88] == b'DX10' else 128
    fmt = struct.unpack('<I', d[128:132])[0] if off == 148 else 28
    px = np.frombuffer(d, np.uint8, w * h * 4, off).reshape(h, w, 4)
    if fmt in (87, 91):  # BGRA
        px = px[..., [2, 1, 0, 3]]
    return px


def load_rgba(path, info: TexInfo | None = None):
    """Top mip as float32 RGBA in [0, 1], values in the file's own colour space (sRGB stays sRGB-encoded)."""
    if not path.lower().endswith('.dds'):
        with Image.open(path) as im:
            return np.asarray(im.convert('RGBA')).astype(np.float32) / 255.0
    info = info or read_info(path)
    work = tempfile.mkdtemp(prefix='atb_in_')
    try:
        src = os.path.join(work, 'x.dds')
        shutil.copyfile(path, src)  # mod authors' file names upset texconv
        out = os.path.join(work, 'out')
        os.makedirs(out)
        fmt = 'R8G8B8A8_UNORM_SRGB' if info.srgb else 'R8G8B8A8_UNORM'
        _run([TEXCONV, '-nologo', '-y', '-dx10', '-m', '1', '-f', fmt, '-ft', 'dds', '-o', out, src])
        return _read_raw_dds(os.path.join(out, 'x.dds')).astype(np.float32) / 255.0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def save_texture(path, rgba, fmt, srgb=False):
    """rgba float32 [0,1] -> .dds in DXGI format fmt (full mip chain) or .png when path ends with .png."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    px = (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)
    if path.lower().endswith('.png'):
        Image.fromarray(px, 'RGBA').save(path)
        return
    work = tempfile.mkdtemp(prefix='atb_out_')
    try:
        raw = os.path.join(work, 'x.dds')
        _write_raw_dds(raw, px, srgb)
        out = os.path.join(work, 'out')
        os.makedirs(out)
        cmd = [TEXCONV, '-nologo', '-y', '-m', '0', '-f', fmt, '-o', out]
        if fmt.startswith('BC7'):
            cmd += ['-bcquick']  # visually the same for overlays, several times faster on CPU
        _run(cmd + [raw])
        tmp = path + '.atb-tmp'
        shutil.copyfile(os.path.join(out, 'x.dds'), tmp)
        os.replace(tmp, path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------- maps

@lru_cache(maxsize=5)  # a composed map needs its two parts loaded too; ~80 MB each at 4K
def _load_map(name):
    if name in COMPOSED:
        return _compose(*COMPOSED[name])
    if name.split('-')[0] == name.split('-')[1]:
        return _identity_map()
    z = np.load(os.path.join(MAPS_DIR, name + '.npz'))
    u, v = z['u'], z['v']
    cov = u != NONE
    return u, v, cov


def _identity_map():
    c = np.minimum(((np.arange(MAP_RES) + 0.5) / MAP_RES * NONE).round(), NONE - 1).astype(np.uint16)
    return np.broadcast_to(c[None, :], (MAP_RES, MAP_RES)), np.broadcast_to(c[:, None], (MAP_RES, MAP_RES)), \
        np.ones((MAP_RES, MAP_RES), bool)


def _compose(outer, inner):
    """Target texel -> intermediate (3BA) coordinate through `outer`, then -> source coordinate through `inner`,
    read at the nearest intermediate texel (4K maps: under half a texel). Only coordinates are chained; the
    pixels are still resampled once."""
    ou, ov, oc = _load_map(outer)
    iu, iv, ic = _load_map(inner)
    x = np.minimum((ou.astype(np.float32) / NONE * MAP_RES).astype(np.int32), MAP_RES - 1)
    y = np.minimum((ov.astype(np.float32) / NONE * MAP_RES).astype(np.int32), MAP_RES - 1)
    cov = oc & ic[y, x]
    u = np.where(cov, iu[y, x], NONE).astype(np.uint16)
    v = np.where(cov, iv[y, x], NONE).astype(np.uint16)
    return u, v, cov


@lru_cache(maxsize=3)  # float32 copies, ~150 MB each at 4K
def get_map(name, res):
    """(u, v, covered) at the requested output resolution; u, v float32 in [0, 1] of the source texture.
    Lower resolutions take, per output texel, the shipped texel nearest its centre (no averaging across seams)."""
    u, v, cov = _load_map(name)
    if res != MAP_RES:
        idx = np.minimum(((np.arange(res) + 0.5) * MAP_RES / res).astype(int), MAP_RES - 1)
        u, v, cov = u[np.ix_(idx, idx)], v[np.ix_(idx, idx)], cov[np.ix_(idx, idx)]
    return u.astype(np.float32) / NONE, v.astype(np.float32) / NONE, cov


# ---------------------------------------------------------------- resampling

def remap(src, mu, mv, cov, rows=512):
    """Premultiplied bilinear sample of src (H, W, 4) through the map; uncovered texels come out fully transparent."""
    h, w = src.shape[:2]
    pm = src.copy()
    pm[..., :3] *= pm[..., 3:4]  # filter premultiplied so transparent texels do not bleed their colour
    res = mu.shape[0]
    out = np.zeros((res, res, 4), np.float32)
    for r0 in range(0, res, rows):  # row bands keep the temporaries small at 4K
        sl = slice(r0, r0 + rows)
        x = np.clip(mu[sl] * w - 0.5, 0, w - 1)
        y = np.clip(mv[sl] * h - 0.5, 0, h - 1)
        x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
        x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
        fx, fy = (x - x0)[..., None], (y - y0)[..., None]
        s = (pm[y0, x0] * (1 - fx) * (1 - fy) + pm[y0, x1] * fx * (1 - fy) +
             pm[y1, x0] * (1 - fx) * fy + pm[y1, x1] * fx * fy)
        a = s[..., 3:4]
        rgb = np.where(a > 1e-6, s[..., :3] / np.maximum(a, 1e-6), 0.0)
        band = np.concatenate([rgb, a], axis=-1)
        band[~cov[sl]] = 0.0
        out[sl] = band
    return out


def fill_outside(img, mask):
    """Every texel outside `mask` gets the nearest inside value (all channels). Push-pull: halve the image with
    mask-weighted 2x2 averages down to 1 px, then on the way back up fill each level's gaps from the coarser
    one — linear time, unlike growing the border texel by texel."""
    c = img.shape[2]
    acc = img * mask[..., None]
    w = mask.astype(np.float32)
    levels = []
    while min(acc.shape[:2]) > 1 and acc.shape[0] % 2 == 0 and acc.shape[1] % 2 == 0:
        levels.append((acc, w))
        h, wd = acc.shape[0] // 2, acc.shape[1] // 2
        acc = acc.reshape(h, 2, wd, 2, c).sum(axis=(1, 3))
        w = w.reshape(h, 2, wd, 2).sum(axis=(1, 3))
    val = acc / np.maximum(w, 1e-6)[..., None]
    for acc, w in reversed(levels):
        up = val.repeat(2, axis=0).repeat(2, axis=1)
        val = np.where(w[..., None] > 0, acc / np.maximum(w, 1e-6)[..., None], up)
    out = img.copy()
    out[~mask] = val[~mask]
    return out


def dilate(rgba, cov):
    """Seam padding for opaque skin/detail output, so mips and filtering never pull black in at island edges."""
    return fill_outside(rgba[..., :3], cov)


@lru_cache(maxsize=1)
def _island_masks():
    z = np.load(os.path.join(MAPS_DIR, 'islands.npz'))
    return {k: np.unpackbits(z[k]).reshape(MAP_RES, MAP_RES).astype(bool) for k in z.files}


def pad_islands(img, layout, part):
    """Edge padding of a SOURCE texture: colour and alpha of every UV island run on past its edge into the empty
    space around it, other islands untouched. Bilinear reads at an island's border then stay on that island
    instead of mixing in the void (transparent for overlays, filler for skins); in UBE the hands and feet islands
    are so small that, magnified ~3x into 3BA, that mix showed as rings and lines along every seam.
    Averaged premultiplied, so a fading paint edge pads with its own colour."""
    islands = _island_masks().get(physical_texture(layout, part))
    if islands is None:
        return img
    h, w = img.shape[:2]
    rows = ((np.arange(h) + 0.5) * MAP_RES / h).astype(int)
    cols = ((np.arange(w) + 0.5) * MAP_RES / w).astype(int)
    mask = islands[np.ix_(rows, cols)]  # nearest island texel for each source texel (any size, any aspect)
    if mask.all() or not mask.any():
        return img
    pm = np.concatenate([img[..., :3] * img[..., 3:4], img[..., 3:4]], axis=-1)
    pm = fill_outside(pm, mask)
    a = pm[..., 3:4]
    out = np.concatenate([np.where(a > 1e-6, pm[..., :3] / np.maximum(a, 1e-6), 0.0), a], axis=-1)
    out[mask] = img[mask]
    return out.astype(np.float32)


# ---------------------------------------------------------------- layout check

@lru_cache(maxsize=1)
def _masks():
    z = np.load(os.path.join(MAPS_DIR, 'masks.npz'))
    return {k.replace('__', '-'): z[k] for k in z.files}


def part_maps(direction, part):
    """Maps one texture of this part goes through. CBBE and UNP paint the feet on the body texture (toes and soles
    in its upper corners) and UBE keeps them in its atlas, so 'body' carries body + feet in every direction; 'feet'
    alone is for feet-only overlays (SlaveTats Feet area)."""
    if part == 'body':
        return [map_name(direction, 'body'), map_name(direction, 'feet')]
    return [map_name(direction, part)]


def source_layout(direction, part):
    """Islands of the layout a texture must be in to be converted this way (the opposite maps' coverage)."""
    if is_identity(direction, part):
        return np.ones((512, 512), bool)
    m = _masks()
    return np.logical_or.reduce([m[n] for n in part_maps(direction[::-1], part)])


@dataclass
class Analysis:
    info: TexInfo
    opaque: bool
    fit: dict  # (direction, part) -> share of the painted alpha that lies on that source layout's islands


def analyze(path):
    info = read_info(path)
    src = load_rgba(path, info)
    a = src[..., 3]
    opaque = (a > 0.995).mean() > 0.98
    small = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((512, 512), Image.BOX), np.float32)
    total = small.sum()
    fit = {}
    for d in ((a, b) for a in LAYOUTS for b in LAYOUTS if a != b):
        for p in PARTS:
            fit[(d, p)] = 1.0 if opaque or total <= 0 else float(small[source_layout(d, p)].sum() / total)
    # Only a hint: the layouts overlap a lot (the head islands fill ~80 % of their square), so a low score
    # flags a wrong direction or part, while a high one proves little.
    return Analysis(info, opaque, fit)


# ---------------------------------------------------------------- one job

@dataclass
class Options:
    resolution: int | None = None   # None = as the source (clamped 512..4096, power of two)
    out_format: str = 'auto'        # 'auto' | DXGI name | 'png'
    opaque: str = 'auto'            # 'auto' | 'yes' | 'no' — opaque textures get seam padding and a solid alpha
    overwrite: bool = False


def output_format(info: TexInfo, opts: Options, has_alpha: bool):
    if opts.out_format != 'auto':
        return opts.out_format
    f = info.fmt
    if f.startswith('BC1') and has_alpha:
        f = 'BC3_UNORM_SRGB' if info.srgb else 'BC3_UNORM'
    if f in DXGI_NAMES.values() and not f.startswith(('BC6', 'R32', 'R16')):
        return f
    return 'BC7_UNORM_SRGB' if info.srgb else 'BC7_UNORM'


def output_res(info: TexInfo, opts: Options):
    if opts.resolution:
        return opts.resolution
    side = max(info.width, info.height)
    return int(min(4096, max(512, 2 ** round(np.log2(max(side, 1))))))


def _is_opaque(rgba, opts: Options):
    return (rgba[..., 3] > 0.995).mean() > 0.98 if opts.opaque == 'auto' else opts.opaque == 'yes'


def check_atlas(parts, name=''):
    """An atlas takes at most one body, one hands and one feet texture; the face has its own UBE head."""
    if 'head' in parts or len(set(parts)) != len(parts):
        raise UserError('group_bad', name=name)


def _ordered(sources):
    return sorted(sources, key=lambda sp: PARTS.index(sp[1]))


def _layers(sources, direction):
    """(source index, map name) in fill order: every source's own part first, then the feet a body texture
    carries — so a separate feet texture in the same atlas wins over the body's feet."""
    own = [(i, map_name(direction, part)) for i, (_, part) in enumerate(sources)]
    implied = [(i, n) for i, (_, part) in enumerate(sources) for n in part_maps(direction, part)[1:]]
    return own + implied


def _composite(images, sources, direction, res):
    """Remap every layer into one target; the islands of different maps are disjoint, first come first served."""
    out = np.zeros((res, res, 4), np.float32)
    filled = np.zeros((res, res), bool)
    for i, name in _layers(sources, direction):
        mu, mv, cov = get_map(name, res)
        take = cov & ~filled
        if take.any():
            out[take] = remap(images[i], mu, mv, cov)[take]
            filled |= take
    return out, filled


def convert_sources(sources, dst_path, direction, opts: Options):
    """sources: [(path, part)]. One source = a plain conversion. Several (3BA body/hands/feet, direction to_ube)
    are baked into ONE UBE atlas: their maps cover disjoint islands, so each fills its own part of the target.
    Resolution: the largest any source asks for; format: the body's (else the first part's).
    Returns {res, fmt, opaque, parts}. Raises on failure; never touches the sources."""
    sources = _ordered(sources)
    if len(sources) > 1:
        name = os.path.basename(dst_path)
        if not atlas_direction(direction):
            raise UserError('group_bad', name=name)
        check_atlas([p for _, p in sources], name)
    if os.path.exists(dst_path) and not opts.overwrite:
        raise ExistsError('err_exists')
    infos = [read_info(path) for path, _ in sources]
    res = max(output_res(i, opts) for i in infos)
    images, all_opaque = [], True
    for (path, _part), info in zip(sources, infos):
        src = load_rgba(path, info)
        if _is_opaque(src, opts):
            src[..., 3] = 1.0
        else:
            all_opaque = False
        images.append(pad_islands(src, direction[0], _part))
    out, filled = _composite(images, sources, direction, res)
    del images
    if all_opaque:
        out[..., :3] = dilate(out, filled)
        out[..., 3] = 1.0
    if dst_path.lower().endswith('.png'):
        save_texture(dst_path, out, 'png')
        fmt = 'PNG'
    else:
        fmt = output_format(infos[0], opts, not all_opaque)
        save_texture(dst_path, out, fmt, srgb=fmt.endswith('_SRGB'))
    return {'res': res, 'fmt': fmt, 'opaque': all_opaque, 'parts': len(sources)}


def convert_file(src_path, dst_path, direction, part, opts: Options):
    return convert_sources([(src_path, part)], dst_path, direction, opts)


def companion_outputs(direction, part, dst_path):
    """Extra files one source should also produce: UBE keeps the hands in the body atlas, 3BA and UNP give them a
    texture of their own, so a UBE 'body' converted out of UBE also writes the hands file next to the body one
    (femalebody_1 -> femalehands_1; a name without 'body' gets '_hands')."""
    if part != 'body' or direction[0] != 'ube' or direction[1] == 'ube':
        return []
    folder, name = os.path.split(dst_path)
    stem, ext = os.path.splitext(name)
    m = re.search('body', stem, re.I)
    if m:
        word = m.group(0)
        hands = 'HANDS' if word.isupper() else 'Hands' if word[0].isupper() else 'hands'
        stem = stem[:m.start()] + hands + stem[m.end():]
    else:
        stem += '_hands'
    return [('hands', os.path.join(folder, stem + ext))]


def preview_sources(sources, direction, size=512):
    """(first source RGBA, converted RGBA) as uint8 arrays at preview size; several sources are composited
    into one atlas the same way convert_sources does."""
    sources = _ordered(sources)
    images = [pad_islands(load_rgba(path), direction[0], part) for path, part in sources]
    out, _filled = _composite(images, sources, direction, size)
    first = np.asarray(Image.fromarray((images[0] * 255 + 0.5).astype(np.uint8), 'RGBA').resize(
        (size, size), Image.BILINEAR))
    return first, (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- finding body/hands/feet sets

_PART_WORD = re.compile(r'(body|hands?|feet|foot)', re.I)
_AREA_DIRS = {'body': 'body', 'hands': 'hands', 'hand': 'hands', 'feet': 'feet', 'foot': 'feet'}


def find_atlas_sets(entries):
    """entries: [(path, part)] with parts already chosen. Returns lists of paths that look like one texture set
    for the three 3BA parts: same folder and the same name once the part word is cut out
    (femalebody_1.dds + femalehands_1.dds), or the same file name under sibling Body/Hands/Feet folders
    (SlaveTats areas). Each set holds 2-3 distinct parts."""
    keys = {}
    for path, part in entries:
        if part == 'head':
            continue
        folder, name = os.path.split(path)
        stem, ext = os.path.splitext(name)
        if _AREA_DIRS.get(os.path.basename(folder).lower()) == part:
            key = ('area', os.path.dirname(folder).lower(), name.lower())
        elif _PART_WORD.search(stem):
            key = ('name', folder.lower(), _PART_WORD.sub('#', stem, count=1).lower() + ext.lower())
        else:
            continue
        keys.setdefault(key, []).append((path, part))
    sets = []
    for members in keys.values():
        parts = [p for _, p in members]
        if len(members) >= 2 and len(set(parts)) == len(parts):
            sets.append([path for path, _ in _ordered(members)])
    return sets
