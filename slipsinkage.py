import config as c 
import DEME 
from DEME import PDSampler
import numpy as np 
import random
import os
import pandas as pd 

#----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (selects wheel/terrain configuration, prepares output directory, defines reference kinematics)
#----------------------------------------------------------------------------------------------------------------------------

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
    # select wheel and terrain parameters (demo vs user-defined)
    # ensures consistency between terrain resolution and wheel scale

os.makedirs(c.SLIP_SINKAGE_OUT_DIR, exist_ok=True)
    # create directory for slip–sinkage outputs (one subfolder per trial)
    # exist_ok=True prevents crash if directory already exists

WHEEL_REF_LINEAR_VEL = c.WHEEL_ANG_VEL_st * WHEEL_RAD
    # reference rolling velocity (v = ωR)
    # represents the forward velocity corresponding to pure rolling (zero slip)
    # used as baseline to compute slip-controlled translational velocity

#----------------------------------------------------------------------------------------------------------------------------
# TRIAL LOOP (runs independent simulations for each slip value)
#----------------------------------------------------------------------------------------------------------------------------

for trial_num, slip_value in enumerate(c.SLIP_VALUES_st):

    CURR_TERRAIN_RAD = BASE_TERRAIN_RAD
    # reset terrain particle radius for template reconstruction (must match generation stage)
    # ensures terrain geometry consistency across trials

#------------------------------------------------------------------------------------------------------------------------
# SOLVER SETUP (initializes DEM solver and defines integration + output)
#------------------------------------------------------------------------------------------------------------------------

    solver = DEME.DEMSolver()
        # instantiate DEM solver (handles time integration, contact resolution, and output)
        # central engine controlling physics simulation

    solver.SetVerbosity("INFO")
        # enable solver progress output
        # useful for debugging and monitoring runtime

    solver.SetOutputFormat("CSV")
        # set particle output format to CSV (used for analysis/post-processing)
        # allows easy import into Python/MATLAB

    solver.SetOutputContent(["XYZ"])
        # output particle positions (x, y, z)
        # velocities are not written directly and must be derived from time history if required
        # reduces file size compared to full state output

    solver.SetContactOutputContent(["OWNER", "FORCE", "POINT"])
        # output contact-level data:
            # OWNER → interacting bodies
            # FORCE → contact force vector
            # POINT → contact location
        # essential for traction and stress analysis

    solver.SetMaxVelocity(c.MAX_VELOCITY_st)
        # limit particle velocities to maintain numerical stability
        # prevents divergence in high-energy contacts

    solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)
        # terminate simulation if velocities exceed threshold; instability detection)
        # acts as safety check for exploding simulations

    solver.SetInitTimeStep(c.STEP_SIZE_st)
        # define integration time step (controls resolution vs computational cost)
        # smaller timestep → more accurate but slower simulation

    solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)
        # apply gravity (z-down)
        # drives terrain settling and wheel loading

#------------------------------------------------------------------------------------------------------------------------
# MATERIAL + CONTACT MODEL (defines bulk and interaction behavior)
#------------------------------------------------------------------------------------------------------------------------

    mat_type_terrain = solver.LoadMaterial({
        "E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st,
        "mu": c.MU_st, "Crr": c.CRR_st, "Cohesion": c.COHESION_st
    })
        # terrain material (elastic + frictional + cohesive granular behavior)
        # E → stiffness, nu → Poisson ratio
        # mu → internal friction, cohesion → particle bonding

    mat_type_wheel = solver.LoadMaterial({
        "E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st,
        "mu": c.MU_st, "Crr": c.CRR_st
    })
        # wheel material (typically rigid, no cohesion)
        # same base properties but without cohesion term

    solver.SetMaterialPropertyPair("mu", mat_type_wheel, mat_type_terrain, c.MU_contact_wheel_st)
    solver.SetMaterialPropertyPair("CoR", mat_type_wheel, mat_type_terrain, c.COR_contact_wheel_st)
    solver.SetMaterialPropertyPair("Cohesion", mat_type_wheel, mat_type_terrain, c.COHESION_contact_wheel_st)
        # define wheel–terrain interaction: friction → traction limit, restitution → impact energy loss, cohesion → adhesive interaction (if present)
        # overrides default material interaction for this pair

#------------------------------------------------------------------------------------------------------------------------
# DOMAIN + WHEEL INITIALIZATION
#------------------------------------------------------------------------------------------------------------------------

    bin_floor_z_loc = -c.DEPTH_st / 2.0
        # bottom of domain (centers terrain vertically)
        # ensures symmetric domain setup

    solver.InstructBoxDomainDimension(
        [-c.WIDTH_st/2, c.WIDTH_st/2],
        [-c.LENGTH_st/2, c.LENGTH_st/2],
        [-c.DEPTH_st/2, c.DEPTH_st/2 + 10 * WHEEL_RAD]
    )
        # define simulation domain
        # top extended slightly above terrain to allow wheel motion
        # prevents clipping of wheel during motion

    solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)
        # open top boundary (no confinement from above)
        # allows particles to move freely upward if needed

    solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)
        # rigid floor boundary (supports terrain under gravity)
        # normal vector [0,0,1] defines upward-facing plane

    if c.USE_DEMO_WHEEL_st:
        wheel = solver.AddWavefrontMeshObject(DEME.GetDEMEDataFile(WHEEL_OBJ_FILE), mat_type_wheel, True, False)
    else:
        wheel = solver.AddWavefrontMeshObject(WHEEL_OBJ_FILE, mat_type_wheel, True, False)
        # load wheel geometry from mesh file
        # Wavefront (.obj) used for complex geometry representation

    wheel.SetMass(WHEEL_MASS)
    wheel.SetMOI([WHEEL_IXX, WHEEL_IYY, WHEEL_IXX])
        # assign physical properties (mass + inertia)
        # inertia affects rotational response

    wheel.SetFamily(1)
    wheel_tracker = solver.Track(wheel)
        # assign family ID (used for motion control) and enable tracking
        # tracking allows retrieval of kinematic data

