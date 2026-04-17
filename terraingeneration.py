import config as c
import DEME
from DEME import PDSampler
import numpy as np
import random
import os

# ----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (prepare output directories, select terrain particle scale, initialize setup)
# ----------------------------------------------------------------------------------------------------------------------------

os.makedirs(c.SPHERE_TERRAIN_GEN_OUT_DIR, exist_ok=True)
# create terrain-generation output directory if it does not already exist

motion_dir = os.path.join(c.SPHERE_TERRAIN_GEN_OUT_DIR, "motion")
settled_dir = os.path.join(c.SPHERE_TERRAIN_GEN_OUT_DIR, "settled data")
# dedicated subdirectories for time-resolved settling motion and final settled terrain state

os.makedirs(motion_dir, exist_ok=True)
os.makedirs(settled_dir, exist_ok=True)

SEED = 77
# random seed for reproducible terrain generation

if c.USE_DEMO_WHEEL_st:
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
else:
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
# terrain particle scale follows the active wheel configuration

CURR_TERRAIN_RAD = BASE_TERRAIN_RAD
# current particle radius, incremented during template creation to introduce mild polydispersity


# ----------------------------------------------------------------------------------------------------------------------------
# SOLVER SETUP
# ----------------------------------------------------------------------------------------------------------------------------

solver = DEME.DEMSolver()

solver.SetVerbosity("INFO")
solver.SetOutputFormat("CSV")
solver.SetOutputContent(["XYZ"])
solver.SetMaxVelocity(c.MAX_VELOCITY_st)
solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)
solver.SetInitTimeStep(c.STEP_SIZE_st)
solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)


# ----------------------------------------------------------------------------------------------------------------------------
# MATERIAL DEFINITION
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


# ----------------------------------------------------------------------------------------------------------------------------
# DOMAIN AND BOUNDARY CONDITIONS
# ----------------------------------------------------------------------------------------------------------------------------

bin_floor_z_loc = -c.DEPTH_st / 2.0

solver.InstructBoxDomainDimension(
    [-c.WIDTH_st / 2, c.WIDTH_st / 2],
    [-c.LENGTH_st / 2, c.LENGTH_st / 2],
    [-c.DEPTH_st / 2, c.DEPTH_st / 2 + 1000 * CURR_TERRAIN_RAD],
)

solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)
solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)


# ----------------------------------------------------------------------------------------------------------------------------
# PARTICLE TEMPLATES / SIZE DISTRIBUTION
# ----------------------------------------------------------------------------------------------------------------------------

templates_terrain = []

for i in range(12):
    m = (CURR_TERRAIN_RAD**3) * c.TERRAIN_DENSITY_st * (4.0 / 3.0) * np.pi
    curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)
    curr_template.AssignName(f"t{i}")
    templates_terrain.append(curr_template)

    CURR_TERRAIN_RAD += BASE_TERRAIN_RAD / 100.0
    # narrow particle-size distribution for more realistic packing

# after this loop, CURR_TERRAIN_RAD is slightly larger than the largest created template radius


# ----------------------------------------------------------------------------------------------------------------------------
# INITIAL PARTICLE PLACEMENT
# ----------------------------------------------------------------------------------------------------------------------------

rng = random.Random(SEED)

sampler = PDSampler(2.01 * CURR_TERRAIN_RAD)
# Poisson-disk-style spacing to reduce severe initial overlap

sample_halfwidth_x = (c.WIDTH_st / 2.0) - 2.0 * CURR_TERRAIN_RAD
sample_halfwidth_y = (c.LENGTH_st / 2.0) - 2.0 * CURR_TERRAIN_RAD

sample_z = (-c.DEPTH_st / 2.0) + 2.0 * CURR_TERRAIN_RAD
# begin slightly above the floor

num_particle = 0

while sample_z < c.FULL_HEIGHT_st:
    sample_center = np.array([0.0, 0.0, sample_z], dtype=float)
    sample_region = np.array([sample_halfwidth_x, sample_halfwidth_y, 1e-6], dtype=float)
    # very thin layer, effectively sampling one horizontal slice at a time

    particle_xyz = sampler.SampleBox(sample_center, sample_region)

    selected_templates = [
        templates_terrain[rng.randrange(len(templates_terrain))]
        for _ in range(len(particle_xyz))
    ]

    solver.AddClumps(selected_templates, particle_xyz)

    num_particle += len(particle_xyz)
    sample_z += 4.01 * CURR_TERRAIN_RAD
    # advance to next layer

print(f"total num of particles: {num_particle}")


# ----------------------------------------------------------------------------------------------------------------------------
# SOLVER INITIALIZATION
# ----------------------------------------------------------------------------------------------------------------------------

solver.Initialize()


# ----------------------------------------------------------------------------------------------------------------------------
# TERRAIN SETTLING / DYNAMIC RELAXATION
# ----------------------------------------------------------------------------------------------------------------------------

settle_time = 1.0
frame_time = 1e-3

t = 0.0
frame = 0

while t < settle_time:
    print(f"Frame: {frame}")

    solver.WriteSphereFile(
        os.path.join(
            motion_dir,
            f"{c.SPHERE_TERRAIN_GENERATION_MOTION_FILE_NAME}_{frame:04d}.csv"
        )
    )
    # fixed: use _0000 naming convention for consistency with the rest of the project

    solver.DoDynamics(frame_time)

    t += frame_time
    frame += 1


# ----------------------------------------------------------------------------------------------------------------------------
# FINAL SETTLED TERRAIN OUTPUT
# ----------------------------------------------------------------------------------------------------------------------------

solver.WriteClumpFile(
    os.path.join(
        settled_dir,
        f"{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv"
    )
)
# final settled terrain used as the initial condition for later simulations
