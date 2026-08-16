"""
Osculating orbital elements — equivalent to getElements in Mathematica.

Returns:
  e_in, a_in, cos_i_in   — inner orbit AB
  e_out, a_out, cos_i_out — outer orbit C relative to CM(AB)
  cos_i_mut, i_mut_deg    — mutual inclination
"""

from __future__ import annotations
import numpy as np
from typing import Dict


def _orbital_elements_from_rv(r: np.ndarray, v: np.ndarray, mu: float) -> dict:
    """
    Classical osculating elements from r, v.
    Follows Mathematica logic (alpha = 2/r - w², e = |w×j - r̂|).
    """
    r_norm = np.linalg.norm(r)
    if r_norm < 1e-30 or mu <= 0:
        return dict(a=np.nan, e=np.nan, cos_i=np.nan, h=np.zeros(3))

    # w = v / sqrt(mu)  — as in Mathematica
    sqrt_mu = np.sqrt(mu)
    w = v / sqrt_mu
    w2 = np.dot(w, w)

    alpha = 2.0 / r_norm - w2          # 1/a
    a = 1.0 / alpha if abs(alpha) > 1e-30 else np.inf

    # Specific angular momentum j = r × w
    j = np.cross(r, w)
    j_norm = np.linalg.norm(j)
    cos_i = j[2] / j_norm if j_norm > 1e-30 else 1.0
    cos_i = float(np.clip(cos_i, -1.0, 1.0))

    # Eccentricity vector: e = w × j - r/|r|
    e_vec = np.cross(w, j) - r / r_norm
    e = np.linalg.norm(e_vec)

    # True h = r × v (used for mutual inclination)
    h = np.cross(r, v)

    return dict(a=a, e=e, cos_i=cos_i, h=h)


def get_elements(positions: np.ndarray, velocities: np.ndarray,
                 masses: np.ndarray) -> Dict[str, float]:
    """
    Equivalent to getElements[m1, m2, m3, xyzvList] from Mathematica.

    positions  : (3, 3)  [body, xyz]
    velocities : (3, 3)
    masses     : (3,)
    """
    m1, m2, m3 = masses
    M12 = m1 + m2
    M123 = M12 + m3

    r1, r2, r3 = positions
    v1, v2, v3 = velocities

    # ---------- Inner orbit AB ----------
    # Relative vector (as in Mathematica: scale (m1+m2)/m2 * (r1 - r_cm12))
    # Equivalent to: r_rel = r2 - r1, v_rel = v2 - v1
    r_rel = r2 - r1
    v_rel = v2 - v1
    mu_in = M12

    el_in = _orbital_elements_from_rv(r_rel, v_rel, mu_in)

    # ---------- Outer orbit C relative to CM(AB) ----------
    r_cm12 = (m1 * r1 + m2 * r2) / M12
    v_cm12 = (m1 * v1 + m2 * v2) / M12

    # Mathematica uses scale (M123/M12) * (r3 - r_cm_total)
    # which is equivalent to r3 - r_cm12 (position of C relative to CM AB)
    r_out = r3 - r_cm12
    v_out = v3 - v_cm12
    mu_out = M123   # often M12 in hierarchical approximation, but M123 here

    el_out = _orbital_elements_from_rv(r_out, v_out, mu_out)

    # ---------- Mutual inclination ----------
    h_in = el_in['h']
    h_out = el_out['h']
    h_in_n = np.linalg.norm(h_in)
    h_out_n = np.linalg.norm(h_out)

    if h_in_n > 1e-30 and h_out_n > 1e-30:
        cos_i_mut = float(np.clip(np.dot(h_in, h_out) / (h_in_n * h_out_n), -1.0, 1.0))
    else:
        cos_i_mut = 1.0

    i_mut_deg = float(np.degrees(np.arccos(cos_i_mut)))

    return {
        'e_in': el_in['e'],
        'a_in': el_in['a'],
        'cos_i_in': el_in['cos_i'],
        'e_out': el_out['e'],
        'a_out': el_out['a'],
        'cos_i_out': el_out['cos_i'],
        'cos_i_mut': cos_i_mut,
        'i_mut_deg': i_mut_deg,
    }


def compute_elements_series(positions: np.ndarray, velocities: np.ndarray,
                            masses: np.ndarray) -> Dict[str, np.ndarray]:
    """
    positions  : (N, 3, 3)
    velocities : (N, 3, 3)
    → dicts of arrays of length N
    """
    n = len(positions)
    keys = ['e_in', 'a_in', 'cos_i_in', 'e_out', 'a_out', 'cos_i_out',
            'cos_i_mut', 'i_mut_deg']
    out = {k: np.empty(n) for k in keys}

    for i in range(n):
        el = get_elements(positions[i], velocities[i], masses)
        for k in keys:
            out[k][i] = el[k]

    return out


def moment_of_inertia(positions: np.ndarray, masses: np.ndarray) -> np.ndarray:
    """
    I(t) = sum_i m_i |r_i - r_cm|^2
    positions : (N, 3, 3) or (3, 3)
    returns array of length N (or scalar)
    """
    pos = np.asarray(positions)
    single = pos.ndim == 2
    if single:
        pos = pos[None, ...]
    r_cm = (masses[None, :, None] * pos).sum(axis=1, keepdims=True) / masses.sum()
    dr = pos - r_cm
    I = (masses[None, :, None] * dr**2).sum(axis=(1, 2))
    return float(I[0]) if single else I


