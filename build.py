"""Builds the Windows release: dist/AtelierTextureBridge/ (one folder, AtelierTextureBridge.exe) + a zip next to it.
venv\\Scripts\\python.exe build.py

Maps must exist first (app/maps, from tools/bake_maps.py in Blender + tools/pack_maps.py)."""
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, 'app')
NAME = 'AtelierTextureBridge'
sys.path.insert(0, APP)
from main import VERSION  # noqa: E402

EXCLUDE = ['PyQt6.QtNetwork', 'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtWebEngineCore', 'PyQt6.QtMultimedia',
           'PyQt6.QtPdf', 'PyQt6.QtSql', 'PyQt6.QtTest', 'PyQt6.QtOpenGL', 'PyQt6.QtDBus', 'tkinter', 'unittest']


def main():
    if not os.path.exists(os.path.join(APP, 'maps', 'masks.npz')):
        raise SystemExit('app/maps is empty: bake and pack the maps first')
    sep = os.pathsep
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--name', NAME,
           '--icon', os.path.join(APP, 'assets', 'icon.ico'),
           '--distpath', os.path.join(HERE, 'dist'), '--workpath', os.path.join(HERE, 'build'),
           '--specpath', os.path.join(HERE, 'build'),
           '--add-data', f'{os.path.join(APP, "maps")}{sep}maps',
           '--add-data', f'{os.path.join(APP, "assets")}{sep}assets',
           '--add-binary', f'{os.path.join(APP, "bin", "texconv.exe")}{sep}bin',
           '--paths', APP]
    for m in EXCLUDE:
        cmd += ['--exclude-module', m]
    subprocess.run(cmd + [os.path.join(APP, 'main.py')], check=True)

    out = os.path.join(HERE, 'dist', NAME)
    shutil.copyfile(os.path.join(HERE, 'README.md'), os.path.join(out, 'README.md'))
    lic = os.path.join(out, 'licenses')
    os.makedirs(lic, exist_ok=True)
    shutil.copyfile(os.path.join(APP, 'assets', 'font', 'OFL.txt'), os.path.join(lic, 'AtelierUI-font-OFL.txt'))
    with open(os.path.join(lic, 'THIRD-PARTY.txt'), 'w', encoding='utf-8') as f:
        f.write('texconv.exe — Microsoft DirectXTex, MIT License, https://github.com/microsoft/DirectXTex\n'
                'Qt 6 / PyQt6 — LGPLv3 / GPLv3 (Riverbank Computing), https://www.riverbankcomputing.com\n'
                'NumPy — BSD-3-Clause; Pillow — MIT-CMU (HPND)\n'
                'Atelier UI font — Inter 4.1 renamed, SIL Open Font License 1.1 (AtelierUI-font-OFL.txt)\n'
                'UV maps baked from the meshes of Grognak\'s UBE Texture Conversion Tool (StencilTool.blend).\n')

    zpath = os.path.join(HERE, 'dist', f'{NAME}-{VERSION}-win64.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dp, _dn, fn in os.walk(out):
            for f in fn:
                full = os.path.join(dp, f)
                z.write(full, os.path.join(NAME, os.path.relpath(full, out)))
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(out) for f in fn)
    print(f'built {out} ({size / 1e6:.0f} MB), {zpath} ({os.path.getsize(zpath) / 1e6:.0f} MB)')


if __name__ == '__main__':
    main()
