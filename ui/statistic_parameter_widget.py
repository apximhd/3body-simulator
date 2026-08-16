"""
Parameter widget for Statistic (batch) mode.
Each parameter has a checkbox; when checked, three fields appear:
Start / End / Step. Unchecked parameters keep a single fixed value.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QGroupBox, QVBoxLayout,
    QHBoxLayout, QCheckBox, QLabel, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtCore import QLocale, Qt, pyqtSignal
from typing import Dict, Any, List, Tuple
import itertools
import numpy as np


def _make_validator() -> QDoubleValidator:
    v = QDoubleValidator()
    v.setLocale(QLocale(QLocale.Language.C))
    v.setNotation(QDoubleValidator.Notation.ScientificNotation)
    return v


# (key, display label, default value)
PARAM_SPEC: List[Tuple[str, str, float]] = [
    ("mass_A",   "Mass A",        1.5),
    ("mass_B",   "Mass B",        0.5),
    ("mass_C",   "Mass C",        0.5),
    ("a_AB",     "a_AB (AU)",     1.0),
    ("e_AB",     "e_AB",          0.6),
    ("i_AB",     "i_AB (°)",      0.0),
    ("Omega_AB", "Ω_AB (°)",      0.0),
    ("omega_AB", "ω_AB (°)",      60.0),
    ("M_AB",     "M_AB (°)",      0.0),
    ("Q",        "Q (q / a_AB)",  5.0),
    ("e_AC",     "e_AC",          0.5),
    ("i_AC",     "i_AC (°)",      140.0),
    ("Omega_AC", "Ω_AC (°)",      0.0),
    ("omega_AC", "ω_AC (°)",      155.0),
    ("M_AC",     "M_AC (°)",      0.0),
]

# Parameters that can be scanned (t_max is excluded — always fixed)
SCANNABLE = {
    "mass_A", "mass_B", "mass_C",
    "a_AB", "e_AB", "i_AB", "Omega_AB", "omega_AB", "M_AB",
    "Q", "e_AC", "i_AC", "Omega_AC", "omega_AC", "M_AC",
}

GROUPS = [
    ("Masses (M☉)", ["mass_A", "mass_B", "mass_C"]),
    ("Inner orbit AB", ["a_AB", "e_AB", "i_AB", "Omega_AB", "omega_AB", "M_AB"]),
    ("Outer orbit C", ["Q", "e_AC", "i_AC", "Omega_AC", "omega_AC", "M_AC"]),
]


def _values_from_range(start: float, end: float, step: float) -> np.ndarray:
    """Inclusive range generator robust to float noise."""
    if step == 0:
        return np.array([start])
    if start == end:
        return np.array([start])
    n = int(round(abs(end - start) / abs(step))) + 1
    if n < 1:
        n = 1
    vals = start + np.arange(n) * step
    if step > 0:
        vals = vals[vals <= end + abs(step) * 1e-9]
        if vals.size and vals[-1] < end - abs(step) * 1e-9:
            vals = np.append(vals, end)
    else:
        vals = vals[vals >= end - abs(step) * 1e-9]
        if vals.size and vals[-1] > end + abs(step) * 1e-9:
            vals = np.append(vals, end)
    if vals.size == 0:
        vals = np.array([start])
    return vals


class _ParamRow(QWidget):
    """One parameter row: checkbox + fixed value OR Start/End/Step."""

    changed = pyqtSignal()

    def __init__(self, key: str, label: str, default: float,
                 scannable: bool = True, parent=None):
        super().__init__(parent)
        self.key = key
        self._default = default
        self._scannable = scannable

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(3)

        if scannable:
            self.cb = QCheckBox()
            self.cb.setToolTip("Scan this parameter (Start / End / Step)")
            self.cb.toggled.connect(self._on_toggle)
            layout.addWidget(self.cb)
        else:
            self.cb = None
            # spacer matching checkbox width so columns align
            spacer = QLabel("")
            spacer.setFixedWidth(18)
            layout.addWidget(spacer)

        self.lbl = QLabel(label)
        self.lbl.setMinimumWidth(85)
        self.lbl.setMaximumWidth(100)
        layout.addWidget(self.lbl)

        self.fixed = QLineEdit(f"{default:g}")
        self.fixed.setValidator(_make_validator())
        self.fixed.setMaximumHeight(22)
        self.fixed.setMinimumWidth(227)
        # self.fixed.setMaximumWidth(90)
        layout.addWidget(self.fixed)

        # Range fields — empty by default so placeholders are visible
        self.start = QLineEdit()
        self.start.setValidator(_make_validator())
        self.start.setMaximumHeight(22)
        self.start.setMinimumWidth(54)
        self.start.setMaximumWidth(74)
        self.start.setPlaceholderText("Start")
        self.start.setVisible(False)
        self.start.setToolTip("Start value")
        layout.addWidget(self.start)

        self.end = QLineEdit()
        self.end.setValidator(_make_validator())
        self.end.setMaximumHeight(22)
        self.end.setMinimumWidth(54)
        self.end.setMaximumWidth(74)
        self.end.setPlaceholderText("End")
        self.end.setVisible(False)
        self.end.setToolTip("End value")
        layout.addWidget(self.end)

        self.step = QLineEdit()
        self.step.setValidator(_make_validator())
        self.step.setMaximumHeight(22)
        self.step.setMinimumWidth(54)
        self.step.setMaximumWidth(74)
        self.step.setPlaceholderText("Step")
        self.step.setVisible(False)
        self.step.setToolTip("Step")
        layout.addWidget(self.step)

        layout.addStretch(1)

        for w in (self.fixed, self.start, self.end, self.step):
            w.editingFinished.connect(self.changed.emit)

    def _on_toggle(self, checked: bool):
        # Parent may reject a third checkbox — re-check actual state
        self.changed.emit()  # parent enforces max-2 first
        checked = self.cb.isChecked() if self.cb is not None else False
        self.fixed.setVisible(not checked)
        self.start.setVisible(checked)
        self.end.setVisible(checked)
        self.step.setVisible(checked)
        if checked:
            # Leave fields empty so placeholders Start / End / Step are shown
            self.start.clear()
            self.end.clear()
            self.step.clear()

    def is_scanned(self) -> bool:
        return self.cb is not None and self.cb.isChecked()

    def fixed_value(self) -> float:
        try:
            return float(self.fixed.text())
        except ValueError:
            return self._default

    def range_values(self) -> Tuple[float, float, float]:
        try:
            s = float(self.start.text())
            e = float(self.end.text())
            st = float(self.step.text())
            if st == 0:
                st = 1.0
            return s, e, st
        except ValueError:
            # incomplete range → treat as single fixed value
            fv = self.fixed_value()
            return fv, fv, 1.0

    def set_fixed(self, value: float):
        text = f"{float(value):g}"
        self.fixed.setText(text)


class StatisticParameterWidget(QWidget):
    scan_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: Dict[str, _ParamRow] = {}
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._build_ui()
        for row in self._rows.values():
            row.changed.connect(self._enforce_max_two)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        inner = QWidget()
        main = QVBoxLayout(inner)
        main.setContentsMargins(2, 2, 2, 2)
        main.setSpacing(3)

        key_to_spec = {k: (lbl, d) for k, lbl, d in PARAM_SPEC}

        for group_title, keys in GROUPS:
            g = QGroupBox(group_title)
            fl = QVBoxLayout(g)
            fl.setContentsMargins(4, 4, 4, 4)
            fl.setSpacing(1)
            for key in keys:
                label, default = key_to_spec[key]
                row = _ParamRow(
                    key, label, default,
                    scannable=(key in SCANNABLE)
                )
                self._rows[key] = row
                fl.addWidget(row)
            main.addWidget(g)

        main.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _enforce_max_two(self, *args):
        """Allow at most two scanned parameters at once.

        If a third checkbox is turned on, it is switched back off.
        """
        checked = [(k, r) for k, r in self._rows.items() if r.is_scanned()]
        if len(checked) <= 2:
            return

        # Prefer unchecking the row whose fields are still empty (just toggled)
        def _is_fresh(row):
            return (not row.start.text().strip()
                    and not row.end.text().strip()
                    and not row.step.text().strip())
        fresh = [(k, r) for k, r in checked if _is_fresh(r)]
        victim = fresh[-1] if fresh else checked[-1]
        k, row = victim
        row.cb.blockSignals(True)
        row.cb.setChecked(False)
        row.cb.blockSignals(False)
        row.fixed.setVisible(True)
        row.start.setVisible(False)
        row.end.setVisible(False)
        row.step.setVisible(False)

    def get_base_params(self) -> Dict[str, float]:

        result = {}
        for key, row in self._rows.items():
            if row.is_scanned():
                s, e, st = row.range_values()
                # if range incomplete (start==end from fallback), use fixed
                result[key] = s
            else:
                result[key] = row.fixed_value()
        return result

    def get_scan_spec(self) -> List[Tuple[str, np.ndarray]]:
        specs = []
        for key, row in self._rows.items():
            if not row.is_scanned():
                continue
            s, e, st = row.range_values()
            # skip incomplete ranges (empty Start/End/Step → s==e from fallback)
            if s == e and not row.start.text().strip():
                continue
            vals = _values_from_range(s, e, st)
            specs.append((key, vals))
        return specs

    def iter_param_sets(self) -> List[Dict[str, float]]:
        base = self.get_base_params()
        scan = self.get_scan_spec()
        if not scan:
            return [base]

        keys = [k for k, _ in scan]
        value_lists = [v.tolist() for _, v in scan]
        result = []
        for combo in itertools.product(*value_lists):
            p = base.copy()
            for k, v in zip(keys, combo):
                p[k] = float(v)
            result.append(p)
        return result

    def scanned_keys(self) -> List[str]:
        # only keys that actually have a valid scan range
        return [k for k, _ in self.get_scan_spec()]

    def set_params(self, params: Dict[str, Any]):
        for key, value in params.items():
            if key in self._rows:
                self._rows[key].set_fixed(float(value))

    def get_params(self) -> Dict[str, Any]:
        return self.get_base_params()
