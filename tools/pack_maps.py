"""Packs the raw Blender bakes (maps_raw/*.npy, float32) into the app's shipped maps (app/maps/*.npz).

Per map: uint16 'u', 'v' in 1/65535 of the source texture, 65535 in both = not covered. Stray bake hits are dropped
first (texels whose source position agrees with none of their 8 neighbours).
Also prints a round-trip check: source -> target -> source should land on the texel it started from.
venv\\Scripts\\python.exe tools\\pack_maps.py"""
import glob
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'maps_raw')
OUT = os.path.join(HERE, '..', 'app', 'maps')
NONE = 65535
MASK_RES = 512


def drop_lonely(m):
    """The tolerance follows the map's own scale: the UBE atlas packs the hands ~3x smaller than the CBBE hands
    texture, so honest neighbours there sit ~3 source texels apart and a fixed 3 px dropped most of them."""
    res = m.shape[0]
    cov = m[..., 2] > 0.5
    pos = m[..., :2] * res
    pair = cov[:, :-1] & cov[:, 1:]
    step = np.median(np.hypot(*(pos[:, 1:] - pos[:, :-1])[pair].T))
    tol = max(3.0, 3.0 * step)
    ok = np.zeros_like(cov)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                nb_pos = np.roll(pos, (dy, dx), axis=(0, 1))
                nb_cov = np.roll(cov, (dy, dx), axis=(0, 1))
                ok |= nb_cov & (np.hypot(*(pos - nb_pos).transpose(2, 0, 1)) <= tol)
    return cov & ok


def lookup(m, cov, uv):
    """Nearest-texel lookup of map m at normalised uv (N, 2); returns (uv', hit)."""
    res = m.shape[0]
    x = np.clip((uv[:, 0] * res).astype(int), 0, res - 1)
    y = np.clip((uv[:, 1] * res).astype(int), 0, res - 1)
    return m[y, x, :2], cov[y, x]


def main():
    os.makedirs(OUT, exist_ok=True)
    maps = {}
    for path in sorted(glob.glob(os.path.join(RAW, '*_4096.npy'))):
        name = os.path.basename(path)[:-len('_4096.npy')]
        m = np.load(path)
        cov = drop_lonely(m)
        maps[name] = (m, cov)
        u = np.where(cov, np.clip(np.round(m[..., 0] * NONE), 0, NONE - 1), NONE).astype(np.uint16)
        v = np.where(cov, np.clip(np.round(m[..., 1] * NONE), 0, NONE - 1), NONE).astype(np.uint16)
        out = os.path.join(OUT, name + '.npz')
        np.savez_compressed(out, u=u, v=v)
        print(f'{name:22s} covered {cov.mean():6.1%}  dropped {int((m[..., 2] > 0.5).sum() - cov.sum()):6d}  '
              f'{os.path.getsize(out) / 1e6:6.1f} MB')

    # layout masks (512 px, max-pooled): where each map's SOURCE texture has islands, i.e. the coverage of the
    # opposite-direction map. The app scores how much of a texture's alpha sits inside them to catch a wrong
    # direction or body part before converting.
    masks = {}
    for name, (m, cov) in maps.items():
        k = cov.shape[0] // MASK_RES
        masks[name] = cov.reshape(MASK_RES, k, MASK_RES, k).any(axis=(1, 3))
    np.savez_compressed(os.path.join(OUT, 'masks.npz'), **{n.replace('-', '__'): v for n, v in masks.items()})

    # round trip on 3BA texels: 3BA -> UBE (reverse map) -> 3BA (forward map)
    for part in ('body', 'hands', 'feet', 'head'):
        rev = maps['ube_head-3ba_head' if part == 'head' else f'ube-3ba_{part}']
        fwd = maps['3ba_head-ube_head' if part == 'head' else f'3ba_{part}-ube']
        m, cov = rev
        ys, xs = np.nonzero(cov)
        start = (np.stack([xs, ys], 1) + 0.5) / m.shape[0]
        back, hit = lookup(*fwd, m[ys, xs, :2])
        err = np.hypot(*((back[hit] - start[hit]) * 4096).T)
        print(f'round trip {part:5s}: {hit.mean():6.1%} of texels return, median error {np.median(err):.2f} px, '
              f'95% {np.percentile(err, 95):.2f} px (4K)')


if __name__ == '__main__':
    main()
