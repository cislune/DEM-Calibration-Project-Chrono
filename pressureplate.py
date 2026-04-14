import config as c
import DEME
import numpy as np
import pandas as pd
import os

#----------------------------------------------------------------------------------------------------------------------------
# PREPROCESSING (import configuration parameters/libraries, prepare output directory and basic setup)
#----------------------------------------------------------------------------------------------------------------------------

os.makedirs(c.PRESSURE_PLATE_OUT_DIR, exist_ok=True)
    # create directory for pressure plate outputs
    # ensures persistent storage of simulation data (kinematics, contact forces, and terrain response)
    # 'exist_ok=True' prevents runtime failure if directory already exists

#----------------------------------------------------------------------------------------------------------------------------
# SOLVER SETUP (initialize DEM solver and define integration + output)
#----------------------------------------------------------------------------------------------------------------------------

solver = DEME.DEMSolver()
    # instantiate DEM solver (responsible for time integration, contact detection, and force resolution)

solver.SetVerbosity("INFO")
    # enable runtime logging to monitor solver progress and detect numerical issues

solver.SetOutputFormat("CSV")
    # set output format for particle data (facilitates post-processing in Python/MATLAB)

solver.SetOutputContent(["XYZ"])
    # output particle positions (x, y, z) at each frame
    # velocities are not directly written and must be reconstructed via temporal differentiation if required

solver.SetContactOutputContent(["OWNER", "FORCE", "POINT"])
    # output contact-level information:
        # OWNER → identifiers of interacting bodies
        # FORCE → contact force vector (normal + tangential components)
        # POINT → spatial location of contact
    # essential for analyzing stress transmission and force chains in granular media

solver.SetInitTimeStep(5e-5)
    # define numerical integration time step
    # must satisfy stability criteria (typically related to Rayleigh time step for DEM systems)

solver.SetMaxVelocity(c.MAX_VELOCITY_st)
    # impose upper bound on particle velocity to prevent non-physical behavior and numerical divergence

solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)
    # terminate simulation if velocity exceeds threshold
    # indicates instability or poor time step selection

solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)
    # apply gravitational body force (typically along negative z-direction)
    # drives consolidation and load transfer within granular assembly

#----------------------------------------------------------------------------------------------------------------------------
# MATERIAL + CONTACT MODEL (defines bulk and interaction behavior)
#----------------------------------------------------------------------------------------------------------------------------

mat_type_terrain = solver.LoadMaterial({
    "E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st,
    "mu": c.MU_st, "Crr": c.CRR_st, "Cohesion":c.COHESION_st
}) 
    # terrain material model parameters:
        # E → Young’s modulus (controls stiffness of contacts)
        # nu → Poisson’s ratio (affects deformation response)
        # mu → inter-particle friction coefficient (governs shear resistance)
        # cohesion → adhesive force between particles (important for cohesive soils)

mat_type_plate = solver.LoadMaterial({
    "E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st,
    "mu": c.MU_st, "Crr": c.CRR_st
}) 
    # plate material (assumed rigid relative to terrain, no cohesion term included)

solver.SetMaterialPropertyPair("mu", mat_type_plate, mat_type_terrain, c.MU_contact_plate_st)
    # define interface friction between plate and terrain
    # controls mobilized shear stress at contact interface → directly affects bearing capacity and resistance

#----------------------------------------------------------------------------------------------------------------------------
# DOMAIN SETUP (defines simulation boundaries and environment)
#----------------------------------------------------------------------------------------------------------------------------

bin_floor_z_loc = -c.DEPTH_st/2.0                                                                                                                   
    # sets the vertical position of the bin floor at half the bin depth below the origin, centering terrain vertically in the simulation domain
    
solver.InstructBoxDomainDimension(
    [-c.WIDTH_st/2, c.WIDTH_st/2],
    [-c.LENGTH_st/2, c.LENGTH_st/2],
    [-c.DEPTH_st/2, c.DEPTH_st/2 + 10*c.DOMAIN_EXPANSION_FACTOR_st]
)     
    # defines the physical size of the simulation box (width × length × depth variables from earlier) that contains the terrain and particles
    
solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)                                                                                    
    # sets open boundary conditions at the top of the domain
    # allows particles to move freely upward, while applying the terrain material to any boundary interactions
    # assumes region of interest is far from enclosing walls
    
solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)   
    # introduce rigid planar boundary at bottom
    # provides support reaction to balance gravitational loading and prevents particle escape

#----------------------------------------------------------------------------------------------------------------------------
# TERRAIN RECONSTRUCTION (load settled terrain from generation stage)
#----------------------------------------------------------------------------------------------------------------------------

if c.USE_DEMO_WHEEL_st:
    CURR_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
else:
    CURR_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
    # initialize particle radius based on configuration (ensures consistency with pre-generated terrain)

template_dict = {} 
for i in range(12):
    m = (CURR_TERRAIN_RAD**3)*c.TERRAIN_DENSITY_st*(4/3)*np.pi 
    curr_template = solver.LoadSphereType(m, CURR_TERRAIN_RAD, mat_type_terrain)
    key = f"t{i}"
    template_dict[key] = curr_template
    CURR_TERRAIN_RAD += BASE_TERRAIN_RAD/100.0
    # generate a set of particle templates with gradually increasing radii
    # introduces controlled polydispersity → improves packing density and realism of granular assembly

#----------------------------------------------------------------------------------------------------------------------------
# NOTE: from this point on, CURR_TERRAIN_RAD is now the largest particle radius that is spawned 
#----------------------------------------------------------------------------------------------------------------------------

df = pd.read_csv(c.SPHERE_TERRAIN_GEN_OUT_DIR + f"/{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv")
    # load previously settled terrain configuration (positions + orientations)
    # ensures repeatability and avoids recomputing initial packing

