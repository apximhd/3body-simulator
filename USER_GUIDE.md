# 3-Body AB+C Simulator User Guide

## Overview

The **3-Body AB+C Simulator** is a cross-platform desktop application for simulating and analyzing hierarchical three-body systems. The model consists of:

- **Inner binary**: bodies A and B orbiting their common center of mass
- **Outer body**: body C orbiting the center of mass of the inner binary

The application uses REBOUND library with IAS15 (high-accuracy) or WHFast (fast) integrators, and provides interactive 3D visualization, projection views, and statistical analysis capabilities.

### System Requirements

- Python 3.8 or later
- 64-bit operating system (Windows, macOS, Linux)
- Minimum 4 GB RAM (8 GB+ recommended for statistical runs)
- OpenGL-capable graphics card recommended for 3D visualization

## Installation

### 1. Clone or locate the application

Ensure you have the application files in a directory (e.g., `3body_simulator/`).

### 2. Create and activate a virtual environment

**Linux / macOS:**
```bash
cd 3body_simulator
python -m venv env
source env/bin/activate
```

**Windows:**
```cmd
cd 3body_simulator
python -m venv env
.\env\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the application

```bash
python main.py
```

## Basic Operation

### Starting the Application

Run `python main.py` from the application directory. The main window will appear.

### Window Size

- On screens smaller than 1400×900 pixels, the window maximizes automatically
- On larger screens, the window opens at 1400×900 pixels position at (0, 0)

## User Interface Overview

The main window contains:

### Menu Bar

- **File** menu:
  - Open configuration...
  - Save configuration...
  - Import statistic table (CSV)...
  - Export statistic table (CSV)...
  - Quit

- **Mode** menu (critical — switches between run modes):
  - **1. Single run** — interactive plots for one simulation
  - **2. Statistic run** — parameter scan (batch processing)

- **Help** menu:
  - About

### Toolbar Areas (Tabs)

The interface is organized into several key areas:

1. **Parameters Panel** — Input system parameters (masses, orbital elements)
2. **Run Controls** — Execute simulations
3. **Plot Area** — Visualize results (3D trajectories, 2D projections, plots)
4. **Statistics Panel** (Statistic mode only) — Scan results table and histogram

## Parameter Input

### Single Run Mode Parameters

In Single run mode, you can input all system parameters:

#### Masses (M☉ — solar masses)
- **M₁ (mass_A)**: Mass of inner body A (default: 1.5)
- **M₂ (mass_B)**: Mass of inner body B (default: 0.5)
- **M₃ (mass_C)**: Mass of outer body C (default: 0.5, but see configs)

#### Inner Orbit AB
- **a_in (a_AB)**: Semi-major axis in AU (default: 1.0)
- **e_in (e_AB)**: Eccentricity (default: 0.6, range: 0–1 for ellipse)
- **i_in (i_AB)**: Inclination in degrees (default: 0.0)
- **Ω_in (Omega_AB)**: Longitude of ascending node in degrees (default: 0.0)
- **ω_in (omega_AB)**: Argument of periapsis in degrees (default: 60.0)
- **M_in (M_AB)**: Mean anomaly in degrees (default: 0.0)

#### Outer Orbit C
- **Q**: Periapsis distance as ratio to inner binary semi-major axis (q/a_in, default: 5.0)
- **e_out (e_AC)**: Outer orbit eccentricity (default: 0.5)
  - If e_AC < 1: Mean anomaly field appears (M_out)
  - If e_AC >= 1: Time field appears (t_out in years)
- **i_out (i_AC)**: Inclination in degrees (default: 140.0)
- **Ω_out (Omega_AC)**: Longitude of ascending node in degrees (default: 0.0)
- **ω_out (omega_AC)**: Argument of periapsis in degrees (default: 155.0)
- **M_out/t_out**: Mean anomaly (elliptic orbits) or time to periastron (parabolic/hyperbolic orbits)

### Statistic Run Mode Parameters

In Statistic mode, each parameter has a checkbox and range controls:

- **Check box**: Enable scanning for this parameter
- **Start / End / Step**: Define the range of values to scan
- **At most 2 parameters** can be scanned simultaneously
- Unchecked parameters keep their fixed value

**Scannable parameters include**: All masses, orbital elements, and Q factor.

### Parameter Groups

Parameters are organized into groups for clarity:

1. **Masses (M☉)**: mass_A, mass_B, mass_C
2. **Inner orbit AB**: a_AB, e_AB, i_AB, Omega_AB, omega_AB, M_AB
3. **Outer orbit C**: Q, e_AC, i_AC, Omega_AC, omega_AC, M_AC, t_AC

### AC Anomaly Switch

When e_AC >= 1 (parabolic or hyperbolic outer orbit), the interface automatically switches from showing Mean anomaly (M_out) to showing time to periastron (t_out in years).

## Run Modes

### Single Run Mode

**Purpose**: Run one simulation with the current parameters and visualize the results.

**Controls**:
- **Run** button: Execute the simulation
- **Stop**: (Optional) Stop a running simulation
- **Progress indicator**: Shows simulation progress

**Visualizations**:
- 3D trajectory plot (OpenGL if available, otherwise matplotlib fallback)
- XY projection
- e_in (inner eccentricity) vs time
- Moment of inertia vs time
- cos(i_mut) vs e_in (Kozai-Lidov phase plane)
- Energy conservation plot
- Body separations

**Output**: Results are displayed in real-time during and after the simulation.

### Statistic Run Mode

**Purpose**: Perform a parameter scan to explore how varying parameters affect system behavior.

**Configuration**:
1. Select parameters to scan (check their checkboxes)
2. Set Start, End, and Step values for each scanned parameter
3. **Maximum 2 parameters** can be scanned simultaneously
4. Click **Start** to begin the batch processing

**Batch Processing**:
- Uses `ProcessPoolExecutor` for parallel processing
- Default workers: `cpu_count - 1` (at least 1)
- Each parameter combination runs a full simulation
- Results are collected in a table

**Available Statistic Quantities**:
- **Imax**: Maximum moment of inertia
- **Imin**: Minimum moment of inertia
- **R**: Sundman ratio (chaos indicator)
- **δe (delta_e)**: Inner eccentricity change (final - initial)
- **δe_out**: Outer eccentricity change
- **δe_pred**: Predicted eccentricity change
- **Stability status**: "Stable" or breakup information
- **Internal breakup**: Whether inner eccentricity crossed threshold

**Results Table Columns**:
- Scanned parameter values
- I_last_min, L_in_0/f, E_0/f
- delta_e, delta_e_out
- success status, message

**Export**: Results can be exported to CSV format.

**Summary Tab**:
- Histogram of δe (inner eccentricity change)
- Adjustable number of bins
- Export PDF for publication-quality figures

## 3D Visualization

### Trajectory Views

The application provides multiple visualization options:

1. **3D Trajectory** (OpenGL preferred):
   - Interactive 3D view of orbital paths
   - Colored lines for bodies A, B, C
   - Grid and axis labels
   - Camera distance readout

2. **XY Projection**:
   - 2D projection of orbits in the x-y plane
   - Body labels (A, B, C)
   - Aspect ratio locked

3. **Matplotlib Fallback**:
   - Used when OpenGL is not available
   - 3D and 2D plots still functional

### Plot Controls

- **Zoom/pan**: Standard mouse interactions
- **Reset view**: Return to default perspective
- **Save images**: PNG or EPS format via toolbar buttons

## Configuration Management

### Loading/Saving Configurations

- **Open configuration**: Load a YAML file with system parameters
- **Save configuration**: Save current parameters to a YAML file
- **Default configuration**: The app ships with `configs/default.yaml`

### Configuration File Format (YAML)

Configuration files contain key-value pairs for all parameters. Example:

```yaml
mass_A: 1.5
mass_B: 0.5
mass_C: 0.5
a_AB: 1.0
e_AB: 0.6
i_AB: 0.0
Omega_AB: 0.0
omega_AB: 60.0
M_AB: 0.0
Q: 5.0
e_AC: 0.5
i_AC: 140.0
Omega_AC: 0.0
omega_AC: 155.0
M_AC: 0.0
t_AC: -50.0
t_max: 30000.0
t_delay: 50.0
```

### Pre-configured Configurations

The `configs/` directory contains several test configurations with varying parameters for quick exploration.

## Statistic Results Analysis

### Summary Histogram

The Summary tab displays a histogram of the inner eccentricity change (δe = e_in(final) - e_in(initial)):

- **Bins**: Adjustable parameter (default: 50)
- **Export PDF**: Save a vector figure with publication-style labels
- The histogram includes only successful runs without internal breakup
- Also works with imported CSV data

### Exporting Results

- **CSV export**: Export the full statistic table to comma-separated values
- **PDF export**: Export the summary histogram as a publication-quality vector figure
- **Diagram.py utility**: Command-line tool for plotting histograms from CSV files

**Diagram.py usage**:
```bash
# Plot histogram from results CSV
python diagram.py results.csv

