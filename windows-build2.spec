# -*- mode: python ; coding: utf-8 -*-
# windows-build.spec — size-optimized, graphs working
# Build:  pyinstaller --clean windows-build.spec

from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_dynamic_libs,
    collect_data_files,
    collect_submodules,
)

block_cipher = None

datas = [('configs', 'configs')]
binaries = []

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
hiddenimports = [
    # --- application packages ---
    'core',
    'core.constants',
    'core.kepler',
    'core.simulation',
    'core.batch',
    'core.config',
    'core.elements',
    'ui',
    'ui.main_window',
    'ui.parameter_widget',
    'ui.statistic_parameter_widget',
    'ui.plot_widget',
    'ui.stat_plot_widget',

    # --- rebound ---
    'rebound',

    # --- PyQt6 ---
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'PyQt6.QtPrintSupport',

    # --- matplotlib (3D + statistic plots) ---
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_qt',
    'matplotlib.backends.backend_agg',
    'matplotlib.backends.backend_ps',
    'matplotlib.figure',
    'matplotlib.pyplot',
    'matplotlib.ticker',
    'mpl_toolkits',
    'mpl_toolkits.mplot3d',
    'mpl_toolkits.mplot3d.axes3d',

    # --- pyqtgraph (all 2D tabs, including stacked plots on first tab) ---
    'pyqtgraph',
    'pyqtgraph.opengl',
    'OpenGL',
    'OpenGL.GL',

    # --- scipy (I_min_max uses scipy.signal.find_peaks; stat plots use interpolate) ---
    'scipy',
    *collect_submodules('scipy.signal'),
    *collect_submodules('scipy.interpolate'),
    *collect_submodules('scipy.spatial'),
    'scipy.linalg',
    'scipy.special',
    'scipy.fft',

    # --- other deps ---
    'numpy',
    'pandas',
    'yaml',
]

# ---------------------------------------------------------------------------
# REBOUND native library
# ---------------------------------------------------------------------------
tmp = collect_all('rebound')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]
binaries += collect_dynamic_libs('rebound')

try:
    import rebound
    site = Path(rebound.__file__).resolve().parent.parent
    for pattern in ('librebound*.pyd', 'librebound*.dll', 'librebound*.so'):
        for f in site.glob(pattern):
            binaries.append((str(f), '.'))
            print('Adding rebound native lib:', f)
except Exception as e:
    print('WARNING: could not locate librebound:', e)

# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------
try:
    datas += collect_data_files('pyqtgraph')
except Exception:
    pass

try:
    datas += collect_data_files('matplotlib')
except Exception:
    pass

# ---------------------------------------------------------------------------
# Excludes — heavy unused Qt modules and unrelated packages
# ---------------------------------------------------------------------------
excludes = [
    'PyQt6.QtWebEngine',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineQuick',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.Qt3DInput',
    'PyQt6.Qt3DLogic',
    'PyQt6.Qt3DAnimation',
    'PyQt6.Qt3DExtras',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtBluetooth',
    'PyQt6.QtNfc',
    'PyQt6.QtPositioning',
    'PyQt6.QtLocation',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtSerialBus',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtTextToSpeech',
    'PyQt6.QtQuick',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtQml',
    'PyQt6.QtNetworkAuth',
    'PyQt6.QtPdf',
    'PyQt6.QtPdfWidgets',
    'PyQt6.QtSpatialAudio',
    'PyQt6.QtCharts',
    'PyQt6.QtDataVisualization',
    'PyQt6.QtDesigner',
    'PyQt6.QtHelp',
    'PyQt6.QtTest',
    'PyQt6.QtSql',
    'PyQt6.QtXml',
    'PyQt6.QtDBus',
    'tkinter',
    'PySide6',
    'PySide2',
    'PyQt5',
    'IPython',
    'jupyter',
    'notebook',
    'pytest',
    'sphinx',
    'tornado',
    'zmq',
]

# ---------------------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={
        'matplotlib': {
            'backends': ['QtAgg', 'Agg', 'PS'],
        },
    },
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
    console=False,   # True while debugging; set False for release
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'Qt6Core.dll',
        'Qt6Gui.dll',
        'Qt6Widgets.dll',
        'qwindows.dll',
        'qwindowsvistastyle.dll',
        'opengl32sw.dll',
        'libEGL.dll',
        'libGLESv2.dll',
        'd3dcompiler*.dll',
    ],
    name='3BodySimulator',
)