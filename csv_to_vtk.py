import pandas as pd
import pyvista as pv
import config as c
import os

BASE_DIR = c.SLIP_SINKAGE_OUT_DIR

for trial in os.listdir(BASE_DIR):
    trial_dir = os.path.join(BASE_DIR, trial)

    if not os.path.isdir(trial_dir):
        continue

    for file in os.listdir(trial_dir):
        if file.endswith(".csv") and c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME in file:

            path = os.path.join(trial_dir, file)
            df = pd.read_csv(path)

            # point coordinates
            points = df[["X", "Y", "Z"]].values
            cloud = pv.PolyData(points)

            # add every column as point data
            for col in df.columns:
                if col not in ["X", "Y", "Z"]:
                    cloud[col] = df[col].values

            cloud.save(os.path.join(trial_dir, file.replace(".csv", ".vtk")))