# With custom bins and output file
python diagram.py results.csv --bins 100 --output histogram.png
```

## Troubleshooting

### Common Issues

1. **OpenGL not available**
   - The application falls back to matplotlib rendering
   - Some visual effects may be reduced

2. **Simulation takes too long**
   - Reduce t_max (integration time)
   - Reduce n_output (number of output points)
   - Use WHFast integrator for faster (but less accurate) results

3. **Statistical runs fail**
   - Check that at most 2 parameters are scanned simultaneously
   - Ensure valid numeric ranges (Start < End, Step > 0)
   - Some parameter combinations may lead to unstable systems (this is expected)

4. **Memory issues during statistical runs**
   - Reduce the number of workers
   - Reduce t_max or n_output
   - Close other applications to free memory

5. **"Internal breakup detected"**
   - This means the inner binary's eccentricity crossed a threshold
   - The simulation may have been terminated early
   - Check the stability_status column in results

### Need Help?

- Check the `README.md` file for quick start information
- View the `about` dialog in the application menu
- Ensure all dependencies are installed per `requirements.txt`

## Technical Notes

### Unit System

The application uses a natural unit system:
- **Mass**: Solar masses (M☉)
- **Length**: Astronomical units (AU)
- **Time**: 1 year = 2π (with G = 1, meaning Earth's angular frequency is 1 rad/year)

### Integrators

- **IAS15**: High-accuracy Radau integrator (default recommended)
- **WHFast**: Fast Whfast integrator for quicker runs

### Parallel Processing

Statistical runs use `ProcessPoolExecutor` with `spawn` start method (required for Windows and macOS with PyInstaller). Each worker process:
- Does not share Qt objects
- Returns plain Python dict results
- Uses multiprocessing.freeze_support() for PyInstaller builds

### Stability Detection

The application detects:
- **Orbital instability**: Outer orbit eccentricity >= 1 or semi-major axis <= 0
- **Internal breakup**: Inner binary eccentricity crosses threshold (1 - e_in_initial)

## Appendices

### Keyboard Shortcuts

- **F5**: Run simulation (Single mode)
- **Ctrl+O**: Open configuration
- **Ctrl+S**: Save configuration
- **Ctrl+I**: Import statistic table
- **Ctrl+E**: Export statistic table

### Frequently Asked Questions

**Q**: Can I run the app on a Mac with Apple Silicon?  
**A**: Yes, the application is universal and runs natively on Apple Silicon Macs.

**Q**: How do I cite this tool?  
**A**: Refer to it as "3-Body AB+C Simulator" with the version from the about dialog.

**Q**: Can I integrate this into my own Python code?  
**A**: Yes, the core modules (simulation, config, elements) can be imported and used independently.