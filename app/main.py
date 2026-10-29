"""Atelier Texture Bridge — 3BA <-> UBE body texture converter (GUI).

Dwemer Atelier look: the MO2 theme's QSS and glyphs (assets/theme) plus a few app-only rules (APP_QSS),
Atelier UI font. Eight interface languages (i18n.py), switched live; every visible text is set in retranslate().
Work runs off the GUI thread: Analyzer (per added file), PreviewTask (selected row), Converter."""
from __future__ import annotations

import ctypes
import os
import sys
import time
import traceback

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

import core
import i18n
from i18n import tr

APP_NAME = 'Atelier Texture Bridge'
VERSION = '1.2.0'
ASSETS = os.path.join(core.BASE, 'assets')
EXTS = ('.dds', '.png', '.tga')

T = {  # tokens from work/MO2_Theme/build_theme.py
    'view': '#171A20', 'base': '#1D2128', 'surf1': '#232830', 'surf2': '#2C313B', 'border': '#2E343E',
    'border_strong': '#3F4655', 'text': '#E4E1D9', 'bright': '#F4F1EA', 'muted': '#9AA1AE', 'disabled': '#5C6370',
    'accent': '#D6AC62', 'accent_hover': '#E8C27E', 'danger': '#E0645C', 'success': '#6DB37A',
}

APP_QSS = f"""
QWidget#header {{ background: {T['base']}; border-bottom: 1px solid {T['border']}; }}
QWidget#footer {{ background: {T['base']}; border-top: 1px solid {T['border']}; }}
QLabel#title {{ font-size: 17px; font-weight: 600; color: {T['bright']}; }}
QLabel#subtitle {{ color: {T['muted']}; }}
QLabel#cardTitle {{ color: {T['muted']}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel#hint {{ color: {T['muted']}; font-size: 11px; }}
QFrame#card {{ background: {T['surf1']}; border: 1px solid {T['border']}; border-radius: 8px; }}
QFrame#card QLabel {{ background: transparent; }}

QComboBox#lang {{ min-width: 120px; }}
QComboBox#layout {{ min-width: 130px; font-weight: 600; }}
QLabel#layoutCaption {{ color: {T['muted']}; font-size: 11px; }}
QPushButton#swap {{ min-width: 34px; max-width: 34px; padding: 4px; font-size: 15px; }}

QFrame#dropZone {{
  background: {T['view']}; border: 2px dashed {T['border_strong']}; border-radius: 10px;
}}
QFrame#dropZone[hot="true"] {{ border-color: {T['accent']}; background: #1E1C18; }}
QLabel#dropTitle {{ font-size: 15px; color: {T['text']}; background: transparent; }}
QLabel#dropHint {{ color: {T['muted']}; background: transparent; }}

QLabel#preview {{ background: {T['view']}; border: 1px solid {T['border']}; border-radius: 6px; }}

QPlainTextEdit#log {{ background: {T['view']}; color: {T['muted']}; border: 1px solid {T['border']};
  font-family: "Cascadia Mono", Consolas, monospace; font-size: 11px; }}
QPushButton#startButton {{ padding: 8px 26px; font-size: 14px; }}
QProgressBar {{ min-height: 8px; max-height: 8px; }}
"""

STATUS_COLORS = {'ok': T['success'], 'err': T['danger'], 'warn': T['accent'], 'busy': T['accent_hover'],
                 'idle': T['muted']}
STATUS_MARKS = {'ok': '✓ ', 'err': '✕ ', 'warn': '! ', 'busy': '⟳ ', 'idle': ''}


# ================================================================ helpers

def dark_title_bar(widget):
    """Windows 11: dark caption in the window's base colour (no-op elsewhere)."""
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), 4)  # DWMWA_USE_IMMERSIVE_DARK_MODE
        for attr, name in ((35, 'base'), (34, 'border')):  # DWMWA_CAPTION_COLOR, DWMWA_BORDER_COLOR
            c = QtGui.QColor(T[name])
            colorref = ctypes.c_int(c.red() | c.green() << 8 | c.blue() << 16)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(colorref), 4)
    except Exception:
        pass


def load_fonts():
    for f in ('AtelierUI-Regular.ttf', 'AtelierUI-SemiBold.ttf', 'AtelierUI-Bold.ttf'):
        QtGui.QFontDatabase.addApplicationFont(os.path.join(ASSETS, 'font', f))


def apply_theme(app):
    """Theme QSS with absolute glyph paths; the font list gains a system CJK font for zh/ja/ko."""
    families = ['Atelier UI', 'Segoe UI Variable Text', 'Segoe UI']
    cjk = i18n.CJK_FONTS.get(i18n.lang())
    if cjk:
        families.insert(1, cjk)
    font = QtGui.QFont()
    font.setFamilies(families)
    font.setPointSize(10)
    app.setFont(font)
    theme_dir = os.path.join(ASSETS, 'theme')
    with open(os.path.join(theme_dir, 'Dwemer Atelier.qss'), encoding='utf-8') as f:
        qss = f.read()
    qss = qss.replace('./Dwemer Atelier/', theme_dir.replace('\\', '/') + '/Dwemer Atelier/')
    qss = qss.replace('font-family: "Atelier UI", "Segoe UI Variable Text", "Segoe UI";',
                      'font-family: ' + ', '.join(f'"{f}"' for f in families) + ';')
    app.setStyleSheet(qss + APP_QSS)


def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024


