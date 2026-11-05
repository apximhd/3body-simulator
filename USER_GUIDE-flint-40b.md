# 3-Body AB+C Simulator — User Guide

This guide explains how to use the 3-Body AB+C Simulator: how to enter a
hierarchical three-body system, run a single integration, run a parameter
scan, inspect and export the results, and plot a histogram from exported data.

For a short project overview and developer structure, see [README.md](README.md).

---

## 1. Contents

1. [Concepts](#2-concepts)
2. [Installation and starting the program](#3-installation-and-starting-the-program)
3. [The main window](#4-the-main-window)
4. [Entering system parameters](#5-entering-system-parameters)
5. [Integrator and time settings](#6-integrator-and-time-settings)
6. [Single run mode](#7-single-run-mode)
7. [Statistic run mode](#8-statistic-run-mode)
8. [Configuration files (YAML)](#9-configuration-files-yaml)
9. [Importing and exporting statistic tables (CSV)](#10-importing-and-exporting-statistic-tables-csv)
10. [Histogram of `delta_e`](#11-histogram-of-delta_e)
11. [Output reference](#12-output-reference)
12. [Troubleshooting](#13-troubleshooting)

---

## 2. Concepts

The simulator models a **hierarchical system**: an inner binary **AB**
(bodies A and B) and an outer body **C** orbiting the binary's centre of mass.

| Symbol | Meaning |
|--------|---------|
| M₁, M₂ | Masses of the inner binary bodies A and B (M☉) |
| M₃ | Mass of the outer body C (M☉) |
| a_in, e_in, i_in, Ω_in, ω_in, M_in | Inner orbit AB (semi-major axis, eccentricity, inclination, node, argument of periapsis, mean anomaly) |
| Q | Outer periapsis divided by a_in (q / a_in) |
| e_out, i_out, Ω_out, ω_out | Outer orbit C |
| M_out | Mean anomaly of the outer orbit (used when e_out < 1) |
| t_out | Time until the outer body passes periapsis (used when e_out ≥ 1) |

**Units**

- Mass — solar masses (M☉)
- Length — astronomical units (AU)
- Time — years, where 1 year = 2π in internal units (G = 1)
- Angles — degrees in the interface and in configuration files

**Key quantities reported**

- **e_in** — inner eccentricity. Its change over the run is the central
  result: `delta_e = e_in(final) − e_in(initial)`.
- **cos(i_mut)** — cosine of the mutual inclination between the inner and
  outer orbits. The main plot in single-run mode is *cos(i_mut) vs e_in*
  (Kozai–Lidov dynamics).
- **Instability** — the run is treated as unstable when the outer orbit becomes
  unbound (`e_out ≥ 1`) or `a_out ≤ 0`. In statistic runs, integration stops
  shortly after this (see *Extra Time* below).
- **Internal breakup** — the inner binary is considered broken when
  `e_in` rises above `1 − e_AB` (its initial value).

---

## 3. Installation and starting the program

Requirements are listed in `requirements.txt`: PyQt6, numpy, pyqtgraph,
PyOpenGL, PyYAML, matplotlib, rebound (< 5.1.0), pandas, scipy.

```bash
cd 3body-simulator
python -m venv env
source env/bin/activate        # Linux/macOS
env\Scripts\activate           # Windows

pip install -r requirements.txt
python main.py
```

The window opens maximised on small screens, or at 1400 × 900 otherwise.

---

## 4. The main window

**Menu bar**

| Menu | Item | Purpose |
|------|------|---------|
| File | Open configuration… (Ctrl+O) | Load parameters from a YAML file |
| File | Save configuration… (Ctrl+S) | Save current parameters to a YAML file |
| File | Import statistic table (CSV)… | Load an exported statistic table |
| File | Export statistic table (CSV)… | Save the current statistic table |
| File | Quit (Ctrl+Q) | Exit |
| Mode | 1. Single run | Interactive single-system mode |
| Mode | 2. Statistic run | Parameter-scan mode |
| Help | About | Program information |

The **Mode** menu is the only way to switch modes. Mode switching is blocked
while a run is in progress; stop the run first.

**Layout**

- **Single run:** parameter panel on the left; result tabs on the right.
- **Statistic run:** scan-parameter panel and run controls on the left
  (fixed width); Summary, Table and plot tabs on the right.

The status bar at the bottom shows progress and the last action.

---

## 5. Entering system parameters

Parameters are grouped in the left panel. Each field accepts decimal numbers,
including scientific notation (for example `1e-3`). Invalid input is rejected
by the field validator.

**Masses (M☉):** M₁, M₂, M₃.

**Inner orbit AB:** a_in (AU), e_in, i_in (°), Ω_in (°), ω_in (°), M_in (°).

**Outer orbit C:** Q (q / a_in), e_out, i_out (°), Ω_out (°), ω_out (°), and
one anomaly field:

- If **e_out < 1** (elliptic), the field is **M_out (°)**.
- If **e_out ≥ 1** (parabolic/hyperbolic), the field changes to **t_out (y)**.
  Its default is set automatically to `−T_max / 2` whenever T_max is edited or
  e_out is changed to a value ≥ 1.

The default configuration (`configs/default.yaml`) is loaded at startup:
M₁ = 1.5, M₂ = 0.5, M₃ = 0.5, a_in = 1.0 AU, e_in = 0.6, i_out = 140°,
ω_out = 155°, Q = 5.0.

---

## 6. Integrator and time settings

Both modes have an **Integrator** group:

| Setting | Description |
|---------|-------------|
| Method | **IAS15 (high accuracy)** — adaptive, slower, best energy conservation. **WHFast (fast)** — faster, uses fixed step *dt*. |
| dt (WHFast) | Time step for WHFast, in internal time units (default `0.04`). Ignored by IAS15. |
| Output points | Number of output samples stored along the run (default `5000`). |
| T<sub>max</sub> (years) | Maximum integration time (default `30000`). |

**Time axis** (single-run mode only) switches plot time between:

- **Years**
- **Outer body revolutions** — time divided by the outer orbital period.

Changing this option redraws the existing results without re-running.

---

## 7. Single run mode

Use single-run mode to study one system in detail.

1. Enter the system parameters (section 5) and integrator settings (section 6).
2. Click **▶ Run**. Progress is shown in the bar and percentage label.
3. Click **■ Stop** to cancel. The run is terminated and progress is reset.

When the run finishes, the right-hand tabs are filled:

| Tab | Content |
|-----|---------|
| I_total and e_in | Total moment of inertia and inner eccentricity over time |
| XY projection | Orbit projected onto the XY plane |
| Eccentricities | e_in and e_out over time |
| Semi-major axes | a_in and a_out over time |
| Inclinations | Inner, outer and mutual inclinations over time |
| cos(i_mut) vs e_in | Kozai–Lidov phase-space plot |
| 3D trajectories | 3D orbit plot (matplotlib) |
| 3D trajectories (CM AB) | 3D orbit plot in the centre-of-mass frame of AB (OpenGL) |
| Total Energy check | Total energy over time, for checking conservation |
| Log | Text log: run settings, initial and final values, errors |

The **Log** tab records the initial and final values of energy, e_in, e_out,
I_mut and cos(i_mut) for each run.

---

## 8. Statistic run mode

Use statistic mode to scan one or two parameters across a range and collect
results for every combination.

### 8.1 Choosing parameters to scan

Each scannable parameter has a checkbox ☑ on the left:

- **Unchecked:** the parameter keeps one fixed value (the field on the right).
- **Checked:** three fields appear — **Start**, **End**, **Step**. The values
  are generated inclusively from Start to End. Start and End must differ.

Rules:

- At most **two** parameters can be scanned at once. A third checkbox is
  unchecked automatically.
- Scanning is possible for all masses, the inner orbit parameters, the outer
  orbit parameters and t_out. T_max is always fixed.
- When e_out is scanned and its range reaches ≥ 1, the outer anomaly row
  switches to t_out, as in single-run mode.

### 8.2 Run settings

| Setting | Description |
|---------|-------------|
| Integrator, dt, Output points | Same as single-run mode (section 6) |
| T<sub>max</sub> (years) | Integration time for every run in the batch |
| Extra Time (years) | After an instability is detected (`e_out ≥ 1` or `a_out ≤ 0`), the simulation keeps running for this extra time before stopping. Default `1000`. |
| Workers (0=auto) | Size of the parallel process pool. `0` uses *CPU cores − 1* (minimum 1). `1` runs sequentially. |

### 8.3 Starting a batch

1. Check one or two parameters and set Start / End / Step.
2. Set the other fields and run settings.
3. Click **▶ Run**.

The program warns you if:

- nothing is scanned (*Nothing to scan*),
- more than two parameters are scanned,
- the combination count is 1 (*Only one combination*),
- more than **200** combinations are requested. You are asked to confirm.

While the batch runs, the progress label shows elapsed time and an estimate
of time remaining. Rows fill the **Table** tab as each run completes, in their
original order. Click **■ Stop** to cancel: queued runs are cancelled and
already-running ones finish, after which the table keeps what was computed.

### 8.4 Results tabs

**Summary**

- **Configuration** — the t_max, t_delay, and every parameter value or scan range.
- **Results** — a table with Min, Max, Σ (cumulative), x̄ (average),
  σ (standard deviation) and SE (standard error) for each result quantity,
  computed over successful runs *without* internal breakup.
- **Histogram** — distribution of `delta_e`. Use **Bins** (default 50) to change
  the bin count and **Export PDF** to save a publication-style vector figure.

**Table**

One row per run. Columns are the scanned parameters followed by the results
(see section 12). Rows are coloured:

- **Red** — failed run, or internal breakup occurred.
- **Green** — stable (`Stable at …`).

**Imax, Imin, R, Δe**

Plots of the result quantities against the scanned parameter(s):

- **One scanned parameter:** 2D curve.
- **Two scanned parameters:** 3D surface (or overlay plot for Δe).

Each plot can be saved as PNG or EPS with the buttons under the plot.

---

## 9. Configuration files (YAML)

Use **File → Save configuration…** to store the current parameters, and
**File → Open configuration…** to load them. The dialogs start in the
`configs/` folder.

- Saved files contain every physical parameter plus `t_max` and `t_delay`.
- In statistic mode the saved file contains the *fixed* values from the
  parameter panel. Scan ranges are not saved.
- Missing keys in a loaded file are filled from the built-in defaults.

Example:

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
t_AC: 0.0
t_max: 30000.0
t_delay: 50.0
```

Several example configurations are included in `configs/`.

---

## 10. Importing and exporting statistic tables (CSV)

**Export statistic table (CSV)…** saves the current Table. The default
filename encodes the scan settings, for example
`M1=1.5_M2=0.5_M3=0.5_aAB=1_..._Q=5_eAC=0.1-0.9-0.1_....csv`, and the dialog
starts in the `results/` folder.

**Import statistic table (CSV)…** loads a file exported by this program. The
table, summary, and plots are rebuilt from the file. Import works without
running a simulation, so it is useful for comparing or re-plotting earlier
results. At most two leading parameter columns are treated as scanned.

---

## 11. Histogram of `delta_e`

The **Summary** tab shows the histogram. You can also plot it from the command
line, from an exported CSV:

```bash
python diagram.py "results.csv"
python diagram.py "results.csv" --bins 100 --output histogram.png
```

- Without `--output`, the histogram opens in a window (default 50 bins).
- With `--output`, the image is saved and no window opens.
- Empty and non-finite (`nan`, `inf`) values are skipped with a warning.
- A missing `delta_e` column or an invalid number is reported as an error.

---

## 12. Output reference

**Statistic table columns**

| Column | Meaning |
|--------|---------|
| *scanned parameters* | Values of the scanned parameters for that run |
| Imax, Imin | Extremal moments of inertia over the run |
| R | Sundman-type ratio computed from I_min, I_max, the energy and the angular momentum |
| delta_e | Change in inner eccentricity: `e_in(final) − e_in(initial)` |
| delta_e_out | Change in outer eccentricity |
| e_out_last | Final outer eccentricity |
| a_out_last | Final outer semi-major axis |
| a_in_last/a_in_init | Final inner semi-major axis divided by its initial value |
| stability_status | Text outcome: `Stable at T_max: … years (… revs)`, `Break at: … years (… revs)` (outer instability), or `Total break at: … years (… revs)` (internal breakup) |

Failed runs keep their scanned values and show `nan` in result columns, with
the error text in `stability_status`.

---

## 13. Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| *Integration error* or *Error* dialog | Check the Log tab for details. Ensure the parameters are physical (positive masses, 0 ≤ e < 1 for the inner orbit). |
| *Stop the current run first* on mode switch | A run is in progress. Click **■ Stop**. |
| *Nothing to scan* | No ☑ checkbox is set. Check one or two parameters. |
| *Only one combination generated* | Start equals End, or Step is too large for the range. |
| Many NaN rows in the table | Some runs failed. Check the `stability_status` column for the message. |
| The batch is slow | Increase **Workers** up to your CPU core count, reduce **Output points**, or reduce **T<sub>max</sub>**. |
| `diagram.py` reports *CSV must contain a 'delta_e' column* | The file is not a statistic export. Use a CSV that includes `delta_e`. |
| Decimal values rejected | Use `.` as the decimal separator. |
