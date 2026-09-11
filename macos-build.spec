# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_dynamic_libs,
    collect_submodules,
)


datas = [('configs', 'configs')]
binaries = []
hiddenimports = [
    'rebound',
    'pyqtgraph.opengl',
    'OpenGL',
    'OpenGL.GL',
    'OpenGL.error',
]
hiddenimports += collect_submodules('pyqtgraph.opengl')
hiddenimports += collect_submodules('OpenGL')

# REBOUND loads librebound dynamically from its site-packages directory.
rebound_data, rebound_binaries, rebound_hiddenimports = collect_all('rebound')
datas += rebound_data
binaries += rebound_binaries
hiddenimports += rebound_hiddenimports
binaries += collect_dynamic_libs('rebound')

try:
    import rebound
    site_packages = Path(rebound.__file__).resolve().parent.parent
    for library in site_packages.glob('librebound*.dylib'):
        binaries.append((str(library), '.'))
    for library in site_packages.glob('librebound*.so'):
        binaries.append((str(library), '.'))
except Exception as exc:
    print('WARNING: could not locate REBOUND native library:', exc)


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='3BodySimulator',
)
app = BUNDLE(
    coll,
    name='3BodySimulator.app',
    icon=None,
    bundle_identifier=None,
)
