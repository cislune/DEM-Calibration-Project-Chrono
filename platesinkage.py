import config as c
import DEME
import numpy as np
import pandas as pd
import os

# ----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (import configuration parameters/libraries, prepare output directory and basic setup)
# ----------------------------------------------------------------------------------------------------------------------------

os.makedirs(c.PRESSURE_PLATE_OUT_DIR, exist_ok=True)
# create directory for pressure plate outputs


# ----------------------------------------------------------------------------------------------------------------------------
# OPTIONAL CONFIG FALLBACKS (support both old and updated config.py)
# ----------------------------------------------------------------------------------------------------------------------------

SPHERE_SETTLED_SUBDIR = getattr(c, "SPHERE_TERRAIN_GEN_SETTLED_SUBDIR", "settled data")


# ----------------------------------------------------------------------------------------------------------------------------
# SOLVER SETUP (initialize DEM solver and define integration + output)
# ----------------------------------------------------------------------------------------------------------------------------

solver = DEME.DEMSolver()

solver.SetVerbosity("INFO")
solver.SetOutputFormat("CSV")
solver.SetOutputContent(["XYZ"])
solver.SetContactOutputContent(["OWNER", "FORCE", "POINT"])

solver.SetInitTimeStep(c.STEP_SIZE_st)
# use the configured DEM step size for consistency across scripts

solver.SetMaxVelocity(c.MAX_VELOCITY_st)
solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)
solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)


# ----------------------------------------------------------------------------------------------------------------------------
# MATERIAL + CONTACT MODEL (defines bulk and interaction behavior)
# ----------------------------------------------------------------------------------------------------------------------------

mat_type_terrain = solver.LoadMaterial(
    {
        "E": c.E_st,
        "nu": c.NU_st,
        "CoR": c.COR_st,
        "mu": c.MU_st,
        "Crr": c.CRR_st,
        "Cohesion": c.COHESION_st,
    }
)
# terrain material

mat_type_plate = solver.LoadMaterial(
    {
        "E": c.E_st,
        "nu": c.NU_st,
        "CoR": c.COR_st,
        "mu": c.MU_st,
        "Crr": c.CRR_st,
    }
)
# plate material

solver.SetMaterialPropertyPair("mu", mat_type_plate, mat_type_terrain, c.MU_contact_plate_st)
# interface friction between plate and terrain


# ----------------------------------------------------------------------------------------------------------------------------
# DOMAIN SETUP (defines simulation boundaries and environment)
# ----------------------------------------------------------------------------------------------------------------------------

bin_floor_z_loc = -c.DEPTH_st / 2.0

solver.InstructBoxDomainDimension(
    [-c.WIDTH_st / 2, c.WIDTH_st / 2],
    [-c.LENGTH_st / 2, c.LENGTH_st / 2],
    [-c.DEPTH_st / 2, c.DEPTH_st / 2 + 10 * c.DOMAIN_EXPANSION_FACTOR_st],
)

solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)
solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)


# ----------------------------------------------------------------------------------------------------------------------------
# TERRAIN RECONSTRUCTION (load settled terrain from generation stage)
# ----------------------------------------------------------------------------------------------------------------------------

if c.USE_DEMO_WHEEL_st:
    CURR_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
else:
    CURR_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
# initialize particle radius based on configuration

template_dict = {}

for i in range(12):
    m = (CURR_TERRAIN_RAD**3) * c.TERRAIN_DENSITY_st * (4.0 / 3.0) * np.pi
    curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)

    template_dict[f"{i:02d}"] = curr_template
    template_dict[f"t{i}"] = curr_template
    template_dict[f"t{i:02d}"] = curr_template

    CURR_TERRAIN_RAD += BASE_TERRAIN_RAD / 100.0
# generate a set of particle templates with controlled polydispersity

settled_terrain_csv = os.path.join(
    c.SPHERE_TERRAIN_GEN_OUT_DIR,
    SPHERE_SETTLED_SUBDIR,
    f"{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv",
)

df = pd.read_csv(settled_terrain_csv)
# load previously settled terrain configuration

df["clump_type"] = df["clump_type"].astype(str).str.strip()

