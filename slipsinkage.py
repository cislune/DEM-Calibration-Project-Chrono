import config as c 
import DEME 
from DEME import PDSampler
import numpy as np 
import random
import os
import pandas as pd 

#0. preprocessing 

if c.USE_DEMO_WHEEL_st:
    WHEEL_RAD = c.WHEEL_RAD_DEMO_st
    WHEEL_WIDTH = c.WHEEL_WIDTH_DEMO_st
    WHEEL_WEIGHT = c.WHEEL_WEIGHT_DEMO_st
    WHEEL_MASS = c.WHEEL_MASS_DEMO_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
    WHEEL_IYY = c.WHEEL_IYY_DEMO_st
    WHEEL_IXX = c.WHEEL_IXX_DEMO_st
    WHEEL_OBJ_FILE = c.WHEEL_OBJ_FILE_DEMO_st
    TARGET_NORMAL_FORCE = c.TARGET_NORMAL_FORCE_DEMO_st
    SUPPLEMENTARY_FORCE = c.SUPPLEMENTARY_FORCE_DEMO_st
else: 
    WHEEL_RAD = c.WHEEL_RAD_st
    WHEEL_WIDTH = c.WHEEL_WIDTH_st
    WHEEL_WEIGHT = c.WHEEL_WEIGHT_st
    WHEEL_MASS = c.WHEEL_MASS_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
    WHEEL_IYY = c.WHEEL_IYY_st
    WHEEL_IXX = c.WHEEL_IXX_st
    WHEEL_OBJ_FILE = c.WHEEL_OBJ_FILE_st
    TARGET_NORMAL_FORCE = c.TARGET_NORMAL_FORCE_st
    SUPPLEMENTARY_FORCE = c.SUPPLEMENTARY_FORCE_st



os.makedirs(c.SLIP_SINKAGE_OUT_DIR, exist_ok=True)

WHEEL_REF_LINEAR_VEL = c.WHEEL_ANG_VEL_st * WHEEL_RAD

