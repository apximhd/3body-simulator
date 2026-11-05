Here is a comprehensive User Guide for the **3-Body AB+C Simulator**.

# 3-Body AB+C Simulator User Guide

## 1. Introduction
The **3-Body AB+C Simulator** is a desktop application designed to simulate hierarchical three-body systems consisting of an inner binary pair (Bodies A and B) and an outer body (Body C). It utilizes high-performance numerical integrators from the **REBOUND** library to calculate trajectories, orbital stability, and eccentricity changes over time.

This guide covers two distinct modes of operation:
1.  **Single Run:** Interactive simulation of a specific system configuration with real-time visualizations.
2.  **Statistic Run:** Batch parameter scanning to analyze how system stability changes across a range of initial conditions.

---

## 2. Getting Started

### 2.1 Installation
Ensure Python is installed on your system. Open a terminal in the project directory and set up a virtual environment:

```bash
python -m venv env
source env/bin/activate      # Linux/macOS
# OR
env\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 2.2 Launching the Application
Run the main entry script:
```bash
python main.py
```

The application will launch with default parameter values. The interface is divided into two main views accessible via the **Mode** menu (see Section 4).

---

## 3. Single Run Mode
This mode allows you to simulate a specific hierarchical system and visualize its evolution in real-time.

### 3.1 Parameter Configuration
In the left panel, enter or modify system parameters:
*   **Masses:** Mass of Body A (`M1`), Body B (`M2`), and Body C (`M3`). Units are Solar Masses ($M_{\odot}$).
*   **Orbital Elements (Inner Binary AB):** Semi-major axis `aAB`, eccentricity `eAB`, inclination `iAB`, longitude of ascending node `OmAB`, argument of periastron `omAB`, and mean anomaly `MAB`.
*   **Orbital Elements (Outer Body C):** Parameters relative to the inner binary center of mass (`Q`, `eAC`, `iAC`, `OmAC`, `omAC`, `MAC`).

### 3.2 Simulation Settings
*   **Integrator Method:** Select between **IAS15** (adaptive, high accuracy) and **WHFast** (symplectic, fast for long-term integration).
*   **dt (WHFast):** Time step for the WHFast integrator (default: `0.04`). *Ignored if using IAS15.*
*   **Output Points:** Number of data points to store and plot (default: `5000`).
*   **T_max:** Maximum simulation time in years.

### 3.3 Running the Simulation
1.  Click **▶ Run**. The progress bar will fill as the integration proceeds.
2.  The UI stays responsive during calculation.
3.  To interrupt early, click **■ Stop**.

### 3.4 Viewing Results
The right panel contains multiple tabs displaying different aspects of the simulation:
*   **I_total and e_in:** Time evolution of total inclination and inner eccentricity.
*   **XY Projection:** 2D projection of the orbits in the plane of the sky.
*   **Eccentricities:** Evolution of `e_in` (inner) and `e_out` (outer) eccentricities.
*   **Semi-major axes:** Evolution of orbital sizes.
*   **Inclinations:** Evolution of mutual inclinations.
*   **cos(i_mut) vs e_in:** Phase space plot useful for identifying Kozai-Lidov oscillations.
*   **3D trajectories:** Interactive 3D view of the system positions.
*   **3D trajectories (CM AB):** 3D view relative to the center of mass of the inner binary.
*   **Total Energy check:** Monitor conservation of energy to verify integration accuracy.
*   **Log:** Text log of simulation status and errors.

---

## 4. Statistic Run Mode
This mode is used for exploring parameter space, such as stability maps or distribution histograms.

### 4.1 Accessing Statistic Mode
Go to **Mode** > **2. Statistic run**. The interface will switch to the batch processing view.

### 4.2 Parameter Scanning
In the left panel (**StatisticParameterWidget**), you can define scan ranges:
1.  **Mark Parameters:** Check the ☑ box next to up to **two** parameters (e.g., `aAB` and `eAC`).
2.  **Set Range:** For each marked parameter, enter:
    *   **Start:** Starting value.
    *   **End:** Ending value.
    *   **Step:** Increment between values.
3.  The application calculates the total number of combinations (Start to End with Step).

*Note: If only one parameter is scanned, plots will show a 1D line graph. If two parameters are scanned, they generate a 2D surface/contour map.*

### 4.3 Integration Settings
Similar to Single Run mode, you can select the integrator (`IAS15`/`WHFast`), `dt`, output points, and `T_max`. Additionally:
*   **Extra Time (years):** If an instability condition is met (e.g., outer eccentricity $\ge$ 1), the simulation continues for this additional time before stopping.

### 4.4 Running Statistics
1.  Click **▶ Run**.
2.  A large batch warning may appear if the total number of simulations exceeds 200. Confirm to proceed.
3.  The progress bar shows completion status (e.g., `50/100`).
4.  **Parallel Processing:** Results are calculated in parallel using multiple CPU cores. You can set the number of workers (default: auto-detect).

### 4.5 Analyzing Results

#### Tab: Summary
*   **Configuration:** Displays the scanned ranges and fixed parameters.
*   **Results Table:** Shows statistics for key outcomes (`R` Sundman ratio, `delta_e_in`, etc.) including Min, Max, Sum, Average, Standard Deviation ($\sigma$), and Standard Error (SE).
*   **Histogram:** Visualizes the distribution of $\Delta e_{in}$ (change in inner eccentricity).
    *   Adjust **Bins** to change histogram granularity.
    *   Click **Export PDF** to save the plot for publications.

#### Tab: Table
A full data table of all simulation results. Each row represents one parameter combination. Columns include scanned parameters and outcomes like `Imax`, `Imin`, `stability_status`, etc. Colors indicate stability (green for stable, red for breakup).

#### Tab: Plots
Visual representations of the scanned parameters against specific outputs:
*   **Imax / Imin:** Maximum/Minimum inclination across the parameter space.
*   **R:** Sundman ratio distribution.
*   **$\Delta$e:** Change in inner eccentricity.

---

## 5. File Operations (Global)

These options are available in the **File** menu regardless of the current mode.

### 5.1 Save Configuration
Save current parameters to a YAML file.
*   **Menu:** `File` > `Save configuration…` (`Ctrl+S`)
*   Supports saving both Single Run and Statistic Run configurations.

### 5.2 Load Configuration
Load parameters from a previously saved YAML file.
*   **Menu:** `File` > `Open configuration…` (`Ctrl+O`)

### 5.3 Import/Export Statistics (Statistic Mode Only)
*   **Import CSV:** `File` > `Import statistic table (CSV)…`
    *   Reloads previous batch results for re-analysis or plotting without re-running simulations.
*   **Export CSV:** `File` > `Export statistic table (CSV)…`
    *   Saves the current results table to a `.csv` file for use in external tools like Python/Matplotlib or Excel.

### 5.4 Quit
Exit the application.
*   **Menu:** `File` > `Quit` (`Ctrl+Q`)

---

## 6. User Scenarios

### Scenario A: Simulating a Stable Hierarchical System
**Goal:** Verify that a specific three-body configuration remains stable over long timescales.

1.  Ensure you are in **Single Run** mode (**Mode** > **1. Single run**).
2.  Enter masses and orbital elements for bodies AB and C based on your research data.
3.  Select **IAS15** integrator for high accuracy.
4.  Set `T_max` to a large value (e.g., 10,000 years).
5.  Click **▶ Run**.
6.  Observe the **XY Projection** and **3D trajectories** tabs.
7.  Check the **Total Energy check** tab; energy should remain nearly constant if the system is stable and integrator accuracy is sufficient.

### Scenario B: Mapping Stability with Parameter Scans
**Goal:** Determine how varying the outer body's semi-major axis affects the inner binary's eccentricity variation.

1.  Switch to **Statistic Run** mode (**Mode** > **2. Statistic run**).
2.  In the parameter list, find `a_out` (or equivalent outer semi-major axis). Click the ☑ checkbox next to it.
3.  Set Start, End, and Step values (e.g., Start: 10 AU, End: 100 AU, Step: 5).
4.  Leave other parameters at their default or previously set values.
5.  Select **WHFast** integrator for faster processing of many runs.
6.  Click **▶ Run**. The software will execute hundreds of simulations in parallel.
7.  Go to the **Summary** tab to view the histogram of $\Delta e_{in}$.
8.  Switch to the **Table** tab to see detailed results for each `a_out` value.
9.  Use the plot tabs (e.g., **$\Delta$e**) to visualize the relationship between `a_out` and eccentricity changes.
10. Save your data via **File** > **Export statistic table (CSV)…**.

### Scenario C: Analyzing External Simulation Data
**Goal:** Visualize results from a previous batch run or external code.

1.  If in Single Run mode, switch to **Statistic Run** (**Mode** > **2. Statistic run**).
2.  Go to **File** > **Import statistic table (CSV)…**.
3.  Select the CSV file containing your previous results.
4.  The Table and Plots tabs will automatically populate with the imported data.
5.  You can adjust histogram bins or inspect the raw data in the Table tab.

---

## 7. Troubleshooting

*   **Slow Performance:** Statistic runs are parallelized. Ensure you have sufficient RAM. If using WHFast, keep `dt` small enough for accuracy but large enough for speed (default `0.04` is a good balance).
*   **Instability Errors:** If the simulation stops early with "Total break," it means bodies collided or ejected. This is expected in chaotic regimes; check the `stability_status` column in the Statistic Table.
*   **Energy Drift:** In Single Run mode, significant energy drift indicates either an unstable system or integrator parameters (like `dt` for WHFast) that are too coarse for the desired accuracy.

---

## 8. About
**Application:** 3-Body AB+C Simulator  
**Version:** Current Release  
**Framework:** Python + PyQt6 + REBOUND  

For more information on the underlying physics and integrators, refer to the REBOUND documentation or relevant astronomical literature on hierarchical three-body systems.