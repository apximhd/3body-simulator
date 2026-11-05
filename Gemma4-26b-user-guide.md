# User Manual: 3-Body AB+C Simulator

## 1. Introduction
The **3-Body AB+C Simulator** is a specialized tool for studying the dynamics of hierarchical three-body systems. It simulates a system consisting of an inner binary (bodies A and B) and an outer body (body C). 

The software is designed for both interactive single-run exploration and large-scale statistical parameter scans. It utilizes the high-precision **REBOUND** integration engine to provide accurate trajectories and orbital evolution data.

---

## 2. Physics and Units

The simulator uses a normalized unit system where $G=1$:
- **Mass**: Solar masses ($M_{\odot}$)
- **Length**: Astronomical Units (AU)
- **Time**: 1 Year = $2\pi$ (Earth's angular frequency)

### System Configuration
The system is defined by:
1. **Masses**: $m_A$, $m_B$, and $m_C$.
2. **Inner Orbit (AB)**: Semi-major axis ($a_{AB}$), eccentricity ($e_{AB}$), inclination ($i_{AB}$), longitude of ascending node ($\Omega_{AB}$), argument of periapsis ($\omega_{AB}$), and mean anomaly ($M_{AB}$).
3. **Outer Orbit (C relative to AB center-of-mass)**: Semi-major axis ($a_{AC}$ or periapsis distance $Q$), eccentricity ($e_{AC}$), inclination ($i_{AC}$), $\Omega_{AC}$, $\omega_{AC}$, and mean anomaly ($M_{AC}$) or time until periastron ($t_{AC}$).

---

## 3. Getting Started

### Installation
1. Ensure you have Python installed.
2. Clone the repository.
3. Create and activate a virtual environment:
   ```bash
   python -m venv env
   # Linux/macOS:
   source env/bin/activate
   # Windows:
   env\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Program
Execute the main script:
```bash
python main.py
```

---

## 4. Core Functionality

The application operates in two distinct modes, which can be switched via the **Mode** menu.

### 4.1 Single Run Mode (Interactive Exploration)
Used for studying a single, specific system setup.

**Workflow:**
1. **Input Parameters**: Use the left panel to adjust masses, orbital elements, and integration settings.
2. **Configure Integrator**:
   - **IAS15**: High-accuracy, adaptive-step integrator.
   - **WHFast**: High-speed, fixed-step integrator (best for near-circular, stable orbits).
3. **Run**: Click **▶ Run**. The progress bar indicates the simulation status.
4. **Explore Results**: Once complete, the right panel pop-up several tabs:
   - **I_total and e_in**: Evolution of total moment of inertia and inner eccentricity.
   - **XY projection**: 2D view of the bodies' trajectories in the orbital plane.
   - **Eccentricities**: Time series of $e_{in}$ and $e_{out}$.
   - **3D trajectories**: Interactive 3D visualization (one via standard OpenGL, one via CM-centered OpenGL).
   - **Log**: Detailed text output of the simulation results.

### 4.2 Statistic Run Mode (Parameter Scans)
Used for performing batch simulations over a range of parameters to find statistical trends.

**Workflow:**
1. **Define Scan**: In the **Statistic Parameter** panel, select up to **two** parameters to scan. Mark them with a checkbox ($\boxtimes$).
2. **Set Ranges**: For each selected parameter, provide a **Start**, **End**, and **Step** value.
3. **Configure Batch**: Set the integration method, time duration ($T_{max}$), and the number of parallel **Workers** (0 for auto).
4. **Run**: Click **▶ Run**. The simulation runs in parallel across multiple CPU cores.
5. **View Results**:
   - **Summary Tab**: Shows a histogram of $\Delta e_{in}$ (the change in inner eccentricity) and summary statistics (Mean, Min, Max, etc.).
   - **Table Tab**: A detailed list of every simulation run with its specific outcomes.

---

## 5. Data Management

### Configuration Files
- **Save**: Save your current parameter setup as a `.yaml` file via **File → Save configuration...**.
- **Load**: Load existing setups via **File → Open configuration...**.

### Exporting and Importing Statistics
- **Export Table**: Save your entire batch result as a `.csv` file via **File → Export statistic table (CSV)...**.
- **Import Table**: Load a previously exported CSV to visualize its statistics via **File → Import statistic table (CSV)...**.
- **Export Histogram**: Save the summary histogram as a publication-quality PDF via the **Export PDF** button in the Summary tab.

---

## 6. Technical Appendix

### Stability Criteria
A simulation is considered "unstable" (and may stop early) if the outer body's orbit becomes unbound:
- $e_{out} \ge 1.0$ (Parabolic/Hyperbolic transition)
- $a_{out} \le 0$

If "Stop on Instability" is enabled, the simulation will record the time of this event and continue for a specified **Extra Time ($t_{delay}$)** to capture the subsequent motion.

### Plotting Details
- **Time Axis**: Plots can be viewed in either **Years** or **Outer Body Revolutions**.
- **Delta e Prediction**: In Statistic Mode, the software can compare the simulated $\Delta e_{in}$ against a theoretical prediction based on the formula:
  $$\Delta e \sim 0.3 \cdot \frac{m_C}{m_A + m_B} \cdot \left(\frac{Q}{2}\right)^{-4} \cdot (1 + \cos i_{AC})^2$$