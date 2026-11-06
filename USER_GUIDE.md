# User Guide: 3-Body AB+C Simulator

This guide covers the simulator after it has started. It explains how to set up a system, run and inspect a simulation, scan parameters, and interpret the outputs. It does not cover installation or launch procedures.

## 1. What the simulator does

The application models three gravitating point masses arranged as an inner binary, A and B, plus an outer body, C. You specify the initial system with masses and orbital elements. The program converts those elements into positions and velocities, then numerically integrates the full three-body equations of motion. The plots show how the orbits and their osculating elements evolve.

The simulator is useful for exploring orbital evolution, mutual inclination and eccentricity changes, possible loss of a bound outer orbit, and sensitivity to selected initial parameters. It offers two complementary workflows:

- **Single run** follows one initial configuration and provides time histories and trajectories.
- **Statistic run** repeats the integration over a one- or two-parameter grid and compares a set of summary quantities across runs.

The model is Newtonian: it does not include relativistic corrections, physical body radii, tides, or other non-gravitational effects. The bodies are treated as point masses. A numerically successful run is not, by itself, evidence that the chosen physical model is appropriate for a real system.

## 2. Main window and common controls

Choose **Mode → 1. Single run** or **Mode → 2. Statistic run**. Each mode has its own parameter fields and integration controls. A running job must be stopped before switching modes.

The **File** menu provides:

- **Open configuration…** loads a YAML parameter configuration into the interface.
- **Save configuration…** saves the current parameter values. In Statistic mode, scanned parameters are saved using their start value as the base value; scan ranges themselves are not a substitute for exporting the result table.
- **Import statistic table (CSV)…** loads a previous statistic table into the table, plots, and summary.
- **Export statistic table (CSV)…** saves completed statistic rows. It is not an exporter for single-run trajectories.

Masses are in solar masses ($M_\odot$), distances in astronomical units (AU), and angles in degrees. The simulation uses units with $G=1$; one year corresponds to $2\pi$ internal time units. The `T_max` fields are in years. `dt (WHFast)` is the fixed integration step in the integrator's internal time units; it is not the number of saved output points.

## 3. Initial conditions and parameter fields

The inputs describe two osculating Keplerian orbits at the start of the calculation.

### Masses

- **M1**: mass of body A.
- **M2**: mass of body B.
- **M3**: mass of the outer body C.

### Inner orbit AB

- **a_in (AU)**: inner semi-major axis.
- **e_in**: inner eccentricity.
- **i_in (°)**: inclination of the inner orbital plane to the reference plane.
- **Ω_in (°)**: longitude of the ascending node.
- **ω_in (°)**: argument of periapsis.
- **M_in (°)**: mean anomaly at the initial epoch; it sets the orbital phase for an elliptical orbit.

### Outer orbit C

The outer orbit is specified relative to the centre of mass of AB.

- **Q (q / a_in)**: outer periapsis distance divided by the inner semi-major axis. Thus $q_{out}=Q\,a_{in}$.
- **e_out**: outer eccentricity.
- **i_out, Ω_out, ω_out (°)**: outer inclination, longitude of ascending node, and argument of periapsis.
- **M_out (°)**: mean anomaly at the initial epoch for an elliptical outer orbit ($e_{out}<1$).
- **t_out (y)**: time parameter used to set C's initial phase for a parabolic or hyperbolic outer orbit ($e_{out}\ge1$). The interface switches between `M_out` and `t_out` based on eccentricity. For scans that cross $e_{out}=1$, verify that the selected phase parameter is meaningful for both orbit types.

For an ellipse, the code derives the outer semi-major axis from $q_{out}$ and eccentricity. For a hyperbola it uses a negative semi-major axis internally; for a parabola it uses the periapsis-based parabolic formulation. Make sure `Q`, masses, semi-major axis, and eccentricities describe a physically meaningful initial orbit. Input widgets accept numeric values but do not replace scientific validation of the configuration.

## 4. Choosing an integrator

Both methods are provided by REBOUND and integrate the interacting three-body system.

### IAS15 (high accuracy)

IAS15 is an adaptive, high-order integrator. It adjusts its internal step to resolve the dynamics and is generally the safer first choice for eccentric orbits, close approaches, and exploratory runs where the required resolution is not known in advance.

**Advantages:** adaptive error control; handles a broad range of dynamical timescales; no fixed `dt` tuning is required.

**Trade-offs:** can be slower, particularly for long runs or large scans; accuracy still depends on the system and requested computation, so conservation plots should be inspected.

### WHFast (fast)

WHFast is a fixed-step symplectic method designed for efficient long-term integration of suitable gravitational systems. Its `dt` is used as the integration step; choose it small enough to resolve the shortest important orbital timescale and any close encounter.

**Advantages:** often faster for long integrations of well-separated, near-Keplerian orbits; symplectic structure can give favorable long-term energy behavior when the step is appropriate.

**Trade-offs:** accuracy and stability depend strongly on `dt`; large steps can miss rapid encounters or distort eccentric motion. A good energy trace does not guarantee that every orbital feature is resolved. For difficult or close-encounter cases, compare against IAS15 and repeat WHFast with a smaller step.

