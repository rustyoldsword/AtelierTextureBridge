r"""Screenshot bench: opens the window with sample files, waits for analysis/preview, grabs it.
venv\Scripts\python.exe tools\shot.py <out.png> [paths...] [--lang xx] [--auto-atlas] [--convert]"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
from PyQt6 import QtCore, QtWidgets  # noqa: E402

import main as m  # noqa: E402

args = sys.argv[1:]
lang = args[args.index('--lang') + 1] if '--lang' in args else 'en'
out = args[0]
paths = [a for a in args[1:] if not a.startswith('--') and a != lang]
app = QtWidgets.QApplication(sys.argv[:1])
m.load_fonts()
w = m.MainWindow(app)
w.settings.clear()
w.cb_lang.setCurrentIndex(w.cb_lang.findData(lang))
w.resize(1280, 800)
w.show()
m.dark_title_bar(w)
if paths:
    w.add_paths(paths)
    if '--auto-atlas' in args:
        w.auto_atlas()
    w.tree.setCurrentItem(w.tree.topLevelItem(0))


def grab():
    if '--convert' in args and not getattr(w, '_ran', False):
        w._ran = True
        w.chk_open.setChecked(False)
        w.chk_over.setChecked(True)
        w.ed_out.setText(os.path.join(os.path.dirname(os.path.abspath(out)), 'gui_out'))
        w.sig.finished.connect(lambda *a: QtCore.QTimer.singleShot(400, grab))
        w.start()
        return
    w.grab().save(out)
    print('saved', out)
    w.settings.clear()
    app.quit()


QtCore.QTimer.singleShot(6000 if paths else 800, grab)
app.exec()
