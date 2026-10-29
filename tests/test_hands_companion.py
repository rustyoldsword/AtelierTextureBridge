"""Converting a UBE body texture to 3BA or UNP also writes the hands texture next to it.

UBE keeps the hands in the body atlas; 3BA and UNP give them a texture of their own. Users converting only the body
were left with hands that never changed, so a UBE 'body' job now also produces the hands file (unless it is turned
off, or the same texture is already queued as hands).
venv\\Scripts\\python.exe -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import core  # noqa: E402


class HandsCompanionNames(unittest.TestCase):
    def test_body_from_ube_brings_hands(self):
        self.assertEqual(core.companion_outputs(('ube', '3ba'), 'body', r'C:\out\femalebody_1.dds'),
                         [('hands', r'C:\out\femalehands_1.dds')])

    def test_into_unp_too(self):
        self.assertEqual(core.companion_outputs(('ube', 'unp'), 'body', r'C:\out\FemaleBody_1.dds'),
                         [('hands', r'C:\out\FemaleHands_1.dds')])

    def test_name_without_body_gets_suffix(self):
        self.assertEqual(core.companion_outputs(('ube', '3ba'), 'body', r'C:\out\Bruises.png'),
                         [('hands', r'C:\out\Bruises_hands.png')])

    def test_only_from_ube_and_only_for_body(self):
        self.assertEqual(core.companion_outputs(('3ba', 'ube'), 'body', r'C:\out\femalebody_1.dds'), [])
        self.assertEqual(core.companion_outputs(('ube', '3ba'), 'hands', r'C:\out\femalehands_1.dds'), [])
        self.assertEqual(core.companion_outputs(('ube', '3ba'), 'head', r'C:\out\femalehead.dds'), [])


class HandsCompanionFiles(unittest.TestCase):
    """The converter writes both files, and the hands file equals an explicit hands conversion."""

    def test_converter_writes_body_and_hands(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
        import main  # noqa: E402  (Qt classes; no window is created)
        tmp = tempfile.mkdtemp(prefix='atb_test_')
        rng = np.random.default_rng(0)
        src = os.path.join(tmp, 'ube_paint.png')
        Image.fromarray(rng.integers(0, 255, (512, 512, 4), dtype=np.uint8), 'RGBA').save(src)
        body = os.path.join(tmp, 'out', 'femalebody_1.png')
        opts = core.Options(resolution=512, overwrite=True, out_format='png')
        companions = core.companion_outputs(('ube', '3ba'), 'body', body)
        sig = main.Signals()
        done = []
        sig.progress.connect(lambda i, state, payload, dst: done.append((state, payload)))
        main.Converter([([(src, 'body')], body, companions)], ('ube', '3ba'), opts, sig).run()
        self.assertEqual(done[-1][0], 'ok', done)
        hands = os.path.join(tmp, 'out', 'femalehands_1.png')
        self.assertTrue(os.path.exists(body) and os.path.exists(hands))
        ref = os.path.join(tmp, 'ref_hands.png')
        core.convert_file(src, ref, ('ube', '3ba'), 'hands', opts)
        a, b = (np.asarray(Image.open(p), np.int16) for p in (hands, ref))
        self.assertLessEqual(np.abs(a - b).max(), 1)
        self.assertEqual(done[-1][1]['companions'], [hands])


if __name__ == '__main__':
    unittest.main()
