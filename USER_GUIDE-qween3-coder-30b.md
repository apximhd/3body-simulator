# User Guide for Celestial Mechanics Simulation Application

## Overview
This application is a comprehensive tool for simulating orbital mechanics and gravitational interactions between celestial bodies. It allows users to model orbital dynamics, analyze gravitational systems, and visualize orbital paths using Keplerian mechanics and advanced simulation techniques.

## Getting Started

### Prerequisites
- Python 3.7 or higher
- Required packages (install with: `pip install -r requirements.txt`)

### Installation
1. Clone the repository or download the source code
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## Main Interface

### Main Window Components
The application features a graphical user interface with several key components:

1. **Parameter Controls Panel** (left side)
   - Orbital element configuration
   - Mass and gravitational parameter settings
   - Simulation time parameters

2. **Simulation Control Panel**
   - Start/Stop simulation buttons
   - Reset functionality
   - Parameter adjustment sliders

3. **Visualization Area** (center)
   - Real-time orbital path plotting
   - Celestial body visualization
   - Animation of orbital motion

4. **Statistics and Analysis Panel** (right side)
   - Statistical data output
   - Orbital parameter analysis
   - Export capabilities

## Using the Application

### 1. Configuration
- Select a configuration file from the `configs/` directory or create a new one
- Adjust orbital elements in the parameter panel:
  - Semi-major axis (a)
  - Eccentricity (e)
  - Inclination (i)
  - Longitude of ascending node (Ω)
  - Argument of periapsis (ω)
  - Mean anomaly (M)

### 2. Running Simulations
1. Set desired parameters in the control panel
2. Click "Start Simulation" to begin
3. Watch orbital motion in real-time
4. Adjust parameters during simulation if needed

### 3. Analyzing Results
- View orbital paths and trajectories in the visualization area
- Access statistical data in the analysis panel
- Export results to CSV or Excel formats

## Configuration Files

The application uses YAML configuration files located in the `configs/` directory:

- `default.yaml` - Default simulation settings
- `moon.yaml` - Moon orbital parameters
- Various test configurations for different scenarios
- `current_config.yaml` - Currently loaded configuration

## Key Features

### Orbital Mechanics
- Keplerian orbit calculations
- Multi-body gravitational interactions
- Orbital element transformations
- Time evolution of orbital parameters

### Visualization
- Real-time orbital path plotting
- 3D-like representation of orbital motion
- Customizable viewing angles
- Animation controls

### Statistical Analysis
- Orbit parameter analysis
- Data export capabilities
- Batch processing for multiple scenarios
- Comparison of different orbital configurations

## Troubleshooting

### Common Issues
1. **Missing Dependencies**: Ensure all packages in `requirements.txt` are installed
2. **Performance Issues**: Reduce simulation resolution or time span for complex orbits
3. **Visualization Problems**: Check that display drivers are up to date

### Contact Support
For issues not resolved by this guide, contact the development team or check the project repository.

## Advanced Usage

### Batch Processing
The application supports batch processing of multiple simulations:
1. Configure parameters in `batch.py`
2. Run batch simulations using the appropriate functions
3. Analyze results collectively

### Custom Configurations
Create custom `.yaml` files in the `configs/` directory to define new orbital scenarios with specific gravitational parameters.

## License and Credits
This application is provided under the terms specified in the LICENSE file.