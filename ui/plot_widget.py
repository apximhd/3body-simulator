"""
Result display widgets.
Main plot (as in Mathematica): cos(i_mut) vs e_in
"""

from __future__ import annotations
# from statistics import mode

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  — registers 3d projection

COLORS_GL = {
    0: (1.0, 0.85, 0.1, 1.0),
    1: (0.3, 0.6, 1.0, 1.0),
    2: (1.0, 0.3, 0.3, 1.0),
}
COLORS_2D = {
    0: (255, 217, 26),
    1: (77, 153, 255),
    2: (255, 77, 77),
}
NAMES = ['A', 'B', 'C']


class Trajectory3DWidget(QWidget):
    """Matplotlib-backed 3D orbital trajectory view for the single-run tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._fig = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)
        lay.addWidget(self._canvas)

        self._ax = self._fig.add_subplot(111, projection="3d")
        self._ax.set_facecolor("#0d0d12")
        self._fig.patch.set_facecolor("#0d0d12")
        self._ax.xaxis.pane.set_facecolor((0.08, 0.08, 0.12, 1.0))
        self._ax.yaxis.pane.set_facecolor((0.08, 0.08, 0.12, 1.0))
        self._ax.zaxis.pane.set_facecolor((0.08, 0.08, 0.12, 1.0))
        self._ax.grid(True, alpha=0.3)
        self._ax.set_box_aspect((1, 1, 1))
        self._ax.xaxis.label.set_color("#e5e7eb")
        self._ax.yaxis.label.set_color("#e5e7eb")
        self._ax.zaxis.label.set_color("#e5e7eb")
        self._ax.title.set_color("#e5e7eb")
        self._ax.tick_params(colors="#e5e7eb")

    def clear_plots(self):
        self._ax.clear()
        self._ax.set_facecolor("#0d0d12")
        self._ax.xaxis.pane.set_facecolor((0.08, 0.08, 0.12, 1.0))
        self._ax.yaxis.pane.set_facecolor((0.08, 0.08, 0.12, 1.0))
        self._ax.zaxis.pane.set_facecolor((0.08, 0.08, 0.12, 1.0))
        self._ax.grid(True, alpha=0.3)
        self._ax.set_box_aspect((1, 1, 1))
        self._ax.xaxis.label.set_color("#e5e7eb")
        self._ax.yaxis.label.set_color("#e5e7eb")
        self._ax.zaxis.label.set_color("#e5e7eb")
        self._ax.title.set_color("#e5e7eb")
        self._ax.tick_params(colors="#e5e7eb")
        self._ax.set_xlabel("x (AU)")
        self._ax.set_ylabel("y (AU)")
        self._ax.set_zlabel("z (AU)")

    def plot_trajectories(self, positions: np.ndarray, stride: int = 1):
        self.clear_plots()
        if positions.size == 0:
            return

        pos = np.asarray(positions[::stride], dtype=float)
        finite = np.isfinite(pos)
        if not finite.any():
            return

        for i in range(3):
            pts = pos[:, i, :]
            good = np.all(np.isfinite(pts), axis=1)
            if not np.any(good):
                continue
            pts = pts[good]
            self._ax.plot(
                pts[:, 0], pts[:, 1], pts[:, 2],
                color=COLORS_GL[i][:3], linewidth=1.5, alpha=0.95
            )
            self._ax.scatter(
                [pts[-1, 0]], [pts[-1, 1]], [pts[-1, 2]],
                color=[COLORS_GL[i][:3]], s=36, depthshade=True
            )

        self._ax.scatter([0.0], [0.0], [0.0], color=[(0.7, 0.7, 0.7)], s=24)
        self._ax.set_title("3D trajectories")
        self._ax.title.set_color("#e5e7eb")
        self._ax.set_xlabel("x (AU)")
        self._ax.set_ylabel("y (AU)")
        self._ax.set_zlabel("z (AU)")
        self._ax.xaxis.label.set_color("#e5e7eb")
        self._ax.yaxis.label.set_color("#e5e7eb")
        self._ax.zaxis.label.set_color("#e5e7eb")
        self._ax.tick_params(colors="#e5e7eb")

        finite_coords = pos[np.isfinite(pos)]
        if finite_coords.size:
            data_min = float(finite_coords.min())
            data_max = float(finite_coords.max())
            span = data_max - data_min
            if np.isclose(span, 0.0):
                span = 1.0
            center = (data_min + data_max) / 2.0
            half_span = span / 2.0 * 1.08
            limits = (center - half_span, center + half_span)
            self._ax.set_xlim(limits)
            self._ax.set_ylim(limits)
            self._ax.set_zlim(limits)

        self._ax.set_box_aspect((1, 1, 1))
        self._fig.tight_layout()
        self._canvas.draw_idle()


class Trajectory2DWidget(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0d0d12')
        self._plot = self.addPlot(title="XY Projection")
        self._plot.setLabel('bottom', 'x', units='AU')
        self._plot.setLabel('left', 'y', units='AU')
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setAspectLocked(True)
        self._plot.addLegend()

    def clear_plots(self):
        self._plot.clear()

    def plot_trajectories(self, positions: np.ndarray, stride: int = 1):
        self.clear_plots()
        if positions.size == 0:
            return
        pos = positions[::stride]
        for i, name in enumerate(NAMES):
            self._plot.plot(
                pos[:, i, 0], pos[:, i, 1],
                pen=pg.mkPen(COLORS_2D[i], width=1.5), name=name
            )


class Plot2DWidget(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0d0d12')
        self.time_mode = 'years'  # 'years' or 'outer_revolutions'
        self.period_outer = 1.0

    def _add_plot(self, **kwargs):
        """addPlot with SI prefix scaling disabled on all axes."""
        p = self.addPlot(**kwargs)
        for ax in ('left', 'right', 'top', 'bottom'):
            p.getAxis(ax).enableAutoSIPrefix(False)
        return p

    def set_time_mode(self, mode: str, a_out: float = None, masses: tuple = None):
        """Set time axis mode. If mode='outer_revolutions', provide a_out and masses."""
        self.time_mode = mode
        if mode == 'outer_revolutions' and a_out is not None and masses is not None:
            import numpy as np
            from core.constants import YEAR
            M123 = sum(masses)
            self.period_outer = np.sqrt(a_out**3 / M123) * YEAR

    def _time_years(self, t: np.ndarray) -> np.ndarray:
        from core.constants import YEAR
        t_yr = t / YEAR
        if self.time_mode == 'outer_revolutions' and self.period_outer > 0:
            return t / self.period_outer
        return t_yr

    def plot_overview(self, t: np.ndarray, elements: dict,
                      positions: np.ndarray, masses: np.ndarray,
                      stride: int = 1):
        """e_in(t) and moment of inertia I(t) stacked vertically."""
        self.clear()
        if t.size == 0 or not elements:
            return
        t_yr = self._time_years(t[::stride])
        t_label = 'revolutions' if self.time_mode == 'outer_revolutions' else 'years'

        p1 = self._add_plot(title="e_in (t)")
        p1.setLabel('bottom', 't', units=t_label)
        p1.setLabel('left', 'e_in')
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.plot(t_yr, elements['e_in'][::stride], pen=pg.mkPen('#ffd54f', width=1.5))

        # I = sum_i m_i * |r_i - r_cm|^2
        pos = positions[::stride]                          # (N, 3, 3)
        r_cm = (masses[None, :, None] * pos).sum(axis=1, keepdims=True) / masses.sum()
        dr = pos - r_cm
        moment_of_inertia = (masses[None, :, None] * dr**2).sum(axis=(1, 2))

        self.nextRow()
        p2 = self._add_plot(title="Moment of inertia I (t)")
        p2.setLabel('bottom', 't', units=t_label)
        p2.setLabel('left', 'I', units='M☉·AU²')
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.plot(t_yr, moment_of_inertia, pen=pg.mkPen('#80cbc4', width=1.5))
        p2.setXLink(p1)

    def plot_cos_i_vs_e(self, elements: dict, stride: int = 1):
        """
        Main plot: cos(i_mut) vs e_in
        (as in Mathematica — Kozai-Lidov phase plane).
        """
        self.clear()
        if not elements or 'e_in' not in elements:
            return

        e = np.asarray(elements['e_in'][::stride], dtype=float)
        c = np.asarray(elements['cos_i_mut'][::stride], dtype=float)

        # discard NaN
        mask = np.isfinite(e) & np.isfinite(c)
        e, c = e[mask], c[mask]
        if e.size == 0:
            return

        p = self._add_plot(title="cos(i_mut)  vs  e_in")
        p.setLabel('bottom', 'e_in')
        p.setLabel('left', 'cos(i_mut)')
        p.showGrid(x=True, y=True, alpha=0.3)
        p.setXRange(0.0, min(1.0, float(np.nanmax(e)) * 1.05 + 0.02))
        p.setYRange(-1.05, 1.05)

        # Full phase-plane trajectory (bright line on dark background)
        p.plot(e, c, pen=pg.mkPen('#c5e1a5', width=1.5))

        # # Initial point (blue circle)
        # p.plot([e[0]], [c[0]], pen=None, symbol='o',
        #        symbolBrush='#42a5f5',
        #        symbolPen=pg.mkPen('#e3f2fd'),
        #        symbolSize=12)

        # # Final point (red square)
        # p.plot([e[-1]], [c[-1]], pen=None, symbol='s',
        #        symbolBrush='#ef5350',
        #        symbolPen=pg.mkPen('#ffebee'),
        #        symbolSize=12)

    def plot_eccentricities(self, t: np.ndarray, elements: dict):
        self.clear()
        if t.size == 0 or not elements:
            return
        t_yr = self._time_years(t)
        t_label = 'revolutions' if self.time_mode == 'outer_revolutions' else 'years'

        p1 = self._add_plot(title="e_in (t)")
        p1.setLabel('bottom', 't', units=t_label)
        p1.setLabel('left', 'e_in')
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.plot(t_yr, elements['e_in'], pen=pg.mkPen('#ffd54f', width=1.5))

        self.nextRow()
        p2 = self._add_plot(title="e_out (t)")
        p2.setLabel('bottom', 't', units=t_label)
        p2.setLabel('left', 'e_out')
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.plot(t_yr, elements['e_out'], pen=pg.mkPen('#81c784', width=1.5))
        p2.setXLink(p1)

    def plot_semimajor(self, t: np.ndarray, elements: dict):
        self.clear()
        if t.size == 0 or not elements:
            return
        t_yr = self._time_years(t)
        t_label = 'revolutions' if self.time_mode == 'outer_revolutions' else 'years'

        p1 = self._add_plot(title="a_in (t)")
        p1.setLabel('bottom', 't', units=t_label)
        p1.setLabel('left', 'a_in', units='AU')
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.plot(t_yr, elements['a_in'], pen=pg.mkPen('#1565c0', width=1.2))

        self.nextRow()
        p2 = self._add_plot(title="a_out (t)")
        p2.setLabel('bottom', 't', units=t_label)
        p2.setLabel('left', 'a_out', units='AU')
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.plot(t_yr, elements['a_out'], pen=pg.mkPen('#1565c0', width=1.2))
        p2.setXLink(p1)

    def plot_inclinations(self, t: np.ndarray, elements: dict):
        self.clear()
        if t.size == 0 or not elements:
            return
        t_yr = self._time_years(t)
        t_label = 'revolutions' if self.time_mode == 'outer_revolutions' else 'years'

        p1 = self._add_plot(title="cos i_mut (t)")
        p1.setLabel('bottom', 't', units=t_label)
        p1.setLabel('left', 'cos i_mut')
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.plot(t_yr, elements['cos_i_mut'],
                pen=pg.mkPen('#6a1b9a', width=1.2))

        self.nextRow()
        p2 = self._add_plot(title="I_mut (t)")
        p2.setLabel('bottom', 't', units=t_label)
        p2.setLabel('left', 'I_mut', units='deg')
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.plot(t_yr, elements['i_mut_deg'],
                pen=pg.mkPen('#c62828', width=1.2))
        p2.setXLink(p1)

    def plot_energy(self, t: np.ndarray, energy: np.ndarray):
        self.clear()
        if t.size == 0:
            return
        t_yr = self._time_years(t)
        t_label = 'revolutions' if self.time_mode == 'outer_revolutions' else 'years'

        p = self._add_plot(title="Total energy")
        p.setLabel('bottom', 't', units=t_label)
        p.setLabel('left', 'E')
        p.showGrid(x=True, y=True, alpha=0.3)
        p.plot(t_yr, energy, pen=pg.mkPen('#4fc3f7', width=1.5))

        if len(energy) > 1 and abs(energy[0]) > 1e-30:
            dE = (energy - energy[0]) / abs(energy[0])
            self.nextRow()
            p2 = self._add_plot(title="ΔE / E₀")
            p2.setLabel('bottom', 't', units=t_label)
            p2.setLabel('left', 'ΔE/E₀')
            p2.showGrid(x=True, y=True, alpha=0.3)
            p2.plot(t_yr, dE, pen=pg.mkPen('#ef5350', width=1.5))

    def plot_xy(self, positions: np.ndarray, stride: int = 1):
        self.clear()
        if positions.size == 0:
            return
        pos = positions[::stride]
        p = self._add_plot(title="XY Projection")
        p.setLabel('bottom', 'x', units='AU')
        p.setLabel('left', 'y', units='AU')
        p.showGrid(x=True, y=True, alpha=0.3)
        p.setAspectLocked(True)
        p.addLegend()
        for i, name in enumerate(NAMES):
            p.plot(pos[:, i, 0], pos[:, i, 1],
                   pen=pg.mkPen(COLORS_2D[i], width=1.2), name=name)

        xy = np.asarray(pos[:, :, :2], dtype=float)
        finite_xy = xy[np.isfinite(xy)]
        if finite_xy.size:
            data_min = float(finite_xy.min())
            data_max = float(finite_xy.max())
            span = data_max - data_min
            if np.isclose(span, 0.0):
                span = 1.0
            center = (data_min + data_max) / 2.0
            half_span = span / 2.0 * 1.08
            limits = (center - half_span, center + half_span)
            p.setRange(xRange=limits, yRange=limits, padding=0.0)
