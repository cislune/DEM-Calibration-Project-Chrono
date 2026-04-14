import config as c
import DEME
import numpy as np
import pandas as pd
import os

#0. preprocessing 
os.makedirs(c.PRESSURE_PLATE_OUT_DIR, exist_ok=True)

#1. solver 
solver = DEME.DEMSolver()
solver.SetVerbosity("INFO")
solver.SetOutputFormat("CSV")
solver.SetOutputContent(["XYZ"])
solver.SetContactOutputContent(["OWNER", "FORCE", "POINT"])

solver.SetInitTimeStep(5e-5)
solver.SetMaxVelocity(c.MAX_VELOCITY_st)
solver.SetErrorOutVelocity(c.ERROR_OUT_VELOCITY_st)
solver.SetGravitationalAcceleration(c.GRAVITATIONAL_ACCELERATION_st)

#2. mat and contact behavior
mat_type_terrain = solver.LoadMaterial({"E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st, "mu": c.MU_st, "Crr": c.CRR_st, "Cohesion":c.COHESION_st}) 
mat_type_plate = solver.LoadMaterial({"E": c.E_st, "nu": c.NU_st, "CoR": c.COR_st, "mu": c.MU_st, "Crr": c.CRR_st}) 

solver.SetMaterialPropertyPair("mu", mat_type_plate, mat_type_terrain, c.MU_contact_plate_st)

#3. make the world 
bin_floor_z_loc = -c.DEPTH_st/2.0                                                                                                                   #sets the vertical position of the bin floor at half the bin depth below the origin, centering terrain vertically in the simulation domain
solver.InstructBoxDomainDimension([-c.WIDTH_st/2, c.WIDTH_st/2], [-c.LENGTH_st/2, c.LENGTH_st/2], [-c.DEPTH_st/2, c.DEPTH_st/2 + 10*c.DOMAIN_EXPANSION_FACTOR_st])     #defines the physical size of the simulation box (width × length × depth variables from earlier) that contains the terrain and particles
solver.InstructBoxDomainBoundingBC("top_open", mat_type_terrain)                                                                                    #sets open boundary conditions at the top of the domain; allows particles to move freely upward, while applying the terrain material to any boundary interactions; assumes region of interest is far from enclosing walls
solver.AddBCPlane([0, 0, bin_floor_z_loc], [0, 0, 1], mat_type_terrain)   

#4. terrain templates 
if c.USE_DEMO_WHEEL_st:
    CURR_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_DEMO_st
else:
    CURR_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st
    BASE_TERRAIN_RAD = c.BASE_TERRAIN_RAD_st

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

terrain_top_z = df["Z"].max()

#6. plate 
plate = solver.AddWavefrontMeshObject(c.PLATE_OBJ_FILE_st, mat_type_plate, True, False)

plate.SetInitPos([0, 0, terrain_top_z + c.PLATE_THICK_st + 1e-3])
plate.SetMass(c.PLATE_MASS_st)
plate.SetMOI([c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12, c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12, c.PLATE_MASS_st * c.PLATE_THICK_st**2 / 12])
plate.SetFamily(10)
solver.SetFamilyPrescribedLinVel(10, "none", "none", f"-{c.PLATE_VEL_st}", False)
solver.SetFamilyPrescribedAngVel(10, "0", "0", "0")


plate_tracker = solver.Track(plate)

#7. inspectors 
max_z_finder = solver.CreateInspector("clump_max_z")
mass_finder  = solver.CreateInspector("clump_mass")

#8. initialize and logging preperation 
solver.Initialize()

plate_area = c.PLATE_X_st * c.PLATE_Y_st
log = []

plate_z0 = plate_tracker.Pos()[2]

t = 0.0
frame = 0
dt = 1e-3

#9. run 
while t < c.TRIAL_RUN_TIME_PRESSURE_PLATE_st:
    print(f"Frame: {frame}")
    acc = np.array(plate_tracker.ContactAcc())
    force = acc * c.PLATE_MASS_st
    Fz = force[2]

    plate_z = plate_tracker.Pos()[2]
    sinkage = plate_z0 - plate_z
    pressure = abs(Fz) / plate_area

    terrain_max_z = max_z_finder.GetValue()
    terrain_mass  = mass_finder.GetValue()

    log.append([t, plate_z, sinkage, Fz, pressure, terrain_max_z, terrain_mass])

    solver.WriteSphereFile(
            os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_MOTION_TERRAIN_FILE_NAME}_{frame:04d}.csv")
        )
    solver.WriteContactFile(
            os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_CONTACT_FORCE_FILE_NAME}_{frame:04d}.csv")
        )

    solver.WriteMeshFile(
            os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_MOTION_PLATE_FILE_NAME}_{frame:04d}.vtk")
        )   


    solver.DoDynamics(dt)
    t += dt
    frame += 1

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

solver.WriteClumpFile(os.path.join(c.PRESSURE_PLATE_OUT_DIR, f"{c.PRESSURE_PLATE_SETTLED_DATA_FILE_NAME}.csv"))
