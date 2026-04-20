# Setup Instructions for PyChrono and PyDEME

This document explains how to install the required software, prepare the environment, verify required assets, and run the main workflows in this project.

---

**1. Notes**

**Removing a conda environment**  
Use the following command to remove a conda environment:

```
conda env remove --name myenv
```

Replace `myenv` with the name of the environment to remove.

**Listing conda environments**  
Use:

```
conda env list
```

This displays all existing conda environments. The currently active environment is marked with an asterisk (*).

---

**2. Pre-Requisites**

**Check NVIDIA driver**  
Run:

```
nvidia-smi
```

The CUDA version shown in the top-right corner should be **12.8 or higher**. If the version is lower, update the NVIDIA driver before proceeding.

Resources:

- NVIDIA Driver Downloads: https://www.nvidia.com/Download/index.aspx
- Linux Installation Guide: https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html

**Install Miniconda3**  
Download the Miniconda shell installer:

https://www.anaconda.com/download/success

Miniconda is a lightweight Python distribution that includes Conda for environment management.

Installation steps:

Make the installer executable:

```
sudo chmod +x shell_script_name.sh
```

Run the installer:

```
./shell_script_name.sh
```

Replace `shell_script_name.sh` with the actual filename you downloaded.

If issues occur, verify system requirements:

https://www.anaconda.com/docs/getting-started/miniconda/system-requirements

---

**3. Create Environment and Install Dependencies**

**Create and activate environment**  
Use:

```
conda create -n myenv python=3.12 -c conda-forge -y
conda activate myenv
```

`myenv` can be replaced with any preferred environment name. The `-y` flag skips confirmation prompts. :contentReference[oaicite:0]{index=0}

**Install PyChrono and PyDEME**  
Ensure the environment is activated before running:

```
conda install bochengzou::pychrono bochengzou::pydeme -c bochengzou -c conda-forge
```

The required package versions are not yet available through standard conda-forge alone, so the `bochengzou` channel is used. :contentReference[oaicite:1]{index=1}

**Install additional dependencies**  
Use your current commands:

```
conda install -c conda-forge imageio-ffmpeg
conda install -c conda-forge pandas
```

Additional dependencies required by the repository:

```
conda install -c conda-forge numpy
conda install -c conda-forge matplotlib
conda install -c conda-forge pyvista
```

Optional:

```
conda install typing_extensions
```

These are needed because the code imports `numpy` throughout the simulation scripts, `pandas` for CSV reading and writing, `matplotlib` for compaction plotting, and `pyvista` for VTK reading/writing and wheel-path extraction. :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4} :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6}

---

**4. Required Assets**

**Purpose:**  
These mesh files are required by the simulation scripts for wheel and pressure-plate geometry.

**Required files:**
- `mesh/rover_wheels/viper_wheel_right.obj`
- `TREAD_Assembly.obj`
- `reference wheel meshes/pressureplate.obj`

The demo wheel path is defined in `config.py` as `mesh/rover_wheels/viper_wheel_right.obj`. The custom wheel path is `TREAD_Assembly.obj`. The pressure-plate mesh path is `reference wheel meshes/pressureplate.obj`. :contentReference[oaicite:7]{index=7} :contentReference[oaicite:8]{index=8}

If these files are missing or located elsewhere, update the paths in `config.py` before running the simulations. `slipsinkage.py` loads the wheel mesh with `AddWavefrontMeshObject(...)`, and `platesinkage.py` loads the plate mesh the same way. :contentReference[oaicite:9]{index=9} :contentReference[oaicite:10]{index=10}

---

**5. Configuration File**

**Purpose:**  
`config.py` is the central control file for the project. It defines output paths, solver settings, terrain parameters, material properties, wheel parameters, pressure-plate parameters, and slip test settings. :contentReference[oaicite:11]{index=11} :contentReference[oaicite:12]{index=12} :contentReference[oaicite:13]{index=13} :contentReference[oaicite:14]{index=14}

**What it controls:**
- output directories for terrain generation, slip/sinkage, and pressure plate runs
- solver timestep and gravity
- terrain material properties
- contact parameters for wheel-terrain and plate-terrain interaction
- wheel configuration (demo vs custom)
- bin dimensions
- slip values and angular velocity
- plate dimensions, mass, and penetration velocity. :contentReference[oaicite:15]{index=15} :contentReference[oaicite:16]{index=16} :contentReference[oaicite:17]{index=17} :contentReference[oaicite:18]{index=18}

All major scripts import `config.py`, so it should be reviewed before running anything. :contentReference[oaicite:19]{index=19} :contentReference[oaicite:20]{index=20} :contentReference[oaicite:21]{index=21} :contentReference[oaicite:22]{index=22}

---

**6. Core Simulation Workflow**

**Terrain generation workflow**
1. Edit `config.py`
2. Run `terraingeneration.py`