def checker(size, a='#22262E', b='#1B1E25', cell=12):
    y, x = np.mgrid[0:size, 0:size]
    m = ((x // cell + y // cell) % 2).astype(bool)
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    out = np.empty((size, size, 3), np.float32)
    out[m] = (ca.red(), ca.green(), ca.blue())
    out[~m] = (cb.red(), cb.green(), cb.blue())
    return out


def compose_preview(rgba, mask=None):
    """RGBA uint8 over a dark checkerboard, the layout's islands faintly brass-tinted."""
    size = rgba.shape[0]
    bg = checker(size)
    if mask is not None:
        if mask.shape[0] != size:
            idx = (np.arange(size) * mask.shape[0] // size)
            mask = mask[np.ix_(idx, idx)]
        bg[mask] = bg[mask] * 0.82 + np.array([214, 172, 98], np.float32) * 0.18
    a = rgba[..., 3:4].astype(np.float32) / 255
    rgb = rgba[..., :3].astype(np.float32) * a + bg * (1 - a)
    rgb = np.ascontiguousarray(rgb.clip(0, 255).astype(np.uint8))
    img = QtGui.QImage(rgb.data, size, size, size * 3, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(img.copy())


LAYOUT_LABELS = {'3ba': '3BA / CBBE', 'unp': 'UNP / BHUNP', 'ube': 'UBE'}


def layout_name(layout, head):
    if head:
        return tr('layout_ube_head') if layout == 'ube' else tr('layout_vanilla_head')
    return core.LAYOUT_TAGS[layout]


def summary_text(s):
    text = f"{s['res']}px · {s['fmt']}"
    if s.get('parts', 1) > 1:
        text += f" · {tr('sum_parts', n=s['parts'])}"
    text += f" · {tr('sum_opaque')}" if s['opaque'] else ''
    for extra in s.get('companions', []):
        text += f" · {tr('sum_hands', name=os.path.basename(extra))}"
    return text


def error_text(e):
    return tr(e.key, **e.fields) if isinstance(e, core.UserError) else (str(e) or e.__class__.__name__)


# ================================================================ background work

class Signals(QtCore.QObject):
    analyzed = QtCore.pyqtSignal(str, object, object)        # path, Analysis | None, exception
    previewed = QtCore.pyqtSignal(int, object, object, object)  # token, src, out, exception
    progress = QtCore.pyqtSignal(int, str, object, str)        # job index, state, payload, out path
    finished = QtCore.pyqtSignal(int, int, int, float)         # ok, failed, skipped, seconds


class Analyzer(QtCore.QRunnable):
    def __init__(self, path, sig):
        super().__init__()
        self.path, self.sig = path, sig

    def run(self):
        try:
            self.sig.analyzed.emit(self.path, core.analyze(self.path), None)
        except Exception as e:
            self.sig.analyzed.emit(self.path, None, e)


class PreviewTask(QtCore.QRunnable):
    def __init__(self, token, sources, direction, sig):
        super().__init__()
        self.token, self.sources, self.direction, self.sig = token, sources, direction, sig

    def run(self):
        try:
            src, out = core.preview_sources(self.sources, self.direction, 384)
            self.sig.previewed.emit(self.token, src, out, None)
        except Exception as e:
            self.sig.previewed.emit(self.token, None, None, e)


class Converter(QtCore.QThread):
    """jobs: [(sources [(path, part)], dst, companions [(part, dst)])] — several sources make one UBE atlas;
    companions are extra files from the same single source (core.companion_outputs: the hands next to a UBE body).
    payload per progress state: None (busy), summary dict (ok, with 'companions': written paths), exception."""

    def __init__(self, jobs, direction, opts, sig):
        super().__init__()
        self.jobs, self.direction, self.opts, self.sig = jobs, direction, opts, sig
        self.cancelled = False

    def run(self):
        ok = failed = skipped = 0
        t0 = time.time()
        for i, (sources, dst, companions) in enumerate(self.jobs):
            if self.cancelled:
                break
            self.sig.progress.emit(i, 'busy', None, dst)
            try:
                summary = core.convert_sources(sources, dst, self.direction, self.opts)
                summary['companions'] = []
                for part, extra in companions:
                    core.convert_sources([(sources[0][0], part)], extra, self.direction, self.opts)
                    summary['companions'].append(extra)
                ok += 1
                self.sig.progress.emit(i, 'ok', summary, dst)
            except core.ExistsError as e:
                skipped += 1
                self.sig.progress.emit(i, 'warn', e, dst)
            except Exception as e:
                failed += 1
                self.sig.progress.emit(i, 'err', e, dst)
                traceback.print_exc()
        self.sig.finished.emit(ok, failed, skipped, time.time() - t0)


# ================================================================ widgets

class DropZone(QtWidgets.QFrame):
    def __init__(self, on_click_files, on_click_folder):
        super().__init__()
        self.setObjectName('dropZone')
        lay = QtWidgets.QVBoxLayout(self)
        lay.addStretch(1)
        icon = QtWidgets.QLabel()
        icon.setPixmap(QtGui.QIcon(os.path.join(ASSETS, 'icon.svg')).pixmap(72, 72))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet('background: transparent;')
        self.title = QtWidgets.QLabel()
        self.title.setObjectName('dropTitle')
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint = QtWidgets.QLabel()
        self.hint.setObjectName('dropHint')
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        self.btn_files = QtWidgets.QPushButton()
        self.btn_folder = QtWidgets.QPushButton()
        self.btn_files.clicked.connect(on_click_files)
        self.btn_folder.clicked.connect(on_click_folder)
        btns.addWidget(self.btn_files)
        btns.addWidget(self.btn_folder)
        btns.addStretch(1)
        for w in (icon, self.title, self.hint):
            lay.addWidget(w)
        lay.addSpacing(10)
        lay.addLayout(btns)
        lay.addStretch(1)

    def retranslate(self):
        self.title.setText(tr('drop_title'))
        self.hint.setText(tr('drop_hint'))
        self.btn_files.setText(tr('drop_files'))
        self.btn_folder.setText(tr('drop_folder'))

    def set_hot(self, hot):
        self.setProperty('hot', 'true' if hot else 'false')
        self.style().unpolish(self)
        self.style().polish(self)


def card():
    frame = QtWidgets.QFrame()
    frame.setObjectName('card')
    lay = QtWidgets.QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 14)
    lay.setSpacing(8)
    lab = QtWidgets.QLabel()
    lab.setObjectName('cardTitle')
    lay.addWidget(lab)
    return frame, lay, lab


def fill_combo(combo, entries):
    """entries: [(label, data)]; keeps the current selection by data across a language switch."""
    cur = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for text, data in entries:
        combo.addItem(text, data)
    i = combo.findData(cur)
    combo.setCurrentIndex(i if i >= 0 else 0)
    combo.blockSignals(False)


COL_FILE, COL_PART, COL_INFO, COL_FIT, COL_STATUS = range(5)
ROW_H = 32  # fits the part combo, so rows with and without one line up
ROLE_PATH, ROLE_ROOT, ROLE_STATUS, ROLE_PART, ROLE_GROUP = (Qt.ItemDataRole.UserRole + i for i in range(5))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.settings = QtCore.QSettings('DwemerAtelier', 'AtelierTextureBridge')
        self.sig = Signals()
        self.sig.analyzed.connect(self.on_analyzed)
        self.sig.previewed.connect(self.on_previewed)
        self.sig.progress.connect(self.on_progress)
        self.sig.finished.connect(self.on_finished)
        self.pool = QtCore.QThreadPool()
        self.pool.setMaxThreadCount(max(2, min(4, os.cpu_count() or 2)))
        self.preview_pool = QtCore.QThreadPool()
        self.preview_pool.setMaxThreadCount(1)
        self.analysis: dict[str, core.Analysis] = {}
        self.analysis_err: dict[str, Exception] = {}
        self.preview_token = 0
        self.preview_state = 'idle'  # idle | busy | done | fail
        self.preview_err = None
        self.converter: Converter | None = None
        self.job_items: list[QtWidgets.QTreeWidgetItem] = []
        self.finish_text = None  # (ok, failed, skipped, secs, cancelled) of the last run

        self.setWindowTitle(f'{APP_NAME} — 3BA ⇄ UBE')
        self.setWindowIcon(QtGui.QIcon(os.path.join(ASSETS, 'icon.ico')))
        self.setAcceptDrops(True)
        self.resize(1240, 780)
        self.setMinimumSize(1000, 640)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.build_header())
        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(16, 14, 16, 10)
        body.setSpacing(14)
        root.addLayout(body, 1)
        body.addLayout(self.build_queue(), 1)
        body.addWidget(self.build_sidebar())
        root.addWidget(self.build_footer())

        self.restore_settings()
        self.retranslate()

    # ------------------------------------------------------------ layout

    def build_header(self):
        w = QtWidgets.QWidget()
        w.setObjectName('header')
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(18, 12, 18, 12)
        logo = QtWidgets.QLabel()
        logo.setPixmap(QtGui.QIcon(os.path.join(ASSETS, 'icon.svg')).pixmap(40, 40))
        lay.addWidget(logo)
        lay.addSpacing(6)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(0)
        title = QtWidgets.QLabel(APP_NAME)
        title.setObjectName('title')
        self.subtitle = QtWidgets.QLabel()
        self.subtitle.setObjectName('subtitle')
        text.addWidget(title)
        text.addWidget(self.subtitle)
        lay.addLayout(text)
        lay.addStretch(1)

        self.cb_lang = QtWidgets.QComboBox()
        self.cb_lang.setObjectName('lang')
        for code, name in i18n.LANGS:
            self.cb_lang.addItem(name, code)
        self.cb_lang.currentIndexChanged.connect(self.on_language)
        lay.addWidget(self.cb_lang)
        lay.addSpacing(14)

        # direction: source layout -> target layout (3BA / CBBE, UNP / BHUNP, UBE)
        self.cb_from, self.cb_to = QtWidgets.QComboBox(), QtWidgets.QComboBox()
        self.lab_from, self.lab_to = QtWidgets.QLabel(), QtWidgets.QLabel()
        for combo, lab, default in ((self.cb_from, self.lab_from, '3ba'), (self.cb_to, self.lab_to, 'ube')):
            combo.setObjectName('layout')
            for key in core.LAYOUTS:
                combo.addItem(LAYOUT_LABELS[key], key)
            combo.setCurrentIndex(core.LAYOUTS.index(default))
            lab.setObjectName('layoutCaption')
        self.btn_swap = QtWidgets.QPushButton('⇄')
        self.btn_swap.setObjectName('swap')
        self.btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_swap.clicked.connect(self.swap_direction)
        self.cb_from.currentIndexChanged.connect(lambda _i: self.on_layout_changed(self.cb_from))
        self.cb_to.currentIndexChanged.connect(lambda _i: self.on_layout_changed(self.cb_to))
        for combo, lab in ((self.cb_from, self.lab_from), (self.cb_to, self.lab_to)):
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(lab)
            col.addWidget(combo)
            lay.addLayout(col)
            if combo is self.cb_from:
                lay.addSpacing(6)
                lay.addWidget(self.btn_swap, 0, Qt.AlignmentFlag.AlignBottom)
                lay.addSpacing(6)
        return w

    def build_queue(self):
        lay = QtWidgets.QVBoxLayout()
        lay.setSpacing(8)
        bar = QtWidgets.QHBoxLayout()
        self.queue_label = QtWidgets.QLabel()
        self.queue_label.setObjectName('cardTitle')
        bar.addWidget(self.queue_label)
        bar.addStretch(1)
        self.btn_add = QtWidgets.QPushButton()
        self.btn_add_dir = QtWidgets.QPushButton()
        self.btn_atlas = QtWidgets.QPushButton()
        self.btn_remove = QtWidgets.QPushButton()
        self.btn_clear = QtWidgets.QPushButton()
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_add_dir.clicked.connect(self.pick_folder)
        self.btn_atlas.clicked.connect(self.auto_atlas)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_queue)
        for b in (self.btn_add, self.btn_add_dir, self.btn_atlas, self.btn_remove, self.btn_clear):
            bar.addWidget(b)
        lay.addLayout(bar)

        self.stack = QtWidgets.QStackedWidget()
        self.drop = DropZone(self.pick_files, self.pick_folder)
        self.stack.addWidget(self.drop)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setRootIsDecorated(True)  # atlas groups fold their body/hands/feet rows
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(False)  # group rows carry no combo; every row gets ROW_H via sizeHint
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.context_menu)
        self.tree.itemSelectionChanged.connect(self.on_selection)
        self.tree.itemDoubleClicked.connect(self.open_result)
        hdr = self.tree.header()
        hdr.setSectionResizeMode(COL_FILE, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for c, w in ((COL_PART, 120), (COL_INFO, 180), (COL_FIT, 100), (COL_STATUS, 240)):
            hdr.setSectionResizeMode(c, QtWidgets.QHeaderView.ResizeMode.Interactive)
            self.tree.setColumnWidth(c, w)
        hdr.setStretchLastSection(False)
        self.stack.addWidget(self.tree)

        split = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.stack)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setObjectName('log')
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        split.addWidget(self.log)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 1)
        split.setSizes([520, 110])
        lay.addWidget(split, 1)
        return lay

    def build_sidebar(self):
        side = QtWidgets.QWidget()
        side.setStyleSheet('background: transparent;')
        lay = QtWidgets.QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(12)

        prev, pl, self.lab_preview = card()
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.prev_src = QtWidgets.QLabel()
        self.prev_out = QtWidgets.QLabel()
        self.prev_src_cap = QtWidgets.QLabel()
        self.prev_out_cap = QtWidgets.QLabel()
        for lab, cap in ((self.prev_src, self.prev_src_cap), (self.prev_out, self.prev_out_cap)):
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(4)
            lab.setObjectName('preview')
            lab.setFixedSize(160, 160)
            lab.setScaledContents(True)
            cap.setObjectName('hint')
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lab)
            col.addWidget(cap)
            row.addLayout(col)
        pl.addLayout(row)
        self.prev_note = QtWidgets.QLabel()
        self.prev_note.setObjectName('hint')
        self.prev_note.setWordWrap(True)
        pl.addWidget(self.prev_note)
        lay.addWidget(prev)

        opts, ol, self.lab_options = card()
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.cb_res = QtWidgets.QComboBox()
        self.cb_fmt = QtWidgets.QComboBox()
        self.cb_opaque = QtWidgets.QComboBox()
        self.lab_res = QtWidgets.QLabel()
        self.lab_fmt = QtWidgets.QLabel()
        self.lab_opaque = QtWidgets.QLabel()
        form.addRow(self.lab_res, self.cb_res)
        form.addRow(self.lab_fmt, self.cb_fmt)
        form.addRow(self.lab_opaque, self.cb_opaque)
        ol.addLayout(form)
        self.fill_option_combos()

        self.lab_out = QtWidgets.QLabel()
        ol.addWidget(self.lab_out)
        orow = QtWidgets.QHBoxLayout()
        self.ed_out = QtWidgets.QLineEdit()
        self.ed_out.setClearButtonEnabled(True)
        browse = QtWidgets.QPushButton('…')
        browse.setFixedWidth(34)
        browse.clicked.connect(self.pick_output)
        orow.addWidget(self.ed_out, 1)
        orow.addWidget(browse)
        ol.addLayout(orow)
        self.out_hint = QtWidgets.QLabel()
        self.out_hint.setObjectName('hint')
        self.out_hint.setWordWrap(True)
        ol.addWidget(self.out_hint)
        self.ed_out.textChanged.connect(self.update_state)
        self.chk_over = QtWidgets.QCheckBox()
        self.chk_open = QtWidgets.QCheckBox()
        self.chk_hands = QtWidgets.QCheckBox()
        ol.addWidget(self.chk_over)
        ol.addWidget(self.chk_hands)
        ol.addWidget(self.chk_open)
        lay.addWidget(opts)

        about, al, self.lab_how = card()
        self.how = QtWidgets.QLabel()
        self.how.setWordWrap(True)
        self.how.setObjectName('hint')
        al.addWidget(self.how)
        lay.addWidget(about)
        lay.addStretch(1)

        scroll = QtWidgets.QScrollArea()  # cards keep their natural height; short windows scroll instead of squashing
        scroll.setWidget(side)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedWidth(380)
        return scroll

    def fill_option_combos(self):
        fill_combo(self.cb_res, [(tr('res_source'), 0), ('1024 (1K)', 1024), ('2048 (2K)', 2048), ('4096 (4K)', 4096)])
        fill_combo(self.cb_fmt, [(tr('fmt_auto'), 'auto'), (tr('fmt_bc7'), 'BC7_UNORM'), (tr('fmt_bc3'), 'BC3_UNORM'),
                                 (tr('fmt_bc1'), 'BC1_UNORM'), (tr('fmt_raw'), 'R8G8B8A8_UNORM'), ('PNG', 'png')])
        fill_combo(self.cb_opaque, [(tr('opaque_auto'), 'auto'), (tr('opaque_yes'), 'yes'), (tr('opaque_no'), 'no')])

    def build_footer(self):
        w = QtWidgets.QWidget()
        w.setObjectName('footer')
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(18, 10, 18, 12)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(5)
        self.status = QtWidgets.QLabel()
        self.status.setObjectName('subtitle')
        self.bar = QtWidgets.QProgressBar()
        self.bar.setTextVisible(False)
        col.addWidget(self.status)
        col.addWidget(self.bar)
        lay.addLayout(col, 1)
        lay.addSpacing(16)
        self.btn_stop = QtWidgets.QPushButton()
        self.btn_stop.clicked.connect(self.stop)
        self.btn_go = QtWidgets.QPushButton()
        self.btn_go.setObjectName('startButton')
        self.btn_go.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_go.clicked.connect(self.start)
        lay.addWidget(self.btn_stop)
        lay.addWidget(self.btn_go)
        return w

    # ------------------------------------------------------------ language

    def on_language(self, _i):
        i18n.set_lang(self.cb_lang.currentData())
        apply_theme(self.app)
        self.retranslate()

    def retranslate(self):
        self.subtitle.setText(tr('subtitle'))
        self.cb_lang.setToolTip(tr('lang_tip'))
        self.lab_from.setText(tr('layout_from'))
        self.lab_to.setText(tr('layout_to'))
        self.cb_from.setToolTip(tr('layout_from_tip'))
        self.cb_to.setToolTip(tr('layout_to_tip'))
        self.btn_swap.setToolTip(tr('swap_tip'))
        self.btn_add.setText(tr('btn_files'))
        self.btn_add_dir.setText(tr('btn_folder'))
        self.btn_atlas.setText(tr('btn_auto_atlas'))
        self.btn_atlas.setToolTip(tr('tip_auto_atlas'))
        self.btn_remove.setText(tr('btn_remove'))
        self.btn_clear.setText(tr('btn_clear'))
        self.drop.retranslate()
        self.tree.setHeaderLabels([tr('col_file'), tr('col_part'), tr('col_source'), tr('col_fit'), tr('col_result')])
        self.lab_preview.setText(tr('card_preview'))
        self.lab_options.setText(tr('card_options'))
        self.lab_how.setText(tr('card_how'))
        self.lab_res.setText(tr('opt_res'))
        self.lab_fmt.setText(tr('opt_format'))
        self.lab_opaque.setText(tr('opt_opaque'))
        self.cb_opaque.setToolTip(tr('opaque_tip'))
        self.lab_out.setText(tr('opt_output'))
        self.ed_out.setPlaceholderText(tr('out_placeholder'))
        self.chk_over.setText(tr('chk_overwrite'))
        self.chk_open.setText(tr('chk_open'))
        self.chk_hands.setText(tr('chk_hands'))
        self.chk_hands.setToolTip(tr('chk_hands_tip'))
        self.how.setText(tr('how_text') + '<br><br>' + tr('how_atlas'))
        self.btn_stop.setText(tr('btn_stop'))
        self.btn_go.setText(tr('btn_convert'))
        self.fill_option_combos()
        for it in self.leaves():
            combo = self.tree.itemWidget(it, COL_PART)
            fill_combo(combo, [(tr('part_' + p), p) for p in core.PARTS])
            self.render_info(it)
            self.render_status(it)
        for g in self.groups():
            self.render_group(g)
            self.render_status(g)
        self.render_preview_text()
        self.update_state()

    # ------------------------------------------------------------ state

    @property
    def direction(self):
        return self.cb_from.currentData(), self.cb_to.currentData()

    def units(self):
        """Top-level rows: single files and atlas groups — one conversion each (towards UBE)."""
        return [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]

    @staticmethod
    def is_group(it):
        return bool(it.data(0, ROLE_GROUP))

    @staticmethod
    def members(group):
        return [group.child(i) for i in range(group.childCount())]

    def groups(self):
        return [u for u in self.units() if self.is_group(u)]

    def leaves(self):
        """Every file row, inside groups too."""
        out = []
        for u in self.units():
            out.extend(self.members(u) if self.is_group(u) else [u])
        return out

    def part_of(self, item):
        return item.data(0, ROLE_PART)

    def base_member(self, group):
        """The member the atlas is named after: the body if there is one."""
        return min(self.members(group), key=lambda m: core.PARTS.index(self.part_of(m)))

    def output_path(self, item):
        if self.is_group(item):
            item = self.base_member(item)
        src, root = item.data(0, ROLE_PATH), item.data(0, ROLE_ROOT)
        stem, ext = os.path.splitext(os.path.relpath(src, root))
        fmt = self.cb_fmt.currentData()
        if fmt == 'png':
            ext = '.png'
        elif fmt != 'auto' or ext.lower() == '.tga':
            ext = '.dds'
        rel = stem + ext
        custom = self.ed_out.text().strip()
        if custom:
            return os.path.join(custom, rel)
        return os.path.join(root, core.LAYOUT_TAGS[self.direction[1]], rel)

    def update_state(self):
        n = self.tree.topLevelItemCount()
        busy = self.converter is not None
        self.stack.setCurrentIndex(1 if n else 0)
        self.queue_label.setText(f"{tr('queue')} · {n}" if n else tr('queue'))
        self.btn_go.setEnabled(n > 0 and not busy)
        self.btn_stop.setVisible(busy)
        for w in (self.btn_add, self.btn_add_dir, self.btn_remove, self.btn_clear, self.cb_from, self.cb_to, self.btn_swap,
                  self.cb_res, self.cb_fmt, self.cb_opaque, self.ed_out, self.chk_over, self.chk_hands):
            w.setEnabled(not busy)
        tag = core.LAYOUT_TAGS[self.direction[1]]
        self.out_hint.setText(tr('out_hint_custom') if self.ed_out.text().strip() else tr('out_hint_auto', tag=tag))
        if not busy:
            self.status.setText(self.finished_text() or (tr('status_ready') if n else tr('status_empty')))
        if not n:
            self.prev_src.clear()
            self.prev_out.clear()
            self.preview_state = 'idle'
            self.render_preview_text()
        for it in self.leaves():
            it.setToolTip(COL_STATUS, self.output_path(it))
            self.tree.itemWidget(it, COL_PART).setEnabled(not busy)
            self.refresh_fit(it)
        for g in self.groups():
            g.setToolTip(COL_STATUS, self.output_path(g))
            self.render_group(g)
        self.btn_atlas.setEnabled(not busy and core.atlas_direction(self.direction))

    # ------------------------------------------------------------ adding files

    def pick_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, tr('dlg_textures'), self.settings.value('last_dir', ''), f"{tr('dlg_textures')} (*.dds *.png *.tga)")
        if files:
            self.settings.setValue('last_dir', os.path.dirname(files[0]))
            self.add_paths(files)

    def pick_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, tr('dlg_folder'), self.settings.value('last_dir', ''))
        if d:
            self.settings.setValue('last_dir', d)
            self.add_paths([d])

    def pick_output(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, tr('opt_output'), self.ed_out.text())
        if d:
            self.ed_out.setText(os.path.normpath(d))

    def add_paths(self, paths):
        known = {it.data(0, ROLE_PATH).lower() for it in self.leaves()}
        added = 0
        for p in paths:
            p = os.path.normpath(p)
            if os.path.isdir(p):
                root = p
                for dp, dn, fn in os.walk(p):
                    # earlier output of this app inside the mod folder is not input
                    dn[:] = [d for d in dn if os.path.relpath(os.path.join(dp, d), root).lower() not in ('ube', '3ba')]
                    for f in sorted(fn):
                        full = os.path.join(dp, f)
                        if f.lower().endswith(EXTS) and full.lower() not in known:
                            known.add(full.lower())
                            self.add_item(full, root)
                            added += 1
            elif p.lower().endswith(EXTS) and p.lower() not in known:
                known.add(p.lower())
                self.add_item(p, os.path.dirname(p))
                added += 1
        if added:
            self.finish_text = None
            self.say(tr('added', n=added))
        self.update_state()

    def add_item(self, path, root):
        it = QtWidgets.QTreeWidgetItem()
        it.setData(0, ROLE_PATH, path)
        it.setData(0, ROLE_ROOT, root)
        it.setData(0, ROLE_STATUS, ('idle', 'st_queued'))
        it.setData(0, ROLE_PART, core.guess_part(path))
        it.setText(COL_FILE, os.path.relpath(path, root))
        it.setToolTip(COL_FILE, path)
        self.tree.addTopLevelItem(it)
        self.attach_combo(it)
        self.render_info(it)
        self.render_status(it)
        self.pool.start(Analyzer(path, self.sig))

    @staticmethod
    def size_row(it):
        it.setSizeHint(COL_PART, QtCore.QSize(0, ROW_H))

    def attach_combo(self, it):
        """The part combo; Qt drops item widgets whenever a row is moved, so grouping re-attaches it."""
        combo = QtWidgets.QComboBox()
        fill_combo(combo, [(tr('part_' + p), p) for p in core.PARTS])
        combo.setCurrentIndex(core.PARTS.index(self.part_of(it)))
        combo.setEnabled(self.converter is None)
        combo.currentIndexChanged.connect(lambda _i, item=it, c=combo: self.on_part_changed(item, c.currentData()))
        self.tree.setItemWidget(it, COL_PART, combo)
        self.size_row(it)

    def render_group(self, g):
        font = g.font(COL_FILE)
        font.setBold(True)
        g.setFont(COL_FILE, font)
        g.setForeground(COL_FILE, QtGui.QColor(T['accent_hover']))
        g.setText(COL_FILE, tr('atlas_row', name=os.path.basename(self.output_path(g))))
        g.setText(COL_PART, tr('part_atlas', n=g.childCount()))
        g.setText(COL_INFO, '→ UBE')
        if self.converter is None and (g.data(0, ROLE_STATUS) or ('idle',))[0] == 'idle':
            to_ube = core.atlas_direction(self.direction)
            g.setData(0, ROLE_STATUS, ('idle', 'st_queued') if to_ube else ('idle', 'st_split', None, {'arrow': self.arrow()}))
            for m in self.members(g):
                if (m.data(0, ROLE_STATUS) or ('idle',))[0] == 'idle':
                    m.setData(0, ROLE_STATUS, ('idle', 'st_in_atlas' if to_ube else 'st_queued'))
            for it in [g] + self.members(g):
                self.render_status(it)
        self.refresh_fit(g)

    def render_info(self, it):
        path = it.data(0, ROLE_PATH)
        size = human_size(os.path.getsize(path)) if os.path.exists(path) else '?'
        an = self.analysis.get(path)
        if path in self.analysis_err:
            it.setText(COL_INFO, f"{size} · {tr('info_error')}")
        elif an is None:
            it.setText(COL_INFO, f"{size} · {tr('st_analyzing')}")
        else:
            i = an.info
            kind = core.texture_kind(path, i.fourcc)
            extra = f" · {tr('info_normal')}" if kind == 'normal' else (f" · {tr('info_opaque')}" if an.opaque else '')
            it.setText(COL_INFO, f'{i.width}×{i.height} · {i.fmt.replace("_UNORM", "")}{extra}')

    def set_status(self, it, state, key=None, raw=None, **fields):
        """Status is kept as (state, i18n key | None, raw text, fields) so a language switch can re-render it."""
        it.setData(0, ROLE_STATUS, (state, key, raw, fields))
        self.render_status(it)

    def render_status(self, it):
        st = it.data(0, ROLE_STATUS)
        state, key, raw, fields = (tuple(st) + (None, None, {}))[:4]
        text = tr(key, **(fields or {})) if key else (raw or '')
        it.setText(COL_STATUS, STATUS_MARKS[state] + text)
        it.setForeground(COL_STATUS, QtGui.QColor(STATUS_COLORS[state]))

    def on_analyzed(self, path, an, err):
        for it in self.leaves():
            if it.data(0, ROLE_PATH) != path:
                continue
            if an is None:
                self.analysis_err[path] = err
                self.set_status(it, 'err', 'st_unreadable', err=error_text(err))
            else:
                self.analysis[path] = an
                if core.texture_kind(path, an.info.fourcc) == 'normal':
                    self.set_status(it, 'warn', 'st_normal_warn')
            self.render_info(it)
            self.refresh_fit(it)
            if it.parent() is not None:
                self.refresh_fit(it.parent())
        cur = self.tree.currentItem()
        if cur is not None and (cur.data(0, ROLE_PATH) == path or self.is_group(cur)):
            self.on_selection()

    def refresh_fit(self, it):
        if self.is_group(it):
            fits = [self.fit_of(m) for m in self.members(it)]
            if not core.atlas_direction(self.direction) or any(f is None for f in fits):
                it.setText(COL_FIT, '')
                return
            self.show_fit(it, min(fits))
            return
        an = self.analysis.get(it.data(0, ROLE_PATH))
        if not an:
            return
        if an.opaque:
            it.setText(COL_FIT, '—')
            it.setToolTip(COL_FIT, tr('fit_opaque_tip'))
            it.setForeground(COL_FIT, QtGui.QColor(T['muted']))
            return
        self.show_fit(it, an.fit[(self.direction, self.part_of(it))])

    def fit_of(self, it):
        an = self.analysis.get(it.data(0, ROLE_PATH))
        if an is None:
            return None
        return 1.0 if an.opaque else an.fit[(self.direction, self.part_of(it))]

    def show_fit(self, it, fit):
        it.setText(COL_FIT, f'{"✓" if fit >= 0.5 else "⚠"} {fit:.0%}')
        it.setForeground(COL_FIT, QtGui.QColor(T['success'] if fit >= 0.75 else T['accent'] if fit >= 0.5 else T['danger']))
        it.setToolTip(COL_FIT, tr('fit_tip', fit=f'{fit:.0%}'))

    # ------------------------------------------------------------ queue actions

    def remove_selected(self):
        sel = self.tree.selectedItems()
        for it in [i for i in sel if self.is_group(i)]:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(it))
        for it in sel:
            if self.is_group(it):
                continue
            parent = it.parent()
            if parent is None:
                if self.tree.indexOfTopLevelItem(it) >= 0:
                    self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(it))
            elif self.tree.indexOfTopLevelItem(parent) >= 0:  # its group was not removed whole
                parent.removeChild(it)
                if parent.childCount() < 2:
                    self.ungroup(parent)
        self.update_state()

    def make_group(self, rows):
        """rows: top-level single files -> one atlas group, inserted where the first of them was."""
        rows = sorted(rows, key=lambda r: core.PARTS.index(self.part_of(r)))
        try:
            core.check_atlas([self.part_of(r) for r in rows], os.path.basename(rows[0].data(0, ROLE_PATH)))
        except core.UserError as e:
            QtWidgets.QMessageBox.warning(self, APP_NAME, error_text(e))
            return None
        at = min(self.tree.indexOfTopLevelItem(r) for r in rows)
        for r in rows:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(r))
        g = QtWidgets.QTreeWidgetItem()
        self.size_row(g)
        g.setData(0, ROLE_GROUP, True)
        g.setData(0, ROLE_STATUS, ('idle', 'st_queued'))
        self.tree.insertTopLevelItem(at, g)
        for r in rows:
            r.setData(0, ROLE_STATUS, ('idle', 'st_in_atlas'))
            g.addChild(r)
            self.attach_combo(r)
            self.render_status(r)
        g.setExpanded(True)
        self.render_group(g)
        return g

    def ungroup(self, g):
        at = self.tree.indexOfTopLevelItem(g)
        rows = self.members(g)
        self.tree.takeTopLevelItem(at)
        for k, r in enumerate(rows):
            g.removeChild(r)
            r.setData(0, ROLE_STATUS, ('idle', 'st_queued'))
            self.tree.insertTopLevelItem(at + k, r)
            self.attach_combo(r)
            self.render_status(r)
            self.refresh_fit(r)

    def auto_atlas(self):
        singles = [u for u in self.units() if not self.is_group(u)]
        by_path = {u.data(0, ROLE_PATH): u for u in singles}
        sets = core.find_atlas_sets([(u.data(0, ROLE_PATH), self.part_of(u)) for u in singles])
        made = sum(1 for paths in sets if self.make_group([by_path[p] for p in paths]))
        self.say(tr('auto_atlas_done', n=made) if made else tr('auto_atlas_none'))
        self.update_state()
        if not made:
            self.status.setText(tr('auto_atlas_none'))

    def clear_queue(self):
        self.tree.clear()
        self.analysis.clear()
        self.analysis_err.clear()
        self.finish_text = None
        self.update_state()

    def context_menu(self, pos):
        sel = self.tree.selectedItems()
        if not sel or self.converter is not None:
            return
        files = [i for i in sel if not self.is_group(i)]
        m = QtWidgets.QMenu(self)
        if files:
            sub = m.addMenu(tr('col_part'))
            for p in core.PARTS:
                sub.addAction(tr('part_' + p), lambda p=p: [self.tree.itemWidget(i, COL_PART).setCurrentIndex(
                    core.PARTS.index(p)) for i in files])
        singles = [i for i in files if i.parent() is None]
        if len(singles) >= 2 and len(singles) == len(sel) and core.atlas_direction(self.direction):
            m.addAction(tr('menu_group'), lambda: (self.make_group(singles), self.update_state()))
        grouped = {id(g): g for g in [i for i in sel if self.is_group(i)] + [i.parent() for i in files if i.parent()]}
        if grouped:
            m.addAction(tr('menu_ungroup'), lambda: ([self.ungroup(g) for g in grouped.values()], self.update_state()))
        m.addSeparator()
        src_row = files[0] if files else self.base_member(sel[0])
        m.addAction(tr('menu_open_src'), lambda: self.reveal(src_row.data(0, ROLE_PATH)))
        out = self.output_path(sel[0])
        a = m.addAction(tr('menu_open_out'), lambda: self.reveal(out))
        a.setEnabled(os.path.exists(out))
        m.addSeparator()
        m.addAction(tr('menu_remove'), self.remove_selected)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def reveal(self, path):
        if os.path.exists(path):
            QtCore.QProcess.startDetached('explorer.exe', ['/select,', os.path.normpath(path)])
        else:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.dirname(path)))

    def open_result(self, it, _col):
        if it.parent() is not None and core.atlas_direction(self.direction):
            it = it.parent()  # a member's result is the atlas
        out = self.output_path(it)
        src = self.base_member(it) if self.is_group(it) else it
        self.reveal(out if os.path.exists(out) else src.data(0, ROLE_PATH))

    def on_part_changed(self, it, part):
        it.setData(0, ROLE_PART, part)
        self.refresh_fit(it)
        if it.parent() is not None:
            self.render_group(it.parent())
        cur = self.tree.currentItem()
        if cur is not None and (cur is it or cur is it.parent()):
            self.on_selection()

    def on_layout_changed(self, changed):
        """Keep source and target different: picking the other side's layout swaps them."""
        other = self.cb_to if changed is self.cb_from else self.cb_from
        if self.cb_from.currentData() == self.cb_to.currentData():
            prev = getattr(self, '_last_direction', ('3ba', 'ube'))
            keep = prev[1] if changed is self.cb_from else prev[0]
            if keep == changed.currentData():
                keep = next(k for k in core.LAYOUTS if k != changed.currentData())
            other.blockSignals(True)
            other.setCurrentIndex(core.LAYOUTS.index(keep))
            other.blockSignals(False)
        self._last_direction = self.direction
        self.on_direction(None)

    def swap_direction(self):
        src, dst = self.direction
        for combo, key in ((self.cb_from, dst), (self.cb_to, src)):
            combo.blockSignals(True)
            combo.setCurrentIndex(core.LAYOUTS.index(key))
            combo.blockSignals(False)
        self._last_direction = self.direction
        self.on_direction(None)

    def on_direction(self, _id):
        self.update_state()
        self.on_selection()

    # ------------------------------------------------------------ preview

    def on_selection(self):
        it = self.tree.currentItem()
        if it is None or not it.isSelected():
            return
        if self.is_group(it) and core.atlas_direction(self.direction):
            rows = self.members(it)
        else:
            rows = [self.base_member(it) if self.is_group(it) else it]
        sources = [(r.data(0, ROLE_PATH), self.part_of(r)) for r in rows]
        self.preview_token += 1
        self.preview_part = sources[0][1]  # sources come body-first
        self.preview_parts = [p for _, p in sources]
        self.preview_count = len(sources)
        self.preview_dir = self.direction
        self.preview_state = 'busy'
        self.render_preview_text()
        self.preview_pool.clear()
        self.preview_pool.start(PreviewTask(self.preview_token, sources, self.direction, self.sig))

    def render_preview_text(self):
        if self.preview_state == 'idle':
            self.prev_src_cap.setText('')
            self.prev_out_cap.setText('')
            self.prev_note.setText(tr('prev_idle'))
            return
        (src, dst), head = self.preview_dir, self.preview_part == 'head'
        before = layout_name(src, head) + (f' ×{self.preview_count}' if self.preview_count > 1 else '')
        self.prev_src_cap.setText(tr('prev_before', layout=before))
        self.prev_out_cap.setText(tr('prev_after', layout=layout_name(dst, head)))
        self.prev_note.setText({'busy': tr('prev_busy'), 'done': tr('prev_done')}.get(
            self.preview_state) or tr('prev_fail', err=error_text(self.preview_err)))

    def on_previewed(self, token, src, out, err):
        if token != self.preview_token:
            return
        if src is None:
            self.preview_state, self.preview_err = 'fail', err
        else:
            d, p = self.preview_dir, self.preview_part
            other = d[::-1]
            self.prev_src.setPixmap(compose_preview(src, core.source_layout(d, p)))
            islands = np.logical_or.reduce([core.source_layout(other, q) for q in self.preview_parts])
            self.prev_out.setPixmap(compose_preview(out, islands))
            self.preview_state = 'done'
        self.render_preview_text()

    # ------------------------------------------------------------ run

    def options(self):
        return core.Options(resolution=self.cb_res.currentData() or None, out_format=self.cb_fmt.currentData(),
                            opaque=self.cb_opaque.currentData(), overwrite=self.chk_over.isChecked())

    def start(self):
        items, jobs = [], []
        for u in self.units():
            if self.is_group(u) and core.atlas_direction(self.direction):
                try:
                    core.check_atlas([self.part_of(m) for m in self.members(u)], os.path.basename(self.output_path(u)))
                except core.UserError as e:
                    QtWidgets.QMessageBox.warning(self, APP_NAME, error_text(e))
                    return
                items.append(u)
                jobs.append(([(m.data(0, ROLE_PATH), self.part_of(m)) for m in self.members(u)], self.output_path(u), []))
            else:  # single files, and group members one by one when not building a UBE atlas
                for it in (self.members(u) if self.is_group(u) else [u]):
                    items.append(it)
                    jobs.append(([(it.data(0, ROLE_PATH), self.part_of(it))], self.output_path(it), []))
        if self.chk_hands.isChecked():
            # a UBE body also writes the 3BA / UNP hands file, unless that texture is already queued as hands
            queued_hands = {it.data(0, ROLE_PATH).lower() for it in self.leaves() if self.part_of(it) == 'hands'}
            for sources, dst, companions in jobs:
                if len(sources) == 1 and sources[0][0].lower() not in queued_hands:
                    companions.extend(core.companion_outputs(self.direction, sources[0][1], dst))
        clash = {}
        for sources, dst, companions in jobs:
            for out in [dst] + [extra for _part, extra in companions]:
                clash.setdefault(out.lower(), []).append(' + '.join(p for p, _ in sources))
        dup = [v for v in clash.values() if len(v) > 1]  # two jobs, one file; an atlas's own sources are fine
        if dup:
            QtWidgets.QMessageBox.warning(self, APP_NAME, tr('clash', files='\n'.join(dup[0])))
            return
        low = [it.text(COL_FILE) for it in self.leaves() if it.text(COL_FIT).startswith('⚠')]
        if low:
            r = QtWidgets.QMessageBox.question(self, APP_NAME, tr('low_fit', n=len(low), name=low[0]))
            if r != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self.job_items = items
        self.finish_text = None
        for it in items:
            self.set_status(it, 'idle', 'st_waiting')
        self.bar.setRange(0, len(jobs))
        self.bar.setValue(0)
        self.converter = Converter(jobs, self.direction, self.options(), self.sig)
        self.update_state()
        self.say(f"— {self.arrow()}: {tr('files_n', n=len(jobs))}")
        self.converter.start()

    def arrow(self):
        src, dst = self.direction
        return f'{core.LAYOUT_TAGS[src]} → {core.LAYOUT_TAGS[dst]}'

    def stop(self):
        if self.converter:
            self.converter.cancelled = True
            self.status.setText(tr('stopping'))

    def on_progress(self, i, state, payload, dst):
        it = self.job_items[i]
        name = it.text(COL_FILE)
        if state == 'busy':
            self.set_status(it, 'busy', 'st_converting')
            self.tree.scrollToItem(it)
            self.status.setText(f"{self.arrow()} · {tr('run_progress', name=name, i=i + 1, n=len(self.job_items))}")
            return
        self.bar.setValue(i + 1)
        if state == 'ok':
            text = summary_text(payload)
            self.set_status(it, 'ok', raw=text)
            self.say(f'OK  {name} → {dst}  ({text})')
        else:
            if isinstance(payload, core.UserError):
                self.set_status(it, state, payload.key, **payload.fields)
            else:
                self.set_status(it, state, raw=error_text(payload))
            mark = tr('log_skip') if state == 'warn' else tr('log_err')
            self.say(f'{mark}  {name}: {error_text(payload)}')

    def finished_text(self):
        if not self.finish_text:
            return None
        ok, failed, skipped, secs, cancelled = self.finish_text
        parts = [tr('done_ok', n=ok)]
        if skipped:
            parts.append(tr('done_skip', n=skipped))
        if failed:
            parts.append(tr('done_err', n=failed))
        parts.append(tr('seconds', s=f'{secs:.1f}'))
        return (tr('done_stopped') + ' · ' if cancelled else '') + ' · '.join(parts)

    def on_finished(self, ok, failed, skipped, secs):
        conv = self.converter
        self.converter = None
        self.finish_text = (ok, failed, skipped, secs, bool(conv and conv.cancelled))
        self.say('— ' + self.finished_text())
        self.update_state()
        if ok and self.chk_open.isChecked():
            done = next((self.output_path(it) for it in self.job_items
                         if (it.data(0, ROLE_STATUS) or ('',))[0] == 'ok'), None)
            if done:
                self.reveal(done)
        QtWidgets.QApplication.alert(self)

    def say(self, line):
        self.log.appendPlainText(time.strftime('%H:%M:%S  ') + line)

    # ------------------------------------------------------------ drag & drop

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self.converter is None:
            e.acceptProposedAction()
            self.drop.set_hot(True)

    def dragLeaveEvent(self, e):
        self.drop.set_hot(False)

    def dropEvent(self, e):
        self.drop.set_hot(False)
        self.add_paths([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    # ------------------------------------------------------------ settings

    def restore_settings(self):
        s = self.settings
        i = self.cb_lang.findData(s.value('lang', 'en'))
        self.cb_lang.blockSignals(True)
        self.cb_lang.setCurrentIndex(max(0, i))
        self.cb_lang.blockSignals(False)
        i18n.set_lang(self.cb_lang.currentData())
        apply_theme(self.app)
        src, dst = s.value('layout_from', '3ba'), s.value('layout_to', 'ube')
        if src in core.LAYOUTS and dst in core.LAYOUTS and src != dst:
            for combo, key in ((self.cb_from, src), (self.cb_to, dst)):
                combo.blockSignals(True)
                combo.setCurrentIndex(core.LAYOUTS.index(key))
                combo.blockSignals(False)
        self._last_direction = self.direction
        for combo, key in ((self.cb_res, 'res'), (self.cb_fmt, 'fmt'), (self.cb_opaque, 'opaque')):
            i = combo.findData(s.value(key, combo.currentData(), type=type(combo.currentData())))
            if i >= 0:
                combo.setCurrentIndex(i)
        self.ed_out.setText(s.value('out', ''))
        self.chk_over.setChecked(s.value('overwrite', False, type=bool))
        self.chk_open.setChecked(s.value('open', True, type=bool))
        self.chk_hands.setChecked(s.value('hands_companion', True, type=bool))
        geo = s.value('geometry')
        if geo is not None:
            self.restoreGeometry(geo)

    def closeEvent(self, e):
        if self.converter is not None:
            r = QtWidgets.QMessageBox.question(self, APP_NAME, tr('close_busy'))
            if r != QtWidgets.QMessageBox.StandardButton.Yes:
                e.ignore()
                return
            self.converter.cancelled = True
            self.converter.wait(60000)
        s = self.settings
        s.setValue('lang', i18n.lang())
        s.setValue('layout_from', self.direction[0])
        s.setValue('layout_to', self.direction[1])
        s.setValue('res', self.cb_res.currentData())
        s.setValue('fmt', self.cb_fmt.currentData())
        s.setValue('opaque', self.cb_opaque.currentData())
        s.setValue('out', self.ed_out.text().strip())
        s.setValue('overwrite', self.chk_over.isChecked())
        s.setValue('open', self.chk_open.isChecked())
        s.setValue('hands_companion', self.chk_hands.isChecked())
        s.setValue('geometry', self.saveGeometry())
        super().closeEvent(e)


def cli(args):
    """AtelierTextureBridge.exe --cli <from>-<to> body|hands|feet|head <src> <dst> [--res N] [--format F]
    <from>-<to> is two of 3ba / unp / ube, e.g. 3ba-unp; the 1.x spellings to_ube / to_3ba still work.
    Exit code 0 on success; the summary or error also goes to <dst>.log (the GUI build has no console)."""
    spec, part, src, dst = args[:4]
    direction = {'to_ube': core.TO_UBE, 'to_3ba': core.TO_3BA}.get(spec) or tuple(spec.lower().split('-'))
    res = int(args[args.index('--res') + 1]) if '--res' in args else None
    fmt = args[args.index('--format') + 1] if '--format' in args else 'auto'
    try:
        msg, code = summary_text(core.convert_file(src, dst, direction, part, core.Options(res, fmt, overwrite=True))), 0
    except Exception as e:
        msg, code = f'ERROR {error_text(e)}', 1
    with open(dst + '.log', 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    return code


def main():
    if '--cli' in sys.argv:
        sys.exit(cli(sys.argv[sys.argv.index('--cli') + 1:]))
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('DwemerAtelier.AtelierTextureBridge')
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    load_fonts()
    w = MainWindow(app)
    w.show()
    dark_title_bar(w)
    args = [a for a in sys.argv[1:] if os.path.exists(a)]
    if args:  # files/folders dropped onto the .exe
        w.add_paths(args)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
