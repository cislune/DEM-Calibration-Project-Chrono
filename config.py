import numpy as np 

#----------------------------------------------------------------------------------------------------------------------------
# SIMULATION MODE CONFIGURATION (defines test parameters + terrain representation)
#---------------------------------------------------------------------------------------------------------------------------- 

MOVIE_TYPES_LIST = ["generation", "slip", "pressure_plate"]
# generation → settle particles to form terrain
# slip → wheel slip/sinkage test
# pressure_plate → plate penetration test

TERRAIN_TYPES_LIST = ["sphere"]  
# particle-based terrain (discrete spheres)

MOVIE_TYPE = MOVIE_TYPES_LIST[0]  
# select experiment type (default: terrain generation)
# [1] → slip
# [2] → plate penetration

TERRAIN_TYPE = TERRAIN_TYPES_LIST[0]  
# terrain representation (sphere-based)

DEFAULT_FRAMERATE = 60
# output visualization frame rate (frames per second, fps)

MOVIE_OUT_DIR = "./movies"  
# directory for rendered simulation outputs
    

# SPHERE TERRAIN OUTPUT PATHS (file and directory names for sphere-terrain simulation outputs)

# terrain generation outputs
SPHERE_TERRAIN_GEN_OUT_DIR = "./sphere_tgen_output"
# directory where terrain generation outputs are written
    
SPHERE_TERRAIN_GENERATION_MOTION_FILE_NAME = "sphere_terrain_settling_motion"
# time-resolved particle motion during terrain settling (positions vs time, used to then calculate velocities)
    
SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME = "settled_sphere_terrain_data"
# final settled particle state after generation (used as initial condition for later tests)

# slip-sinkage experiment outputs
SLIP_SINKAGE_OUT_DIR = "./slip_sinkage_output/sphere_particles"
# directory where slip–sinkage simulation outputs are written

SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME = "sphere_terrain_slip_sinkage_trials_motion_terrain"
# time-resolved terrain particle positions during slip-sinkage trials

SLIP_SINKAGE_TRIALS_MOTION_WHEEL_FILE_NAME = "sphere_terrain_slip_sinkage_trials_motion_wheel"
# time-resolved wheel kinematics and mesh motion

SLIP_SINKAGE_TRIALS_CONTACT_FORCE_FILE_NAME = "sphere_terrain_slip_sinkage_trials_contact_force"
# contact forces between wheel and terrain over time

SLIP_SINKAGE_TRIALS_SETTLED_DATA_FILE_NAME = "sphere_terrain_slip_sinkage_trials_settled_data"
# settled terrain state, used as initial condition for slip–sinkage trials

# pressure-plate experiment outputs
PRESSURE_PLATE_MOTION_TERRAIN_FILE_NAME = "sphere_terrain_pressure_plate_motion_terrain"
# time-resolved terrain particle positions written per frame as a .csv file

PRESSURE_PLATE_CONTACT_FORCE_FILE_NAME = "sphere_terrain_pressure_plate_contact_force"
# time-resolved plate–terrain contact data written per frame (contact ownership, force, and contact point)

PRESSURE_PLATE_RESPONSE_FILE_NAME = "sphere_terrain_pressure_plate_response"
# processed pressure-plate response data (time, plate position, sinkage, vertical force, pressure, terrain height, terrain mass)

PRESSURE_PLATE_SETTLED_DATA_FILE_NAME = "sphere_terrain_pressure_plate_settled_data"
# final terrain state at the end of the pressure-plate simulation

PRESSURE_PLATE_MOTION_PLATE_FILE_NAME = "sphere_terrain_pressure_plate_motion_plate"
# time-resolved plate mesh output written per frame as VTK
    
#----------------------------------------------------------------------------------------------------------------------------
# SOLVER / NUMERICAL INTEGRATION SETTINGS	
#----------------------------------------------------------------------------------------------------------------------------

MAX_VELOCITY_st = 30  
# velocity cap to maintain numerical stability and avoid missed contacts

ERROR_OUT_VELOCITY_st = 30  
# hard cutoff: abort simulation if exceeded (indicates instability)

G_MAG_st = 9.81  
# gravitational acceleration magnitude (m/s^2)

GRAVITATIONAL_ACCELERATION_st = [0, 0, -G_MAG_st]  
# gravity vector (z-down convention)

