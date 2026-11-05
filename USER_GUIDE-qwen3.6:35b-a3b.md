# User Guide: 3-Body AB+C Simulator

**Version:** 1.0  
**Platform:** Python + PyQt6 (Cross-platform)

## 1. Introduction

The **3-Body AB+C Simulator** is a desktop application designed for simulating hierarchical three-body systems. It models a system consisting of an inner binary pair (Bodies A and B) and an outer body (Body C). This tool is widely used in astrophysics to study orbital dynamics, stability, and chaotic evolution using high-precision numerical integrators.

### Key Features
*   **Dual Run Modes:**
    *   **Single Run:** Simulates a specific system configuration with interactive 2D/3D visualizations.
    *   **Statistic Run:** Performs batch parameter scans to analyze how orbital changes affect system stability across thousands of simulations.
*   **Advanced Integrators:** Uses the REBOUND library for high-accuracy (`IAS15`) and fast (`WHFast`) integration.
*   **Visualization:** 3D trajectory plots (OpenGL), 2D projections, eccentricity evolution, and energy conservation checks.
*   **Statistical Analysis:** Histograms of orbital changes (e.g., $\Delta e$), Sundman ratio calculations, and exportable CSV data.

---

## 2. Installation & Launch

### Requirements
*   Python 3.8+
*   Dependencies listed in `requirements.txt` (including `PyQt6`, `numpy`, `scipy`, `rebound`, `yaml`).

