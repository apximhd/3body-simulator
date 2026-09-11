"""
Result display widgets.
Main plot (as in Mathematica): cos(i_mut) vs e_in
"""

from __future__ import annotations
# from statistics import mode

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  — registers 3d projection
from core.elements import I_min_max

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


def _has_usable_opengl() -> bool:
    """Return whether this process can create and use a basic GL context."""
    format_ = QSurfaceFormat()
    format_.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    format_.setVersion(2, 1)
    surface = QOffscreenSurface()
    surface.setFormat(format_)
    surface.create()
    if not surface.isValid():
        return False

    context = QOpenGLContext()
    context.setFormat(format_)
    if not context.create() or not context.makeCurrent(surface):
        surface.destroy()
        return False

    try:
        from OpenGL import GL

        GL.glGetError()
        GL.glClearColor(0.05, 0.05, 0.08, 1.0)
        return GL.glGetError() == GL.GL_NO_ERROR
    except Exception:
        return False
    finally:
        context.doneCurrent()
        surface.destroy()


HAS_OPENGL = _has_usable_opengl()
if HAS_OPENGL:
    try:
        from pyqtgraph.opengl import (
            GLViewWidget,
            GLLinePlotItem,
            GLScatterPlotItem,
            GLGridItem,
            GLAxisItem,
        )
    except Exception:
        HAS_OPENGL = False


def _positions_relative_to_cm_ab(positions: np.ndarray,
                                 masses: np.ndarray) -> np.ndarray:
    """Body positions shifted so CM(A, B) is the origin at every time step."""
    mA, mB = masses[0], masses[1]
    r_cm_ab = (mA * positions[:, 0, :] + mB * positions[:, 1, :]) / (mA + mB)
    return positions - r_cm_ab[:, None, :]


def _densify_positions_for_display(times: np.ndarray, pos: np.ndarray,
                                   factor: int = 8,
                                   max_points: int = 120_000) -> np.ndarray:
    """
    Cubic-spline interpolation in time, purely to render a smooth curve.

    An adaptive integrator (e.g. IAS15) only takes as many real steps as its
    own error control needs, so raising Output Points beyond that count adds
    no new integrated data — the recorded trajectory stays exactly as coarse.
    This interpolates between the existing samples for display only; it does
    not add or alter any physics.
    """
    n = times.shape[0]
    if n < 4:
        return pos
    # Drop non-increasing timestamps (can happen at floating-point ties).
    keep = np.concatenate(([True], np.diff(times) > 0))
    times, pos = times[keep], pos[keep]
    n = times.shape[0]
    if n < 4:
        return pos

    target = min(max(n * factor, n), max_points)
    if target <= n:
        return pos

    from scipy.interpolate import CubicSpline

    dense_t = np.linspace(times[0], times[-1], target)
    dense_pos = np.empty((target,) + pos.shape[1:], dtype=float)
    for body in range(pos.shape[1]):
        for axis in range(pos.shape[2]):
            spline = CubicSpline(times, pos[:, body, axis])
            dense_pos[:, body, axis] = spline(dense_t)
    return dense_pos


def _nice_grid_step(half_extent: float) -> float:
    """Round half_extent/10 to a 1/2/5 * 10^n step, for ~10 grid divisions."""
    if half_extent <= 0 or not np.isfinite(half_extent):
        return 1.0
    raw_step = half_extent / 5.0
    exponent = np.floor(np.log10(raw_step))
    fraction = raw_step / (10 ** exponent)
    if fraction < 1.5:
        nice_fraction = 1.0
    elif fraction < 3.0:
        nice_fraction = 2.0
    elif fraction < 7.0:
        nice_fraction = 5.0
    else:
        nice_fraction = 10.0
    return float(nice_fraction * (10 ** exponent))


