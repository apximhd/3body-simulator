"""
Main application window.
Supports two modes (switch via Mode menu only):
  1. Single run  — original interactive interface with plots
  2. Statistic run — batch parameter scan with results table
"""

from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QComboBox, QLineEdit, QRadioButton, QButtonGroup,
    QGroupBox, QFormLayout, QFileDialog, QMessageBox, QStatusBar,
    QProgressBar, QTabWidget, QTextEdit, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QStackedWidget,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QColor

from .parameter_widget import ParameterWidget
from .statistic_parameter_widget import StatisticParameterWidget
from .plot_widget import Trajectory3DWidget, Plot2DWidget
from .stat_plot_widget import StatPlotWidget, build_stat_arrays
from core.config import load_config, save_config, get_default_params
from core.simulation import run_simulation, SimulationResult
from core.batch import run_stat_task, default_max_workers
import csv
import multiprocessing as mp
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, FIRST_COMPLETED


class SimulationWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(float)  # 0..100

    def __init__(self, params, integrator, dt, n_output):
        super().__init__()
        self.params = params
        self.integrator = integrator
        self.dt = dt
        self.n_output = n_output

    def run(self):
        try:
            def _cb(pct):
                self.progress.emit(pct)

            result = run_simulation(
                self.params,
                integrator=self.integrator,
                dt=self.dt,
                n_output=self.n_output,
                progress_cb=_cb
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class StatisticWorker(QThread):
    """
    Batch of simulations via ProcessPoolExecutor.

    Cross-platform notes
    --------------------
    * Uses multiprocessing context ``"spawn"`` on all platforms so behaviour
      is identical on Windows, macOS and Linux (and safe alongside Qt).
    * Worker function ``core.batch.run_stat_task`` is a top-level function
      (picklable); no Qt objects cross the process boundary.
    """
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(float, str)
    row_ready = pyqtSignal(dict)

    def __init__(self, param_sets, scanned_keys, integrator, dt, n_output,
                 max_workers: int = 0):
        super().__init__()
        self.param_sets = param_sets
        self.scanned_keys = list(scanned_keys)
        self.integrator = integrator
        self.dt = dt
        self.n_output = n_output
        self.max_workers = default_max_workers(max_workers)
        self._stop = False
        self._executor: ProcessPoolExecutor | None = None

    def stop(self):
        self._stop = True
        # Best-effort cancel of not-yet-started futures
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                # Python < 3.9 has no cancel_futures
                self._executor.shutdown(wait=False)

    def run(self):
        n = len(self.param_sets)
        if n == 0:
            self.finished.emit([])
            return

        tasks = []
        for i, params in enumerate(self.param_sets):
            tasks.append({
                "params": params,
                "scanned_keys": self.scanned_keys,
                "integrator": self.integrator,
                "dt": self.dt,
                "n_output": self.n_output,
                "index": i,
            })

        workers = min(self.max_workers, n)
        self.progress.emit(
            0.0,
            f"Starting {n} run(s) on {workers} worker(s)…"
        )

        # spawn is the only reliable context with Qt on all platforms
        ctx = mp.get_context("spawn")
        rows_by_index: dict[int, dict] = {}
        done_count = 0

        try:
            with ProcessPoolExecutor(
                max_workers=workers,
                mp_context=ctx,
            ) as executor:
                self._executor = executor
                future_map = {
                    executor.submit(run_stat_task, task): task["index"]
                    for task in tasks
                }

                pending = set(future_map.keys())
                while pending:
                    if self._stop:
                        for f in pending:
                            f.cancel()
                        break

                    finished, pending = wait(
                        pending, timeout=0.2, return_when=FIRST_COMPLETED
                    )
                    if not finished:
                        continue

                    for fut in finished:
                        idx = future_map[fut]
                        try:
                            row = fut.result()
                        except Exception as exc:  # noqa: BLE001
                            # reconstruct a failure row
                            params = self.param_sets[idx]
                            row = {k: params[k] for k in self.scanned_keys}
                            row.update({
                                "Imax": float("nan"),
                                "Imin": float("nan"),
                                "R": float("nan"),
                                "delta_e": float("nan"),
                                "delta_e_pred": float("nan"),
                                "success": False,
                                "message": str(exc),
                                "_index": idx,
                            })

                        rows_by_index[idx] = row
                        done_count += 1
                        self.row_ready.emit(row)
                        pct = 100.0 * done_count / n
                        label = ", ".join(
                            f"{k}={row.get(k, '?'):g}"
                            if isinstance(row.get(k), (int, float))
                            else f"{k}={row.get(k)}"
                            for k in self.scanned_keys
                        ) or f"#{idx}"
                        self.progress.emit(
                            pct,
                            f"[{done_count}/{n}] {label}"
                        )

            self._executor = None

            # stable order by original index
            ordered = [
                rows_by_index[i]
                for i in range(n)
                if i in rows_by_index
            ]
            self.progress.emit(100.0, "Done")
            self.finished.emit(ordered)

        except Exception as e:
            self._executor = None
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3-Body AB+C Simulator")
        self._result: SimulationResult | None = None
        self._worker: SimulationWorker | None = None
        self._stat_worker: StatisticWorker | None = None
        self.time_mode = 'years'  # or 'outer_revolutions'
        self.mode = "single"  # "single" | "statistic"
        self._stat_rows: list = []

        self._build_menu()
        self._build_ui()
        self._build_statusbar()
        defaults = get_default_params()
        self.param_widget.set_params(defaults)
        self.stat_param_widget.set_params(defaults)
        self.spin_tmax.setText(f"{float(defaults['t_max']):g}")
        self.spin_tmax_s.setText(f"{float(defaults['t_max']):g}")
        default_tmax = float(defaults['t_max'])
        self._last_tmax = {"single": default_tmax, "statistic": default_tmax}

        self.stat_param_widget.scan_changed.connect(self._refresh_stat_summary)
        self.spin_tmax.editingFinished.connect(self._sync_t_ac_with_tmax)
        self.spin_tmax_s.editingFinished.connect(self._sync_t_ac_with_tmax)
        self.spin_tmax_s.editingFinished.connect(self._refresh_stat_summary)
        self._refresh_stat_summary()

    def _sync_t_ac_with_tmax(self):
        """Keep the automatic t_AC default tied to the current T_max."""
        try:
            mode_key = "statistic" if self.mode == "statistic" else "single"
            previous_tmax = self._last_tmax[mode_key]
            current_tmax = float(
                self.spin_tmax_s.text()
                if self.mode == "statistic" else self.spin_tmax.text()
            )
        except (AttributeError, ValueError):
            return

        expected_auto_t_ac = -previous_tmax / 2.0
        field = (self.stat_param_widget._rows["t_AC"].fixed
                 if self.mode == "statistic"
                 else self.param_widget.field_t_AC)
        try:
            current_t_ac = float(field.text())
        except ValueError:
            current_t_ac = None
        if current_t_ac is not None and np.isclose(
                current_t_ac, expected_auto_t_ac):
            field.setText(f"{-current_tmax / 2.0:g}")
        self._last_tmax[mode_key] = current_tmax

    # ------------------------------------------------------------------ menu
    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        act_open = QAction("Open configuration…", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.load_config)
        file_menu.addAction(act_open)

        act_save = QAction("Save configuration…", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_config)
        file_menu.addAction(act_save)

        file_menu.addSeparator()
        act_import = QAction("Import statistic table (CSV)…", self)
        act_import.triggered.connect(self.import_stat_csv)
        file_menu.addAction(act_import)

        act_export = QAction("Export statistic table (CSV)…", self)
        act_export.triggered.connect(self.export_stat_csv)
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        mode_menu = menubar.addMenu("Mode")
        self.act_single = QAction("1. Single run", self)
        self.act_single.setCheckable(True)
        self.act_single.setChecked(True)
        self.act_single.triggered.connect(lambda: self._set_mode("single"))
        mode_menu.addAction(self.act_single)

        self.act_stat = QAction("2. Statistic run", self)
        self.act_stat.setCheckable(True)
        self.act_stat.triggered.connect(lambda: self._set_mode("statistic"))
        mode_menu.addAction(self.act_stat)

        help_menu = menubar.addMenu("Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)

        self.main_stack = QStackedWidget()

        # ========== PAGE 0: Single run (original layout) ==========
        single_page = QWidget()
        single_layout = QHBoxLayout(single_page)
        single_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ----- Left panel (original) -----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.param_widget = ParameterWidget()
        left_layout.addWidget(self.param_widget)

        g_int = QGroupBox("Integrator")
        fl = QFormLayout(g_int)

        self.combo_integrator = QComboBox()
        self.combo_integrator.addItems(["IAS15 (high accuracy)", "WHFast (fast)"])
        fl.addRow("Method", self.combo_integrator)

        self.spin_dt = QLineEdit("0.04")
        self.spin_dt.setMinimumWidth(100)
        self.spin_dt.setMaximumHeight(21)
        fl.addRow("dt (WHFast)", self.spin_dt)

        self.spin_noutput = QLineEdit("5000")
        self.spin_noutput.setMinimumWidth(100)
        self.spin_noutput.setMaximumHeight(21)
        fl.addRow("Output points", self.spin_noutput)
        self.spin_tmax = QLineEdit("30000")
        self.spin_tmax.setMinimumWidth(100)
        self.spin_tmax.setMaximumHeight(21)
        fl.addRow("T<sub>max</sub> (years)", self.spin_tmax)

        left_layout.addWidget(g_int)

        g_time = QGroupBox("Time axis")
        fl_time = QFormLayout(g_time)
        self.time_group = QButtonGroup()
        rb_years = QRadioButton("Years")
        rb_revolutions = QRadioButton("Outer body revolutions")
        rb_years.setChecked(True)
        self.time_group.addButton(rb_years, 0)
        self.time_group.addButton(rb_revolutions, 1)
        self.time_group.buttonClicked.connect(self._on_time_mode_changed)
        fl_time.addRow(rb_years)
        fl_time.addRow(rb_revolutions)
        left_layout.addWidget(g_time)

        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("▶  Run")
        self.btn_run.setMinimumHeight(36)
        self.btn_run.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.btn_run)

        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_simulation)
        btn_layout.addWidget(self.btn_stop)
        left_layout.addLayout(btn_layout)

        prog_box = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        prog_box.addWidget(self.progress)
        self.lbl_progress = QLabel("0%")
        self.lbl_progress.setMinimumWidth(40)
        prog_box.addWidget(self.lbl_progress)
        left_layout.addLayout(prog_box)

        left.setMaximumWidth(360)
        splitter.addWidget(left)

        # ----- Right panel (original tabs) -----
        right = QTabWidget()

        self.plot_overview = Plot2DWidget()
        right.addTab(self.plot_overview, "I_total and e_in")

        self.plot_xy = Plot2DWidget()
        right.addTab(self.plot_xy, "XY projection")

        self.plot_ecc = Plot2DWidget()
        right.addTab(self.plot_ecc, "Eccentricities")

        self.plot_sma = Plot2DWidget()
        right.addTab(self.plot_sma, "Semi-major axes")

        self.plot_inc = Plot2DWidget()
        right.addTab(self.plot_inc, "Inclinations")

        self.plot_phase = Plot2DWidget()
        right.addTab(self.plot_phase, "cos(i_mut) vs e_in")

        self.view3d = Trajectory3DWidget()
        right.addTab(self.view3d, "3D trajectories")

        self.plot_energy = Plot2DWidget()
        right.addTab(self.plot_energy, "Total Energy check")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        right.addTab(self.log_text, "Log")

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        single_layout.addWidget(splitter)

        self.main_stack.addWidget(single_page)  # index 0

        # ========== PAGE 1: Statistic run ==========
        stat_page = QWidget()
        stat_page.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        stat_layout = QHBoxLayout(stat_page)
        stat_layout.setContentsMargins(0, 0, 0, 0)

        stat_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: statistic parameters + integrator + run
        stat_left = QWidget()
        stat_left.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        stat_left_lay = QVBoxLayout(stat_left)
        stat_left_lay.setContentsMargins(0, 0, 0, 0)

        self.stat_param_widget = StatisticParameterWidget()
        stat_left_lay.addWidget(self.stat_param_widget, stretch=1)

        g_int_s = QGroupBox("Integrator")
        fl_s = QFormLayout(g_int_s)
        self.combo_integrator_s = QComboBox()
        self.combo_integrator_s.addItems(
            ["IAS15 (high accuracy)", "WHFast (fast)"]
        )
        fl_s.addRow("Method", self.combo_integrator_s)
        self.spin_dt_s = QLineEdit("0.04")
        self.spin_dt_s.setMinimumWidth(100)
        fl_s.addRow("dt (WHFast)", self.spin_dt_s)
        self.spin_noutput_s = QLineEdit("5000")
        self.spin_noutput_s.setMinimumWidth(100)
        fl_s.addRow("Output points", self.spin_noutput_s)
        self.spin_tmax_s = QLineEdit("30000")
        self.spin_tmax_s.setMinimumWidth(100)
        fl_s.addRow("T<sub>max</sub> (years)", self.spin_tmax_s)
        # 0 = auto (cpu_count - 1)
        self.spin_workers_s = QLineEdit("0")
        self.spin_workers_s.setMinimumWidth(100)
        self.spin_workers_s.setToolTip(
            "Parallel workers (ProcessPoolExecutor).\n"
            "0 = auto (number of CPU cores − 1).\n"
            "1 = sequential (no parallel processes)."
        )
        fl_s.addRow("Workers (0=auto)", self.spin_workers_s)
        stat_left_lay.addWidget(g_int_s)

        btn_s = QHBoxLayout()
        self.btn_run_s = QPushButton("▶  Run")
        self.btn_run_s.setMinimumHeight(36)
        self.btn_run_s.clicked.connect(self.start_simulation)
        btn_s.addWidget(self.btn_run_s)
        self.btn_stop_s = QPushButton("■  Stop")
        self.btn_stop_s.setEnabled(False)
        self.btn_stop_s.clicked.connect(self.stop_simulation)
        btn_s.addWidget(self.btn_stop_s)
        stat_left_lay.addLayout(btn_s)

        prog_s = QHBoxLayout()
        self.progress_s = QProgressBar()
        self.progress_s.setRange(0, 100)
        self.progress_s.setValue(0)
        self.progress_s.setTextVisible(True)
        self.progress_s.setFormat("%p%")
        prog_s.addWidget(self.progress_s)
        self.lbl_progress_s = QLabel("0%")
        self.lbl_progress_s.setMinimumWidth(40)
        prog_s.addWidget(self.lbl_progress_s)
        stat_left_lay.addLayout(prog_s)

        # Fixed band — must not grow when table columns appear
        stat_left.setFixedWidth(350)
        stat_splitter.addWidget(stat_left)

        # Right: table + result plots
        self.stat_tabs = QTabWidget()
        self.stat_tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # --- Summary tab ---
        self.stat_summary = QTextEdit()
        self.stat_summary.setReadOnly(True)
        self.stat_summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.stat_summary.setStyleSheet("QTextEdit { background: white; }")
        self._stat_summary_rows = None
        self.stat_tabs.addTab(self.stat_summary, "Summary")

        # --- Table tab ---
        table_page = QWidget()
        table_lay = QVBoxLayout(table_page)
        table_lay.setContentsMargins(4, 4, 4, 4)

        self.stat_info = QLabel(
            "Mark up to 2 parameters with ☑, set Start / End / Step, then Run."
        )
        self.stat_info.setWordWrap(True)
        self.stat_info.setMaximumHeight(40)
        self.stat_info.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        table_lay.addWidget(self.stat_info)

        self.stat_table = QTableWidget()
        self.stat_table.setAlternatingRowColors(True)
        self.stat_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.stat_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.stat_table.setSizeAdjustPolicy(
            QAbstractItemView.SizeAdjustPolicy.AdjustIgnored
        )
        self.stat_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.stat_table.horizontalHeader().setStretchLastSection(True)
        self.stat_table.horizontalHeader().setMinimumSectionSize(70)
        self.stat_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.stat_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.stat_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        table_lay.addWidget(self.stat_table)
        self.stat_tabs.addTab(table_page, "Table")

        # --- Plot tabs ---
        self.stat_plot_Imax = StatPlotWidget("Imax")
        self.stat_plot_Imin = StatPlotWidget("Imin")
        self.stat_plot_R = StatPlotWidget("Sundman R")
        self.stat_plot_de = StatPlotWidget("Δe  (sim vs pred)")
        self.stat_tabs.addTab(self.stat_plot_Imax, "Imax")
        self.stat_tabs.addTab(self.stat_plot_Imin, "Imin")
        self.stat_tabs.addTab(self.stat_plot_R, "R")
        self.stat_tabs.addTab(self.stat_plot_de, "Δe")

        self._stat_plot_map = [
            (self.stat_plot_Imax, "Imax"),
            (self.stat_plot_Imin, "Imin"),
            (self.stat_plot_R, "R"),
        ]
        # Δe is handled specially (sim + pred overlay)

        stat_splitter.addWidget(self.stat_tabs)
        stat_splitter.setStretchFactor(0, 0)
        stat_splitter.setStretchFactor(1, 1)
        stat_splitter.setChildrenCollapsible(False)
        stat_layout.addWidget(stat_splitter)

        self.main_stack.addWidget(stat_page)  # index 1

        self.main_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.main_stack)

    def _build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    # ------------------------------------------------------------------ mode
    def _set_mode(self, mode: str):
        if mode == self.mode:
            return
        if (self._worker and self._worker.isRunning()) or \
           (self._stat_worker and self._stat_worker.isRunning()):
            QMessageBox.information(self, "Busy", "Stop the current run first.")
            self.act_single.setChecked(self.mode == "single")
            self.act_stat.setChecked(self.mode == "statistic")
            return

        # Preserve window size — page switch / table fill must not resize it
        locked = self.size()

        self.mode = mode
        is_stat = mode == "statistic"

        self.act_single.setChecked(not is_stat)
        self.act_stat.setChecked(is_stat)

        # Make only the active page contribute to size hints
        for i in range(self.main_stack.count()):
            w = self.main_stack.widget(i)
            if i == (1 if is_stat else 0):
                w.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
            else:
                w.setSizePolicy(
                    QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
                )

        self.main_stack.setCurrentIndex(1 if is_stat else 0)
        self.resize(locked)

        self.status.showMessage(
            "Statistic run" if is_stat else "Ready"
        )

    # ------------------------------------------------------------------ time
    def _on_time_mode_changed(self):
        mode_idx = self.time_group.checkedId()
        self.time_mode = 'outer_revolutions' if mode_idx == 1 else 'years'
        if self._result is not None:
            self._apply_time_mode()

    def _apply_time_mode(self):
        """Apply time mode to all plots."""
        if self._result is None:
            return
        a_out = self._result.elements.get('a_out')
        if a_out is None or len(a_out) == 0:
            return
        a_out_val = float(a_out[0])
        masses_tuple = (
            tuple(self._result.masses)
            if self._result.masses is not None
            else (1.0, 1.0, 1.0)
        )
        for plot_widget in [
            self.plot_overview, self.plot_ecc, self.plot_sma,
            self.plot_inc, self.plot_energy
        ]:
            plot_widget.set_time_mode(self.time_mode, a_out_val, masses_tuple)
        stride = max(1, self._result.n_steps // 20000)
        self.plot_overview.plot_overview(
            self._result.t, self._result.elements,
            self._result.positions, self._result.masses, stride=stride
        )
        self.plot_ecc.plot_eccentricities(self._result.t, self._result.elements)
        self.plot_sma.plot_semimajor(self._result.t, self._result.elements)
        self.plot_inc.plot_inclinations(self._result.t, self._result.elements)
        self.plot_energy.plot_energy(self._result.t, self._result.energy)

    # ------------------------------------------------------------------ config
    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open configuration",
            str(Path(__file__).parent.parent / "configs"),
            "YAML (*.yaml *.yml);;All files (*)"
        )
        if path:
            try:
                params = load_config(path)
                self.param_widget.set_params(params)
                self.stat_param_widget.set_params(params)
                if "t_max" in params:
                    text = f"{float(params['t_max']):g}"
                    self.spin_tmax.setText(text)
                    self.spin_tmax_s.setText(text)
                    loaded_tmax = float(params["t_max"])
                    self._last_tmax["single"] = loaded_tmax
                    self._last_tmax["statistic"] = loaded_tmax
                self.status.showMessage(f"Loaded: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")

    def save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save configuration",
            str(Path(__file__).parent.parent / "configs" / "my_config.yaml"),
            "YAML (*.yaml *.yml)"
        )
        if path:
            try:
                if self.mode == "statistic":
                    params = self.stat_param_widget.get_params()
                    params["t_max"] = float(self.spin_tmax_s.text())
                else:
                    params = self.param_widget.get_params()
                    params["t_max"] = float(self.spin_tmax.text())
                save_config(params, path)
                self.status.showMessage(f"Saved: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    # ------------------------------------------------------------------ run
    def start_simulation(self):
        if self.mode == "statistic":
            self._start_statistic()
        else:
            self._start_single()

    def _start_single(self):
        if self._worker and self._worker.isRunning():
            return

        params = self.param_widget.get_params()
        params["t_max"] = float(self.spin_tmax.text())
        integrator = self.combo_integrator.currentText().split()[0]
        dt = float(self.spin_dt.text())
        n_output = int(float(self.spin_noutput.text()))

        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)
        self.lbl_progress.setText("0%")
        self.status.showMessage(f"Integrating ({integrator})…")
        self.log_text.append(
            f"\n=== Run: {integrator}, T_max={params['t_max']} years ==="
        )

        self._worker = SimulationWorker(params, integrator, dt, n_output)
        self._worker.finished.connect(self.on_simulation_finished)
        self._worker.error.connect(self.on_simulation_error)
        self._worker.progress.connect(self.on_progress)
        self._worker.start()

    def _start_statistic(self):
        if self._stat_worker and self._stat_worker.isRunning():
            return

        scanned = self.stat_param_widget.scanned_keys()
        if not scanned:
            QMessageBox.warning(
                self, "Nothing to scan",
                "No parameters are marked with ☑.\n\n"
                "Check the box next to a parameter, then set\n"
                "Start / End / Step (start and end must differ).\n"
                "At most two parameters may be scanned at once."
            )
            return
        if len(scanned) > 2:
            QMessageBox.warning(
                self, "Too many parameters",
                "At most two parameters can be scanned simultaneously.\n"
                f"Currently selected: {', '.join(scanned)}"
            )
            return

        scan_spec = self.stat_param_widget.get_scan_spec()
        details = []
        for key, vals in scan_spec:
            details.append(f"  {key}: {vals.tolist()}  ({len(vals)} values)")
        param_sets = self.stat_param_widget.iter_param_sets()
        t_max = float(self.spin_tmax_s.text())
        for params in param_sets:
            params["t_max"] = t_max
        n = len(param_sets)

        if n <= 1:
            QMessageBox.warning(
                self, "Only one combination",
                "Only 1 combination generated. Check that start ≠ end.\n\n"
                + "\n".join(details)
            )
            return

        if n > 200:
            reply = QMessageBox.question(
                self, "Large batch",
                f"You are about to run {n} simulations:\n"
                + "\n".join(details) + "\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        integrator = self.combo_integrator_s.currentText().split()[0]
        dt = float(self.spin_dt_s.text())
        n_output = int(float(self.spin_noutput_s.text()))
        try:
            max_workers = int(float(self.spin_workers_s.text()))
        except ValueError:
            max_workers = 0
        max_workers = default_max_workers(max_workers)

        result_cols = [
            "Imax", "Imin", "R", "delta_e", "delta_e_pred"
        ]
        headers = list(scanned) + result_cols
        self.stat_table.clear()
        self.stat_table.setColumnCount(len(headers))
        self.stat_table.setHorizontalHeaderLabels(headers)
        # Pre-allocate rows in original cycle order; fill by _index as
        # parallel workers complete (so the table stays sorted).
        self.stat_table.setRowCount(n)
        self._stat_rows = [None] * n
        self._stat_headers = headers
        self._stat_scanned = list(scanned)
        self._stat_n = n

        for plot, _ in self._stat_plot_map:
            plot.clear()

        self.btn_run_s.setEnabled(False)
        self.btn_stop_s.setEnabled(True)
        self.progress_s.setValue(0)
        self.lbl_progress_s.setText("0%")
        self.stat_info.setText(
            f"Running {n} simulation(s) on {max_workers} worker(s)…"
        )
        self.status.showMessage(f"Statistic run: 0/{n}  workers={max_workers}")

        self._stat_worker = StatisticWorker(
            param_sets, scanned, integrator, dt, n_output,
            max_workers=max_workers,
        )
        self._stat_worker.finished.connect(self.on_statistic_finished)
        self._stat_worker.error.connect(self.on_simulation_error)
        self._stat_worker.progress.connect(self.on_stat_progress)
        self._stat_worker.row_ready.connect(self.on_stat_row)
        self._stat_worker.start()

    def on_progress(self, pct: float):
        value = int(min(100, max(0, pct)))
        self.progress.setValue(value)
        self.lbl_progress.setText(f"{value}%")
        self.status.showMessage(f"Integrating… {value}%")

    def on_stat_progress(self, pct: float, msg: str):
        value = int(min(100, max(0, pct)))
        self.progress_s.setValue(value)
        self.lbl_progress_s.setText(f"{value}%")
        self.status.showMessage(msg)

    def on_stat_row(self, row: dict):
        locked = self.size()
        # Place row at its original cycle index (not append order)
        idx = int(row.get("_index", -1))
        if idx < 0 or idx >= len(self._stat_rows):
            idx = len([r for r in self._stat_rows if r is not None])
            if idx >= self.stat_table.rowCount():
                self.stat_table.setRowCount(idx + 1)
                self._stat_rows.append(None)

        self._stat_rows[idx] = row

        result_keys = {
            "Imax", "Imin", "R", "delta_e", "delta_e_pred"
        }
        for c, key in enumerate(self._stat_headers):
            val = row.get(key, "")
            if isinstance(val, float):
                if key in result_keys:
                    text = f"{val:.8f}"
                else:
                    text = f"{val:.1f}"
            else:
                text = str(val)
            item = QTableWidgetItem(text)
            if not row.get("success", True):
                item.setForeground(QColor("#c62828"))
            self.stat_table.setItem(idx, c, item)

        self.resize(locked)

    def stop_simulation(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
            self.btn_run.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.progress.setValue(0)
            self.lbl_progress.setText("0%")
        if self._stat_worker and self._stat_worker.isRunning():
            self._stat_worker.stop()
            self._stat_worker.wait(3000)
            self.btn_run_s.setEnabled(True)
            self.btn_stop_s.setEnabled(False)
            self.progress_s.setValue(0)
            self.lbl_progress_s.setText("0%")
        self.status.showMessage("Stopped by user")

    def on_simulation_finished(self, result: SimulationResult):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setValue(100)
        self.lbl_progress.setText("100%")
        self._result = result

        if not result.success:
            self.status.showMessage("Error")
            self.log_text.append(f"ERROR: {result.message}")
            QMessageBox.warning(self, "Integration error", result.message)
            return

        self.status.showMessage(
            f"Done in {result.wall_time:.1f} s | steps: {result.n_steps} | "
            f"{result.integrator}"
        )
        el = result.elements
        self.log_text.append(
            f"Success. Time: {result.wall_time:.1f} s, steps: {result.n_steps}\n"
            f"E₀ = {result.energy[0]:.10e},  E_final = {result.energy[-1]:.10e}\n"
            f"e_in:  {el['e_in'][0]:.6f} → {el['e_in'][-1]:.6f}\n"
            f"e_out: {el['e_out'][0]:.6f} → {el['e_out'][-1]:.6f}\n"
            f"I_mut: {el['i_mut_deg'][0]:.2f}° → {el['i_mut_deg'][-1]:.2f}°\n"
            f"cos(i_mut): {el['cos_i_mut'][0]:.6f} → {el['cos_i_mut'][-1]:.6f}"
        )

        stride = max(1, result.n_steps // 20000)
        a_out = result.elements.get('a_out')
        if a_out is not None and len(a_out) > 0:
            a_out_val = float(a_out[0])
            masses_tuple = (
                tuple(result.masses)
                if result.masses is not None
                else (1.0, 1.0, 1.0)
            )
            for plot_widget in [
                self.plot_overview, self.plot_ecc, self.plot_sma,
                self.plot_inc, self.plot_energy
            ]:
                plot_widget.set_time_mode(
                    self.time_mode, a_out_val, masses_tuple
                )

        self.plot_overview.plot_overview(
            result.t, result.elements, result.positions, result.masses,
            stride=stride
        )
        self.plot_xy.plot_xy(result.positions, stride=stride)
        self.plot_ecc.plot_eccentricities(result.t, result.elements)
        self.plot_sma.plot_semimajor(result.t, result.elements)
        self.plot_inc.plot_inclinations(result.t, result.elements)
        self.view3d.plot_trajectories(result.positions, stride=stride)
        self.plot_phase.plot_cos_i_vs_e(result.elements, stride=stride)
        self.plot_energy.plot_energy(result.t, result.energy)

    def on_statistic_finished(self, rows: list):
        self.btn_run_s.setEnabled(True)
        self.btn_stop_s.setEnabled(False)
        self.progress_s.setValue(100)
        self.lbl_progress_s.setText("100%")
        n_ok = sum(1 for r in rows if r.get("success"))
        self.status.showMessage(f"Statistic done: {n_ok}/{len(rows)} successful")
        self.stat_info.setText(
            f"Finished: {n_ok}/{len(rows)} successful. "
            "File → Export statistic table (CSV) to save."
        )
        # Prefer the ordered list kept in the UI (filled by _index)
        ordered = [
            r if r is not None else rows[i] if i < len(rows) else None
            for i, r in enumerate(self._stat_rows)
        ]
        if not any(ordered):
            ordered = rows
        self._update_stat_plots(ordered)
        self._stat_summary_rows = ordered
        self._refresh_stat_summary()

    def _update_stat_plots(self, rows: list):
        scanned = getattr(self, "_stat_scanned", []) or []
        if not scanned:
            return
        for plot, quantity in self._stat_plot_map:
            kind, data = build_stat_arrays(rows, scanned, quantity)
            if kind is None or data is None:
                plot.clear()
                continue
            if kind == "1d":
                x, y, xlabel, ylabel = data
                plot.plot_1d(x, y, xlabel, ylabel)
            elif kind == "2d":
                x, y, Z, xlabel, ylabel, zlabel = data
                plot.plot_2d_surface(x, y, Z, xlabel, ylabel, zlabel)

        # Combined Δe: simulated vs predicted
        kind_s, data_s = build_stat_arrays(rows, scanned, "delta_e")
        kind_p, data_p = build_stat_arrays(rows, scanned, "delta_e_pred")
        if kind_s == "1d" and data_s is not None and data_p is not None:
            x, y_s, xlabel, _ = data_s
            y_p = data_p[1]
            self.stat_plot_de.plot_1d_overlay(
                x, y_s, y_p, xlabel,
                "Δe (sim)", "Δe (pred)",
            )
        elif kind_s == "2d" and data_s is not None and data_p is not None:
            x, y, Z_s, xlabel, ylabel, _ = data_s
            Z_p = data_p[2]
            self.stat_plot_de.plot_2d_overlay(
                x, y, Z_s, Z_p, xlabel, ylabel,
                "Δe (sim)", "Δe (pred)",
            )
        else:
            self.stat_plot_de.clear()

    # ------------------------------------------------------------------ summary tab
    def _refresh_stat_summary(self, *args):
        rows = getattr(self, "_stat_summary_rows", None)
        html = self._build_stat_summary_html(rows)
        self.stat_summary.setHtml(html)

    @staticmethod
    def _fmt_num(value) -> str:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "—"
        if not np.isfinite(v):
            return "—"
        return f"{v:.6g}"

    def _build_stat_summary_html(self, rows: list | None) -> str:
        fmt = self._fmt_num

        try:
            t_max = float(self.spin_tmax_s.text())
        except ValueError:
            t_max = float("nan")

        parts = [
            "<div style=\"font-family: Georgia, 'Cambria Math', 'DejaVu Serif', "
            "serif; font-size: 11pt; line-height: 1.4;\">",
            "<h2 style='margin-bottom:4px;'>Statistic Run — Summary</h2>",
            "<h3 style='margin-bottom:2px;'>Configuration</h3>",
            "<p style='margin:2px 0 8px 0;'><b>Integration:</b>&nbsp; "
            f"T<sub>max</sub> = {fmt(t_max)} years</p>",
        ]

        groups = self.stat_param_widget.describe_params()
        for group_title, rows_info in groups:
            parts.append(f"<p style='margin:6px 0 2px 0;'><b>{group_title}</b></p>")
            parts.append(
                "<table cellspacing='0' cellpadding='2' "
                "style='margin-left:14px;'>"
            )
            for info in rows_info:
                label = info["label"]
                if info.get("scanned"):
                    s, e, st = info["start"], info["end"], info["step"]
                    value_html = (
                        f"{fmt(s)} &nbsp;&rarr;&nbsp; {fmt(e)} "
                        f"&nbsp;&nbsp;(step&nbsp;&Delta;&nbsp;=&nbsp;{fmt(st)})"
                    )
                else:
                    value_html = fmt(info["value"])
                parts.append(
                    f"<tr><td style='padding-right:18px; color:#333;'>{label}"
                    f"</td><td>{value_html}</td></tr>"
                )
            parts.append("</table>")

        parts.append("<h3 style='margin:14px 0 2px 0;'>Results</h3>")

        def column(key: str) -> np.ndarray:
            vals = []
            for r in rows or []:
                if not r or not r.get("success", True):
                    continue
                try:
                    v = float(r.get(key))
                except (TypeError, ValueError):
                    continue
                if np.isfinite(v):
                    vals.append(v)
            return np.array(vals, dtype=float)

        if not rows:
            parts.append(
                "<p><i>Run a statistic simulation to see results here.</i></p>"
            )
        else:
            R = column("R")
            de = column("delta_e")
            dep = column("delta_e_pred")
            n_ok = sum(1 for r in rows if r and r.get("success", True))

            if R.size == 0 and de.size == 0 and dep.size == 0:
                parts.append("<p><i>No successful runs to summarise.</i></p>")
            else:
                def stat_row(label: str, arr: np.ndarray, cumulative: bool) -> str:
                    if arr.size == 0:
                        vmin = vmax = vsum = vavg = "—"
                    else:
                        vmin, vmax = fmt(arr.min()), fmt(arr.max())
                        if cumulative:
                            vsum, vavg = fmt(arr.sum()), fmt(arr.mean())
                        else:
                            vsum = vavg = "—"
                    return (
                        f"<tr><td style='padding-right:18px;'>{label}</td>"
                        f"<td style='padding-right:14px;'>{vmin}</td>"
                        f"<td style='padding-right:14px;'>{vmax}</td>"
                        f"<td style='padding-right:14px;'>{vsum}</td>"
                        f"<td>{vavg}</td></tr>"
                    )

                parts.append(
                    "<table cellspacing='0' cellpadding='5' border='1' "
                    "style='border-collapse:collapse; margin-left:14px;'>"
                )
                parts.append(
                    "<tr style='background:#eee;'>"
                    "<th>Quantity</th><th>Min</th><th>Max</th>"
                    "<th>&Sigma; (cumulative)</th><th>x&#772; (average)</th></tr>"
                )
                parts.append(stat_row("R (Sundman ratio)", R, cumulative=False))
                parts.append(
                    stat_row("&Delta;e<sub>in</sub> (simulated)", de, cumulative=True)
                )
                parts.append(
                    stat_row(
                        "&Delta;e<sub>in</sub> (predicted)", dep, cumulative=True
                    )
                )
                parts.append("</table>")

                total = len(rows)
                note = f"Based on {n_ok} successful run(s)"
                if n_ok != total:
                    note += f" out of {total} total"
                note += "."
                parts.append(
                    f"<p style='margin-top:8px; color:#555;'><i>{note}</i></p>"
                )

        parts.append("</div>")
        return "".join(parts)

    def on_simulation_error(self, msg: str):
        if self.mode == "single":
            self.btn_run.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.progress.setValue(0)
            self.lbl_progress.setText("0%")
            self.log_text.append(f"EXCEPTION: {msg}")
        else:
            self.btn_run_s.setEnabled(True)
            self.btn_stop_s.setEnabled(False)
            self.progress_s.setValue(0)
            self.lbl_progress_s.setText("0%")
        self.status.showMessage("Error")
        QMessageBox.critical(self, "Error", msg)

    # ------------------------------------------------------------------ import / export
    _RESULT_COLS = (
        "Imax", "Imin", "R", "delta_e", "delta_e_pred"
    )

    def import_stat_csv(self):
        """Load a previously exported statistic CSV into the table and plots."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import statistic CSV",
            str(Path(__file__).parent.parent / "results"),
            "CSV (*.csv);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("CSV has no header row")
                fieldnames = list(reader.fieldnames)
                raw_rows = list(reader)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV:\n{e}")
            return

        if not raw_rows:
            QMessageBox.information(self, "Empty", "CSV contains no data rows.")
            return

        result_set = set(self._RESULT_COLS)
        # Scanned parameters = columns that are not known result columns
        # and not metadata
        skip = result_set | {"success", "message", "_index"}
        scanned = [c for c in fieldnames if c not in skip]
        if len(scanned) > 2:
            # keep at most two leftmost parameter columns for plotting
            scanned = scanned[:2]

        headers = list(scanned) + [
            c for c in self._RESULT_COLS if c in fieldnames
        ]
        # include any extra result-like columns present in file
        for c in fieldnames:
            if c not in headers and c not in skip:
                headers.append(c)

        def _to_float(val, default=float("nan")):
            if val is None or val == "":
                return default
            try:
                return float(val)
            except (TypeError, ValueError):
                return default

        rows = []
        for i, raw in enumerate(raw_rows):
            row = {}
            for c in headers:
                row[c] = _to_float(raw.get(c, ""))
            for c in scanned:
                row[c] = _to_float(raw.get(c, ""), default=0.0)
            row["success"] = True
            row["message"] = "imported"
            row["_index"] = i
            rows.append(row)

        # Switch to Statistic mode so the table is visible
        if self.mode != "statistic":
            self._set_mode("statistic")

        self.stat_table.clear()
        self.stat_table.setColumnCount(len(headers))
        self.stat_table.setHorizontalHeaderLabels(headers)
        self.stat_table.setRowCount(len(rows))
        self._stat_headers = headers
        self._stat_scanned = scanned
        self._stat_rows = rows
        self._stat_n = len(rows)

        result_keys = set(self._RESULT_COLS)
        for r_idx, row in enumerate(rows):
            for c, key in enumerate(headers):
                val = row.get(key, "")
                if isinstance(val, float):
                    if key in result_keys:
                        text = f"{val:.8f}"
                    else:
                        text = f"{val:.1f}"
                else:
                    text = str(val)
                self.stat_table.setItem(r_idx, c, QTableWidgetItem(text))

        self._update_stat_plots(rows)
        self._stat_summary_rows = rows
        self._refresh_stat_summary()
        self.stat_info.setText(
            f"Imported {len(rows)} row(s) from {Path(path).name}. "
            f"Scanned: {', '.join(scanned) if scanned else '(none)'}."
        )
        self.status.showMessage(f"Imported: {path}")
        self.stat_tabs.setCurrentIndex(1)  # Table tab (0 = Summary)

    def export_stat_csv(self):
        rows = [r for r in self._stat_rows if r is not None]
        if not rows:
            QMessageBox.information(
                self, "Empty", "No statistic results to export."
            )
            return

        filename = self._statistic_filename()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV",
            str(Path(__file__).parent.parent / "results" / filename),
            "CSV (*.csv)"
        )
        if not path:
            return
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=self._stat_headers, extrasaction="ignore"
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {k: row.get(k, "") for k in self._stat_headers}
                    )
            self.status.showMessage(f"Exported: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def _statistic_filename(self) -> str:
        """Build a descriptive filename from the Statistic-mode inputs."""
        parameter_names = (
            ("mass_A", "M1"),
            ("mass_B", "M2"),
            ("mass_C", "M3"),
            ("a_AB", "aAB"),
            ("e_AB", "eAB"),
            ("i_AB", "iAB"),
            ("Omega_AB", "OmAB"),
            ("omega_AB", "omAB"),
            ("M_AB", "MAB"),
            ("Q", "Q"),
            ("e_AC", "eAC"),
            ("i_AC", "iAC"),
            ("Omega_AC", "OmAC"),
            ("omega_AC", "omAC"),
            ("M_AC", "MAC"),
        )

        def _number(value: float) -> str:
            return f"{float(value):g}"

        base = self.stat_param_widget.get_base_params()
        ranges = {}
        for key, values in self.stat_param_widget.get_scan_spec():
            step = values[1] - values[0] if len(values) > 1 else 0.0
            ranges[key] = (values[0], values[-1], step)

        parts = []
        for key, name in parameter_names:
            if key in ranges:
                start, end, step = ranges[key]
                value = "-".join(
                    (_number(start), _number(end), _number(step))
                )
            else:
                value = _number(base[key])
            parts.append(f"{name}={value}")
        return "_".join(parts) + ".csv"

    def show_about(self):
        QMessageBox.about(
            self, "About",
            "<b>3-Body AB+C Simulator</b><br><br>"
            "Hierarchical three-body system (inner binary + outer body).<br>"
            "Modes: <b>Single run</b> and <b>Statistic run</b> "
            "(switch via Mode menu).<br>"
            "Main plot: <b>cos(i_mut) vs e_in</b> (Kozai–Lidov).<br><br>"
            "Integrators: REBOUND (IAS15, WHFast)."
        )