#------------------------------------------------------------------------------------------------------------------------
# MOTION PRESCRIPTION + SLIP CONTROL
#------------------------------------------------------------------------------------------------------------------------

    solver.SetFamilyPrescribedAngVel(1, "0", f"{c.WHEEL_ANG_VEL_st}", "0", False)
        # prescribe constant angular velocity (wheel rotation)
        # rotation about y-axis (assuming standard coordinate system)

    solver.AddFamilyPrescribedAcc(1, "none", "none", f"{(-SUPPLEMENTARY_FORCE / WHEEL_MASS)}")
        # apply vertical acceleration to achieve target normal load
        # simulates additional loading beyond gravity

    solver.SetFamilyPrescribedAngVel(2, "0", f"{c.WHEEL_ANG_VEL_st}", "0", False)
    solver.AddFamilyPrescribedAcc(2, "none", "none", f"{(-SUPPLEMENTARY_FORCE / WHEEL_MASS)}")
        # duplicated setup for family 2 (activated after initialization)

    slip_vel = WHEEL_REF_LINEAR_VEL * (1 - slip_value)
        # compute forward velocity for given slip ratio:
        # s = 1 - (v / (ωR)) → v = (1 - s)(ωR)
        # slip_value = 0 → pure rolling, slip_value = 1 → full slip

    solver.SetFamilyPrescribedLinVel(2, f"{slip_vel}", "0", "none", False)
        # impose translational velocity to enforce desired slip condition
        # ensures controlled slip experiments

#------------------------------------------------------------------------------------------------------------------------
# TERRAIN RECONSTRUCTION (load settled terrain from generation stage)
#------------------------------------------------------------------------------------------------------------------------

    template_dict = {}
        # dictionary mapping clump types to DEM templates

    for i in range(12):
        m = (CURR_TERRAIN_RAD**3) * c.TERRAIN_DENSITY_st * (4/3) * np.pi
        curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)
        template_dict[f"t{i}"] = curr_template
        CURR_TERRAIN_RAD += BASE_TERRAIN_RAD / 100.0
        # recreate particle templates consistent with terrain generation
        # slight radius variation introduces polydispersity

    df = pd.read_csv(c.SPHERE_TERRAIN_GEN_OUT_DIR + f"/{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv")
        # load settled terrain state (positions + orientations)
        # ensures repeatability across simulations

    df["clump_type"] = df["clump_type"].astype(str).str.zfill(2)
        # standardize clump type formatting (e.g., '01', '02')

    for clump_type, g in df.groupby("clump_type"):

        if clump_type not in template_dict:
            raise KeyError(f"Unknown clump_type in CSV: {clump_type}")
        # safety check for mismatched templates

        xyz = g[["X", "Y", "Z"]].to_numpy(dtype=float)
        quat = g[["Qw", "Qx", "Qy", "Qz"]].to_numpy(dtype=float)
        # extract positions and orientations

        template = template_dict[clump_type]

        batch = solver.AddClumps(template, xyz)
        batch.SetFamilies([0] * xyz.shape[0])
        batch.SetOriQ(quat)
        # reconstruct terrain geometry exactly as generated (positions + orientations)

    wheel.SetInitPos([0, 0, df["Z"].max() + CURR_TERRAIN_RAD + WHEEL_RAD + 0.1e-3])
        # place wheel just above terrain surface (avoid initial penetration)
        # small offset prevents numerical instability

#------------------------------------------------------------------------------------------------------------------------
# SIMULATION EXECUTION (time integration and output)
#------------------------------------------------------------------------------------------------------------------------

    solver.Initialize()
        # finalize system and prepare for dynamics
        # builds internal data structures

    frame_time = 1e-3  
    t = 0.0
    frame = 0
        # initialize simulation time tracking

    solver.DoDynamicsThenSync(0)
    solver.ChangeFamily(1, 2)
        # activate prescribed motion for wheel
        # switching family enables motion constraints

    os.makedirs(os.path.join(c.SLIP_SINKAGE_OUT_DIR, f"trial_{trial_num}_slip_{slip_value:09}"), exist_ok=True)
    out_dir = os.path.join(c.SLIP_SINKAGE_OUT_DIR, f"trial_{trial_num}_slip_{slip_value:09}")
        # create output directory for this specific trial

    while t < c.TRIAL_RUN_TIME_SLIP_SINKAGE_st:

        if frame % 5 == 0:
            print(f"Frame: {frame}, Trial: {trial_num}, Slip: {slip_value}")
            # periodic logging for progress monitoring

            solver.WriteSphereFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME}_{frame:04d}.csv"))
            # terrain particle positions
            # used for deformation/sinkage analysis

            solver.WriteMeshFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_MOTION_WHEEL_FILE_NAME}_{frame:04d}.vtk"))
            # wheel mesh motion (VTK for visualization)
            # compatible with ParaView

            solver.WriteContactFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_CONTACT_FORCE_FILE_NAME}_{frame:04d}.csv"))
            # contact forces between wheel and terrain
            # key for traction and stress distribution

        solver.DoDynamics(frame_time)
        t += frame_time
        frame += 1
        # advance simulation in time

    solver.WriteClumpFile(os.path.join(out_dir, f"{c.SLIP_SINKAGE_TRIALS_SETTLED_DATA_FILE_NAME}_trial_{trial_num}_slip_{slip_value:09}.csv"))
        # save final terrain state after slip–sinkage interaction
        # useful for post-run comparison between slip conditions
