"""Compares UNP bake variants (maps_test_<variant>/, 1K): round trip, agreement with 3D nearest-vertex correspondence,
and an image round trip of a CBBE skin. Needs unp/scene/*.npz from tools/export_scene_geom.py.
python tools/compare_unp_wraps.py <skin femalebody_1.dds> <variant> [...]"""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, 'tools')
sys.path.insert(0, 'app')
from pack_maps import drop_lonely, lookup  # noqa: E402
import core  # noqa: E402

RES = 1024
skin, variants = sys.argv[1], sys.argv[2:]


def nearest(a, b, chunk=1500):
    idx = np.empty(len(a), np.int64)
    for i in range(0, len(a), chunk):
        idx[i:i + chunk] = ((a[i:i + chunk, None] - b[None]) ** 2).sum(-1).argmin(1)
    return idx


def sample(m, uv):
    x = np.clip((uv[:, 0] * RES).astype(int), 0, RES - 1)
    y = np.clip((uv[:, 1] * RES).astype(int), 0, RES - 1)
    return m[y, x, :2], m[y, x, 2] > 0.5


geo = {}
for part in ('body', 'hands', 'feet'):
    c, u = np.load(f'unp/scene/cbbe_{part}.npz'), np.load(f'unp/scene/unp_{part}.npz')
    ci = np.random.default_rng(0).choice(len(c['verts']), 1500, replace=False)
    ui = nearest(c['verts'][ci], u['verts'])
    geo[part] = (c['uvs'][ci], u['uvs'][ui])

src = core.load_rgba(skin)
small = np.asarray(Image.fromarray((src * 255).astype(np.uint8)).resize((RES, RES), Image.BILINEAR), np.float32) / 255
tiles = [Image.fromarray((small[..., :3] * 255).astype(np.uint8))]
for v in variants:
    print('==', v)
    maps = {}
    for part in ('body', 'hands', 'feet'):
        f = np.load(f'maps_test_{v}/3ba_{part}-unp_{part}_{RES}.npy')
        r = np.load(f'maps_test_{v}/unp_{part}-3ba_{part}_{RES}.npy')
        fc, rc = drop_lonely(f), drop_lonely(r)
        maps[part] = (f, fc, r, rc)
        ys, xs = np.nonzero(rc)
        start = (np.stack([xs, ys], 1) + 0.5) / RES
        back, hit = lookup(f, fc, r[ys, xs, :2])
        rt = np.hypot(*((back[hit] - start[hit]) * 4096).T)
        cuv, uuv = geo[part]
        got_r, ok_r = sample(r, cuv)
        got_f, ok_f = sample(f, uuv)
        gr = np.linalg.norm((got_r - uuv)[ok_r], axis=1) * 4096
        gf = np.linalg.norm((got_f - cuv)[ok_f], axis=1) * 4096
        print(f'  {part:5s} round trip median {np.median(rt):5.2f} / 95% {np.percentile(rt, 95):6.2f} px'
              f' | vs 3D nearest vertex: 3BA->UNP median {np.median(gf):5.1f}, UNP->3BA median {np.median(gr):5.1f} px  (4K)')
    f, fc, r, rc = maps['body']
    unp = core.remap(src, f[..., 0].astype(np.float32), f[..., 1].astype(np.float32), fc)
    back = core.remap(unp, r[..., 0].astype(np.float32), r[..., 1].astype(np.float32), rc)
    d = np.abs(back[..., :3] - small[..., :3]).mean(-1)
    print(f'  image round trip colour error inside islands: mean {d[rc].mean():.4f}, 95% {np.percentile(d[rc], 95):.4f}')
    tiles.append(Image.fromarray((np.clip(back[..., :3], 0, 1) * 255).astype(np.uint8)))
crop = (300, 380, 724, 700)  # chest and belly
sheet = Image.new('RGB', ((crop[2] - crop[0]) * len(tiles), crop[3] - crop[1]))
for k, t in enumerate(tiles):
    sheet.paste(t.crop(crop), ((crop[2] - crop[0]) * k, 0))
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
sheet.save('unp/compare_wraps.png')
print('sheet: original |', ' | '.join(variants))