for clump_type, g in df.groupby("clump_type"):

    key = clump_type
    if key not in template_dict:
        key = clump_type.zfill(2)

    if key not in template_dict:
        if clump_type.isdigit():
            key = f"t{int(clump_type)}"
        else:
            key = clump_type.lower()

    if key not in template_dict:
        raise KeyError(f"Unknown clump_type in CSV: {clump_type}")

    xyz = g[["X", "Y", "Z"]].to_numpy(dtype=float)
    quat = g[["Qw", "Qx", "Qy", "Qz"]].to_numpy(dtype=float)

    template = template_dict[key]
    batch = solver.AddClumps(template, xyz)
    batch.SetFamilies([0] * xyz.shape[0])
    batch.SetOriQ(quat)
    # reconstruct terrain exactly as generated

terrain_top_z = df["Z"].max()


# ----------------------------------------------------------------------------------------------------------------------------
# PLATE INITIALIZATION (create and configure penetration object)
# ----------------------------------------------------------------------------------------------------------------------------

plate = solver.AddWavefrontMeshObject(c.PLATE_OBJ_FILE_st, mat_type_plate, True, False)

plate.SetInitPos([0, 0, terrain_top_z + c.PLATE_THICK_st + 1e-3])
# place plate slightly above terrain to avoid initial overlap

plate.SetMass(c.PLATE_MASS_st)
plate.SetMOI(
    [
        c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12.0,
        c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12.0,
        c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12.0,
    ]
)

plate.SetFamily(10)
solver.SetFamilyPrescribedLinVel(10, "none", "none", f"-{c.PLATE_VEL_st}", False)
solver.SetFamilyPrescribedAngVel(10, "0", "0", "0")

plate_tracker = solver.Track(plate)


# ----------------------------------------------------------------------------------------------------------------------------
# INSPECTORS + LOGGING SETUP
# ----------------------------------------------------------------------------------------------------------------------------

max_z_finder = solver.CreateInspector("clump_max_z")
mass_finder = solver.CreateInspector("clump_mass")

solver.Initialize()

plate_area = c.PLATE_X_st * c.PLATE_Y_st
log = []

plate_z0 = plate_tracker.Pos()[2]
# record initial plate height for sinkage computation

t = 0.0
frame = 0
dt = 1e-3
# output / logging interval


# ----------------------------------------------------------------------------------------------------------------------------
# SIMULATION EXECUTION (time integration and output)
# ----------------------------------------------------------------------------------------------------------------------------

while t < c.TRIAL_RUN_TIME_PRESSURE_PLATE_st:
    print(f"Frame: {frame}")

    acc = np.array(plate_tracker.ContactAcc(), dtype=float)
    force = acc * c.PLATE_MASS_st
    Fz = force[2]
    # resultant contact force via F = m * a

    plate_z = plate_tracker.Pos()[2]
    sinkage = plate_z0 - plate_z
    pressure = abs(Fz) / plate_area

    terrain_max_z = max_z_finder.GetValue()
    terrain_mass = mass_finder.GetValue()

    log.append([t, plate_z, sinkage, Fz, pressure, terrain_max_z, terrain_mass])

    solver.WriteSphereFile(
        os.path.join(
            c.PRESSURE_PLATE_OUT_DIR,
            f"{c.PRESSURE_PLATE_MOTION_TERRAIN_FILE_NAME}_{frame:04d}.csv",
        )
    )

    solver.WriteContactFile(
        os.path.join(
            c.PRESSURE_PLATE_OUT_DIR,
            f"{c.PRESSURE_PLATE_CONTACT_FORCE_FILE_NAME}_{frame:04d}.csv",
        )
    )

    solver.WriteMeshFile(
        os.path.join(
            c.PRESSURE_PLATE_OUT_DIR,
            f"{c.PRESSURE_PLATE_MOTION_PLATE_FILE_NAME}_{frame:04d}.vtk",
        )
    )

    solver.DoDynamics(dt)
    t += dt
    frame += 1


# ----------------------------------------------------------------------------------------------------------------------------
# OUTPUT (save results for post-processing)
# ----------------------------------------------------------------------------------------------------------------------------

pd.DataFrame(
    log,
    columns=[
        "time",
        "plate_z",
        "sinkage",
        "Fz",
        "pressure",
        "terrain_max_z",
        "terrain_mass",
    ],
).to_csv(
    os.path.join(
        c.PRESSURE_PLATE_OUT_DIR,
        f"{c.PRESSURE_PLATE_RESPONSE_FILE_NAME}.csv",
    ),
    index=False,
)

solver.WriteClumpFile(
    os.path.join(
        c.PRESSURE_PLATE_OUT_DIR,
        f"{c.PRESSURE_PLATE_SETTLED_DATA_FILE_NAME}.csv",
    )
)
# final terrain state after plate loading
