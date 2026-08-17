# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

block_cipher = None

datas = [('configs', 'configs')]
binaries = []
hiddenimports = [
    'rebound',
]
excludes = [
    'OpenGL',
    'OpenGL.GL',
    'OpenGL.GLUT',
    'pyqtgraph.opengl',
]

hiddenimports += [
    'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets',
]

# --- REBOUND (code + native library) ---
tmp = collect_all('rebound')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]
binaries += collect_dynamic_libs('rebound')

# Explicitly include librebound.*.pyd / .dll / .so
try:
    import rebound
    site = Path(rebound.__file__).resolve().parent.parent  # site-packages
    for pattern in ('librebound*.pyd', 'librebound*.dll', 'librebound*.so',
                    'librebound*.dylib'):
        for f in site.glob(pattern):
            binaries.append((str(f), '.'))
            print('Adding rebound native lib:', f)
except Exception as e:
    print('WARNING: could not locate librebound:', e)

# --- PyQt6 / pyqtgraph ---
# Do not use collect_all('pyqtgraph') here: it tries to import the old
# pyqtgraph.opengl submodule, which requires the removed OpenGL dependency.
for pkg in ('PyQt6',):
    try:
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass

try:
    from PyInstaller.utils.hooks import collect_data_files
    datas += collect_data_files('pyqtgraph')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='3BodySimulator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # True — set to True to see errors in the console
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='3BodySimulator',
)