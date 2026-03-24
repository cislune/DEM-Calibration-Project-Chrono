import config as c 
import DEME 
from DEME import PDSampler
import numpy as np 
import random
import os

#0. preprocessing 
os.makedirs(c.SPHERE_TERRAIN_GEN_OUT_DIR, exist_ok=True)
SEED = 77                                                   #to be able to reproduce results using random generator 

if c.USE_DEMO_WHEEL_st:
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
else:
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st

CURR_TERRAIN_RAD = BASE_TERRAIN_RAD

#1. solver 
solver = DEME.DEMSolver()

solver.SetVerbosity("INFO")                                             #sets solver’s logging level to INFO, so it prints basic progress and status messages during the simulation
solver.SetOutputFormat("CSV")                                           #sets the solver to write simulation outputs in CSV format
solver.SetOutputContent(["XYZ"])                                        #tells solver to output particle position data (X, Y, Z coordinates) at each saved step
solver.SetMaxVelocity(c.MAX_VELOCITY_st)                                #sets the maximum allowed particle velocity to keep motion per time step small; limit ensures particles don’t move too far in one step, breaking contact detection laws and destabilizing the simulation
solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)                     #sets a velocity safety threshold that aborts the simulation if particles accelerate unrealistically
solver.SetInitTimeStep(c.STEP_SIZE_st)                                  #sets the initial simulation time step to c.STEP_SIZE_st, controlling how much sim time advances per solver update
solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)    #applies the specified gravity vector to the simulation, accelerating all particles according to c.GRAVITATIONAL_ACCELERATION_st

#2. material 
mat_type_terrain = solver.LoadMaterial({"E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st, "mu": c.MU_st, "Crr": c.CRR_st, "Cohesion":c.COHESION_st}) 

#3. make the world 
bin_floor_z_loc = -c.DEPTH_st/2.0                                                                                                                           #sets the vertical position of the bin floor at half the bin c.depth_st below the origin, centering terrain vertically in the simulation domain
solver.InstructBoxDomainDimension([-c.WIDTH_st/2, c.WIDTH_st/2], [-c.LENGTH_st/2, c.LENGTH_st/2], [-c.DEPTH_st/2, c.DEPTH_st/2 + 1000*CURR_TERRAIN_RAD])    #defines the physical size of the simulation box (c.width_st × c.length_st × c.depth_st variables from earlier) that contains the terrain and particles
solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)                                                                                            #sets open boundary conditions at the top of the domain; allows particles to move freely upward, while applying the terrain material to any boundary interactions; assumes region of interest is far from enclosing walls
solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)                                                                                     #adds a horizontal floor plane at bin_floor_z_loc with an upward normal, using the terrain material so particles collide with it like solid ground

#4. terrain templates 
templates_terrain = [] 
for i in range(12):
    m = (CURR_TERRAIN_RAD**3)*c.TERRAIN_DENSITY_st*(4/3)*np.pi 
    curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)
    curr_template.AssignName(f"t{i}")
    templates_terrain.append(curr_template)
    CURR_TERRAIN_RAD += BASE_TERRAIN_RAD/100.0

#============
#NOTE: from this point on, CURR_TERRAIN_RAD is now the largest particle radius that is spawned 
#===========

#5. terrain generation 
rng = random.Random()
rng.seed(SEED)
sampler = PDSampler(2.01 * CURR_TERRAIN_RAD)                #set min center-to-center spacing for the sampler/spawner  

SAMPLE_HALFWIDTH_X = (c.WIDTH_st/2) - 2*CURR_TERRAIN_RAD
SAMPLE_HALFWIDTH_Y = (c.LENGTH_st/2) - 2*CURR_TERRAIN_RAD
sample_z = (-(c.DEPTH_st/2)) + 2*CURR_TERRAIN_RAD               #start first sampling layer a bit above the ground 
num_particle = 0

while sample_z < (c.FULL_HEIGHT_st):
    sample_center = np.array([0.0, 0.0, sample_z])
    sample_region = np.array([SAMPLE_HALFWIDTH_X, SAMPLE_HALFWIDTH_Y, 1e-6])

    particle_xyz = sampler.SampleBox(sample_center, sample_region)

    selected_templates = [ templates_terrain[rng.randrange(len(templates_terrain))]for _ in range(len(particle_xyz))]

    solver.AddClumps(selected_templates, particle_xyz)
    num_particle += len(particle_xyz)
    sample_z += 4.01 * CURR_TERRAIN_RAD #2.01 * CURR_TERRAIN_RAD #NOTE: changed it to 4 for computational efficiency 

print(f"total num of particles: {num_particle}")

#6. initialize 
solver.Initialize() 

#7. settle 
settle_time = 1.0     
frame_time  = 1e-3  
t = 0.0
frame = 0

while t < settle_time:
    print(f"Frame: {frame}")
    solver.WriteSphereFile(os.path.join(c.SPHERE_TERRAIN_GEN_OUT_DIR, f"{c.SPHERE_TERRAIN_GENERATION_MOTION_FILE_NAME}{frame:04d}.csv"))
    solver.DoDynamics(frame_time)
    t += frame_time
    frame += 1

solver.WriteClumpFile(os.path.join(c.SPHERE_TERRAIN_GEN_OUT_DIR, f"{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv"))
