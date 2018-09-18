
# sugar

Automatic set up of DigitalOcean VM's and execution of pathspider with upload to MAMI PTO

## 1. Config file

Enter all the required parameter in a config.json file. The config_example.json will help you here.
The config consists of 4 parts:

### "slack": - Configures slack

* **"token"**: Your slack channel bot token
* **"channel"**: channel to post in

### "droplet" - Configures your droplet

* **"name" & "region"** will be filled out automatically
* **"size"**: size identifier from Digital Ocean.
* **"image**: OS slug. Use at least "debian-9-x64" for python 3.5 support.
* **"ssh_keys"**: SSH key id number (deployed on your Digital Ocean account)

### "provider" for Digital Ocean parameters

* **"headers"**:Your digital ocean token should replace `<<DO API Token>>`
* **"regions"**: Regions to deploy a VM in. Choose from ["ams3", "blr1", "fra1", "lon1", "nyc1", "nyc3", "sfo2", "sgp1", "tor1"]

### "measurement" for measurement parameters

* **"inputfile"**: List of strings representing either a filename or a link to a downloadable file
* **"campaign"**: Your PTO campaign name as string
* **"token"**: Your PTO access token as string
* **"workers"**: number of workers
* **"debug"**: activate debug mode (_true_/_false_). More information posted to slack channel

## 2. SSH Key

The SSH Private key must be placed in the folder keys with the names `id_rsa` and `id_rsa.pub`

## 3. Usage

The program is started through the terminal. As only parameter you need to specify the pathspider plugin to use. See `pspdr measure -h` for more information. You can run multiple plugin measurements simultaniously as long as your Digital Ocean account supports the large amount of droplets.

`python3 create_droplet PLUGIN`

The program will create a local file containing the commands to delete each droplet as well as their IP address for an manual ssh connection.
