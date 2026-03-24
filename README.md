# Codebase Overview

This document explains the purpose of the core files in this project and how they work together. The files are listed in the order they are typically used.

---

## 1. `config.py` — **Central Settings File**

**Purpose:**  
This file is the control panel for the entire project. All important parameters are defined here. If changes to simulation behavior are required, this is typically the only file that needs to be edited.

### What this file controls:
- Terrain properties (grain size, stiffness, friction)
- Wheel (Baseline, TREAD Coupon Wheel) properties (radius, width, weight)
- Gravity and simulation timing
- Slip values to test
- Output folders and file names

### How it is used:
- All other scripts read values from **config.py`**
- No simulations are run directly from this file
- Changes made here automatically affect all downstream steps

### Typical interaction
- Adjust terrain parameters for generation
- Modify wheel option, size, or weight
- Define number of slip cases to run
- Select between demo values or custom values

### Output directories defined here:
- Terrain generation output → `./sphere_tgen_output`
- Slip/sinkage output → `./slip_sinkage_output`
- VTK terrain output → `./slip_sinkage_output/slip_sinkage_trials_motion_terrain_vtk`

Please note that the current values are compute efficient on a single machine. For finer particle sizes or larger domains, execution on a GPU-enabled compute cluster is recommended.

---

## 2. `terrain_generation.py` — **Terrain Creation and Settling**

**Purpose:**  
This script creates the terrain (loose particles) and allows it to settle under gravity until it reaches a stable state. This represents preparing the soil before any wheel motion occurs.

### What this script does
1. Creates a simulation container (the “bin”)
2. Spawns thousands of small terrain particles using multiple sphere templates
3. Applies gravity
4. Allows the terrain to settle naturally
5. Saves:
   - A sequence of terrain snapshots (for visualization)
   - A final file containing the settled terrain state

### Outputs produced
- Terrain motion files (CSV)
- One settled terrain file (CSV)

### Output directory
- `./sphere_tgen_output`

These files are later reused by the wheel (`slip_sinkage.py`) simulation.

### When to run it
- Run **once** before running slip or sinkage tests
- Only needs to be rerun if terrain settings change

---

## 3. `slip_sinkage.py` — **Wheel–Terrain Interaction Simulation**

**Purpose:**  
This script simulates a wheel rolling on the settled terrain to measure:
- Slip behavior  
- Sinkage  
- Contact forces between the wheel and terrain  
  *(contact_type, A, B, f_x, f_y, f_z, X, Y, Z)*

Each slip value is run as a separate trial. Singular slip trials per run can be configured through `config.py`.

### What this script does
1. Loads the settled terrain from `terrain_generation.py`
2. Reconstructs terrain using clump templates from CSV
3. Places a wheel on the generated terrain
4. Applies:
   - Wheel rotation
   - Vertical loading
   - Forward motion based on slip value
5. Runs the simulation for a short time
6. Records results at each time step

### Outputs produced (per trial)
- Terrain motion files (CSV)
- Wheel motion files (VTK)
- Contact force files (CSV)
- Final settled state after wheel motion

### Output directory
- `./slip_sinkage_output/trial_X_slip_Y/`

Each slip case is stored in its own folder.

### When to run it
- After terrain generation is complete
- Rerun if wheel properties or slip values change

---

## 4. `csv_to_vtk.py` — **CSV → VTK Conversion Utility**

**Purpose:**  
This script converts terrain motion and contact force data from CSV format to VTK format for visualization in tools such as ParaView. CSV is used for simulation output, while VTK is required for 3D visualization workflows.

---

### What this script does
1. Reads terrain CSV files containing particle positions  
2. Extracts:
   - X, Y, Z coordinates (point positions)
   - Additional columns (stored as point data)
3. Constructs a point cloud using `pyvista`
4. Writes `.vtk` files for visualization

---

### Inputs
- Terrain CSV files from:
  ```
  ./slip_sinkage_output/slip_sinkage_trials_motion_terrain_csv
  ```

### Outputs
- Converted VTK files:
  ```
  ./slip_sinkage_output/slip_sinkage_trials_motion_terrain_vtk
  ```

---

### When to run it
- After running `slip_sinkage.py`
- Required only for visualization of terrain particle motion

---

## Typical Workflow Summary

1. **Edit `config.py`**  
   Define terrain, wheel, and test parameters  

2. **Run `terrain_generation.py`**  
   Prepare and settle the terrain  

3. **Run `slip_sinkage.py`**  
   Simulate wheel motion and collect data  

4. **Run `csv_to_vtk.py` (optional)**  
   Convert terrain CSV outputs into VTK format for visualization  

---
