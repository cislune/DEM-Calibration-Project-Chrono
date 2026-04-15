import pandas as pd
import pyvista as pv
import config as c
import os

#----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (import libraries and define base directory)
#----------------------------------------------------------------------------------------------------------------------------

# pandas → used for reading particle data stored in CSV format
# pyvista → used for geometric data structures and VTK file generation for visualization
# config → stores project-specific directory names and file naming conventions (config.py reference) 
    
BASE_DIR = c.SLIP_SINKAGE_OUT_DIR
# root directory containing all slip–sinkage trial subfolders
# each subfolder corresponds to one trial / slip condition

#----------------------------------------------------------------------------------------------------------------------------
# TRIAL LOOP (iterate through each simulation output folder)
#----------------------------------------------------------------------------------------------------------------------------

for trial in os.listdir(BASE_DIR):
    trial_dir = os.path.join(BASE_DIR, trial)
    # construct absolute path to current trial folder

    if not os.path.isdir(trial_dir):
        continue
    # skip non-directory entries to avoid processing unrelated files

    #----------------------------------------------------------------------------------------------------------------------------
    # FILE SELECTION (identify terrain motion CSV files for conversion)
    #----------------------------------------------------------------------------------------------------------------------------

    for file in os.listdir(trial_dir):
        if file.endswith(".csv") and c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME in file:
            # select only terrain motion output files
            # excludes contact-force files, wheel files, and other CSV outputs

            path = os.path.join(trial_dir, file)
            df = pd.read_csv(path)
            # load terrain particle snapshot from CSV
            # each row corresponds to one particle (or clump center) at a given simulation frame

            #----------------------------------------------------------------------------------------------------------------------------
            # POINT CLOUD CONSTRUCTION (convert particle coordinates into VTK-compatible geometry)
            #----------------------------------------------------------------------------------------------------------------------------

            points = df[["X", "Y", "Z"]].values
            # extract Cartesian particle position coordinates from the data table

            cloud = pv.PolyData(points)
            # create PyVista point cloud object
            # in this representation, each particle is stored as a point in 3D space
            # suitable for visualization and post-processing in ParaView / VTK-based tools

            #----------------------------------------------------------------------------------------------------------------------------
            # ATTRIBUTE MAPPING (attach non-coordinate variables as point data)
            #----------------------------------------------------------------------------------------------------------------------------

            for col in df.columns:
                if col not in ["X", "Y", "Z"]:
                    cloud[col] = df[col].values
                    # adds every column as point data
                    # attaches additional particle attributes (ID, velocity, family, radius, etc.)
                    # preserves simulation metadata so scalar fields can be visualized in ParaView

            #----------------------------------------------------------------------------------------------------------------------------
            # OUTPUT (save VTK version of each terrain snapshot)
            #----------------------------------------------------------------------------------------------------------------------------

            cloud.save(os.path.join(trial_dir, file.replace(".csv", ".vtk")))
            # export point cloud to VTK format
            # enables efficient scientific visualization of particle fields and spatial evolution
