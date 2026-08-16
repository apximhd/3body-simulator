"""
Integration of the three-body equations of motion.
Supported integrators: REBOUND IAS15, WHFast.
With progress reporting (callback percent 0..100).
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Callable
import time

try:
    import rebound
    HAS_REBOUND = True
except ImportError:
    HAS_REBOUND = False


ProgressCallback = Optional[Callable[[float], None]]  # percent 0..100


@dataclass
class SimulationResult:
    success: bool
    message: str
    t: np.ndarray
    positions: np.ndarray
    velocities: np.ndarray
    energy: np.ndarray
    elements: dict
    wall_time: float
    n_steps: int
    integrator: str
    params: dict = field(default_factory=dict)
    masses: np.ndarray = field(default_factory=lambda: np.zeros(3))


def total_energy(pos: np.ndarray, vel: np.ndarray, masses: np.ndarray) -> float:
    kinetic = 0.5 * np.sum(masses[:, None] * vel**2)
    potential = 0.0
    for i in range(3):
        for j in range(i + 1, 3):
            rij = pos[j] - pos[i]
            r = np.linalg.norm(rij)
            potential -= masses[i] * masses[j] / r
    return kinetic + potential


def run_rebound(positions, velocities, masses, t_max, integrator='ias15',
                dt=1e-3, n_output=2000, progress_cb: ProgressCallback = None):
    if not HAS_REBOUND:
        raise RuntimeError("REBOUND is not installed")

    sim = rebound.Simulation()
    sim.units = ('AU', 'yr2pi', 'Msun')
    sim.integrator = integrator
    if integrator.lower() == 'whfast':
        sim.dt = dt

    for i in range(3):
        sim.add(m=masses[i],
                x=positions[i, 0], y=positions[i, 1], z=positions[i, 2],
                vx=velocities[i, 0], vy=velocities[i, 1], vz=velocities[i, 2])

    sim.move_to_com()

    times = np.linspace(0.0, t_max, n_output)
    pos_list = []
    vel_list = []

    report_every = max(1, n_output // 50)

    for k, t in enumerate(times):
        sim.integrate(t)
        p = np.array([[p.x, p.y, p.z] for p in sim.particles])
        v = np.array([[p.vx, p.vy, p.vz] for p in sim.particles])
        pos_list.append(p)
        vel_list.append(v)

        if progress_cb is not None and (k % report_every == 0 or k == n_output - 1):
            progress_cb(100.0 * (k + 1) / n_output)

    return times, np.array(pos_list), np.array(vel_list)


def run_simulation(params: dict,
                   integrator: str = 'IAS15',
                   dt: float = 1e-3,
                   n_output: int = 2000,
                   progress_cb: ProgressCallback = None) -> SimulationResult:
    from .kepler import hierarchical_initial_conditions
    from .constants import YEAR
    from .elements import compute_elements_series

    t0 = time.perf_counter()

    try:
        pos0, vel0, masses = hierarchical_initial_conditions(params)
        t_max = params.get('t_max', 1000.0) * YEAR

        integrator = integrator.upper()

        if integrator in ('IAS15', 'WHFAST'):
            t, pos, vel = run_rebound(pos0, vel0, masses, t_max,
                                      integrator=integrator.lower(),
                                      dt=dt, n_output=n_output,
                                      progress_cb=progress_cb)
        else:
            return SimulationResult(
                False, f"Unknown integrator: {integrator}",
                np.array([]), np.array([]), np.array([]),
                np.array([]), {}, 0.0, 0, integrator, params
            )

        if progress_cb is not None:
            progress_cb(100.0)

        energy = np.array([total_energy(pos[i], vel[i], masses) for i in range(len(t))])
        elements = compute_elements_series(pos, vel, masses)

        wall = time.perf_counter() - t0

        return SimulationResult(
            success=True,
            message="OK",
            t=t,
            positions=pos,
            velocities=vel,
            energy=energy,
            elements=elements,
            wall_time=wall,
            n_steps=len(t),
            integrator=integrator,
            params=params.copy(),
            masses=masses
        )

    except Exception as e:
        wall = time.perf_counter() - t0
        return SimulationResult(
            False, str(e), np.array([]), np.array([]), np.array([]),
            np.array([]), {}, wall, 0, integrator, params
        )