This script creates and settles the particle terrain and produces the initial terrain state used by the later simulations. It must be run first. `terraingeneration.py` writes terrain motion snapshots and a final settled terrain CSV into the terrain-generation output directories. :contentReference[oaicite:23]{index=23} :contentReference[oaicite:24]{index=24}

**Slip / sinkage workflow**
1. Edit `config.py`
2. Run `terraingeneration.py`
3. Run `slipsinkage.py`
4. Optionally run `compaction.py`
5. Optionally run `csv_vtk.py`

`slipsinkage.py` loads the settled terrain from the terrain-generation stage, reconstructs the particle field, adds the wheel, prescribes wheel spin and slip-dependent forward velocity, and writes terrain motion, wheel motion, contact-force CSVs, and final terrain state for each slip case. :contentReference[oaicite:25]{index=25} :contentReference[oaicite:26]{index=26} :contentReference[oaicite:27]{index=27}

`compaction.py` should be run after completed slip/sinkage simulations if compaction and settlement maps are needed. `csv_vtk.py` can be used after a simulation if format conversion is needed for visualization. :contentReference[oaicite:28]{index=28} :contentReference[oaicite:29]{index=29} :contentReference[oaicite:30]{index=30}

**Pressure plate workflow**
1. Edit `config.py`
2. Run `terraingeneration.py`
3. Run `platesinkage.py`

`platesinkage.py` loads the settled terrain, reconstructs the terrain particles, inserts a pressure plate, moves it downward at a prescribed velocity, and records sinkage, force, pressure, terrain height, and terrain mass over time. :contentReference[oaicite:31]{index=31} :contentReference[oaicite:32]{index=32}

---

**7. Post-Processing and Visualization**

**CSV / VTK conversion**
`csv_vtk.py` is an interactive conversion utility. It prompts the user to choose either:
- CSV → VTK
- VTK → CSV

It accepts either a single file or a directory and converts all matching files in that location. CSV input must contain `X`, `Y`, and `Z` columns. Additional point-data columns are preserved when converting. :contentReference[oaicite:33]{index=33} :contentReference[oaicite:34]{index=34} :contentReference[oaicite:35]{index=35} :contentReference[oaicite:36]{index=36}

**Compaction analysis**
`compaction.py` loads the baseline settled terrain and all available slip directories, computes top-surface grids and local packing-fraction changes, and produces:
- per-slip aggregate CSV maps
- per-slip PNG overlays
- a comparison summary CSV
- a comparison summary PNG. :contentReference[oaicite:37]{index=37} :contentReference[oaicite:38]{index=38} :contentReference[oaicite:39]{index=39}

It can visualize `compaction_mean`, `compaction_max`, `settlement_mean`, or `settlement_max`, and it also extracts wheel-center trajectories from wheel-motion VTK files for overlay plots. :contentReference[oaicite:40]{index=40} :contentReference[oaicite:41]{index=41} :contentReference[oaicite:42]{index=42}

---

**8. Output Directories**

The output paths are defined in `config.py` as:

- Terrain generation output → `./terrain generation output`
- Slip/sinkage output → `./slip sinkage output`
- Pressure plate output → `./pressure plate output` :contentReference[oaicite:43]{index=43}

Within slip/sinkage, each case is written using a folder structure like:

```
Trial 1/
  Slip 0.0/
    terrain motion/
    wheel motion/
    contact forces/
    settled data/
```

This comes directly from the output-directory setup in `slipsinkage.py`. :contentReference[oaicite:44]{index=44}

`compaction.py` writes into:

```
compaction output/
  slip 0/
  slip 0.3/
  slip 0.6/
  slip-compaction/
```

or equivalent slip-named folders depending on discovered slip values. :contentReference[oaicite:45]{index=45} :contentReference[oaicite:46]{index=46} :contentReference[oaicite:47]{index=47}

`MOVIE_OUT_DIR = "./movies"` is still defined in `config.py`, but none of the main scripts currently write to that directory. :contentReference[oaicite:48]{index=48}

---

**9. Runtime Notes**

- Terrain generation uses a fixed random seed `SEED = 77` for reproducible particle placement. :contentReference[oaicite:49]{index=49}
- `terraingeneration.py` settles terrain for `1.0 s` and writes motion frames at `1e-3 s` intervals. :contentReference[oaicite:50]{index=50}
- `slipsinkage.py` currently uses `NUM_TRIALS = 1`. :contentReference[oaicite:51]{index=51}
- The DEM timestep in `config.py` is `5e-6 s`. :contentReference[oaicite:52]{index=52}
- Slip and pressure-plate runtimes are both `5.0 s`. :contentReference[oaicite:53]{index=53}
- Gravity is defined as `[0, 0, -9.81]`. :contentReference[oaicite:54]{index=54}

For finer particle sizes, larger bins, or heavier parameter sweeps, a GPU-enabled system is recommended.