if HAS_OPENGL:

    class TrajectoryGL3DWidget(GLViewWidget):
        """pyqtgraph OpenGL 3D trajectories, plotted relative to CM(A, B)."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setCameraPosition(distance=40, elevation=25, azimuth=45)
            self.opts['bgcolor'] = (0.05, 0.05, 0.08, 1.0)
            self._lines = []
            self._points = []

            # Scale reference: grid in the xy-plane through CM(AB) plus axes.
            self._grid = GLGridItem()
            self._grid.setColor((150, 150, 150, 80))
            self.addItem(self._grid)
            self._axis = GLAxisItem()
            self.addItem(self._axis)

            # Grid step readout, since GLGridItem draws no tick labels.
            self._scale_label = QLabel(self)
            self._scale_label.setStyleSheet(
                "color: #e5e7eb; background-color: rgba(13, 13, 18, 170);"
                "padding: 2px 6px; border-radius: 3px; font-size: 11px;"
            )
            self._scale_label.move(8, 8)

        def clear_plots(self):
            for item in self._lines + self._points:
                self.removeItem(item)
            self._lines.clear()
            self._points.clear()

        def wheelEvent(self, ev):
            super().wheelEvent(ev)
            self._rescale_grid_to_view()

        def _rescale_grid_to_view(self):
            # Camera distance is the only zoom proxy pyqtgraph exposes here,
            # so re-derive the grid step from it whenever the view zooms.
            distance = float(self.opts.get('distance', 40.0))
            step = _nice_grid_step(distance)
            size = step * np.ceil(distance * 2.5 / step)
            self._grid.setSpacing(step, step, step)
            self._grid.setSize(size, size, size)
            self._axis.setSize(size / 2.0, size / 2.0, size / 2.0)
            self._scale_label.setText(f"Grid step: {step:g} AU")
            self._scale_label.adjustSize()

        def plot_trajectories(self, positions: np.ndarray, masses: np.ndarray,
                              stride: int = 1, times: np.ndarray = None):
            self.clear_plots()
            if positions.size == 0:
                return
            pos = _positions_relative_to_cm_ab(positions[::stride], masses)

            pos_line = pos
            if times is not None:
                pos_line = _densify_positions_for_display(
                    np.asarray(times[::stride], dtype=float), pos
                )

            finite = pos[np.isfinite(pos)]
            half_extent = float(np.max(np.abs(finite))) if finite.size else 1.0
            half_extent = max(half_extent, 1e-6)
            self.setCameraPosition(distance=half_extent * 2.5)
            self._rescale_grid_to_view()

            for i in range(3):
                pts = pos_line[:, i, :]
                line = GLLinePlotItem(pos=pts,
                                      color=COLORS_GL[i],
                                      width=1.5,
                                      antialias=True)
                self.addItem(line)
                self._lines.append(line)
                scatter = GLScatterPlotItem(pos=pts[-1:],
                                            color=COLORS_GL[i],
                                            size=8)
                self.addItem(scatter)
                self._points.append(scatter)
            origin = GLScatterPlotItem(
                pos=np.array([[0., 0., 0.]]),
                color=(0.7, 0.7, 0.7, 1.0), size=5
            )
            self.addItem(origin)
            self._points.append(origin)

else:

    class TrajectoryGL3DWidget(pg.GraphicsLayoutWidget):
        """Fallback 2D projection (relative to CM(A, B)) when OpenGL is unavailable."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setBackground('#0d0d12')
            self._plot = self.addPlot(
                title="XY projection, CM(AB) frame (OpenGL unavailable)"
            )
            self._plot.setLabel('bottom', 'x', units='AU')
            self._plot.setLabel('left', 'y', units='AU')
            self._plot.showGrid(x=True, y=True, alpha=0.4)
            self._plot.setAspectLocked(True)
            self._plot.addLegend()

        def clear_plots(self):
            self._plot.clear()

        def plot_trajectories(self, positions: np.ndarray, masses: np.ndarray,
                              stride: int = 1, times: np.ndarray = None):
            self.clear_plots()
            if positions.size == 0:
                return
            pos = _positions_relative_to_cm_ab(positions[::stride], masses)
            if times is not None:
                pos = _densify_positions_for_display(
                    np.asarray(times[::stride], dtype=float), pos
                )
            for i, name in enumerate(NAMES):
                self._plot.plot(
                    pos[:, i, 0], pos[:, i, 1],
                    pen=pg.mkPen(COLORS_2D[i], width=1.5), name=name
                )


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
        # Imin, Imax = I_min_max(moment_of_inertia, t[::stride],
        #                        elements.get('a_in'), masses)
        # print(f"Moment of inertia: min={Imin}, max={Imax}")

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
