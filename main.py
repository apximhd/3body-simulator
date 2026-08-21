#!/usr/bin/env python3
"""
Entry point: 3-Body AB+C Simulator

Cross-platform notes for parallel Statistic runs:
  ProcessPoolExecutor uses the ``spawn`` start method on Windows (and often
  elsewhere).  ``multiprocessing.freeze_support()`` is required for PyInstaller
  builds on Windows; on macOS/Linux and when running from source it is a no-op.

  Package imports that start the GUI must stay inside main() so worker
  processes do not open a second application window.
"""

import sys
import multiprocessing
from pathlib import Path

# Project root on sys.path before package imports (needed for spawn workers).
# PyInstaller sets sys.frozen and extracts files to sys._MEIPASS.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    """Create the Qt application and show the main window."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from ui.main_window import MainWindow

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("3-Body AB+C Simulator")
    app.setOrganizationName("3BodyLab")

    window = MainWindow()
    ag = QApplication.primaryScreen().availableGeometry()
    if ag.width() < 1400 or ag.height() < 850:
        window.showMaximized()
    else:
        window.resize(1400, 850)
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Required for Windows + PyInstaller + multiprocessing; harmless elsewhere.
    multiprocessing.freeze_support()
    main()