A practical approach is to validate a representative case with IAS15, then test WHFast step-size convergence before using it for a large batch. The `Output points` setting controls recorded snapshots, not WHFast's integration step and not IAS15's adaptive step.

## 5. Workflow A: one detailed simulation

1. Select **Mode → 1. Single run**.
2. Enter or load masses and orbital elements. Start from the provided values or a saved configuration, then change only the parameters needed for the experiment.
3. Choose an integrator. For IAS15, `dt (WHFast)` is ignored. For WHFast, set `dt` deliberately.
4. Set **Output points** to control how many trajectory snapshots are stored and plotted. More points can make curves more detailed but require more memory and plotting work. They do not force the integrator to take more physics steps.
5. Set **T_max (years)**, the final simulated time.
6. Select the time axis: **Years** or **Outer body revolutions**. This changes plot axes only; it does not change the integration.
7. Press **Run** and monitor progress. **Stop** terminates the current single run; an interrupted run does not produce a completed result set.
8. Review the plots and the **Log** tab. The log reports runtime, recorded steps, initial/final energy, inner and outer eccentricity, and mutual inclination.

### Single-run tabs

- **I_total and e_in**: inner eccentricity and total moment of inertia $I(t)$, plotted against time. The moment of inertia is computed about the system centre of mass.
- **XY projection**: projected paths of A, B, and C in the system centre-of-mass frame, with distance in AU.
- **Eccentricities**: $e_{in}(t)$ and $e_{out}(t)$.
- **Semi-major axes**: $a_{in}(t)$ and $a_{out}(t)$ in AU. A non-positive outer semi-major axis corresponds to an unbound osculating outer orbit.
- **Inclinations**: cosine of mutual inclination and mutual inclination in degrees. Mutual inclination is the angle between the two orbital angular-momentum vectors.
- **cos(i_mut) vs e_in**: the phase-plane trajectory, useful for examining coupled eccentricity/inclination evolution, including Kozai-Lidov-like behavior.
- **3D trajectories**: 3D paths in the standard view.
- **3D trajectories (CM AB)**: an interactive OpenGL view plotted relative to the AB centre of mass when OpenGL is available. If OpenGL is unavailable, the application provides a 2D fallback. The displayed curve may be interpolated between recorded samples to look smooth; that rendering interpolation does not add simulated physics data.
- **Total Energy check**: total energy and relative change $\Delta E/E_0$. Energy drift is a useful numerical diagnostic, not a complete accuracy test.
- **Log**: text summary of the completed run or an error.

## 6. Workflow B: parameter scan

Statistic mode runs a grid of independent simulations. It is intended for sensitivity studies and parameter surveys rather than detailed inspection of a single trajectory.

1. Select **Mode → 2. Statistic run**.
2. For each parameter to vary, check its box and enter **Start**, **End**, and **Step**. Leave other parameters unchecked; their fixed values apply to every simulation.
3. Scan no more than two parameters at once. The interface enforces this limit. A third checked parameter is rejected.
4. Choose the grid carefully. The number of simulations is the product of the number of values in each scanned range. For example, 21 values for one parameter and 11 for another produce 231 runs. The range is inclusive; if the step does not land exactly on the end, the end may be added as a final value. The step must point from Start toward End. A zero step is treated as a single value, so it is not useful for a scan.
5. Set the integrator, `dt (WHFast)` if applicable, `Output points`, and `T_max (years)` as for a single run.
6. Set **Extra Time (years)**. In statistic mode, the application monitors initially bound outer orbits for the osculating unbound condition ($e_{out}\ge1$ or $a_{out}\le0$). If detected, it can continue integrating for this additional interval before finalizing the row. This is a batch-mode monitoring feature; the ordinary single-run workflow integrates to `T_max` unless stopped manually.
7. Set **Workers (0=auto)**. `0` chooses an automatic process count based on available CPU cores; `1` runs with one worker. More workers may reduce elapsed time, but compete for memory and CPU. Start conservatively on a machine with limited resources.
8. Press **Run**. For more than 200 combinations, the application asks for confirmation. Progress shows completed runs and an approximate remaining time. **Stop** requests cancellation; completed rows remain available and can be exported.

The grid combinations are Cartesian products: every selected value of one parameter is paired with every selected value of the other. A scan is not random sampling. For reproducible comparisons, record the fixed parameters, scanned ranges, integrator, time horizon, and WHFast step (if used) along with the CSV.

### Statistic tabs and columns

- **Summary** displays the current statistic-mode configuration, summary statistics, and a histogram of $\Delta e_{in}$. Adjust **Bins** to change histogram resolution; **Export PDF** saves the histogram.
- **Table** lists each scanned parameter combination with its calculated outputs. Rows are ordered by scan combination even when parallel runs finish out of order.
- **Imax**, **Imin**, **R**, and **Δe** plot one-dimensional results for one scanned parameter or a surface for two. Use **Save PNG** or **Save EPS** on a plot tab to export that figure. Two-parameter surfaces are interpolated to make the rendering smoother; the underlying results are only the sampled grid points.

