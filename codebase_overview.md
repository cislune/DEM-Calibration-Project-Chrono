# Setup Instructions for PyChrono and PyDEME

This document explains how to set up the environment, dependencies, and execution workflow for this project.

---

**1. Conda Environment Management**

**Removing a conda environment**  
```
conda env remove --name myenv
```

**Listing conda environments**  
```
conda env list
```

This displays all environments. The active environment is marked with (*).

---

**2. Prerequisites**

**Check NVIDIA driver**  
Run:

```
nvidia-smi
```

The CUDA Version (top right) must be **12.8 or higher**.

If not, update your driver:

- https://www.nvidia.com/Download/index.aspx  
- https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html  

---

**Install Miniconda3**

Download:  
https://www.anaconda.com/download/success  

Make executable:

```
chmod +x <miniconda-installer>.sh
```

Run installer:

```
./<miniconda-installer>.sh
```

---

**3. Creating Environment and Installing PyChrono / PyDEME**

**Create and activate environment**

```
conda create -n myenv python=3.12 -c conda-forge -y
conda activate myenv
```

---

**Install PyChrono and PyDEME**

```
conda install bochengzou::pychrono bochengzou::pydeme -c bochengzou -c conda-forge
```

This project depends on a version not yet fully available on conda-forge.

---

**Install additional dependencies**

```
conda install -c conda-forge pandas numpy matplotlib pyvista imageio-ffmpeg
```

Optional:

```
conda install typing_extensions
```

---

**4. Required Assets**

**Purpose:**  
These mesh files are required for wheel and plate geometry in DEM simulations.

**Required files:**
- `mesh/rover_wheels/viper_wheel_right.obj`
- `TREAD_Assembly.obj`
- `reference wheel meshes/pressureplate.obj`

These are loaded using `AddWavefrontMeshObject()` in simulation scripts. :contentReference[oaicite:0]{index=0} :contentReference[oaicite:1]{index=1}  

If paths are incorrect, update `config.py`.

---

**5. Core Simulation Workflows**

---

**Terrain generation (`terraingeneration.py`)**

**Purpose:**  
Generates a discrete particle terrain and settles it under gravity to produce an initial condition for all experiments.

**What this script does**
1. Creates output directories for motion + settled terrain  
2. Initializes DEM solver with timestep, gravity, and velocity limits  
3. Defines terrain material (E, μ, restitution, cohesion)  
4. Constructs simulation domain with open top and floor boundary  
5. Generates **polydisperse sphere templates (12 sizes)**  
6. Uses Poisson-disk sampling to place particles layer-by-layer  
7. Runs dynamic relaxation for ~1.0 s  
8. Writes:
   - time-resolved terrain motion (CSV)
   - final settled terrain (CSV)

**Key implementation detail:**  
Particle size increases slightly per template to create realistic packing. :contentReference[oaicite:2]{index=2}  

---

**Slip / sinkage simulation (`slipsinkage.py`)**

**Purpose:**  
Simulates wheel motion over terrain to measure slip behavior, sinkage, and contact forces.

**What this script does**
1. Selects wheel configuration (demo or user-defined)  
2. Loads settled terrain CSV and reconstructs particle field  
3. Rebuilds clump templates to match terrain generation  
4. Loads wheel mesh and assigns mass + inertia  
5. Prescribes:
   - angular velocity
   - vertical loading force
   - slip-controlled forward velocity  
6. Runs simulation for each slip value  
7. Writes:
   - terrain motion (CSV)
   - wheel motion (VTK)
   - contact forces (CSV)
   - final terrain state (CSV)

**Slip physics used:**  
```
v = (1 - slip) * (ωR)
```

**Key behavior:**  
Wheel transitions between constraint families to activate motion after initialization. :contentReference[oaicite:3]{index=3}  

---

**Pressure plate simulation (`platesinkage.py`)**

**Purpose:**  
Simulates plate penetration into terrain to measure pressure–sinkage behavior.

**What this script does**
1. Loads settled terrain and reconstructs particles  
2. Initializes plate mesh above terrain  
3. Applies constant downward velocity  
4. Tracks:
   - contact force (Fz)
   - sinkage
   - pressure
   - terrain height
   - terrain mass  
5. Writes:
   - terrain motion (CSV)
   - contact data (CSV)
   - plate motion (VTK)
   - response data (CSV)
   - final terrain state (CSV)

**Key equation:**  
```
pressure = |Fz| / plate_area
```

**Force computed via:**  
```
F = m * a
``` 
:contentReference[oaicite:4]{index=4}  

---

**6. Post-Processing and Visualization**

---

**CSV / VTK conversion (`csv_vtk.py`)**

**Purpose:**  
Converts simulation data between CSV and VTK formats for visualization and analysis.

**What this script does**
- Interactive CLI (user selects mode)
- Supports:
  - CSV → VTK
  - VTK → CSV
- Works on single files or entire directories
- Preserves point data fields

**Important requirement:**  
CSV must contain `X, Y, Z` columns. :contentReference[oaicite:5]{index=5}  

---

**Compaction analysis (`compaction.py`)**

**Purpose:**  
Quantifies terrain deformation due to wheel motion across slip cases.

**What this script does**
1. Loads baseline terrain (pre-wheel)  
2. Iterates over all slip trial folders  
3. Builds spatial grid over terrain  
4. Computes:
   - top surface height
   - packing fraction (ϕ)
5. Calculates:
   - compaction = Δϕ
   - settlement = height difference  
6. Applies smoothing and thresholding  
7. Tracks wheel path from VTK data  
8. Generates:
   - per-slip CSV maps
   - per-slip PNG visualizations
   - comparison summary (CSV + PNG)

**Key outputs**
- compaction_mean / compaction_max
- settlement_mean / settlement_max
- integrated compaction metrics :contentReference[oaicite:6]{index=6}  

---

**7. Output Directories**

Defined in `config.py`:

- Terrain generation → `./terrain generation output`
- Slip-sinkage → `./slip sinkage output`
- Pressure plate → `./pressure plate output`

Each slip case is stored as:

```
Trial X/
  Slip Y/
    terrain motion/
    wheel motion/
    contact forces/
    settled data/
```

---

**8. Runtime and Solver Behavior**

- DEM timestep: `5e-6 s`  
- Output interval: ~`1e-3 s`  
- Terrain settling time: ~1.0 s  
- Slip simulation runtime: 5.0 s  
- Plate simulation runtime: 5.0 s  
- Gravity: `[0, 0, -9.81]`  

Velocity limits are enforced for numerical stability. :contentReference[oaicite:7]{index=7}  

---

**9. Important Notes**

- All simulations depend on `config.py`
- Terrain generation must be run first
- Slip and plate simulations reuse the same terrain
- Compaction analysis requires completed slip simulations
- Movie output is defined but currently unused