for trial_num, slip_value in enumerate(c.SLIP_VALUES_st):

    CURR_TERRAIN_RAD = BASE_TERRAIN_RAD

    #1. solver 
    solver = DEME.DEMSolver()

    solver.SetVerbosity("INFO")                                             #sets solver’s logging level to INFO, so it prints basic progress and status messages during the simulation
    solver.SetOutputFormat("CSV")                                           #sets the solver to write simulation outputs in CSV format
    solver.SetOutputContent(["XYZ"])                                        #tells solver to output particle position data (X, Y, Z coordinates) at each saved step
    solver.SetContactOutputContent(["OWNER", "FORCE", "POINT"])
    solver.SetMaxVelocity(c.MAX_VELOCITY_st)                                #sets the maximum allowed particle velocity to keep motion per time step small; limit ensures particles don’t move too far in one step, breaking contact detection laws and destabilizing the simulation
    solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)                     #sets a velocity safety threshold that aborts the simulation if particles accelerate unrealistically
    solver.SetInitTimeStep(c.STEP_SIZE_st)                                  #sets the initial simulation time step to STEP_SIZE, controlling how much sim time advances per solver update
    solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)    #applies the specified gravity vector to the simulation, accelerating all particles according to GRAVITATIONAL_ACCELERATION

    #2. mat and contact behavior 
    mat_type_terrain = solver.LoadMaterial({"E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st, "mu": c.MU_st, "Crr": c.CRR_st, "Cohesion":c.COHESION_st}) 
    mat_type_wheel = solver.LoadMaterial({"E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st, "mu": c.MU_st, "Crr": c.CRR_st}) 

    solver.SetMaterialPropertyPair("mu", mat_type_wheel, mat_type_terrain, c.MU_contact_wheel_st)
    solver.SetMaterialPropertyPair("CoR", mat_type_wheel, mat_type_terrain, c.COR_contact_wheel_st)
    solver.SetMaterialPropertyPair("Cohesion", mat_type_wheel, mat_type_terrain, c.COHESION_contact_wheel_st)

    #3. make the world and wheel 
    bin_floor_z_loc = -c.DEPTH_st/2.0                                                                                                                   #sets the vertical position of the bin floor at half the bin depth below the origin, centering terrain vertically in the simulation domain
    solver.InstructBoxDomainDimension([-c.WIDTH_st/2, c.WIDTH_st/2], [-c.LENGTH_st/2, c.LENGTH_st/2], [-c.DEPTH_st/2, c.DEPTH_st/2 + 10*WHEEL_RAD])     #defines the physical size of the simulation box (width × length × depth variables from earlier) that contains the terrain and particles
    solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)                                                                                    #sets open boundary conditions at the top of the domain; allows particles to move freely upward, while applying the terrain material to any boundary interactions; assumes region of interest is far from enclosing walls
    solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)                                                                             #adds a horizontal floor plane at bin_floor_z_loc with an upward normal, using the terrain material so particles collide with it like solid ground


    if c.USE_DEMO_WHEEL_st:
        wheel = solver.AddWavefrontMeshObject(DEME.GetDEMEDataFile(WHEEL_OBJ_FILE), mat_type_wheel, True, False)
    else:
        wheel = solver.AddWavefrontMeshObject(WHEEL_OBJ_FILE, mat_type_wheel, True, False)
    wheel.SetMass(WHEEL_MASS)
    wheel.SetMOI([WHEEL_IXX, WHEEL_IYY, WHEEL_IXX])
    wheel.SetFamily(1)

    wheel_tracker = solver.Track(wheel)


    solver.SetFamilyPrescribedAngVel(1, "0", f"{c.WHEEL_ANG_VEL_st}", "0", False)
    solver.AddFamilyPrescribedAcc(1, "none", "none", f"{(-SUPPLEMENTARY_FORCE / WHEEL_MASS)}")


    solver.SetFamilyPrescribedAngVel(2, "0", f"{c.WHEEL_ANG_VEL_st}", "0", False)
    solver.AddFamilyPrescribedAcc(2, "none", "none", f"{(-SUPPLEMENTARY_FORCE / WHEEL_MASS)}")
    slip_vel = WHEEL_REF_LINEAR_VEL * (1 - slip_value)
    solver.SetFamilyPrescribedLinVel(2, f"{slip_vel}", "0", "none", False)

    #4. terrain templates 
    template_dict = {} 
    for i in range(12):
        m = (CURR_TERRAIN_RAD**3)*c.TERRAIN_DENSITY_st*(4/3)*np.pi 
        curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)
        key = f"t{i}"
        template_dict[key] = curr_template
        CURR_TERRAIN_RAD += BASE_TERRAIN_RAD/100.0

    #============
    #NOTE: from this point on, CURR_TERRAIN_RAD is now the largest particle radius that is spawned 
    #===========

    #5. loading from csv
    df = pd.read_csv(c.SPHERE_TERRAIN_GEN_OUT_DIR + f"/{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv")
    df["clump_type"] = df["clump_type"].astype(str).str.zfill(2)

    for clump_type, g in df.groupby("clump_type"):
        
        print(clump_type)
        if clump_type not in template_dict:
            raise KeyError(f"Unknown clump_type in CSV: {clump_type}")

        xyz = g[["X", "Y", "Z"]].to_numpy(dtype=float)

        quat = g[["Qw", "Qx", "Qy", "Qz"]].to_numpy(dtype=float)

        template = template_dict[clump_type] 

        batch = solver.AddClumps(template, xyz)
        batch.SetFamilies([0]*xyz.shape[0])
        batch.SetOriQ(quat) 

    wheel.SetInitPos([0, 0, df["Z"].max() + CURR_TERRAIN_RAD + WHEEL_RAD + 0.1e-3])

    #6. initialize and run
    solver.Initialize()
  
    frame_time  = 1e-3  
    t = 0.0
    frame = 0

    solver.DoDynamicsThenSync(0)
    solver.ChangeFamily(1,2)

    os.makedirs(os.path.join(c.SLIP_SINKAGE_OUT_DIR, f"trial_{trial_num}_slip_{slip_value:09}"), exist_ok=True)
    out_dir = os.path.join(c.SLIP_SINKAGE_OUT_DIR, f"trial_{trial_num}_slip_{slip_value:09}")

    while t < c.TRIAL_RUN_TIME_SLIP_SINKAGE_st:
        if frame % 5 == 0: 
            print(f"Frame: {frame}, Trial: {trial_num}, Slip: {slip_value}")
            solver.WriteSphereFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME}_{frame:04d}.csv"))
            solver.WriteMeshFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_MOTION_WHEEL_FILE_NAME}_{frame:04d}.vtk"))

            solver.WriteContactFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_CONTACT_FORCE_FILE_NAME}_{frame:04d}.csv"))

        solver.DoDynamics(frame_time)
        t += frame_time
        frame += 1

    solver.WriteClumpFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_SETTLED_DATA_FILE_NAME}_trial_{trial_num}_slip_{slip_value:09}.csv"))
