import numpy as np 

#=== TODO: MOVIE GENERATION CONFIG ==== 
MOVIE_TYPES_LIST = ["generation", "slip", "pressure_plate"]
TERRAIN_TYPES_LIST = ["sphere"]
MOVIE_TYPE = MOVIE_TYPES_LIST[0] 
TERRAIN_TYPE = TERRAIN_TYPES_LIST[0]
DEFAULT_FRAMERATE = 60
MOVIE_OUT_DIR = "./movies"

#==== TODO: SPHERE PARTICLE TERRAIN CONFIG ==== 
#NOTE: st == "sphere terrain"

##GENERATION DIRECTORIES AND FILE NAMES 
SPHERE_TERRAIN_GEN_OUT_DIR = "./sphere_tgen_output"
SPHERE_TERRAIN_GENERATION_MOTION_FILE_NAME = "sphere_terrain_settling_motion"
SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME = "settled_sphere_terrain_data"

##SLIP SINKAGE DIRECTORIES AND FILE NAMES 
SLIP_SINKAGE_OUT_DIR = "./slip_sinkage_output/sphere_particles"
SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME = "sphere_terrain_slip_sinkage_trials_motion_terrain"
SLIP_SINKAGE_TRIALS_MOTION_WHEEL_FILE_NAME = "sphere_terrain_slip_sinkage_trials_motion_wheel"
SLIP_SINKAGE_TRIALS_CONTACT_FORCE_FILE_NAME = "sphere_terrain_slip_sinkage_trials_contact_force"
SLIP_SINKAGE_TRIALS_SETTLED_DATA_FILE_NAME = "sphere_terrain_slip_sinkage_trials_settled_data"

##PRESSURE PLATE DIRECTORIES AND FILE NAMES 
PRESSURE_PLATE_OUT_DIR = "./sphere_pressure_plate_output"
PRESSURE_PLATE_MOTION_TERRAIN_FILE_NAME = "sphere_terrain_pressure_plate_motion_terrain"
PRESSURE_PLATE_CONTACT_FORCE_FILE_NAME = "sphere_terrain_pressure_plate_contact_force"
PRESSURE_PLATE_RESPONSE_FILE_NAME = "sphere_terrain_pressure_plate_response"
PRESSURE_PLATE_SETTLED_DATA_FILE_NAME = "sphere_terrain_pressure_plate_settled_data"
PRESSURE_PLATE_MOTION_PLATE_FILE_NAME = "sphere_terrain_pressure_plate_motion_plate"

##SOLVER CONFIG 
MAX_VELOCITY_st = 30                               #sets an upper speed limit so particles don’t move too far in one time step; keeps contact detection stable and reliable
ERROR_OUT_VELOCITY_st = 30                         #sets a velocity threshold that triggers an error and stops the simulation if particles accelerate unrealistically
G_MAG_st = 9.81
GRAVITATIONAL_ACCELERATION_st = [0, 0, -G_MAG_st]  #sets gravity to act in the negative Z direction (Earth: 9.81 m/s²)
STEP_SIZE_st = 5e-6                                #sets the simulation time step; each physics update advances the system by one microsecond
TRIAL_RUN_TIME_SLIP_SINKAGE_st = 5.0              #sets the time for each trial run
TRIAL_RUN_TIME_PRESSURE_PLATE_st = 5.0             #sets the time for each trial run
DOMAIN_EXPANSION_FACTOR_st = 4.0                   #factor to expand the domain by to ensure the plate is not in contact with the edge of the domain

##SPHERE PARTICLE TERRAIN CONFIG 
E_st = 1e5                     #young's modulus: measures how stiff a material is — how much it resists stretching or compression
NU_st = 0.24                    #poisson's ratio: decribes how a material deforms in directions perpendicular to the direction of loading
COR_st = 0.9                    #coefficient of restitution: describes how much relative motion is preserved after impact along the line of contact, how much kinetic energy is recovered after a collision 
MU_st = 0.3                     #coefficient of static friction: describes how much resistance there is to the start of sliding between two surfaces in contact
CRR_st = 0.1                    #coefficient of rolling resistance: describes how much a rolling object resists motion due to deformation and contact losses
COHESION_st = 50.0              #cohesion: describes how much a material resists shear stress, how much it resists sliding between two surfaces in contact 
TERRAIN_DENSITY_st = 2.5e3      #bulk density of the granular terrain (mass per volume) used to compute particle mass from their size, and to set the bed’s overall weight/inertia

