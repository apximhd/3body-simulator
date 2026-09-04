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

    n_output = max(2, int(n_output))
    interval = t_max / (n_output - 1)
    report_every = max(1, n_output // 50)

    times: list = []
    pos_list: list = []
    vel_list: list = []
    next_output = [0.0]

    def sample(sim_ptr):
        s = sim_ptr.contents
        if s.t < next_output[0]:
            return
        next_output[0] += interval
        times.append(s.t)
        pos_list.append([[p.x, p.y, p.z] for p in s.particles])
        vel_list.append([[p.vx, p.vy, p.vz] for p in s.particles])
        if progress_cb is not None and len(times) % report_every == 0:
            progress_cb(min(100.0, 100.0 * s.t / t_max))

    # Snapshots are taken from inside the integrator's own step loop instead of
    # stopping at every output time: a stop truncates the current step, which
    # would make the step sequence — and hence the trajectory of this chaotic
    # system — depend on t_max and n_output.
    callback = rebound.simulation.AFF(sample)
    sim._heartbeat = callback           # keep `callback` alive while sim exists
    sim.integrate(t_max, exact_finish_time=0)

    if not times or times[-1] < sim.t:
        times.append(sim.t)
        pos_list.append([[p.x, p.y, p.z] for p in sim.particles])
        vel_list.append([[p.vx, p.vy, p.vz] for p in sim.particles])

    if progress_cb is not None:
        progress_cb(100.0)

    return np.array(times), np.array(pos_list), np.array(vel_list)


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
