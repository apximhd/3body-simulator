"""
System parameter input widget.
Mirrors the parameter structure from the Mathematica notebook.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QGroupBox, QVBoxLayout, QScrollArea,
    QLabel, QHBoxLayout
)
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtCore import QLocale
from typing import Dict, Any


def _make_validator() -> QDoubleValidator:
    v = QDoubleValidator()
    v.setLocale(QLocale(QLocale.Language.C))  # always dot as decimal separator
    v.setNotation(QDoubleValidator.Notation.ScientificNotation)
    return v


class ParameterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields: Dict[str, QLineEdit] = {}
        self._build_ui()

    def _make_field(self, key: str, value: float) -> QLineEdit:
        le = QLineEdit()
        le.setValidator(_make_validator())
        le.setMinimumWidth(80)
        le.setMaximumHeight(21)
        le.setText(f"{value:g}")
        self._fields[key] = le
        return le

    def _make_form(self) -> QFormLayout:
        fl = QFormLayout()
        fl.setContentsMargins(4, 2, 4, 2)
        fl.setSpacing(2)
        fl.setVerticalSpacing(2)
        return fl

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        main_layout = QVBoxLayout(inner)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(3)

        g_mass = QGroupBox("Masses (M☉)")
        fl = self._make_form()
        g_mass.setLayout(fl)
        fl.addRow("Mass A",       self._make_field("mass_A",   1.5))
        fl.addRow("Mass B",       self._make_field("mass_B",   0.5))
        fl.addRow("Mass C",       self._make_field("mass_C",   0.5))
        main_layout.addWidget(g_mass)

        g_ab = QGroupBox("Inner orbit AB")
        fl = self._make_form()
        g_ab.setLayout(fl)
        fl.addRow("a_AB (AU)",    self._make_field("a_AB",     1.0))
        fl.addRow("e_AB",         self._make_field("e_AB",     0.6))
        fl.addRow("i_AB (°)",     self._make_field("i_AB",     0.0))
        fl.addRow("Ω_AB (°)",     self._make_field("Omega_AB", 0.0))
        fl.addRow("ω_AB (°)",     self._make_field("omega_AB", 60.0))
        fl.addRow("M_AB (°)",     self._make_field("M_AB",     0.0))
        main_layout.addWidget(g_ab)

        g_ac = QGroupBox("Outer orbit C")
        fl = self._make_form()
        g_ac.setLayout(fl)
        fl.addRow("Q (q / a_AB)", self._make_field("Q",        5.0))
        self.field_e_AC = self._make_field("e_AC", 0.5)
        fl.addRow("e_AC",         self.field_e_AC)
        fl.addRow("i_AC (°)",     self._make_field("i_AC",     140.0))
        fl.addRow("Ω_AC (°)",     self._make_field("Omega_AC", 0.0))
        fl.addRow("ω_AC (°)",     self._make_field("omega_AC", 155.0))

        # M_AC (°) is used for elliptic outer orbits (e_AC < 1); it takes
        # the mean anomaly at t = 0. t_AC (y) is used for parabolic /
        # hyperbolic outer orbits (e_AC >= 1); it takes the time until the
        # third body passes periastron, in the same units as T_max.
        # Only one of the two fields is shown at a time, depending on e_AC.
        self.field_M_AC = self._make_field("M_AC", 0.0)
        self.field_t_AC = self._make_field("t_AC", 0.0)
        self.field_t_AC.setVisible(False)
        ac_anomaly_container = QWidget()
        ac_anomaly_layout = QHBoxLayout(ac_anomaly_container)
        ac_anomaly_layout.setContentsMargins(0, 0, 0, 0)
        ac_anomaly_layout.addWidget(self.field_M_AC)
        ac_anomaly_layout.addWidget(self.field_t_AC)
        self.label_ac_anomaly = QLabel("M_AC (°)")
        fl.addRow(self.label_ac_anomaly, ac_anomaly_container)

        main_layout.addWidget(g_ac)

        self.field_e_AC.textChanged.connect(self._update_ac_anomaly_field)
        self._update_ac_anomaly_field()

        main_layout.addStretch()
        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

    def _update_ac_anomaly_field(self):
        """Switch the outer-orbit anomaly field between M_AC (°) (elliptic,
        e_AC < 1) and t_AC (y) (parabolic / hyperbolic, e_AC >= 1)."""
        try:
            e_ac = float(self.field_e_AC.text())
        except ValueError:
            e_ac = 0.0
        if e_ac >= 1.0:
            self.label_ac_anomaly.setText("t_AC (y)")
            self.field_M_AC.setVisible(False)
            self.field_t_AC.setVisible(True)
        else:
            self.label_ac_anomaly.setText("M_AC (°)")
            self.field_M_AC.setVisible(True)
            self.field_t_AC.setVisible(False)

    def get_params(self) -> Dict[str, Any]:
        result = {}
        for key, le in self._fields.items():
            try:
                result[key] = float(le.text())
            except ValueError:
                result[key] = 0.0
        return result

    def set_params(self, params: Dict[str, Any]):
        for key, value in params.items():
            if key in self._fields:
                self._fields[key].setText(f"{float(value):g}")
        self._update_ac_anomaly_field()
