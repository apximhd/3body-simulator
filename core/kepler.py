"""
Conversion of Keplerian elements to Cartesian coordinates and velocities.
Fully consistent with the original Mathematica code logic.
"""

from __future__ import annotations
import numpy as np
from scipy.optimize import root_scalar
from .constants import DEG, YEAR


def solve_kepler(mean_anomaly: float, ecc: float) -> float:
    """Solves Kepler's equation for ellipse or hyperbola."""
    if ecc < 1e-12:
        return mean_anomaly

    if ecc < 1.0:
        # Elliptic
        def f(E):
            return E - ecc * np.sin(E) - mean_anomaly
        E0 = mean_anomaly if ecc < 0.8 else np.pi
        sol = root_scalar(f, bracket=[mean_anomaly - 2 * np.pi, mean_anomaly + 2 * np.pi],
                          x0=E0, method='brentq')
        return sol.root
    else:
        # Hyperbolic: M = e sinh(F) - F
        def f(F):
            return ecc * np.sinh(F) - F - mean_anomaly
        # Initial guess
        F0 = np.sign(mean_anomaly) * np.log(2 * abs(mean_anomaly) / ecc + 1.8)
        sol = root_scalar(f, x0=F0, method='newton',
                          fprime=lambda F: ecc * np.cosh(F) - 1)
        return sol.root


def orbital_basis(a: float, ecc: float, i: float, Omega: float, omega: float):
    """
    Returns vectors A and B.
    Works for both ellipse (a>0, e<1) and hyperbola (a<0, e>1).
    """
    cos_w, sin_w = np.cos(omega), np.sin(omega)
    cos_O, sin_O = np.cos(Omega), np.sin(Omega)
    cos_i, sin_i = np.cos(i), np.sin(i)

    A = a * np.array([
        cos_w * cos_O - sin_w * sin_O * cos_i,
        cos_w * sin_O + sin_w * cos_O * cos_i,
        sin_w * sin_i
    ])

    # Hyperbola: sqrt(e²-1), Ellipse: sqrt(1-e²)
    if ecc < 1.0:
        factor = np.sqrt(1.0 - ecc**2)
    else:
        factor = np.sqrt(ecc**2 - 1.0)

    B = abs(a) * factor * np.array([   # abs(a) важно!
        -sin_w * cos_O - cos_w * sin_O * cos_i,
        -sin_w * sin_O + cos_w * cos_O * cos_i,
        cos_w * sin_i
    ])
    return A, B


def state_from_elements(a: float, ecc: float, i: float, Omega: float, omega: float,
                        mean_anomaly: float, mu: float):
    """
    Position and velocity for ellipse or hyperbola.
    """
    if ecc < 1.0:
        # --- Ellipse ---
        E = solve_kepler(mean_anomaly, ecc)
        cos_E, sin_E = np.cos(E), np.sin(E)

        A, B = orbital_basis(a, ecc, i, Omega, omega)

        r = (cos_E - ecc) * A + sin_E * B

        n = np.sqrt(mu / a**3)
        factor = n / (1.0 - ecc * cos_E)
        v = factor * (-sin_E * A + cos_E * B)
    else:
        # --- Hyperbola ---
        F = solve_kepler(mean_anomaly, ecc)          # hyperbolic anomaly
        cosh_F = np.cosh(F)
        sinh_F = np.sinh(F)

        A, B = orbital_basis(a, ecc, i, Omega, omega)

        r = (ecc - cosh_F) * A + sinh_F * B          # alter sign!

        # mean motion for hyperbola: n = sqrt(mu / |a|³)
        n = np.sqrt(mu / abs(a)**3)
        factor = n / (ecc * cosh_F - 1.0)
        v = factor * (-sinh_F * A + cosh_F * B)

    return r, v


def solve_barker(mean_anomaly: float) -> float:
    """
    Solves Barker's equation for the parabolic case (e = 1):
        M = D + D^3/3
    for D = tan(true_anomaly / 2).

    Closed-form solution of the depressed cubic D^3 + 3D - 3M = 0
    via Cardano's formula (a single real root always exists because
    the left-hand side is monotonically increasing in D).
    """
    q = -3.0 * mean_anomaly
    term = np.sqrt((q / 2.0) ** 2 + 1.0)   # (p/3)^3 = 1 since p = 3
    D = np.cbrt(-q / 2.0 + term) + np.cbrt(-q / 2.0 - term)
    return D


