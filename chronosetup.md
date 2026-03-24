## INSTRUCTIONS FOR SETTING UP PyChrono and PyDEME

## -1. NOTES 

-1A. REMOVING CONDA ENV 

Use the following command to remove a conda env 

`conda env remove --name myenv`

-1B. LISTING NAMES OF CONDA ENV 

`conda env list` 

will list the names of all of the previously created conda environments on your machine, and there will be an asterisk (*) next to the environment currently activated.


## 0.  PRE-REQUISITES 

0A. CHECK NVIDIA DRIVER 

Use `nvidia-smi` to check your NVIDIA Driver version. The CUDA Version (top right) should be **12.8 or higher**.

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







