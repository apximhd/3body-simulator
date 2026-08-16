"""
Batch / statistic-run helpers.

Designed for use with concurrent.futures.ProcessPoolExecutor:
  - all entry points are top-level (picklable under spawn on Windows/macOS/Linux)
  - no Qt objects are passed across process boundaries
  - return values are plain dicts / Python scalars
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .simulation import run_simulation
from .elements import (
    moment_of_inertia,
    I_min_max,
    total_angular_momentum,
    sundman_ratio,
    delta_e_predicted,
)


def extract_stat_row(
    params: Dict[str, Any],
    scanned_keys: Sequence[str],
    result,
) -> Dict[str, Any]:
    """Build one serialisable table row from a SimulationResult."""
    row: Dict[str, Any] = {k: params[k] for k in scanned_keys}

    if not result.success or result.t is None or getattr(result.t, "size", 0) == 0:
        row.update({
            "Imax": float("nan"),
            "Imin": float("nan"),
            "R": float("nan"),
            "delta_e": float("nan"),
            "delta_e_pred": float("nan"),
            "success": False,
            "message": getattr(result, "message", "failed"),
        })
        return row

    I = moment_of_inertia(result.positions, result.masses)
    Imin, Imax = I_min_max(I)
    # Conserved total energy and angular momentum (evaluate once at t=0)
    h = float(result.energy[0])
    c = total_angular_momentum(
        result.positions[0], result.velocities[0], result.masses
    )
    R = sundman_ratio(Imin, Imax, h, c)
    e_in = result.elements["e_in"]
    de = float(e_in[-1] - e_in[0])
    de_pred = delta_e_predicted(params)

    row.update({
        "Imax": Imax,
        "Imin": Imin,
        "R": R,
        "delta_e": de,
        "delta_e_pred": de_pred,
        "success": True,
        "message": "OK",
    })
    return row


def run_stat_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker entry point for ProcessPoolExecutor.

    Parameters
    ----------
    task : dict
        {
          "params": dict,
          "scanned_keys": list[str],
          "integrator": str,
          "dt": float,
          "n_output": int,
          "index": int,          # original order in the batch
        }

    Returns
    -------
    dict
        Statistic table row plus "_index" for optional ordering.
    """
    params = task["params"]
    scanned_keys = task["scanned_keys"]
    integrator = task["integrator"]
    dt = float(task["dt"])
    n_output = int(task["n_output"])
    index = int(task.get("index", 0))

    try:
        result = run_simulation(
            params,
            integrator=integrator,
            dt=dt,
            n_output=n_output,
            progress_cb=None,  # no per-step progress across processes
        )
        row = extract_stat_row(params, scanned_keys, result)
    except Exception as exc:  # noqa: BLE001 — surface any worker failure
        row = {k: params.get(k) for k in scanned_keys}
        row.update({
            "I_last_min": float("nan"),
            "L_in_0": float("nan"),
            "L_in_f": float("nan"),
            "E_0": float("nan"),
            "E_f": float("nan"),
            "delta_e": float("nan"),
            "success": False,
            "message": str(exc),
        })

    row["_index"] = index
    return row


def default_max_workers(requested: int | None = None) -> int:
    """
    Cross-platform default for pool size.
    Uses cpu_count()-1 (at least 1). Respects an explicit positive request.
    """
    import os
    cpu = os.cpu_count() or 1
    auto = max(1, cpu - 1) if cpu > 1 else 1
    if requested is None or requested <= 0:
        return auto
    return max(1, int(requested))
