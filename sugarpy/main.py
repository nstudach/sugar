import json
import time
import sys
import os
import argparse

import requests
from pssh.clients import ParallelSSHClient
from pssh.utils import enable_logger, logger
from gevent import joinall

def initialize_client(hosts, key):
    enable_logger(logger)
    return ParallelSSHClient(hosts, user = 'root', pkey = key)

def send_ssh(client, jobs_setup, config):
    if config['task']['install'] or config['task']['hellfire']:
        print('Setting up configs')
        # => install mode
        output = client.run_command('%s', host_args = jobs_setup)
        client.join(output, consume_output=False, timeout=None)
        if config['task']['install']:
            print('Installing programs')
            output = client.run_command("python3 -c 'from remote_script import *; install_all()'")
            client.join(output, consume_output=False, timeout=None)
        else:
            print('Installing hellfire')
            output = client.run_command("python3 -c 'from remote_script import *; setup_hellfire()' >>log.txt 2>&1")
            client.join(output, consume_output=False, timeout=None)
    else:
        print('Updating configs')
        output = client.run_command(jobs_setup)
        client.join(output, consume_output=False, timeout=None)
    #execute remote_script
    print('Starting deployment script')
    client.run_command('setsid python3 remote_script.py', use_pty = False)
    sleeping(20)

def copy_files(client, configfile, inputfiles):
    # get install directory where scripts are located
    install_dir = open('/opt/sugar/installation-path.txt', 'r').readline()
    print('Start copying files')
    # copy remote_script, input files, config file
    cmds = client.copy_file(install_dir + 'remote_script.py', 'remote_script.py')
    joinall(cmds, raise_error=True)
    cmds = client.copy_file(install_dir + 'update_config.py', 'update_config.py')
    joinall(cmds, raise_error=True)
    cmds = client.copy_file(configfile, 'config.json')
    joinall(cmds, raise_error=True)
    for inputfile in inputfiles:
        if not inputfile.startswith('http'):
            cmds = client.copy_file(inputfile, os.path.basename(inputfile))
            joinall(cmds, raise_error=True)
    sleeping(10)

def get_info_from_config(config, place):
    try:
        if place == 'setup':
            host_info = config['setup']['host info']
        elif place == 'hellfire':
            host_info = config['hellfire']['host info']
        else:
            print('Neither hellfire nor setup selected')
            return False
    except:
        print('No host info found. Create Droplets first')
        return False
    try:
        hosts = [ip for name, ip, id in host_info]
        if config['task']['install'] or config['task']['hellfire']:
            copy = True
            jobs_setup = ['python3 update_config.py ' + 'name=' + name + ' id=' + str(id) for name, ip, id in host_info]
            # print(jobs_setup)
        else:
            # update config
            copy = False
            jobs_setup = ['python3', 'update_config.py']
            for tag in ['debug', 'install', 'measure', 'upload', 'destroy']:
                jobs_setup.append(tag + '=' + str(config['task'][tag]))
            jobs_setup = ' '.join(jobs_setup)
            # print(jobs_setup)
    except:
        print('Something wrong with config.json.\nCould not read host info')
        print(host_info)
        return False
    return (hosts, jobs_setup, copy)

def setup_droplets(config, plugin):
    #create droplets and save ip adresses and ids
    droplet_config = config['droplet']
    regions = config['provider']['regions']
    headers = config['provider']['headers']
    
    host_info = []

    for region in regions:
        id, name = create_VM(headers, region, plugin, droplet_config)
        time.sleep(10)
        ip = get_IP(headers, id)
        print(name+':'+ip)
        if ip != 'no ip':
            host_info.append([name, ip, id])
        else:
            print(name + ': IP could not be retrieved. Droplet destroyed')
    return host_info

def create_VM(headers, region, plugin, droplet_config):
    #base droplet configuration
    droplet_config['name'] = '-'.join(['ps', region, plugin])
    droplet_config['region'] = region
    
    # create VM
    url = "https://api.digitalocean.com/v2/droplets"
    r = requests.post(url, data=json.dumps(droplet_config), headers=headers)
    data = r.json()
    try:
        print(droplet_config['name']+':'+str(data['droplet']['id']))
        return str(data['droplet']['id']), droplet_config['name']
    except:
        print(data)
        print ('retry')
        sleeping(20)
        r = requests.post(url, data=json.dumps(droplet_config), headers=headers)
        data = r.json()
        print(droplet_config['name']+':'+str(data['droplet']['id']))
        return str(data['droplet']['id']), droplet_config['name']

