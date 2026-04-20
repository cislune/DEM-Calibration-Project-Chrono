# Codebase Overview

This document explains the structure, purpose, and internal behavior of the main scripts in this project. It is intended to help users understand how the simulations are implemented and how the different components interact.

---

**1. `config.py` — Central Configuration File**

**Purpose:**  
`config.py` defines all simulation parameters and is imported by every major script. It acts as the single source of truth for solver settings, geometry, materials, and output paths.

**What it controls:**
- Output directories for all simulations
- DEM solver parameters (time step, gravity, velocity limits)
- Terrain properties (particle size, density, cohesion)
- Contact properties (friction, restitution, cohesion)
- Wheel configuration (demo vs custom)
- Wheel mesh paths and inertial properties
- Pressure plate parameters (size, mass, velocity)
- Domain (bin) geometry
- Slip test parameters (slip values, angular velocity)

**Key behavior:**
- All scripts read from this file at runtime
- Changing values here automatically affects all simulations
- Supports both demo and user-defined wheel configurations

---

**2. `terraingeneration.py` — Terrain Creation and Settling**

**Purpose:**  
Generates a particle-based terrain and settles it under gravity to create a physically realistic initial condition for subsequent simulations.

**What this script does:**
1. Initializes DEM solver with settings from `config.py`
2. Defines terrain material properties
3. Constructs simulation domain with:
   - open top boundary
   - fixed bottom plane
4. Generates multiple sphere templates (polydisperse particles)
5. Distributes particles in layers across the domain
6. Runs dynamic simulation to allow particles to settle
7. Writes:
   - time-resolved terrain motion (CSV per frame)
   - final settled terrain state (CSV)

**Key implementation details:**
- Uses ~12 particle templates with slightly increasing radii to simulate realistic packing
- Particle mass computed from density and radius
- Terrain is saved as clump-based data for reconstruction later

**Output:**
```
./terrain generation output/
  settling terrain motion/
  settled terrain data/
```

**Dependency:**  
Must be run before any other simulation.

---

**3. `slipsinkage.py` — Wheel–Terrain Interaction Simulation**

**Purpose:**  
Simulates a wheel moving across terrain to study slip behavior, sinkage, and contact forces.

**What this script does:**
1. Loads settled terrain CSV from terrain generation
2. Reconstructs particle field using clump templates
3. Selects wheel configuration:
   - demo wheel OR
   - user-defined wheel mesh
4. Loads wheel mesh using `AddWavefrontMeshObject`
5. Assigns:
   - mass
   - inertia tensor
6. Applies motion:
   - angular velocity
   - vertical load
   - slip-dependent forward velocity
7. Runs simulation for each slip value
8. Writes:
   - terrain motion (CSV)
   - wheel motion (VTK)
   - contact force data (CSV)
   - final terrain state (CSV)

**Slip model used:**
```
v = (1 - slip) * (ωR)
```

**Key behavior:**
- Wheel motion is prescribed using solver family constraints
- Slip values are defined in `config.py`
- Each slip case is run independently

**Output structure:**
```
./slip sinkage output/
  Trial 1/
    Slip X/
      terrain motion/
      wheel motion/
      contact forces/
      settled data/
```

---

**4. `platesinkage.py` — Pressure Plate Simulation**

**Purpose:**  
Simulates vertical penetration of a plate into terrain to measure pressure–sinkage behavior.

**What this script does:**
1. Loads settled terrain from terrain generation
2. Reconstructs terrain particles
3. Loads pressure plate mesh
4. Positions plate slightly above terrain surface
5. Applies constant downward velocity
6. Tracks:
   - plate position
   - contact force
   - sinkage
   - pressure
   - terrain height
   - terrain mass
7. Computes:
```
pressure = |Fz| / plate_area
```
8. Writes:
   - terrain motion (CSV)
   - contact force data (CSV)
   - plate motion (VTK)
   - response data (CSV)
   - final terrain state (CSV)

**Key behavior:**
- Contact force computed via:
```
F = m * a
```
- Plate motion is fully prescribed (no dynamics-based motion)

**Output:**
```
./pressure plate output/
```

---

**5. `csv_vtk.py` — Data Conversion Utility**

**Purpose:**  
Converts simulation output between CSV and VTK formats for visualization and analysis.

**What this script does:**
- Interactive command-line interface
- User selects:
  - CSV → VTK
  - VTK → CSV
- Accepts:
  - single file OR
  - entire directory
- For CSV → VTK:
  - requires X, Y, Z columns
  - converts to point cloud
- For VTK → CSV:
  - extracts points and point data
  - flattens multi-dimensional arrays

**Use cases:**
- Visualizing particle data in ParaView
- Converting VTK back to CSV for analysis

---

**6. `compaction.py` — Post-Processing and Analysis**

**Purpose:**  
Computes terrain compaction and settlement caused by wheel motion.

**What this script does:**
1. Loads baseline terrain (pre-wheel)
2. Scans all slip simulation directories
3. Builds spatial grid over terrain
4. Computes:
   - top surface height
   - local packing fraction (ϕ)
5. Calculates:
   - compaction = Δϕ
   - settlement = height change
6. Aggregates across all frames:
   - mean values
   - maximum values
7. Applies:
   - smoothing filters
   - thresholding
8. Extracts wheel path from VTK files
9. Generates:
   - per-slip CSV maps
   - per-slip PNG visualizations
   - summary comparison CSV
   - summary comparison plot

**Key computed fields:**
- compaction_mean
- compaction_max
- settlement_mean
- settlement_max

**Output:**
```
./compaction output/
  slip X/
  slip-compaction/
```

---

**7. Simulation Workflow**

**Terrain generation (required first)**
```
config.py → terraingeneration.py
```

**Slip / sinkage workflow**
```
config.py → terraingeneration.py → slipsinkage.py → compaction.py (optional)
```

**Pressure plate workflow**
```
config.py → terraingeneration.py → platesinkage.py
```

---

**8. Data Flow Between Scripts**

- `terraingeneration.py` produces settled terrain CSV  
- `slipsinkage.py` and `platesinkage.py` both read that terrain  
- `compaction.py` reads slip outputs for analysis  
- `csv_vtk.py` converts outputs for visualization  

---

**9. Key Design Principles**

- Centralized configuration (`config.py`)
- Reusable terrain across simulations
- Separation of simulation and post-processing
- Modular scripts for each experiment type
- Consistent output structure for analysis

---

**10. Important Notes**

- Terrain must always be generated before running other simulations
- Mesh paths must match those defined in `config.py`
- Slip simulations and plate simulations are independent after terrain generation
- GPU acceleration is strongly recommended for large simulations
