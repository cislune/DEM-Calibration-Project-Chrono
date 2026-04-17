import config as c
import DEME
from DEME import PDSampler
import numpy as np
import random
import os

#----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (prepares output directory, selects particle-size scale for terrain, initializes parameters to build solver)
#----------------------------------------------------------------------------------------------------------------------------

os.makedirs(c.SPHERE_TERRAIN_GEN_OUT_DIR, exist_ok=True)
# create terrain-generation output directory if it does not already exist
# define where intermediate settling frames and the final settled terrain state will be written to

motion_dir = os.path.join(c.SPHERE_TERRAIN_GEN_OUT_DIR, "motion")
settled_dir = os.path.join(c.SPHERE_TERRAIN_GEN_OUT_DIR, "settled data")
# create dedicated subdirectories for terrain-generation outputs
# keeps time-resolved settling motion separate from the final settled terrain state

os.makedirs(motion_dir, exist_ok=True)
os.makedirs(settled_dir, exist_ok=True)
# ensure all terrain-generation output directories exist before writing files

SEED = 77
# random-number generator seed; used to make initial particle placement reproducible, and for easy debugging, validation, and data analysis

if c.USE_DEMO_WHEEL_st:
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
else:
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
# base terrain particle radius selection
# terrain particle scale is tied to whether the demo wheel or the user-defined wheel configuration is being used, so that the terrain resolution remains consistent

CURR_TERRAIN_RAD = BASE_TERRAIN_RAD
# initialize current particle radius
# incremented while particle templates are built, to introduce a small particle size distribution (PSD) in the terrain and avoid a perfectly uniform PSD (more realistic)
    
#----------------------------------------------------------------------------------------------------------------------------
# SOLVER SETUP (initializes DEM solver and defines time integration + simulation output)
#----------------------------------------------------------------------------------------------------------------------------

solver = DEME.DEMSolver()
# instantiate the DEM solver
# handles particle dynamics, contact physics, material behavior, boundary conditions, and output computation

solver.SetVerbosity("INFO")
# set solver logging level to INFO
# provides progress and status messages during execution without producing excessive debug output

solver.SetOutputFormat("CSV")
# set .csv output format for particle data

solver.SetOutputContent(["XYZ"])
# set solver to output (x,y,z) particle positions at each frame
# velocities can be derived from this output for further data analysis

solver.SetMaxVelocity(c.MAX_VELOCITY_st)
# set velocity cap to maintain numerical stability
# excessively large velocities can cause particles to move too far in a single time step sometimes, which can degrade contact detection and destabilize the run.

solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)
# define hard velocity threshold that terminates the run if exceeded
# safety check to ensure particles don't accelerate to unrealistic speeds

solver.SetInitTimeStep(c.STEP_SIZE_st)
# set initial integration time step
# time step controls physical time elapsed per solver update (smaller values improve stability/fidelity, but they increase computational runtime)

solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)
# apply the global gravity vector to the simulation.
# in this configuration, gravity acts in the negative z direction

#----------------------------------------------------------------------------------------------------------------------------
# MATERIAL DEFINITION (defines the contact material assigned to the terrain particles)
#----------------------------------------------------------------------------------------------------------------------------

mat_type_terrain = solver.LoadMaterial({
    "E": c.E_st,
    "nu": c.NU_st,
    "CoR": c.COR_st,
    "mu": c.MU_st,
    "Crr": c.CRR_st,
    "Cohesion": c.COHESION_st
})
# load the terrain material model into the solver 
# parameters define elastic stiffness, Poisson response, restitution, sliding friction, rolling resistance, and cohesion

#----------------------------------------------------------------------------------------------------------------------------
# DOMAIN AND BOUNDARY CONDITIONS (defines simulation box boundary conditions to confine terrain during generation/settling)
#----------------------------------------------------------------------------------------------------------------------------

bin_floor_z_loc = -c.DEPTH_st / 2.0
# set z-location of the bin floor
# domain is centered vertically about the origin, so the bottom boundary is placed at negative half-depth.

solver.InstructBoxDomainDimension(
    [-c.WIDTH_st / 2, c.WIDTH_st / 2],
    [-c.LENGTH_st / 2, c.LENGTH_st / 2],
    [-c.DEPTH_st / 2, c.DEPTH_st / 2 + 1000 * CURR_TERRAIN_RAD]
)
# define the 3-D extents of the simulation domain
# x spans bin width, y spans the bin length, and z spans from the bottom of the bin to a height above the terrain
# top of the domain is extended upward by a large multiple of particle radius so there is ample vertical space for particle placement and settling

solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)
# apply domain boundary conditions with an open top.
# keeps the side/lower boundaries active while allowing the top of the domain to remain open, so particles can settle naturally without being artificially constrained.

solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)
# add a rigid floor plane at the bottom of the domain.
# the plane normal points upward so particles contact it as they settle under gravity
    
#----------------------------------------------------------------------------------------------------------------------------
# PARTICLE TEMPLATES / SIZE DISTRIBUTION (creates small family of spherical particle templates for polydisperse distribution)
#----------------------------------------------------------------------------------------------------------------------------

templates_terrain = []

