#!/usr/bin/env python3
"""
Entry point: 3-Body AB+C Simulator

Cross-platform notes for parallel Statistic runs:
  ProcessPoolExecutor uses the ``spawn`` start method.  The project root must
  be on sys.path *before* any package imports so worker processes can import
  ``core.batch``.  The ``if __name__ == "__main__"`` guard is required on
  Windows (and recommended everywhere with spawn).
"""

import sys
from pathlib import Path

# Project root on sys.path BEFORE package imports (needed for spawn workers)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("3-Body AB+C Simulator")
    app.setOrganizationName("3BodyLab")

    window = MainWindow()
    ag = QApplication.primaryScreen().availableGeometry()
    if ag.width() < 1600 or ag.height() < 960:
        window.showMaximized()
    else:
        window.resize(1400, 800)
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
