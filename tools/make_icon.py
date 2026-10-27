"""Draws the app icon (brass Dwemer cog with a two-way arrow) -> app/assets/icon.svg + icon.png + icon.ico.
venv\\Scripts\\python.exe tools\\make_icon.py"""
import io
import math
import os

from PIL import Image
from PyQt6 import QtCore, QtGui, QtSvg, QtWidgets

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'app', 'assets')

teeth = ''.join(
    f'<rect x="28" y="2.5" width="8" height="10" rx="1.6" transform="rotate({i * 45} 32 32)" fill="url(#brass)"/>'
    for i in range(8))
SVG = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>
  <linearGradient id="brass" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#EBC888"/><stop offset="1" stop-color="#A9772F"/>
  </linearGradient>
</defs>
{teeth}
<circle cx="32" cy="32" r="23.5" fill="url(#brass)"/>
<circle cx="32" cy="32" r="18" fill="#1D2128" stroke="#7A5826" stroke-width="1.2"/>
<g fill="none" stroke="#F4F1EA" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 27.5h19M36.5 22.5l5 5-5 5"/>
  <path d="M42 36.5H23M27.5 31.5l-5 5 5 5"/>
</g>
</svg>'''


def render(size):
    img = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    QtSvg.QSvgRenderer(QtCore.QByteArray(SVG.encode())).render(p)
    p.end()
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, 'PNG')
    return Image.open(io.BytesIO(bytes(buf.data()))).convert('RGBA')


def main():
    QtWidgets.QApplication([])
    with open(os.path.join(ASSETS, 'icon.svg'), 'w', encoding='utf-8') as f:
        f.write(SVG)
    big = render(256)
    big.save(os.path.join(ASSETS, 'icon.png'))
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    big.save(os.path.join(ASSETS, 'icon.ico'), sizes=[(s, s) for s in sizes],
             append_images=[render(s) for s in sizes])
    print('icon written')


if __name__ == '__main__':
    main()
