# 3-Body AB+C Simulator: User Guide

## Overview
The **3-Body AB+C Simulator** is a high-performance scientific visualization tool designed to study the gravitational dynamics of a three-body system. It specifically focuses on a configuration where two primary bodies (A and B) interact with a third body (C), allowing for detailed exploration of orbital stability and statistical distributions.

## Core Features
* **Real-time Physics Engine:** Simulates gravitational interactions using high-precision numerical integration.
* **Parameter Control:** Fine-tune the mass, position, and velocity of bodies A, B, and C.
* **Visual Analytics:** Real-time trajectory tracking and statistical data visualization.
* **Batch Processing:** Run hundreds of simulations simultaneously with varying parameters to perform large-scale statistical studies.
* **Cross-Platform Support:** Optimized for Windows, macOS, and Linux.

---

## Getting Started

### 1. Installation & Setup
To run the application from the source:
1. Ensure you have **Python 3.x** installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the application:
   ```bash
   python main.py
   ```

### 2. Navigating the Interface
The application uses a `PyQt6` interface. The main window is organized into several functional areas:

* **Parameter Control Panel:** Side panel used to input specific physical constants and initial conditions.
* **Simulation Viewport:** The central area where the motion of the three bodies is visualized.
* **Statistics & Plots:** Dedicated widgets that display data trends, movement paths, and statistical distributions.

---

## Using the Simulator

### Setting Up a Single Simulation
1. **Input Parameters:** Use the parameter widgets to define:
    * **Masses:** The gravitational mass of Body A, Body B, and Body C.
    * **Initial Conditions:** Starting positions and velocity vectors for each body.
2. **Run Simulation:** Initiate the simulation to observe the movement of the bodies in real-time.
3. **Observe Trajectories:** Monitor the paths taken by each body via the integrated plot widgets.

### Performing Batch Runs (Statistical Analysis)
To study how changing a specific variable (e.g., the mass of Body C) affects the overall system stability:
1. **Configure a Batch:** Use the statistical parameter tools to define a range of values for your target variable.
2. **Start Batch Process:** The application utilizes multi-core processing to run many simulations in parallel.
3. **Analyze Results:** Once the batch is complete, use the Statistical Plot widgets to view the resulting distributions and trends.

---

## Technical Specifications
* **Engine:** Custom gravity engine utilizing `core.simulation` and `core.kepler` modules.
* **UI Framework:** PyQt6 (Fusion Style).
* **Parallelism:** Leverages `multiprocessing` for high-speed, parallel statistical execution.

## Troubleshooting
* **Performance:** For very large batch runs, ensure your system has sufficient CPU cores, as the simulator is designed to maximize parallel processing.
* **Visual Glitches:** If the window does not scale correctly, ensure your OS High-DPI settings are compatible with the application's scaling policy.