The result columns are:

- **Imax** and **Imin**: extrema associated with the system moment-of-inertia history. The calculation smooths over the inner orbital period to identify the slow envelope, then estimates extrema from the recorded series. These are derived summary values, not direct measurements of a single body's orbit.
- **R**: the Sundman ratio $R=(2|h|)^2 I_{min}I_{max}/c^4$, where $h$ is total energy and $c$ is the magnitude of total angular momentum. The cited criterion requires $R\ge1$; interpret it in the context of its assumptions and the finite numerical time series rather than as a standalone stability classifier.
- **delta_e**: simulated change in inner eccentricity, $e_{in}(final)-e_{in}(initial)$.
- **delta_e_out**: change in outer eccentricity over the simulated interval.
- **e_out_last**, **a_out_last**: final sampled osculating outer eccentricity and semi-major axis.
- **a_in_last/a_in_init**: ratio of final sampled to initial inner semi-major axis.
- **stability_status**: a status message such as `Stable at T_max`, an outer-orbit break time, or an inner-system breakup indication.

The **Δe** statistic plot currently shows the simulated change only; it does not overlay the theoretical prediction. Summary statistics and the histogram use successful finite results and exclude rows marked as internal breakup. The table and CSV can still contain those rows, so check the status column before interpreting aggregate plots.

## 7. Importing and exporting results

Use **File → Export statistic table (CSV)…** to save completed statistic rows. The CSV contains the scanned parameter columns and result columns. Export is useful for external analysis and for preserving a batch independently of the current session.

Use **File → Import statistic table (CSV)…** to review prior data without rerunning it. Imported data is shown in statistic plots and the summary. At most the first two non-result columns are treated as scanned parameters for plotting. The summary configuration panel reflects the parameters currently entered in the application; it is not guaranteed to reconstruct the original full configuration from an arbitrary CSV. Keep the original scan settings with the exported file when provenance matters.

The histogram can be saved as PDF from **Summary**. Statistic quantity plots can be saved as PNG or EPS from their own tabs. The application does not currently provide a single-run trajectory or plot export workflow through the File menu.

## 8. Suggested scenarios

### Inspect a known configuration

Load a configuration, use IAS15, choose a manageable `T_max`, and run once. Check `Total Energy check` and compare the eccentricity, semi-major-axis, and inclination histories. Increase the time horizon only after the initial behavior looks plausible.

### Test numerical sensitivity

Run the same setup with IAS15 and WHFast. For WHFast, repeat with progressively smaller `dt`. Compare eccentricity changes, encounter timing, and energy behavior. If the qualitative result changes materially with the step, the coarser WHFast run is not adequately resolved.

### Map dependence on one orbital parameter

In Statistic mode, scan one parameter such as `i_out` or `Q`, keeping the others fixed. Use a coarse range first to identify broad trends, then narrow the range or reduce the step around transitions. Review both the result plot and individual table statuses.

### Explore interactions between two parameters

Scan two parameters to obtain a two-dimensional surface, for example `Q` and `e_out`. Use a modest grid initially because cost grows multiplicatively. Treat interpolated regions between sample points as visualization only; add actual grid points before making claims about narrow features.

### Compare a batch with a reference prediction

Export the CSV and compare simulated `delta_e` values with an independently calculated theoretical estimate. The current GUI does not display the predicted values in the Δe plot, so do not read that tab as a simulation-versus-theory comparison.

## 9. Practical cautions and troubleshooting

- **A run finishes but the orbit appears unbound:** inspect `e_out`, `a_out`, and the status. An unbound osculating orbit may be a physical outcome of the model, not an integration error.
- **WHFast results look suspicious or differ from IAS15:** reduce `dt`; verify convergence. Close encounters and high eccentricities can demand much finer steps.
- **Energy is not well conserved:** inspect the relative-energy plot, then test a more suitable integrator or a tighter WHFast step. Energy conservation is necessary for many analyses but is not sufficient to establish trajectory accuracy in a chaotic system.
- **A statistic scan produces no run or only one combination:** check that at least one valid range is selected, that Start differs from End, and that Step has the correct sign. Empty range fields do not define a scan.
- **A batch is slow or the machine becomes unresponsive:** reduce the number of grid points, lower Workers, or shorten `T_max` for a pilot scan. Independent simulations can still consume substantial CPU and memory.
- **A plot has gaps, non-finite values, or very sharp features:** inspect the corresponding table row and status, increase the number of output points where a sampled extremum matters, and validate the integration settings. More output points do not repair an integration step that is too large.
- **The run is stopped:** a single-run cancellation ends that run without a completed result. A stopped statistic batch may retain and export rows that finished before cancellation.

Three-body dynamics can be chaotic: small changes in initial conditions or numerical resolution may lead to large long-term trajectory differences. Prefer convergence checks, compare suitable methods, and report the model assumptions and numerical settings with scientific conclusions.
