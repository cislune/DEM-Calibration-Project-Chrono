## INSTRUCTIONS FOR SETTING UP PyChrono and PyDEME

## -1. NOTES 

-1A. REMOVING CONDA ENV 

Use the following command to remove a conda env 

`conda env remove --name myenv`

    ^where myenv is the name of the conda env you want to remove 

-1B. LISTING NAMES OF CONDA ENV 

`conda env list` 

will list the names of all of the previously created conda environments on your machine. 

there will also be an asterisk (*) next to the environment you currently have activated :) 


## 0.  PRE-REQUISITES 

0A. CHECK NVIDIA DRIVER 

Use `nvidia-smi` to check your NVIDIA Driver version. The CUDA Version (top right) should be **12.8 or higher**. For example: 

<img src="nvidia_smi.png" alt="nvidia-smi output" width="400"/>

If your driver is lower than 12.8, please upgrade your NVIDIA Driver. You can find instructions and downloads at:

- [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
- [NVIDIA Linux Driver Installation Guide](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html)

Follow the official guide for your operating system to update the driver.

0B. INSTALL miniconda3 (link to download shell script: https://www.anaconda.com/download/success)

miniconda3 is a minimal distribution (i.e lightweight version) of the environment manager Conda. It comes with
Python 3 and a minimal base environment. 

For this project, it will be easiest to create an environment (env). It will be like a nice little container for all of your packages, libraries, and other dependencies. 

Once the shell script is downloaded, turn it into an executable using the command 

`sudo chmod +x shell_script_name.sh` (where shell_script_name.sh is the actual name of the miniconda shell script that was downloaded)

then run the shell script via 

`./shell_script_name.sh` (where shell_script_name.sh is the actual name of the miniconda shell script that was downloaded)

**If you run into issues, it might be worth checking if your machine satisfies the system requriements**
(https://www.anaconda.com/docs/getting-started/miniconda/system-requirements)


## 1. CREATING ENVIRONMENT AND INSTALLING PyChrono AND PyDEME

1A. Creating and activating conda (miniconda3) env 

NOTE: "myenv" can be replaced with any name you want for your environment 

`conda create -n myenv python=3.12 -c conda-forge -y`

    ^creates a conda environment with python version 3.12 (the -y flag skips the confirming prompts) 

    NOTE: you can use the -y flag for later conda install commands as well if you'd like. has essentially the same purpose as above. 

`conda activate myenv`

    ^activate the environment you just made 

1B. INSTALLING PyChrono and PyDEME VIA CONDA 

NOTE: your desired conda environment must be activated before this step 

`conda install bochengzou::pychrono bochengzou::pydeme -c bochengzou -c conda-forge`

    ^while in general this package is avaialbe on conda-forge, the required/newer version is not yet published there.

1C. EXTRA DEPENDENCIES 

NOTE: your desired conda environment must be activated before this step 

`conda install -c conda-forge imageio-ffmpeg`

`conda install -c conda-forge pandas`


## 2. RUN DEMOS 

NOTE: your desired conda environment must be activated before this step 

You are ready to navigate to the demos under the "demo" parent directory and run some code! 

I have included both PyChrono (CRM and MBS) and PyDEME demos from our standard demo collection as a sanity check :) 

### DEMOS: SEVERAL NOTES 

1. Based on the installation instructions in this doc, the CRM demo is only working on linux (for the meantime)
2. CRM does not use GPU computing (executed on the CPU only)
3. DEM (PyDEME) does use GPU computing (handled under the hood, no explicit GPU programming is required by the user)
4. To confirm that your set up properly facilitates GPU utilization/memory for DEM: 

    a. run any PyDEME demo via terminal 

    b. open a new terminal window and run: 

`watch -n 1 nvidia-smi` 

    ^ you should see GPU related stats changing as the simulation is running 

5. Output directories dont necessarily matter for the MBS demos therefore they are not configured. However, directories are configured for the outputs of DEM and CRM demos.







