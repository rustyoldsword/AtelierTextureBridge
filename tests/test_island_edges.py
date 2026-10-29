"""Paint that reaches an island's edge must still reach it after conversion.

A UBE overlay painted exactly up to the edges of every atlas island (transparent outside, as real overlays are) is
converted UBE -> 3BA. Every 3BA texel the conversion writes must come out fully painted: before source islands were
padded, bilinear reads at the borders mixed in the transparent void and left a faded rim along every seam - a ring
around the wrists and ankles once UBE's small hand and foot islands are magnified into 3BA.
venv\\Scripts\\python.exe -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import core  # noqa: E402

R = 2048


class PaintReachesIslandEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.mkdtemp(prefix='atb_test_')
        idx = ((np.arange(R) + 0.5) * core.MAP_RES / R).astype(int)
        paint = np.zeros((R, R, 4), np.uint8)
        paint[core._island_masks()['ube'][np.ix_(idx, idx)]] = (230, 60, 60, 255)
        src = os.path.join(tmp, 'ube_paint.png')
        Image.fromarray(paint, 'RGBA').save(src)
        opts = core.Options(resolution=R, overwrite=True, out_format='png', opaque='no')
        cls.alpha = {}
        for part in ('body', 'hands'):
            dst = os.path.join(tmp, f'{part}.png')
            core.convert_file(src, dst, core.TO_3BA, part, opts)
            cls.alpha[part] = np.asarray(Image.open(dst).convert('RGBA'), np.float32)[..., 3] / 255

    def check(self, part, map_name):
        written = core.get_map(map_name, R)[2]
        faded = (self.alpha[part][written] < 0.9).mean()
        self.assertLess(faded, 0.002, f'{map_name}: {faded:.2%} of the painted texels came out faded')

    def test_body(self):
        self.check('body', 'ube-3ba_body')

    def test_feet(self):
        self.check('body', 'ube-3ba_feet')

    def test_hands(self):
        self.check('hands', 'ube-3ba_hands')


if __name__ == '__main__':
    unittest.main()