for i in range(12):
    m = (CURR_TERRAIN_RAD**3) * c.TERRAIN_DENSITY_st * (4 / 3) * np.pi
    # compute the mass for a sphere of the current radius
    # uses sphere volume (4/3 * pi * r^3) multiplied by terrain density

    curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)
    # create spherical particle template with the specified mass, radius, and material properties

    curr_template.AssignName(f"t{i}")
    # assign name to generated template so different particle sizes can be identified later if required

    templates_terrain.append(curr_template)
    # store generated template for later use during particle placement

    CURR_TERRAIN_RAD += BASE_TERRAIN_RAD / 100.0
    # slightly increase radius before creating the next template
    # produces a narrow particle-size distribution, which helps reduce
    # artificial ordering and can better represent granular media.

# At the end of this loop, CURR_TERRAIN_RAD will have advanced to the largest particle radius represented in the template set

#----------------------------------------------------------------------------------------------------------------------------
# INITIAL PARTICLE PLACEMENT (fills bin by sampling horizontal layers bottom upward, assigns particle template to sampled position)
#----------------------------------------------------------------------------------------------------------------------------

rng = random.Random()
rng.seed(SEED)
# create and seed a local random number generator
# used to assign particle templates in a reproducible manner
    
sampler = PDSampler(2.01 * CURR_TERRAIN_RAD)
# create a Poisson disk sampler
# spacing parameter enforces a minimum center-to-center separation between candidate particles to avoid severe initial overlap during spawning

SAMPLE_HALFWIDTH_X = (c.WIDTH_st / 2) - 2 * CURR_TERRAIN_RAD
SAMPLE_HALFWIDTH_Y = (c.LENGTH_st / 2) - 2 * CURR_TERRAIN_RAD
# define the half-widths of the sampling region in x and y
# spawning region is reduced relative to domain to keep particle centers away from boundaries to avoid initial overlap and non-physical boundary interactions

sample_z = (-(c.DEPTH_st / 2)) + 2 * CURR_TERRAIN_RAD
# starts the first sampling layer slightly above the floor
# avoids immediate penetration of particles into the bottom boundary

num_particle = 0
# Running count of all particles placed into the terrain.

while sample_z < c.FULL_HEIGHT_st:
    sample_center = np.array([0.0, 0.0, sample_z])
    # center of the current sampling layer

    sample_region = np.array([SAMPLE_HALFWIDTH_X, SAMPLE_HALFWIDTH_Y, 1e-6])
    # defines an extremely thin box region so the sampler effectively places particles in a horizontal layer

    particle_xyz = sampler.SampleBox(sample_center, sample_region)
    # generates particle-center locations for the current layer.

    selected_templates = [
        templates_terrain[rng.randrange(len(templates_terrain))]
        for _ in range(len(particle_xyz))
    ]
    # randomly assigns one of the predefined sphere templates to each sampled particle location
    # gives the terrain a mixture of particle sizes

    solver.AddClumps(selected_templates, particle_xyz)
    # adds sampled particles to the solver
    # even though these are spheres, the API uses the generic clump interface for particle insertion

    num_particle += len(particle_xyz)
    # updates total particle count

    sample_z += 4.01 * CURR_TERRAIN_RAD
    # moves upward to next sampling layer
    # layer spacing is intentionally larger than close-packing spacing to reduce the number of inserted particles and improve computational efficiency during initial generation

print(f"total num of particles: {num_particle}")
# reports number of particles spawned into the terrain bed

#----------------------------------------------------------------------------------------------------------------------------
# SOLVER INITIALIZATION ( solver is initialized to begin contact resolution and time integration)
#----------------------------------------------------------------------------------------------------------------------------

solver.Initialize()
# finalizes model setup and prepares the system for dynamics

#----------------------------------------------------------------------------------------------------------------------------
# TERRAIN SETTLING / DYNAMIC RELAXATION (settles particles under gravity, transforms particle cloud into granular bed)
#----------------------------------------------------------------------------------------------------------------------------

settle_time = 1.0
# total physical time allowed for settling

frame_time = 1e-3
# time interval between saved frames and solver updates in this outer loop

t = 0.0
frame = 0
# initializes simulation clock and frame counter

while t < settle_time:
    print(f"Frame: {frame}")
    # prints current frame index for progress tracking

    solver.WriteSphereFile(
        os.path.join(
            motion_dir,
            f"{c.SPHERE_TERRAIN_GENERATION_MOTION_FILE_NAME}{frame:04d}.csv"
        )
    )
    # writes current particle positions to disk
    # files provide a time-resolved record of how the terrain settles, which can later be used for visualization or post-processing

    solver.DoDynamics(frame_time)
    # advances DEM simulation by one frame interval

    t += frame_time
    # advances physical simulation time

    frame += 1
    # increment output frame counter

#----------------------------------------------------------------------------------------------------------------------------
# FINAL SETTLED TERRAIN OUTPUT (writes final terrain state after settling, initial condition for subsequent tests)
#----------------------------------------------------------------------------------------------------------------------------

solver.WriteClumpFile(
    os.path.join(
        settled_dir,
        f"{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv"
    )
)
# saves final settled particle/clump state to disk
# output preserves the end-of-settling geometry and particle orientation data needed to reconstruct the terrain in later simulations
