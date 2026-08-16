# 3-Body AB+C Simulator

Hierarchical three-body system (inner binary AB + outer body C).  
**Python + PyQt6**.

## Features (current version)

- Input of all system parameters (masses, orbital elements)
- Load / save configurations in YAML
- Integrators: **REBOUND** IAS15 (high accuracy) and WHFast (fast)
- 3D trajectories (OpenGL)
- XY projection, body separations, energy conservation
- Background thread execution (UI stays responsive)
- **Two run modes** (menu *Mode*):
  1. **Single run** — interactive plots
  2. **Statistic run** — parameter scan (☑ → Start/End/Step), parallel batch via
     `ProcessPoolExecutor` (`spawn`, Windows/macOS/Linux), results table
     (`I_last_min`, `L_in_0/f`, `E_0/f`, `delta_e`). Export to CSV.
     Field **Workers (0=auto)** sets the process pool size.

## Installation

```bash
cd 3body_simulator
python -m venv env
  source env/bin/activate      # Linux/macOS
  env\Scripts\activate         # Windows

pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Structure

```
3body_simulator/
├── main.py                 # entry point
├── core/
│   ├── constants.py        # unit definitions
│   ├── kepler.py           # elements → Cartesian coordinates
│   ├── simulation.py       # integrators
│   ├── batch.py            # parallel statistic worker
│   └── config.py           # load/save YAML
├── ui/
│   ├── main_window.py
│   ├── parameter_widget.py
│   ├── statistic_parameter_widget.py
│   └── plot_widget.py
├── configs/
│   └── default.yaml
└── results/
```

## Unit system

- Mass — M☉  
- Length — AU  
- Time — 1 year = 2π (G = 1)

## Roadmap

- [ ] GR corrections (1PN, 2.5PN) with on/off toggle
- [x] Batch / statistic mode (parameter scan)
- [x] Export results (CSV)
- [ ] Standalone application build (PyInstaller)