def get_IP(headers, id):
    # get ip: curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer ${MYTOKEN}" "https://api.digitalocean.com/v2/droplets/${MYDROPLETID}"
    url = "https://api.digitalocean.com/v2/droplets/" + str(id)
    r = requests.get(url, headers=headers)
    data= r.json()
    try:
        return data['droplet']['networks']['v4'][0]['ip_address']
    except:
        for _ in range(3):
            print ('Digital Ocean not yet ready.\nretry')
            sleeping(20)
            r = requests.get(url, headers=headers)
            data= r.json()
            try:
                return data['droplet']['networks']['v4'][0]['ip_address']
            except:
                pass
        #kill droplet
        requests.delete(url, headers=headers)
        return 'no ip'

def sleeping(seconds):
    print('Sleeping for %d sec' % seconds)
    time.sleep(seconds)

def main(configfile):
    config = json.load(open(configfile))
    overwrite = True

    if config['task']['hellfire']:
        if 'hellfire' not in config: config['hellfire'] = {}
        # check if host info exists
        elif 'host info' in config['hellfire']:
            answer = input('Do you want to override the current hellfire host information?\ny or yes to continue:')
            if answer not in ['y', 'yes']: overwrite = False
        
        if overwrite:
            config['hellfire']['host info'] = setup_droplets(config, 'hellfire')
            json.dump(config, open(configfile, 'w'), indent=4)   
            print ('Created hellfire server.')
            sleeping(50)
        else:
            host_info =  config['hellfire']['host info']
        
        # extract ip addresses
        hosts, jobs_setup, copy = get_info_from_config(config, 'hellfire')
        client = initialize_client(hosts, config['setup']['ssh key'])
        # copy files - dont copy inputfiles. you create them now
        copy_files(client, configfile, [])
        # update config and install go, canid and hellfire
        send_ssh(client, jobs_setup, config)
        # start hellfire remotly
        print('Starting Hellfire')
        client.run_command('setsid hellfire -h', use_pty = False)
        # exit program: Hellfire should not run (opt: is_ready function too check if hellfire completex. then get input files)
        sys.exit([0])

    if config['task']['create']:
        if 'host info' in config['setup']:
            answer = input('Do you want to override the current host information?\ny or yes to continue:')
            if answer not in ['y', 'yes']: overwrite = False

    if overwrite:
        if config['task']['create']:
            host_info = setup_droplets(config, config['measure']['plugin'])
            # writing host inforamtion in config
            config['setup']['host info'] = host_info
            json.dump(config, open(configfile, 'w'), indent=4)   
            print ('Created droplets.')
            if config['task']['install']: sleeping(50)
        
        if config['task']['install'] or config['task']['measure'] or config['task']['upload'] or config['task']['destroy']:
            hosts, jobs_setup, copy = get_info_from_config(config, 'setup')
            client = initialize_client(hosts, config['setup']['ssh key'])
            if copy: copy_files(client, configfile, config['measure']['inputfile'])
            send_ssh(client, jobs_setup, config)
            print('Disconnected from hosts! Progress will be displayed on the slack channel.')

def comand_line_parser():
    parser = argparse.ArgumentParser(description = 'Manage automated pathspider measurements')
    parser.add_argument('--plugin', help = 'Pathspider plugin to use', metavar = 'plugin')
    parser.add_argument('--config', help = 'Path to config file', metavar = 'file-location', default = 'configs/config.json')
    parser.add_argument('--key', help = 'Path to ssh authentication key', metavar = 'file-location')   
    parser.set_defaults(func = main)
    args=parser.parse_args()

    # add key and plugin to config NOT WORKING
    config = json.load(open(args.config))
    if args.key is not None:
        config['setup']['ssh key'] = args.key
    if args.plugin is not None:
        config['measure']['plugin'] = args.plugin
    elif'plugin' not in config['measure']:
        config['measure']['plugin'] = 'droplet'
    json.dump(config, open(args.config, 'w'), indent=4)

    args.func(args.config)