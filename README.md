
# sugar

This program is written to automate internet path transparency measurements for the MAMI project.

It creates virtual machines at different locations in the internet and sets them up to run pathspider on them.
It can upload the measurements directly to the MAMI PTO and destroy each droplet after a succesfull or failed run.

## 1. Installation

You can install sugar by:

1. Cloning this git repository
1. In the folder sugar run `sudo python3 setup.py install`

## 2. Usage

Sugar can be run in the terminal with `sugar -h`
Sugar will add a folder /opt/sugar/ for application data

The possible arguments are:

* **--config** Expects the path to the config file (See 3. about configuring the file).
  * Example: --config configs/config.json
* **--plugin** The pathspider plugin you want to use (See: pathspider.com).
  * Example: --plugin ecn
* **--key** The location of the SSH keypair (See "droplet" and "setup").
  * Example: --key /home/user/.ssh/rsa_id
* **--fetch** Downloads input from the hellfire VM, executes --split.
  * Example: topsites.ndjson 200000
* **--split** filename n    Splits input into n sized parts, adds them to config file.
  * Example: topsites.ndjson 200000

You can run multiple plugin measurements simultaniously as long as your Digital Ocean account supports the large amount of droplets.

The program will save the host names, ip addresses, and id's in the config.json file.

## 3. Configure Sugar

Enter all the required parameter in a config.json file. The config_example.json will help you here.
The config consists of 4 parts:

### "slack": - Configures slack

* **"token"**: Your slack channel bot token
* **"channel"**: channel to post in

### "provider" for Digital Ocean parameters

* **"headers"**:Your digital ocean token should replace `<<DO API Token>>`
* **"regions"**: Regions to deploy a VM in. Choose from ["ams3", "blr1", "fra1", "lon1", "nyc1", "nyc3", "sfo2", "sgp1", "tor1"]

### "droplet" - Configures your droplet

* **"name" & "region"** will be filled out automatically
* **"size"**: size identifier from Digital Ocean.
* **"image**: OS slug. Use at least "debian-9-x64" for python 3.5 support.
* **"ssh_keys"**: SSH key id number (deployed on your Digital Ocean account)

### "install" for task install

* **"packages"**: List of packages to install with apt-get
* **"py_packages":**: List of packages to install with pip

### "measure" for task measure

* **"inputfile"**: List of strings representing either a filename or a link to a downloadable file
* **"outputfile"**: You can name your outputfiles here. List must be same lenght as inputfile or it will be ignored.
* **"campaign"**: Your PTO campaign name as string
* **"token"**: Your PTO access token as string
* **"workers"**: number of workers

### "upload" for task upload

* **"campaign"**: Your PTO campaign name as string
* **"token"**: Your PTO access token as string

### "task" Defines task to execute

* **"debug"**: (_true_/_false_): activate debug mode. More information posted to slack channel
* **"hellfire"**: (_true_/_false_): Downloads new input file via hellfire
* **"create"**: (_true_/_false_): Creates VM's.
* **"install"**: (_true_/_false_): Sets up VM's
* **"measure""**: (_true_/_false_): Enables Measurement
* **"upload"**: (_true_/_false_): Enables upload
* **"destroy"**: (_true_/_false_): Destroys droplets after completion of all tasks

### "setup" stores setup data

* **"host info"**: Stores current host information after creation (leave empty if no droplets exist yet). Enables connection to existing droplets.
* **"SSH Key"**: The locaction of your SSH private key. Can also be set using --key option.

### "hellfire" stores hellfire setup data

* **"host info"**: Stores current host information after creation (leave empty if no droplets exist yet). Enables connection to existing droplets.