##CONTACT BEHAVIOR CONFIG 
MU_contact_wheel_st = 0.8    #for normal and tangential force during contact 
COR_contact_wheel_st = 0.6   #for kinetic energy dissapation during contact 
COHESION_contact_wheel_st = 50.0 
MU_contact_plate_st = 0.5 

##WHEEL FLAG 
USE_DEMO_WHEEL_st = True

##DEMO WHEEL CONFIG (RECOMMENDED FOR TESTING, DO NOT CHANGE)
WHEEL_RAD_DEMO_st = 0.25
WHEEL_WIDTH_DEMO_st = 0.2 
WHEEL_WEIGHT_DEMO_st = 100.0 
WHEEL_MASS_DEMO_st = WHEEL_WEIGHT_DEMO_st / G_MAG_st
WHEEL_IYY_DEMO_st = WHEEL_MASS_DEMO_st * ((WHEEL_RAD_DEMO_st**2)/2) 
WHEEL_IXX_DEMO_st = (WHEEL_MASS_DEMO_st/12)*((3*(WHEEL_RAD_DEMO_st**2)) + (WHEEL_WIDTH_DEMO_st**2))
WHEEL_OBJ_FILE_DEMO_st = "mesh/rover_wheels/viper_wheel_right.obj"
BASE_TERRAIN_RAD_DEMO_st = ((1344.3720907681325)/1000)/50#WHEEL_RAD_DEMO_st/10 
TARGET_NORMAL_FORCE_DEMO_st = 200.0 
SUPPLEMENTARY_FORCE_DEMO_st = TARGET_NORMAL_FORCE_DEMO_st - WHEEL_WEIGHT_DEMO_st

##USER WHEEL CONFIG 
#3 inches wide with a 40 cm diameter, and we have data available for loads of 10, 40, and 60 kg
WHEEL_RAD_st = 0.201 
WHEEL_WIDTH_st = 0.08  
LOADS = [10.0, 40.0, 60.0]
WHEEL_MASS_st = LOADS[0] 
WHEEL_WEIGHT_st = WHEEL_MASS_st * 9.81 
WHEEL_IYY_st = WHEEL_MASS_st * ((WHEEL_RAD_st**2)/2)  
WHEEL_IXX_st = (WHEEL_MASS_st/12)*((3*(WHEEL_RAD_st**2)) + (WHEEL_WIDTH_st**2)) 
WHEEL_OBJ_FILE_st = "TREAD_Assembly.obj" 
BASE_TERRAIN_RAD_st = ((1344.3720907681325)/1000)/50#WHEEL_RAD_st/10 
TARGET_NORMAL_FORCE_st = WHEEL_WEIGHT_st
SUPPLEMENTARY_FORCE_st = 0 

##PRESSURE PLATE CONFIG 
PLATE_X_st = 1.4      
PLATE_Y_st = 1.4       
PLATE_THICK_st = 0.05   
PLATE_MASS_st = 200.0  
PLATE_VEL_st = 1e-3
PLATE_OBJ_FILE_st = "pressure_plate.obj" 


##BIN CONFIG 
WIDTH_st = 3.5                 #width of the bin (physical container) 
LENGTH_st = 3.5                #length of the bin (physical container)
DEPTH_st = 0.5                 #depth of the bin (physical container)
FULL_HEIGHT_st = DEPTH_st/2.0

##SLIP CONFIG 
SLIP_VALUES_st = np.linspace(0.0, 0.6, 3)
WHEEL_ANG_VEL_st = np.pi/2 