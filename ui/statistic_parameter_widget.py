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
    ("mass_A",   "M<sub>1</sub>",        1.5),
    ("mass_B",   "M<sub>2</sub>",        0.5),
    ("mass_C",   "M<sub>3</sub>",        0.5),
    ("a_AB",     "a<sub>in</sub> (AU)",     1.0),
    ("e_AB",     "e<sub>in</sub>",          0.6),
    ("i_AB",     "i<sub>in</sub> (°)",      0.0),
    ("Omega_AB", "Ω<sub>in</sub> (°)",      0.0),
    ("omega_AB", "ω<sub>in</sub> (°)",      60.0),
    ("M_AB",     "M<sub>in</sub> (°)",      0.0),
    ("Q",        "Q (q / a<sub>in</sub>)",  5.0),
    ("e_AC",     "e<sub>out</sub>",         0.5),
    ("i_AC",     "i<sub>out</sub> (°)",     140.0),
    ("Omega_AC", "Ω<sub>out</sub> (°)",     0.0),
    ("omega_AC", "ω<sub>out</sub> (°)",     155.0),
    ("M_AC",     "M<sub>out</sub> (°)",     0.0),
    ("t_AC",     "t<sub>out</sub> (y)",     0.0),
]

# Parameters that can be scanned (t_max is excluded — always fixed)
SCANNABLE = {
    "mass_A", "mass_B", "mass_C",
    "a_AB", "e_AB", "i_AB", "Omega_AB", "omega_AB", "M_AB",
    "Q", "e_AC", "i_AC", "Omega_AC", "omega_AC", "M_AC", "t_AC",
}

# M_AC (°) is used when e_AC < 1 (elliptic outer orbit); t_AC (y) is used
# when e_AC >= 1 (parabolic / hyperbolic outer orbit — time until the third
# body passes periastron). Only one of the two rows is shown at a time.
GROUPS = [
    ("Masses (M☉)", ["mass_A", "mass_B", "mass_C"]),
    ("Inner orbit AB", ["a_AB", "e_AB", "i_AB", "Omega_AB", "omega_AB", "M_AB"]),
    ("Outer orbit C", ["Q", "e_AC", "i_AC", "Omega_AC", "omega_AC", "M_AC", "t_AC"]),
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
            row.changed.connect(self.scan_changed.emit)
        self._rows["e_AC"].changed.connect(self._update_ac_anomaly_row)
        self._update_ac_anomaly_row()

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

    def _e_ac_has_time_mode_value(self) -> bool:
        """True if any e_AC value currently configured (fixed value, or any
        value within the scanned Start/End/Step range) is >= 1."""
        row = self._rows["e_AC"]
        if row.is_scanned():
            s, e, st = row.range_values()
            try:
                vals = _values_from_range(s, e, st)
            except Exception:
                vals = np.array([s, e])
            return bool(np.any(vals >= 1.0))
        return row.fixed_value() >= 1.0

    def _update_ac_anomaly_row(self):
        """Show t_AC (y) instead of M_AC (°) when at least one configured
        e_AC value is >= 1 (parabolic / hyperbolic outer orbit)."""
        if "M_AC" not in self._rows or "t_AC" not in self._rows:
            return
        time_mode = self._e_ac_has_time_mode_value()
        self._rows["M_AC"].setVisible(not time_mode)
        self._rows["t_AC"].setVisible(time_mode)

    def describe_params(self) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """
        Describe the current configuration for display (e.g. in a summary
        tab), grouped the same way as the UI.

        Returns a list of (group_title, rows) where each row is a dict:
          {"key", "label", "scanned": bool,
           "value": float}                         if not scanned
           or
          {"key", "label", "scanned": True,
           "start": float, "end": float, "step": float}   if scanned

        Whichever of M_AC / t_AC is not relevant for the current e_AC
        configuration is omitted (see _e_ac_has_time_mode_value).
        """
        key_to_label = {k: lbl for k, lbl, _ in PARAM_SPEC}
        time_mode = self._e_ac_has_time_mode_value()

        result: List[Tuple[str, List[Dict[str, Any]]]] = []
        for group_title, keys in GROUPS:
            rows_info = []
            for key in keys:
                if key == "M_AC" and time_mode:
                    continue
                if key == "t_AC" and not time_mode:
                    continue
                row = self._rows[key]
                info: Dict[str, Any] = {"key": key, "label": key_to_label[key]}
                if row.is_scanned():
                    s, e, st = row.range_values()
                    info["scanned"] = True
                    info["start"] = s
                    info["end"] = e
                    info["step"] = st
                else:
                    info["scanned"] = False
                    info["value"] = row.fixed_value()
                rows_info.append(info)
            result.append((group_title, rows_info))
        return result

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
        self._update_ac_anomaly_row()
        self.scan_changed.emit()

    def get_params(self) -> Dict[str, Any]:
        return self.get_base_params()
