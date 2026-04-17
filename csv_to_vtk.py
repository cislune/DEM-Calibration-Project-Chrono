import os
import pandas as pd
import pyvista as pv
import config as c

# ----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (define base directory and optional config fallbacks)
# ----------------------------------------------------------------------------------------------------------------------------

BASE_DIR = c.SLIP_SINKAGE_OUT_DIR
# root directory containing all slip-sinkage trial groups

SLIP_TERRAIN_MOTION_SUBDIR = getattr(c, "SLIP_SINKAGE_TERRAIN_MOTION_SUBDIR", "terrain motion")
# support both old and updated config.py layouts


# ----------------------------------------------------------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------------------------------------------------------

def is_valid_slip_case_dir(path: str) -> bool:
    return os.path.isdir(path) and os.path.basename(path).startswith("Slip ")


def convert_csv_to_vtk(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    # load terrain particle snapshot from CSV

    required_cols = ["X", "Y", "Z"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"{csv_path} is missing required columns: {missing}")

    points = df[["X", "Y", "Z"]].values
    # extract Cartesian particle coordinates

    cloud = pv.PolyData(points)
    # create PyVista point cloud object

    for col in df.columns:
        if col not in required_cols:
            cloud[col] = df[col].values
            # preserve all additional particle attributes as point data

    vtk_path = csv_path.replace(".csv", ".vtk")
    cloud.save(vtk_path)
    # save VTK file next to the original CSV


# ----------------------------------------------------------------------------------------------------------------------------
# TRIAL LOOP (iterate through each trial and slip-case folder)
# ----------------------------------------------------------------------------------------------------------------------------

if not os.path.isdir(BASE_DIR):
    raise FileNotFoundError(f"Slip-sinkage output directory not found: {BASE_DIR}")

for trial_name in sorted(os.listdir(BASE_DIR)):
    trial_dir = os.path.join(BASE_DIR, trial_name)

    if not os.path.isdir(trial_dir):
        continue
    # skip non-directory entries

    for slip_name in sorted(os.listdir(trial_dir)):
        slip_dir = os.path.join(trial_dir, slip_name)

        if not is_valid_slip_case_dir(slip_dir):
            continue
        # process only folders like "Slip 0.0", "Slip 0.3", etc.

        terrain_motion_dir = os.path.join(slip_dir, SLIP_TERRAIN_MOTION_SUBDIR)

        if not os.path.isdir(terrain_motion_dir):
            print(f"Skipping {slip_dir}: missing '{SLIP_TERRAIN_MOTION_SUBDIR}' directory")
            continue

        # --------------------------------------------------------------------------------------------------------------------
        # FILE SELECTION (identify terrain motion CSV files for conversion)
        # --------------------------------------------------------------------------------------------------------------------

        for file_name in sorted(os.listdir(terrain_motion_dir)):
            if not file_name.endswith(".csv"):
                continue

            if c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME not in file_name:
                continue
            # convert only terrain motion CSV files
            # skips contact-force CSVs, settled-data CSVs, and unrelated files

            csv_path = os.path.join(terrain_motion_dir, file_name)

            print(f"Converting: {csv_path}")
            convert_csv_to_vtk(csv_path)