def inner_angular_momentum(positions: np.ndarray, velocities: np.ndarray,
                           masses: np.ndarray) -> np.ndarray:
    """
    Angular momentum of the inner binary AB:
    L = μ * (r_rel × v_rel),  μ = mA*mB/(mA+mB)
    Returns |L| for each time step (or scalar).
    positions/velocities : (N, 3, 3) or (3, 3)
    """
    pos = np.asarray(positions)
    vel = np.asarray(velocities)
    single = pos.ndim == 2
    if single:
        pos = pos[None, ...]
        vel = vel[None, ...]
    mA, mB = masses[0], masses[1]
    mu = mA * mB / (mA + mB)
    r_rel = pos[:, 1] - pos[:, 0]   # B - A
    v_rel = vel[:, 1] - vel[:, 0]
    h = np.cross(r_rel, v_rel)      # specific
    L = mu * np.linalg.norm(h, axis=1)
    return float(L[0]) if single else L


def inner_binary_energy(positions: np.ndarray, velocities: np.ndarray,
                        masses: np.ndarray) -> np.ndarray:
    """
    Two-body energy of the inner binary AB (relative orbit):

        E_in = ½ μ |v_rel|² − mA mB / |r_rel|

    where μ = mA mB / (mA + mB),  r_rel = r_B − r_A,  v_rel = v_B − v_A.
    G = 1 in the code units.  Does *not* include the outer body C.

    positions/velocities : (N, 3, 3) or (3, 3)
    Returns array of length N (or scalar).
    """
    pos = np.asarray(positions)
    vel = np.asarray(velocities)
    single = pos.ndim == 2
    if single:
        pos = pos[None, ...]
        vel = vel[None, ...]
    mA, mB = float(masses[0]), float(masses[1])
    mu = mA * mB / (mA + mB)
    r_rel = pos[:, 1] - pos[:, 0]
    v_rel = vel[:, 1] - vel[:, 0]
    r = np.linalg.norm(r_rel, axis=1)
    v2 = np.sum(v_rel * v_rel, axis=1)
    # guard against r → 0
    r_safe = np.where(r > 1e-30, r, np.nan)
    E = 0.5 * mu * v2 - mA * mB / r_safe
    return float(E[0]) if single else E


def last_local_minimum(arr: np.ndarray) -> float:
    """
    Minimum of the moment-of-inertia series I(t).

    Uses the global minimum — the same value visible as the lowest point
    on the Single-run I(t) plot.  (Local-min heuristics were unreliable on
    noisy / multi-dip curves after close encounters.)
    """
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return float('nan')
    return float(np.nanmin(arr))


def I_min_max(arr: np.ndarray):
    """
    I_min = global minimum of I(t).
    I_max = maximum of I on [0, t_min] (Szebehely: previous max before I_min).
    """
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return float('nan'), float('nan')
    imin_idx = int(np.nanargmin(arr))
    I_min = float(arr[imin_idx])
    I_max = float(np.nanmax(arr[: imin_idx + 1]))
    return I_min, I_max


def total_angular_momentum(positions: np.ndarray, velocities: np.ndarray,
                            masses: np.ndarray) -> float:
    """|L| of the full three-body system in the CM frame (at first snapshot)."""
    pos = np.asarray(positions)
    vel = np.asarray(velocities)
    if pos.ndim == 2:
        pos = pos[None, ...]
        vel = vel[None, ...]
    msum = float(np.sum(masses))
    r_cm = (masses[None, :, None] * pos).sum(axis=1) / msum
    v_cm = (masses[None, :, None] * vel).sum(axis=1) / msum
    L = np.zeros(3)
    for i in range(3):
        ri = pos[0, i] - r_cm[0]
        vi = vel[0, i] - v_cm[0]
        L += masses[i] * np.cross(ri, vi)
    return float(np.linalg.norm(L))


def sundman_ratio(I_min: float, I_max: float, h: float, c: float) -> float:
    """
    R = (2 |h|)^2 * I_min * I_max / c^4   (Szebehely form).
    Must satisfy R >= 1.
    """
    if not (np.isfinite(I_min) and np.isfinite(I_max) and np.isfinite(h) and np.isfinite(c)):
        return float('nan')
    if abs(c) < 1e-30:
        return float('nan')
    return float((2.0 * abs(h)) ** 2 * I_min * I_max / (c ** 4))


def delta_e_predicted(params: dict) -> float:
    """
    Δe ~ 0.3 * (m3/M12) * (Q/2)^{-4} * (1 + cos i)^2
    (Valtonen & Karttunen / paper eq. 11).  Q = q_out/a_AB, i = i_AC [deg].
    """
    mA = float(params.get('mass_A', 1.0))
    mB = float(params.get('mass_B', 1.0))
    mC = float(params.get('mass_C', 0.01))
    Q = float(params.get('Q', 5.0))
    i_deg = float(params.get('i_AC', 0.0))
    M12 = mA + mB
    if M12 <= 0 or Q <= 0:
        return float('nan')
    cos_i = np.cos(np.deg2rad(i_deg))
    return float(0.3 * (mC / M12) * (Q / 2.0) ** (-4) * (1.0 + cos_i) ** 2)