STEP_SIZE_st = 5e-6  
# time step size (s); small values improve simulation stability and fidelity, at the cost of runtime

TRIAL_RUN_TIME_SLIP_SINKAGE_st = 5.0  
# duration/total simulation time for each experiment (s)
TRIAL_RUN_TIME_PRESSURE_PLATE_st = 5.0  
# duration/total simulation time for each experiment (s)

DOMAIN_EXPANSION_FACTOR_st = 4.0  
# expands computational domain to mitigate boundary effects
# prevents artificial interactions with domain walls that can influence contact forces and material response

#----------------------------------------------------------------------------------------------------------------------------
# MATERIAL PROPERTIES: PARTICLE TERRAIN (defines bulk and contact behavior of the granular medium)
#----------------------------------------------------------------------------------------------------------------------------

E_st = 1e5  
# Young’s Modulus (Pa): controls elastic stiffness during contact (normal force–displacement response)

NU_st = 0.24  
# Poisson’s Ratio: ratio of lateral to axial strain under loading (affects contact deformation behavior)

COR_st = 0.9  
# Coefficient of Restitution: fraction of normal relative velocity recovered after collision (controls energy loss)

MU_st = 0.3  
# Static Friction Coefficient: threshold ratio of tangential to normal force for onset of sliding

CRR_st = 0.1  
# Rolling Resistance Coefficient: resists relative rolling motion at contacts due to deformation and energy dissipation

COHESION_st = 50.0  
# Cohesive strength: resistance to shear separation

TERRAIN_DENSITY_st = 2.5e3  
# Bulk density (kg/m^3): used to compute particle mass

#----------------------------------------------------------------------------------------------------------------------------
# OBJECT-SPECIFIC CONTACT PARAMETERS
#----------------------------------------------------------------------------------------------------------------------------

MU_contact_wheel_st = 0.8  
# wheel–terrain friction coefficient: sets the Coulomb limit (max tangential force = μ·normal force)

COR_contact_wheel_st = 0.6  
# wheel–terrain coefficient of restitution: controls normal velocity recovery and impact energy loss at contacts

COHESION_contact_wheel_st = 50.0  
# wheel–terrain cohesive strength (Pa or equivalent): adds adhesive normal/tangential resistance independent of load

MU_contact_plate_st = 0.5  
# plate–terrain friction coefficient: limits tangential shear force at the plate–terrain interface

#----------------------------------------------------------------------------------------------------------------------------
# WHEEL CONFIGURATION
#----------------------------------------------------------------------------------------------------------------------------

USE_DEMO_WHEEL_st = True  
# if True, use the predefined reference wheel configuration below 
# if False, use the user-defined wheel parameters in the next section


# DEMO WHEEL (REFERENCE CONFIGURATION)
# predefined wheel setup used for verification, debugging, and baseline testing
# provides a stable reference case before introducing custom wheel geometry or loading

WHEEL_RAD_DEMO_st = 0.25        
# demo wheel radius (m); sets the outer size of the wheel and affects contact geometry and sinkage behavior

WHEEL_WIDTH_DEMO_st = 0.2       
# demo wheel width (m); sets the lateral contact width with the terrain

WHEEL_WEIGHT_DEMO_st = 100.0    
# demo wheel weight (N); gravitational load applied by the wheel

WHEEL_MASS_DEMO_st = WHEEL_WEIGHT_DEMO_st / G_MAG_st  
# demo wheel mass (kg), computed from weight using gravitational acceleration magnitude set earlier

WHEEL_IYY_DEMO_st = WHEEL_MASS_DEMO_st * ((WHEEL_RAD_DEMO_st**2)/2)  
# mass moment of inertia about the wheel spin axis (kg*m^2) 
# governs resistance to angular acceleration during rolling (aka how hard it is to change how fast the wheel is spinning)

WHEEL_IXX_DEMO_st = (WHEEL_MASS_DEMO_st/12)*((3*(WHEEL_RAD_DEMO_st**2)) + (WHEEL_WIDTH_DEMO_st**2))
# mass moment of inertia about transverse axis (kg*m^2) 
# governs resistance to rotation about axes perpendicular to the spin axis

WHEEL_OBJ_FILE_DEMO_st = "mesh/rover_wheels/viper_wheel_right.obj"  
# mesh file used to represent the demo/baseline wheel geometry in the simulation
    
