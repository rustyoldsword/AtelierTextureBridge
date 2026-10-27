"""Conversion core: 3BA (CBBE UVs, vanilla head) <-> UBE body atlas / UBE head.

A coordinate map baked once from Grognak's StencilTool.blend says,
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

TO_UBE, TO_3BA = 'to_ube', 'to_3ba'
PARTS = ('body', 'hands', 'feet', 'head')


class UserError(Exception):
    """A failure the GUI shows in the user's language: key into i18n.S plus its fields."""
    def __init__(self, key, **fields):
        super().__init__(key)
        self.key, self.fields = key, fields


class ExistsError(UserError):
    pass


def map_name(direction, part):
    if direction == TO_UBE:
        return '3ba_head-ube_head' if part == 'head' else f'3ba_{part}-ube'
    return 'ube_head-3ba_head' if part == 'head' else f'ube-3ba_{part}'


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

@lru_cache(maxsize=4)
def _load_map(name):
    z = np.load(os.path.join(MAPS_DIR, name + '.npz'))
    u, v = z['u'], z['v']
    cov = u != NONE
    return u, v, cov


@lru_cache(maxsize=6)
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


def dilate(rgba, cov):
    """Fill every uncovered texel from the nearest covered colour (seam padding for opaque skin/detail maps),
    so mips and filtering never pull black in at UV island edges. Push-pull: halve the image with
    coverage-weighted 2x2 averages down to 1 px, then on the way back up fill each level's gaps from the
    coarser one — linear time, unlike growing the border texel by texel."""
    rgb = rgba[..., :3] * cov[..., None]
    w = cov.astype(np.float32)
    levels = []
    while rgb.shape[0] > 1 and rgb.shape[0] % 2 == 0 and rgb.shape[1] % 2 == 0:
        levels.append((rgb, w))
        h, wd = rgb.shape[0] // 2, rgb.shape[1] // 2
        rgb = rgb.reshape(h, 2, wd, 2, 3).sum(axis=(1, 3))
        w = w.reshape(h, 2, wd, 2).sum(axis=(1, 3))
    color = rgb / np.maximum(w, 1e-6)[..., None]
    for rgb, w in reversed(levels):
        up = color.repeat(2, axis=0).repeat(2, axis=1)
        color = np.where(w[..., None] > 0, rgb / np.maximum(w, 1e-6)[..., None], up)
    out = rgba[..., :3].copy()
    out[~cov] = color[~cov]
    return out


# ---------------------------------------------------------------- layout check

@lru_cache(maxsize=1)
def _masks():
    z = np.load(os.path.join(MAPS_DIR, 'masks.npz'))
    return {k.replace('__', '-'): z[k] for k in z.files}


def part_maps(direction, part):
    """Maps one texture of this part goes through. CBBE paints the feet on the body texture (femalebody_1.dds has
    the toes and soles in its upper corners), so 'body' carries body + feet both ways; 'feet' alone is for
    feet-only overlays (SlaveTats Feet area)."""
    if part == 'body':
        return [map_name(direction, 'body'), map_name(direction, 'feet')]
    return [map_name(direction, part)]


def source_layout(direction, part):
    """Islands of the layout a texture must be in to be converted this way (the opposite maps' coverage)."""
    other = TO_3BA if direction == TO_UBE else TO_UBE
    m = _masks()
    return np.logical_or.reduce([m[n] for n in part_maps(other, part)])


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
    for d in (TO_UBE, TO_3BA):
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
        if direction != TO_UBE:
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
        images.append(src)
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


def preview_sources(sources, direction, size=512):
    """(first source RGBA, converted RGBA) as uint8 arrays at preview size; several sources are composited
    into one atlas the same way convert_sources does."""
    sources = _ordered(sources)
    images = [load_rgba(path) for path, _ in sources]
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