df["clump_type"] = df["clump_type"].astype(str).str.zfill(2)
    # normalize clump identifiers to match template dictionary keys

for clump_type, g in df.groupby("clump_type"):
    
    print(clump_type)
    if clump_type not in template_dict:
        raise KeyError(f"Unknown clump_type in CSV: {clump_type}")
        # consistency check between stored terrain data and template definitions

    xyz = g[["X", "Y", "Z"]].to_numpy(dtype=float)
        # extract spatial coordinates of particles

    quat = g[["Qw", "Qx", "Qy", "Qz"]].to_numpy(dtype=float)
        # extract orientation (quaternion representation avoids gimbal lock)

    template = template_dict[clump_type] 
    batch = solver.AddClumps(template, xyz)
    batch.SetFamilies([0]*xyz.shape[0])
    batch.SetOriQ(quat) 
        # reconstruct terrain exactly as generated
        # assign all terrain particles to family 0 (unconstrained, governed only by physics)

terrain_top_z = df["Z"].max()
    # determine maximum terrain elevation (reference surface for loading)

#----------------------------------------------------------------------------------------------------------------------------
# PLATE INITIALIZATION (create and configure penetration object)
#----------------------------------------------------------------------------------------------------------------------------

plate = solver.AddWavefrontMeshObject(c.PLATE_OBJ_FILE_st, mat_type_plate, True, False)
    # import plate geometry from mesh file (Wavefront .obj format)

plate.SetInitPos([0, 0, terrain_top_z + c.PLATE_THICK_st + 1e-3])
    # position plate slightly above terrain to avoid initial overlap/contact instability

plate.SetMass(c.PLATE_MASS_st)
plate.SetMOI([
    c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12,
    c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12,
    c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12
])
    # assign mass and approximate moment of inertia (rectangular plate assumption)

plate.SetFamily(10)
solver.SetFamilyPrescribedLinVel(10, "none", "none", f"-{c.PLATE_VEL_st}", False)
solver.SetFamilyPrescribedAngVel(10, "0", "0", "0")
    # assign plate to family 10 and prescribe constant downward velocity
    # enforces controlled penetration test (displacement-controlled loading)

plate_tracker = solver.Track(plate)
    # enable tracking of plate kinematics and contact response

#----------------------------------------------------------------------------------------------------------------------------
# INSPECTORS + LOGGING SETUP
#----------------------------------------------------------------------------------------------------------------------------

max_z_finder = solver.CreateInspector("clump_max_z")
mass_finder  = solver.CreateInspector("clump_mass")
    # inspectors compute global terrain properties:
    # max_z → evolving surface elevation
    # mass → total system mass (useful for validation)
    
solver.Initialize()
    # finalize solver setup (build neighbor lists, contact structures, etc.)
    # solver initialization and logging preparation 

plate_area = c.PLATE_X_st * c.PLATE_Y_st
    # compute contact area of plate (used to convert force → pressure)

log = []
    # initialize storage for time history data

plate_z0 = plate_tracker.Pos()[2]
    # record initial plate height (reference for sinkage computation)initialize and logging preperation 

t = 0.0
frame = 0
dt = 1e-3
    # initialize simulation time variables

#----------------------------------------------------------------------------------------------------------------------------
# SIMULATION EXECUTION (time integration and output)
#----------------------------------------------------------------------------------------------------------------------------

while t < c.TRIAL_RUN_TIME_PRESSURE_PLATE_st:
    print(f"Frame: {frame}")
        # output current simulation frame for monitoring

    acc = np.array(plate_tracker.ContactAcc())
    force = acc * c.PLATE_MASS_st
    Fz = force[2]
        # compute resultant contact force via Newton’s second law (F = m·a)
        # vertical component corresponds to bearing resistance

    plate_z = plate_tracker.Pos()[2]
    sinkage = plate_z0 - plate_z
    pressure = abs(Fz) / plate_area
        # sinkage → penetration depth into terrain
        # pressure → average normal stress applied by plate

    terrain_max_z = max_z_finder.GetValue()
    terrain_mass  = mass_finder.GetValue()
        # retrieve updated terrain state variables

    log.append([t, plate_z, sinkage, Fz, pressure, terrain_max_z, terrain_mass])
        # store simulation data for post-processing and analysis

    solver.WriteSphereFile(
        os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_MOTION_TERRAIN_FILE_NAME}_{frame:04d}.csv")
    )
        # export terrain particle positions (used for deformation analysis)

    solver.WriteContactFile(
        os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_CONTACT_FORCE_FILE_NAME}_{frame:04d}.csv")
    )
        # export contact force network (used to study stress distribution)

    solver.WriteMeshFile(
        os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_MOTION_PLATE_FILE_NAME}_{frame:04d}.vtk")
    )   
        # export plate motion (visualization in ParaView or similar tools)

    solver.DoDynamics(dt)
    t += dt
    frame += 1
        # advance simulation by one time step

#----------------------------------------------------------------------------------------------------------------------------
# OUTPUT (save results for post-processing)
#----------------------------------------------------------------------------------------------------------------------------

pd.DataFrame(
    log,
    columns=[
        "time",
        "plate_z",
        "sinkage",
        "Fz",
        "pressure",
        "terrain_max_z",
        "terrain_mass"
    ]
).to_csv(
    os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_RESPONSE_FILE_NAME}.csv"),
    index=False
)
    # save time history of plate response (force–sinkage–pressure relationship)

solver.WriteClumpFile(os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_SETTLED_DATA_FILE_NAME}.csv"))
    # export final terrain configuration after loading
    # useful for analyzing permanent deformation and densification