### Setup
1.  Open your terminal in the project directory.
2.  Create and activate a virtual environment:
    ```bash
    python -m venv env
    source env/bin/activate      # Linux/macOS
    # OR
    env\Scripts\activate         # Windows
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Launching the App
```bash
python main.py
```

---

## 3. System Parameters

The simulator uses a hierarchical configuration for two orbits: the **Inner Orbit** (A-B) and the **Outer Orbit** (C relative to A-B).

### 3.1 Units
*   **Mass:** Solar Masses ($M_\odot$)
*   **Length:** Astronomical Units (AU)
*   **Time:** Years (where $G=1$, $2\pi$ years $\approx$ period of Earth-like orbit in these units).

### 3.2 Parameter Fields
Parameters are grouped into three sections:

#### A. Masses ($M_\odot$)
*   **M₁ (Mass A):** Mass of inner body A.
*   **M₂ (Mass B):** Mass of inner body B.
*   **M₃ (Mass C):** Mass of the outer body C.

#### B. Inner Orbit AB
*   **a_in (AU):** Semi-major axis of the inner orbit.
*   **e_in:** Eccentricity of the inner orbit.
*   **i_in (°):** Inclination of the inner orbit.
*   **Ω_in (°):** Longitude of the ascending node of the inner orbit.
*   **ω_in (°):** Argument of periastron of the inner orbit.
*   **M_in (°):** Mean anomaly of the inner body at $t=0$.

#### C. Outer Orbit C
*   **Q:** Ratio of periapsis distance to semi-major axis ($q/a_{in}$). This determines the scale of the outer orbit's size relative to the inner one.
*   **e_out:** Eccentricity of the outer orbit.
    *   *Note:* If $e_{out} \ge 1$, the orbit is hyperbolic/parabolic. The input field switches from Mean Anomaly to Time ($t_{out}$).
*   **i_out (°):** Inclination of the outer orbit.
*   **Ω_out (°):** Longitude of the ascending node of the outer orbit.
*   **ω_out (°):** Argument of periastron of the outer orbit.
*   **M_out / t_out:**
    *   If $e_{out} < 1$: Input is **Mean Anomaly (°)** at $t=0$.
    *   If $e_{out} \ge 1$: Input is **Time to Periastron (years)**. This indicates how many years until body C reaches its closest approach to the AB center of mass.

### 3.3 Integration Settings
*   **Integrator Method:**
    *   `IAS15`: High-accuracy adaptive integrator. Best for detailed studies.
    *   `WHFast`: Fast symplectic integrator. Best for long-term stability checks.
*   **dt (WHFast):** Time step size for the WHFast integrator (default: 0.04). IAS15 ignores this but requires it in the UI.
*   **Output Points:** Number of data snapshots to save during the simulation (default: 2000–5000). Higher numbers provide smoother plots but use more memory.
*   **T<sub>max</sub> (Years):** Total duration of the simulation.
*   **Extra Time (years) / t<sub>delay</sub>:** If an instability is detected (e.g., body C escapes or collides), the simulator continues running for this additional time to record final states before stopping.

---

## 4. Mode 1: Single Run

Use this mode to simulate a specific scenario and observe its evolution in real-time.

### 4.1 Starting a Simulation
1.  Configure your parameters in the left panel.
2.  Click **▶ Run**.
3.  The progress bar will update as the integrator computes the trajectories.

### 4.2 Viewing Results
The right side of the window contains tabs displaying different aspects of the simulation:

*   **I<sub>total</sub> and e<sub>in</sub>:** Plots the moment of inertia (a measure of system spread) and inner eccentricity over time. Spikes in $I_{total}$ often indicate close encounters or instability.
*   **XY projection:** Top-down 2D view of the orbits.
*   **Eccentricities:** Shows $e_{in}$, $e_{out}$, and mutual inclination evolution.
*   **Semi-major axes:** Tracks changes in orbital size ($a_{in}$, $a_{out}$).
*   **Inclinations:** Tracks orbital tilts.
*   **3D trajectories (Matplotlib):** A basic 3D view of positions.
*   **3D trajectories (CM AB) [OpenGL]:** High-performance 3D visualization centered on the inner binary's center of mass. Use mouse to rotate/zoom.
*   **Total Energy:** Checks conservation of energy. In a stable isolated system, this line should be flat. Deviations indicate numerical errors or close encounters.
*   **Log:** Text output showing integration times, final eccentricities, and error messages.

### 4.3 Time Axis Options
In the **Time axis** section, you can switch between:
*   **Years:** Standard time units.
*   **Outer body revolutions:** Normalizes time based on the outer orbit's period. Useful for comparing resonant dynamics.

### 4.4 Managing Simulations
*   **■ Stop:** Halts the current simulation immediately.
*   **Save Configuration (Ctrl+S):** Saves current parameters to a `.yaml` file.
*   **Open Configuration (Ctrl+O):** Loads a previously saved `.yaml` file.

---

## 5. Mode 2: Statistic Run

Use this mode for parameter scans, stability analysis, and generating publication-ready histograms.

### 5.1 Switching Modes
Go to **Mode > 2. Statistic run** in the menu bar.

### 5.2 Setting Up Scans
In the Statistic mode, you can vary specific parameters while keeping others fixed.

1.  **Select Parameters:** Check the box (☑) next to a parameter you wish to scan (e.g., $e_{in}$ or $i_{out}$).
    *   *Constraint:* You can scan at most **two** parameters simultaneously.
2.  **Define Range:** Enter **Start**, **End**, and **Step** values for the scanned parameters.
3.  **Fixed Parameters:** Unchecked parameters remain fixed at their current value.

### 5.3 Running the Batch
1.  Click **▶ Run**.
2.  The app will open parallel worker processes (using `ProcessPoolExecutor`).
3.  **Workers:** Set to `0` (auto-detect CPU cores) or a specific number. More workers = faster execution but higher RAM/CPU usage.
4.  **Progress:** The status bar and progress bar show completed simulations vs. total planned runs.

### 5.4 Viewing Statistics

#### Summary Tab
Displays:
*   **Configuration:** A summary of the scanned ranges and fixed values.
*   **Results Table:** Statistics for key metrics:
    *   $R$ (Sundman Ratio): A measure of stability.
    *   $\Delta e_{in}$ (simulated): The change in inner eccentricity.
    *   Min/Max/Average/Std Dev statistics for the above.
*   **Histogram:** A visual distribution of $\Delta e_{in}$.
    *   Use **Bins** to adjust resolution.
    *   Click **Export PDF** to save a vector graphic of the histogram for papers/reports.

#### Table Tab
A detailed spreadsheet-like view of every simulation run.
*   Columns include scanned parameters, $I_{max}$, $I_{min}$, $R$, $\Delta e$, stability status, etc.
*   Rows are color-coded: **Red** indicates instability or breakup; **Green** indicates stable runs.

#### Plot Tabs (Imax, Imin, R, Δe)
Visualizes the scanned parameters against results:
*   **1D Plots:** If scanning 1 parameter, shows line plots of results vs. that parameter.
*   **2D Surface Plots:** If scanning 2 parameters, generates a heatmap/surface plot (e.g., Stability vs. $e_{in}$ and $i_{out}$).

### 5.5 Importing/Exporting Data
*   **Export CSV (File > Export):** Saves all simulation results to a CSV file. Useful for offline analysis or sharing data.
*   **Import CSV (File > Import):** Loads a previously exported CSV to re-generate plots and statistics within the app.

---

## 6. Interpreting Results

### Stability Criteria
*   **Sundman Ratio ($R$):** A higher ratio generally indicates a more stable system. $R \ge 1$ is often considered a necessary condition for stability in hierarchical systems.
*   **$\Delta e_{in}$:** The change in inner eccentricity. Large values indicate strong Kozai-Lidov oscillations or chaotic interactions.
*   **Breakup Messages:** If the "Stability Status" column says "Total break," it means body C escaped the system or collided with A/B within the simulation time.

### Energy Conservation
In Single Run mode, check the **Total Energy** plot. Drifting energy indicates that `dt` (for WHFast) is too large or numerical precision issues are affecting long-term integrations.

---

## 7. Histogram of Statistic Results

The **Summary** tab in Statistic Mode features a histogram of the inner eccentricity change ($\Delta e$).

1.  **View:** Displays the distribution of $\Delta e = e_{in}(final) - e_{in}(initial)$ for successful runs without internal breakup.
2.  **Bins:** Use the spinner to change bin count (default: 50).
3.  **Export PDF:** Saves a publication-quality vector figure.
4.  **CLI Histogram:** You can also plot histograms from the command line using the `diagram.py` script:

    ```bash
    # Plot histogram from CSV and open in window
    python diagram.py "results.csv"

    # Custom bins and output file
    python diagram.py "results.csv" --bins 100 --output histogram.png
    ```

    *   `--output` saves the image without opening a window.
    *   `nan` / `inf` values are automatically skipped with a warning.
    *   Only the `delta_e` column is retained in memory to save space.

---

## 8. Troubleshooting

*   **"Integration Error"**: Check your parameter inputs. Ensure masses are positive and orbital elements are physically reasonable.
*   **Slow Performance**: Reduce the number of "Output Points" in Single Run, or reduce the "Step" size/increase the range sparsity in Statistic Run. Use WHFast if you only need long-term integration accuracy.
*   **UI Freezing**: The app runs simulations in background threads. If a simulation hangs, use the **Stop** button. If the UI freezes entirely, force-close the application.
*   **Missing REBOUND**: If you see "REBOUND is not installed," ensure `pip install rebound` succeeded in your virtual environment.

---

## 9. Menu & Shortcuts Reference

| Action | Shortcut / Menu Location | Description |
| :--- | :--- | :--- |
| **Open Config** | `Ctrl+O` or `File > Open...` | Load a `.yaml` parameter file |
| **Save Config** | `Ctrl+S` or `File > Save...` | Export current parameters to `.yaml` |
| **Import CSV** | `File > Import statistic table` | Import results from previous runs |
| **Export CSV** | `File > Export statistic table` | Download results as a CSV file |
| **Quit** | `Ctrl+Q` or `File > Quit` | Close the application |
| **Single Run** | `Mode > 1. Single run` | Interactive simulation mode |
| **Statistic Run** | `Mode > 2. Statistic run` | Batch parameter scan mode |

---

## 10. File Structure Overview

```text
3body_simulator/
├── main.py                 # Entry point (launches UI)
├── diagram.py              # Standalone histogram plotting script
├── core/
│   ├── constants.py        # Physical unit definitions
│   ├── kepler.py           # Keplerian elements to Cartesian conversion
│   ├── simulation.py       # REBOUND IAS15/WHFast integration engine
│   ├── batch.py            # Parallel batch worker logic
│   └── config.py           # YAML loading/saving utilities
├── ui/
│   ├── main_window.py      # Main GUI window and tabs
│   ├── parameter_widget.py # Single run input fields
│   ├── statistic_parameter_widget.py # Statistic scan input fields
│   ├── plot_widget.py      # Matplotlib 2D plots
│   └── stat_plot_widget.py # Statistic mode 1D/3D plotting
├── configs/
│   └── default.yaml        # Example configuration file
└── results/                # Directory for exported CSV files
```

## 11. Acknowledgments & Roadmap

**Current Features:**
*   [x] Batch / Statistic mode (parameter scan)
*   [x] Export results (CSV)
*   [x] Hierarchical three-body integration

**Planned Features:**
*   [ ] GR corrections (1PN, 2.5PN) with on/off toggle
*   [ ] Standalone application build (PyInstaller)

---
*For further questions or to report bugs, please consult the repository documentation.*
