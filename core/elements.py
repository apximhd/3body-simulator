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


def inner_period(a_in: np.ndarray | float, masses: np.ndarray) -> float:
    """Orbital period of the inner binary AB in internal time units (G = 1)."""
    a = np.asarray(a_in, dtype=float)
    if a.ndim > 0:
        a = a[np.isfinite(a) & (a > 0.0)]
        if a.size == 0:
            return float('nan')
        a = float(np.median(a))
    else:
        a = float(a)
    M12 = float(masses[0]) + float(masses[1])
    if not np.isfinite(a) or a <= 0.0 or M12 <= 0.0:
        return float('nan')
    return float(2.0 * np.pi * np.sqrt(a ** 3 / M12))


def _smooth_out_inner_period(arr: np.ndarray, t: np.ndarray, period: float) -> np.ndarray:
    """
    Running average of arr over a time window of exactly one inner-binary
    period, which nulls that harmonic and all of its overtones.

    Works on a non-uniform time grid (snapshots land on the integrator's own
    step boundaries), so the average is taken from the cumulative integral
    rather than over a fixed number of samples.
    """
    cumulative = np.concatenate(
        [[0.0], np.cumsum(0.5 * (arr[1:] + arr[:-1]) * np.diff(t))]
    )
    half = 0.5 * period
    lo = np.clip(t - half, t[0], t[-1])
    hi = np.clip(t + half, t[0], t[-1])
    span = hi - lo
    smooth = (np.interp(hi, t, cumulative) - np.interp(lo, t, cumulative))
    return np.where(span > 0.0, smooth / np.where(span > 0.0, span, 1.0), arr)


def I_min_max(arr: np.ndarray, t: np.ndarray | None = None,
              a_in: np.ndarray | float | None = None,
              masses: np.ndarray | None = None):
    """
    Szebehely pair (I_min, I_max) for the moment-of-inertia series I(t).

    I(t) carries a strong harmonic at the inner-binary period that hides the
    slow envelope, so the extrema are located on a curve smoothed over exactly
    one inner period: the last local minimum before the break-up (the final
    unbounded rise of I) and the local maximum immediately preceding it.
    The returned values are then read off the *raw* curve within a
    half-period neighbourhood of those two instants.

    Falls back to the plain global minimum / preceding maximum when the time
    grid or the inner period is unknown or the smoothed curve has no interior
    minimum.
    """
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return float('nan'), float('nan')

    if a_in is None or masses is None:
        period_inner = float('nan')
    else:
        period_inner = inner_period(a_in, masses)

    idx = _extrema_indices(arr, t, period_inner)
    if idx is None:
        imin_idx = int(np.nanargmin(arr))
        return float(arr[imin_idx]), float(np.nanmax(arr[: imin_idx + 1]))

    imin_idx, imax_idx = idx
    return _parabolic_extremum(arr, imin_idx), _parabolic_extremum(arr, imax_idx)


def _parabolic_extremum(arr: np.ndarray, idx: int) -> float:
    """
    Sub-sample extremum value from a parabola through the three samples at idx.

    The deep I(t) dips are only a few output points wide, so the sampled value
    can overestimate the true minimum by tens of percent.
    """
    if idx <= 0 or idx >= arr.size - 1:
        return float(arr[idx])
    y0, y1, y2 = float(arr[idx - 1]), float(arr[idx]), float(arr[idx + 1])
    denom = y0 - 2.0 * y1 + y2
    if not np.isfinite(denom) or abs(denom) < 1e-30:
        return y1
    shift = 0.5 * (y0 - y2) / denom
    if abs(shift) > 1.0:
        return y1
    return y1 - 0.25 * (y0 - y2) * shift


def _extrema_indices(arr: np.ndarray, t, period_inner):
    """Raw-curve indices of (last envelope minimum, preceding envelope maximum)."""
    from scipy.signal import find_peaks

    if t is None:
        return None
    t = np.asarray(t, dtype=float)
    if t.size != arr.size or t.size < 8 or not np.all(np.diff(t) > 0.0):
        return None
    if not np.isfinite(period_inner) or period_inner <= 0.0:
        return None

    duration = t[-1] - t[0]
    if duration <= 2.0 * period_inner:
        return None

    samples_per_period = (t.size - 1) * period_inner / duration
    if samples_per_period < 4.0:
        # aliased: the AB harmonic cannot be filtered out, so the envelope is
        # meaningless — leave it to the caller's global-minimum fallback
        return None
    smooth = _smooth_out_inner_period(arr, t, period_inner)

    # I spans orders of magnitude, so peaks are ranked in log space: the
    # threshold is then a relative depth and does not depend on how far the
    # escaping body has travelled by the end of the run.
    if np.any(smooth <= 0.0) or not np.all(np.isfinite(smooth)):
        return None
    log_smooth = np.log10(smooth)
    prominence = 0.05                               # dex

    min_idx, _ = find_peaks(-log_smooth, prominence=prominence)
    max_idx, _ = find_peaks(log_smooth, prominence=prominence)
    if min_idx.size == 0:
        return None

    i_min = int(min_idx[-1])
    preceding = max_idx[max_idx < i_min]
    i_max = int(preceding[-1]) if preceding.size else int(np.nanargmax(log_smooth[: i_min + 1]))

    half = 0.5 * period_inner

    def refine(centre, take_min, lo_bound, hi_bound):
        lo = max(lo_bound, int(np.searchsorted(t, t[centre] - half, 'left')))
        hi = min(hi_bound, int(np.searchsorted(t, t[centre] + half, 'right')))
        if hi <= lo:
            return centre
        seg = arr[lo:hi]
        off = int(np.nanargmin(seg) if take_min else np.nanargmax(seg))
        return lo + off

    # keep the maximum strictly before the minimum after refinement
    j_max = refine(i_max, False, 0, i_min)
    j_min = refine(i_min, True, j_max + 1, arr.size)
    return j_min, j_max


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
    # Omega = float(params.get('Omega_AC', 0.0))
    # ecc = float(params.get('e_AB', 0.0))
    # sin_2Omega = np.sin(np.deg2rad(Omega * 2))
    # sin2_i = np.sin(np.deg2rad(i_deg))**2
    M12 = mA + mB
    # M123 = M12 + mC
    if M12 <= 0 or Q <= 0:
        return float('nan')
    cos_i = np.cos(np.deg2rad(i_deg))
    return float(0.3 * (mC / M12) * (Q / 2.0) ** (-4) * (1.0 + cos_i) ** 2)
    # print(i_deg, Omega, ecc)
    # result = -15 * np.pi / 16 * np.sqrt(2 * mC**2 / M12 / M123) * Q**(-3 / 2) * ecc * np.sqrt(1 - ecc**2) * sin2_i * sin_2Omega
    # # print(result)
    # return result
