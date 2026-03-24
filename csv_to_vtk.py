import pandas as pd
import pyvista as pv
import config as c
import os

CSV_DIR = os.path.join(c.SLIP_SINKAGE_OUT_DIR, c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_CSV_FILE_NAME)
OUT_DIR = os.path.join(c.SLIP_SINKAGE_OUT_DIR, c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_VTK_FILE_NAME)

os.makedirs(OUT_DIR, exist_ok=True)

for file in os.listdir(CSV_DIR):
    if file.endswith(".csv"):

        path = os.path.join(CSV_DIR, file)
        df = pd.read_csv(path)

        # point coordinates
        points = df[["X","Y","Z"]].values
        cloud = pv.PolyData(points)

        # add every column as point data
        for col in df.columns:
            if col not in ["X","Y","Z"]:
                cloud[col] = df[col].values

        cloud.save(os.path.join(OUT_DIR, file.replace(".csv", ".vtk")))
