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
skip = {lang} | {args[i + 1] for i, a in enumerate(args[:-1]) if a in ('--from', '--to', '--lang')}
paths = [a for a in args[1:] if not a.startswith('--') and a not in skip]
app = QtWidgets.QApplication(sys.argv[:1])
m.load_fonts()
w = m.MainWindow(app)
w.settings.clear()
w.cb_lang.setCurrentIndex(w.cb_lang.findData(lang))
if '--from' in args:  # direction for the screenshot, e.g. --from unp --to ube
    w.cb_from.setCurrentIndex(w.cb_from.findData(args[args.index('--from') + 1]))
    w.cb_to.setCurrentIndex(w.cb_to.findData(args[args.index('--to') + 1]))
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
    if '--mask-path' in args:  # public screenshots: show a neutral output folder instead of this machine's
        real = w.ed_out.text()
        fake = r'D:\Modding\UBE output'
        w.ed_out.setText(fake)
        if real:
            w.log.setPlainText(w.log.toPlainText().replace(real, fake))
    w.grab().save(out)
    print('saved', out)
    w.settings.clear()
    app.quit()


QtCore.QTimer.singleShot(6000 if paths else 800, grab)
app.exec()