BASE_TERRAIN_RAD_DEMO_st = ((1344.3720907681325)/1000)/50  
# base terrain particle radius (m) used with the demo wheel case 
# sets the nominal particle size for the granular bed

TARGET_NORMAL_FORCE_DEMO_st = 200.0  
# target total normal load (N) applied to the terrain during the demo wheel test

SUPPLEMENTARY_FORCE_DEMO_st = TARGET_NORMAL_FORCE_DEMO_st - WHEEL_WEIGHT_DEMO_st  
# additional downward force (N) required beyond the wheel’s own weight 
# used to achieve the specified target normal load

#----------------------------------------------------------------------------------------------------------------------------
# USER-DEFINED WHEEL CONFIGURATION
#----------------------------------------------------------------------------------------------------------------------------

WHEEL_RAD_st = 0.201  
# wheel radius (m); sets overall size and contact geometry

WHEEL_WIDTH_st = 0.08  
# wheel width (m); defines lateral contact area with the terrain

LOADS = [10.0, 40.0, 60.0]  
# set of test masses (kg) for parametric evaluation

WHEEL_MASS_st = LOADS[0]  
# selected wheel mass (kg) for the current simulation

WHEEL_WEIGHT_st = WHEEL_MASS_st * 9.81  
# wheel weight (N); gravitational load applied to the terrain

WHEEL_IYY_st = WHEEL_MASS_st * ((WHEEL_RAD_st**2)/2)  
# mass moment of inertia about the spin axis (kg*m^2)
# determines resistance to changes in rotational speed

WHEEL_IXX_st = (WHEEL_MASS_st/12)*((3*(WHEEL_RAD_st**2)) + (WHEEL_WIDTH_st**2))  
# mass moment of inertia about transverse axis perpendicular to spin axis (kg*m^2) 
# determines resistance to tilting or pitching motion

WHEEL_OBJ_FILE_st = "TREAD_Assembly.obj"  
# mesh file defining the custom wheel geometry used in the simulation
# file must be located within working directory

BASE_TERRAIN_RAD_st = ((1344.3720907681325)/1000)/50  
# base particle radius (m) for the terrain; sets the nominal grain size

TARGET_NORMAL_FORCE_st = WHEEL_WEIGHT_st  
# target normal load (N) applied to the terrain (equal to wheel weight by default)

SUPPLEMENTARY_FORCE_st = 0  
# additional downward force (N) applied beyond the wheel weight (zero by default)

#----------------------------------------------------------------------------------------------------------------------------
# PRESSURE PLATE CONFIGURATION
#----------------------------------------------------------------------------------------------------------------------------

PLATE_X_st = 1.4      
# plate length in the x-direction (m); defines contact area extent

PLATE_Y_st = 1.4      
# plate width in the y-direction (m); defines lateral contact area

PLATE_THICK_st = 0.05 
# plate thickness (m); used for mass/inertia and geometric representation

PLATE_MASS_st = 200.0  
# plate mass (kg); determines applied load during penetration

PLATE_VEL_st = 1e-3    
# prescribed downward penetration velocity (m/s); controls loading rate

PLATE_OBJ_FILE_st = "pressure_plate.obj"  
# mesh file defining the plate geometry used in the simulation
# must be accessible via a path relative to the working directory

#----------------------------------------------------------------------------------------------------------------------------
# CONTAINER (BIN) GEOMETRY
#----------------------------------------------------------------------------------------------------------------------------

WIDTH_st = 3.5     
# bin width in the x-direction (m); defines lateral domain extent

LENGTH_st = 3.5    
# bin length in the y-direction (m); defines longitudinal domain extent

DEPTH_st = 0.5     
# bin depth in the z-direction (m); sets vertical extent of the granular bed

FULL_HEIGHT_st = DEPTH_st / 2.0  
# mid-depth reference height (m)
# used as an upper bound for terrain generation

#----------------------------------------------------------------------------------------------------------------------------
# SLIP–SINKAGE TEST PARAMETERS
#----------------------------------------------------------------------------------------------------------------------------

SLIP_VALUES_st = np.linspace(0.0, 0.6, 3)  
# array of slip ratios (dimensionless) evaluated across trial
# slip values: 0 = pure rolling/no slip; higher values indicate increasing slip (1 = full slip/no forward motion)

WHEEL_ANG_VEL_st = np.pi / 2  
# prescribed wheel angular velocity (rad/s)
# combined with wheel radius and linear velocity to determine slip ratio/conditions