def state_parabolic(q: float, i: float, Omega: float, omega: float,
                     mean_anomaly: float, mu: float):
    """
    Position and velocity for a parabolic orbit (e = 1) given the
    periapsis distance q and the parabolic mean anomaly.
    """
    D = solve_barker(mean_anomaly)

    cos_w, sin_w = np.cos(omega), np.sin(omega)
    cos_O, sin_O = np.cos(Omega), np.sin(Omega)
    cos_i, sin_i = np.cos(i), np.sin(i)

    # Unit vectors towards periapsis (P) and perpendicular to it in the
    # orbital plane, in the direction of motion (Qhat) — same rotation
    # used in orbital_basis(), but unscaled (a = 1).
    P = np.array([
        cos_w * cos_O - sin_w * sin_O * cos_i,
        cos_w * sin_O + sin_w * cos_O * cos_i,
        sin_w * sin_i
    ])
    Qhat = np.array([
        -sin_w * cos_O - cos_w * sin_O * cos_i,
        -sin_w * sin_O + cos_w * cos_O * cos_i,
        cos_w * sin_i
    ])

    one_plus_D2 = 1.0 + D * D
    x_pf = q * (1.0 - D * D)
    y_pf = 2.0 * q * D
    r = x_pf * P + y_pf * Qhat

    h = np.sqrt(2.0 * mu * q)           # specific angular momentum (e = 1)
    factor = mu / h
    vx_pf = -factor * 2.0 * D / one_plus_D2
    vy_pf = factor * 2.0 / one_plus_D2
    v = vx_pf * P + vy_pf * Qhat

    return r, v


def hierarchical_initial_conditions(params: dict):
    """
    Builds initial conditions for the AB + C system.
    Returns:
        positions  – (3, 3)  [body, xyz]
        velocities – (3, 3)
        masses     – (3,)
    """
    mA = params['mass_A']
    mB = params['mass_B']
    mC = params['mass_C']
    M12 = mA + mB
    M123 = M12 + mC

    # --- Inner orbit AB ---
    a12 = params['a_AB']
    e12 = params['e_AB']
    i12 = params['i_AB'] * DEG
    Om12 = params['Omega_AB'] * DEG
    w12 = params['omega_AB'] * DEG
    M12_anom = params['M_AB'] * DEG

    r_rel, v_rel = state_from_elements(a12, e12, i12, Om12, w12, M12_anom, M12)

    # Positions of A and B relative to the centre of mass of AB
    rA = - (mB / M12) * r_rel
    rB = (mA / M12) * r_rel
    vA = -(mB / M12) * v_rel
    vB = (mA / M12) * v_rel

    # --- Outer orbit C relative to CM(AB) ---
    Q = params['Q']
    e3 = params['e_AC']
    q3 = Q * a12                       # periapsis distance = Q * a_AB (always finite)

    i3 = params['i_AC'] * DEG
    Om3 = params['Omega_AC'] * DEG
    w3 = params['omega_AC'] * DEG

    if e3 < 1.0:
        # --- Elliptic: mean anomaly is given directly, in degrees ---
        a3 = q3 / (1.0 - e3)
        M3 = params['M_AC'] * DEG
        rC_rel, vC_rel = state_from_elements(a3, e3, i3, Om3, w3, M3, M123)
    else:
        # --- Parabolic / hyperbolic: the user supplies the time until
        # periastron passage (t_AC, in years — same units as T_max),
        # not a mean anomaly. Convert it to the corresponding
        # (hyperbolic / parabolic) mean anomaly.
        #   M(t) = n * (t - t_peri)
        # so with delta_t = t_AC (time from now until periastron, in
        # years, positive if periastron lies in the future):
        #   M(t=0) = -n * delta_t
        t_AC = params.get('t_AC', 0.0) * YEAR   # years -> internal time units

        if abs(e3 - 1.0) < 1e-9:
            # Parabolic
            n3 = np.sqrt(M123 / (2.0 * q3 ** 3))
            M3 = -n3 * t_AC
            rC_rel, vC_rel = state_parabolic(q3, i3, Om3, w3, M3, M123)
        else:
            # Hyperbolic
            a3_mag = q3 / (e3 - 1.0)
            a3 = -a3_mag
            n3 = np.sqrt(M123 / a3_mag ** 3)
            M3 = -n3 * t_AC
            rC_rel, vC_rel = state_from_elements(a3, e3, i3, Om3, w3, M3, M123)

    # Centre of mass of the full system
    # At this point rA, rB, rC_rel are relative to CM(AB), so
    # CM of full system = (M12 * 0 + mC * rC_rel) / M123 = (mC / M123) * rC_rel
    r_cm = (mC / M123) * rC_rel
    v_cm = (mC / M123) * vC_rel

    # Shift to the CM frame
    rA -= r_cm
    rB -= r_cm
    rC = rC_rel - r_cm

    vA -= v_cm
    vB -= v_cm
    vC = vC_rel - v_cm

    positions = np.vstack([rA, rB, rC])
    velocities = np.vstack([vA, vB, vC])
    masses = np.array([mA, mB, mC])

    return positions, velocities, masses
