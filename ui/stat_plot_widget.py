"""
Statistic-result plots: 2D curve (1 scanned param) or 3D surface (2 params).
Uses matplotlib for cross-platform 2D/3D rendering inside Qt.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
from scipy.interpolate import griddata
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QSizePolicy, QLabel
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter, ScalarFormatter
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  — registers 3d projection


def _plain_ticks(ax):
    """Disable matplotlib offset notation on the regular statistic plots."""
    for axis in (getattr(ax, "xaxis", None), getattr(ax, "yaxis", None),
                 getattr(ax, "zaxis", None)):
        if axis is None:
            continue
        try:
            fmt = ScalarFormatter(useOffset=False)
            fmt.set_scientific(False)
            axis.set_major_formatter(fmt)
        except Exception:
            pass


def _format_imax_axis(axis):
    """Show Imax values with three decimals and no offset annotation."""
    axis.set_major_formatter(FormatStrFormatter("%.3f"))
    axis.get_offset_text().set_visible(False)


class StatPlotWidget(QWidget):
    """One result quantity vs scanned parameter(s)."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)

        self._fig = Figure(tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)
        lay.addWidget(self._canvas)

        self._placeholder = QLabel("Run a statistic scan to see this plot.")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888;")
        lay.addWidget(self._placeholder)
        self._canvas.hide()

    def clear(self):
        self._fig.clear()
        self._canvas.draw_idle()
        self._canvas.hide()
        self._placeholder.show()

    @staticmethod
    def _smooth_surface(x, y, z):
        """Resample a scanned surface onto a dense grid for smoother rendering."""
        values = np.asarray(z, dtype=float)
        valid = np.isfinite(values)
        if valid.sum() < 4 or len(x) < 2 or len(y) < 2:
            return np.meshgrid(x, y, indexing="ij") + (values,)

        dense_x = np.linspace(float(x[0]), float(x[-1]), max(50, len(x) * 4))
        dense_y = np.linspace(float(y[0]), float(y[-1]), max(50, len(y) * 4))
        dense_X, dense_Y = np.meshgrid(dense_x, dense_y, indexing="ij")
        points = np.column_stack((
            np.asarray(x)[:, None].repeat(len(y), axis=1)[valid],
            np.asarray(y)[None, :].repeat(len(x), axis=0)[valid],
        ))
        sampled = values[valid]

        # Cubic interpolation gives a smooth surface; linear interpolation
        # fills cases where the scan grid is too sparse for cubic interpolation.
        dense_z = griddata(
            points, sampled, (dense_X, dense_Y), method="cubic"
        )
        if dense_z is None or not np.isfinite(dense_z).any():
            dense_z = griddata(
                points, sampled, (dense_X, dense_Y), method="linear"
            )
        return dense_X, dense_Y, dense_z

    def plot_1d(
        self,
        x: np.ndarray,
        y: np.ndarray,
        xlabel: str,
        ylabel: str,
    ):
        self._placeholder.hide()
        self._canvas.show()
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        mask = np.isfinite(x) & np.isfinite(y)
        ax.plot(x[mask], y[mask], "-", color="#4fc3f7", linewidth=1.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if self._title:
            ax.set_title(self._title)
        ax.grid(True, alpha=0.3)
        _plain_ticks(ax)
        if ylabel == "Imax":
            _format_imax_axis(ax.yaxis)
        self._fig.tight_layout()
        self._canvas.draw_idle()

    def plot_2d_surface(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        xlabel: str,
        ylabel: str,
        zlabel: str,
    ):
        """
        x, y : 1-D coordinate axes (lengths nx, ny)
        z    : 2-D array shape (nx, ny)  — z[i,j] at (x[i], y[j])
        """
        self._placeholder.hide()
        self._canvas.show()
        self._fig.clear()
        ax = self._fig.add_subplot(111, projection="3d")

        X, Y, z_plot = self._smooth_surface(x, y, z)
        # replace non-finite with nan so surface skips them
        z_plot = np.where(np.isfinite(z_plot), z_plot, np.nan)

        if np.all(np.isnan(z_plot)):
            ax.text2D(0.3, 0.5, "No valid data", transform=ax.transAxes)
        else:
            surf = ax.plot_surface(
                X, Y, z_plot,
                cmap="viridis",
                edgecolor="none",
                alpha=0.95,
                linewidth=0,
                antialiased=True,
            )
            colorbar = self._fig.colorbar(
                surf, ax=ax, shrink=0.6, pad=0.1, label=zlabel
            )
            if zlabel == "Imax":
                _format_imax_axis(colorbar.ax.yaxis)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_zlabel(zlabel)
        if self._title:
            ax.set_title(self._title)
        _plain_ticks(ax)
        if zlabel == "Imax":
            _format_imax_axis(ax.zaxis)
        self._fig.tight_layout()
        self._canvas.draw_idle()

    def plot_1d_overlay(
        self,
        x, y1, y2,
        xlabel: str,
        label1: str = "sim",
        label2: str = "pred",
    ):
        self._placeholder.hide()
        self._canvas.show()
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        mask = np.isfinite(x)
        m1 = mask & np.isfinite(y1)
        m2 = mask & np.isfinite(y2)
        ax.plot(x[m1], y1[m1], "-", color="#4fc3f7",
                linewidth=1.5, label=label1)
        ax.plot(x[m2], y2[m2], "--", color="#ff8a65",
                linewidth=1.5, label=label2)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Δe")
        if self._title:
            ax.set_title(self._title)
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        _plain_ticks(ax)
        self._fig.tight_layout()
        self._canvas.draw_idle()

    def plot_2d_overlay(
        self,
        x, y, Z1, Z2,
        xlabel: str, ylabel: str,
        label1: str = "sim",
        label2: str = "pred",
    ):
        """Two surfaces on the same 3D axes (sim solid, pred wireframe)."""
        self._placeholder.hide()
        self._canvas.show()
        self._fig.clear()
        ax = self._fig.add_subplot(111, projection="3d")
        X, Y, Z1p = self._smooth_surface(x, y, Z1)
        _, _, Z2p = self._smooth_surface(x, y, Z2)
        Z1p = np.where(np.isfinite(Z1p), Z1p, np.nan)
        Z2p = np.where(np.isfinite(Z2p), Z2p, np.nan)
        if not np.all(np.isnan(Z1p)):
            s1 = ax.plot_surface(
                X, Y, Z1p, cmap="viridis", alpha=0.85,
                edgecolor="none", linewidth=0, antialiased=True,
            )
            colorbar = self._fig.colorbar(
                s1, ax=ax, shrink=0.55, pad=0.08, label=label1
            )
            if label1 == "Imax":
                _format_imax_axis(colorbar.ax.yaxis)
        if not np.all(np.isnan(Z2p)):
            ax.plot_wireframe(
                X, Y, Z2p, color="#ff8a65", linewidth=0.7, alpha=0.9,
                label=label2,
            )
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_zlabel("Δe")
        if self._title:
            ax.set_title(self._title)
        _plain_ticks(ax)
        if label1 == "Imax":
            _format_imax_axis(ax.zaxis)
        self._fig.tight_layout()
        self._canvas.draw_idle()


def build_stat_arrays(
    rows: Sequence[dict],
    scanned_keys: Sequence[str],
    quantity: str,
) -> tuple:
    """
    Build plotting arrays from ordered statistic rows.

    quantity:
      'Imax' | 'Imin' | 'R' | 'delta_e' | 'delta_e_pred'

    Returns
    -------
    kind : '1d' | '2d' | None
    data : for 1d → (x, y, xlabel, ylabel)
           for 2d → (x, y, Z, xlabel, ylabel, zlabel)
    """
    valid = [r for r in rows if r is not None]
    if not valid or not scanned_keys:
        return None, None

    def _qty(r: dict) -> float:
        return float(r.get(quantity, np.nan))

    labels = {
        "Imax": "Imax",
        "Imin": "Imin",
        "R": "Sundman R",
        "delta_e": "Δe (sim)",
        "delta_e_pred": "Δe (pred)",
    }
    ylabel = labels.get(quantity, quantity)

    if len(scanned_keys) == 1:
        key = scanned_keys[0]
        # sort by parameter value to be safe
        ordered = sorted(valid, key=lambda r: float(r.get(key, 0.0)))
        x = np.array([float(r[key]) for r in ordered], dtype=float)
        y = np.array([_qty(r) for r in ordered], dtype=float)
        return "1d", (x, y, key, ylabel)

    if len(scanned_keys) >= 2:
        k0, k1 = scanned_keys[0], scanned_keys[1]
        # unique sorted axes
        x_vals = sorted({float(r[k0]) for r in valid})
        y_vals = sorted({float(r[k1]) for r in valid})
        x = np.array(x_vals, dtype=float)
        y = np.array(y_vals, dtype=float)
        # map (x,y) → value
        lookup = {
            (float(r[k0]), float(r[k1])): _qty(r)
            for r in valid
        }
        Z = np.full((len(x), len(y)), np.nan, dtype=float)
        for i, xv in enumerate(x):
            for j, yv in enumerate(y):
                Z[i, j] = lookup.get((float(xv), float(yv)), np.nan)
        return "2d", (x, y, Z, k0, k1, ylabel)

    return None, None
