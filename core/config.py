"""
Load and save system configurations.
Format: YAML.
"""

from __future__ import annotations
import yaml
from pathlib import Path
from typing import Dict, Any


DEFAULT_PARAMS = {
    # Masses
    "mass_A": 1.5,
    "mass_B": 0.5,
    "mass_C": 0.5,

    # Inner orbit AB
    "a_AB": 1.0,          # AU
    "e_AB": 0.6,
    "i_AB": 0.0,          # deg
    "Omega_AB": 0.0,      # deg
    "omega_AB": 60.0,     # deg  (PeriArg)
    "M_AB": 0.0,          # deg  (mean anomaly)

    # Outer orbit C
    "Q": 5.0,             # periapsis / a_AB
    "e_AC": 0.5,
    "i_AC": 140.0,        # deg
    "Omega_AC": 0.0,
    "omega_AC": 155.0,
    "M_AC": 0.0,          # deg  (mean anomaly, used when e_AC < 1)
    "t_AC": 0.0,          # years (time until periastron, used when e_AC >= 1)

    # Integration
    "t_max": 30000.0,     # years
}


_DEFAULT_YAML = Path(__file__).resolve().parent.parent / 'configs' / 'default.yaml'


def get_default_params() -> Dict[str, Any]:
    if _DEFAULT_YAML.exists():
        return load_config(_DEFAULT_YAML)
    return DEFAULT_PARAMS.copy()


def save_config(params: Dict[str, Any], filepath: str | Path) -> None:
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(params, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_config(filepath: str | Path) -> Dict[str, Any]:
    filepath = Path(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    result = DEFAULT_PARAMS.copy()
    if data:
        result.update(data)
    if not data or "t_AC" not in data:
        result["t_AC"] = -float(result["t_max"]) / 2.0
    return result
