# 3-Body AB+C Simulator — Quick Start

## Start Here

1. **Launch**: `python main.py`
2. **Select Mode**: `Mode` menu → `Single run` or `Statistic run`
3. **Set Parameters**: Fill in masses and orbital elements
4. **Run**: Click **Run** button
5. **View Results**: 3D plot, projections, and statistics appear

## Key Concepts

- **Single Run**: One simulation with interactive plots
- **Statistic Run**: Scan up to 2 parameters in parallel batches
- **Units**: M☉, AU, years (1 yr = 2π)

## File Menu

- **Open/Save**: YAML configs (e.g., `configs/default.yaml`)
- **Import/Export**: CSV statistic tables
- **Quit**: Exit application

## Modes

### Single Run
- Input all parameters
- Click **Run**
- Watch 3D trajectories and plots update live

### Statistic Run
- Check parameters to scan (max 2)
- Set Start / End / Step for each
- Click **Start**
- Results appear in table with histogram
- Export to CSV or PDF

## Tips

- For faster simulation: Use WHFast integrator, reduce `t_max`
- For accuracy: Use IAS15 (default)
- For exploration: Try `configs/moon.yaml`, `configs/i_140-case.yaml`
- For batch analysis: Use `diagram.py` to plot histograms

## Command Line Tools

```bash
# Plot histogram from CSV
python diagram.py results.csv --bins 100

# Save image without opening window
python diagram.py results.csv --output plot.png
```
