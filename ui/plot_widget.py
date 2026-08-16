"""
Result display widgets.
Main plot (as in Mathematica): cos(i_mut) vs e_in
"""

from __future__ import annotations
# from statistics import mode
import numpy as np
import pyqtgraph as pg

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

HAS_OPENGL = False
try:
    from pyqtgraph.opengl import (
        GLViewWidget,
        GLLinePlotItem,
        GLScatterPlotItem
    )
    HAS_OPENGL = True
except Exception:
    HAS_OPENGL = False


if HAS_OPENGL:

    class Trajectory3DWidget(GLViewWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setCameraPosition(distance=40, elevation=25, azimuth=45)
            self.opts['bgcolor'] = (0.05, 0.05, 0.08, 1.0)
            self._lines = []
            self._points = []

        def clear_plots(self):
            for item in self._lines + self._points:
                self.removeItem(item)
            self._lines.clear()
            self._points.clear()

        def plot_trajectories(self, positions: np.ndarray, stride: int = 1):
            self.clear_plots()
            if positions.size == 0:
                return
            pos = positions[::stride]
            for i in range(3):
                pts = pos[:, i, :]
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

    class Trajectory3DWidget(pg.GraphicsLayoutWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setBackground('#0d0d12')
            self._plot = self.addPlot(title="XY Projection (OpenGL unavailable)")
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
