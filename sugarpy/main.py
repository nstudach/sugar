import json
import time
import sys
import bz2
import os
import argparse

import requests
from subprocess import call
from pssh.clients import ParallelSSHClient
from pssh.utils import enable_logger, logger
from gevent import joinall

def initialize_client(hosts, key):
    enable_logger(logger)
    return ParallelSSHClient(hosts, user = 'root', pkey = key)

def send_ssh(client, jobs_setup, config, mode):
    if mode == 'install':
        print('Setting up configs')
        output = client.run_command('%s', host_args = jobs_setup)
        client.join(output, consume_output=False, timeout=None)
        print('Installing programs')
        output = client.run_command("python3 -c 'from remote_script import *; install_all()'")
        client.join(output, consume_output=False, timeout=None)
    elif mode == 'hellfire':
        print('Setting up configs')
        output = client.run_command('%s', host_args = jobs_setup)
        client.join(output, consume_output=False, timeout=None)
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

def copy_files(hosts, key, configfile, inputfiles):
    # get install directory where scripts are located
    i_dir = open('/opt/sugar/installation-path.txt', 'r').readline()
    print('Start copying files')
    files = [(i_dir + 'remote_script.py', 'remote_script.py'),
             (i_dir + 'update_config.py', 'update_config.py'),
             (configfile, 'config.json')]
    # add inputfiles to list if required
    for inputfile in inputfiles:
        if not inputfile.startswith('http'):
            inputfile = compress_file(inputfile)
            files.append((inputfile,os.path.basename(inputfile)))
    # copy remote_script, input files, config file
    for ip in hosts:
        print('Host: %s' % ip)
        host = 'root@' + str(ip) + ':'
        for source, target in files:
            if call(['scp', '-i', key, '-o', 'StrictHostKeyChecking=no', source, host + target]) == 0:
                print('Copied %s' % source)

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
            if copy: copy_files(hosts, config['setup']['ssh key'], configfile, config['measure']['inputfile'])
            mode = 'install' if config['task']['install'] else ''
            send_ssh(client, jobs_setup, config, mode)
            print('Disconnected from hosts! Progress will be displayed on the slack channel.')
    return True

def hellfire_setup(configfile):
    config = json.load(open(configfile))
    overwrite = True

    if 'hellfire' not in config: config['hellfire'] = {}
    # check if host info exists
    elif 'host info' in config['hellfire']:
        answer = input('Do you want to override the current hellfire host information?\ny or yes to continue:')
        if answer not in ['y', 'yes']: overwrite = False
    
    if overwrite:
        # set region to only 1
        config['provider']['regions'] = [config['provider']['regions'][0]]
        config['hellfire']['host info'] = setup_droplets(config, 'hellfire')
        json.dump(config, open(configfile, 'w'), indent=4)   
        print ('Created hellfire server.')
        sleeping(50)

    # extract ip addresses
    hosts, jobs_setup, _ = get_info_from_config(config, 'hellfire')
    client = initialize_client(hosts, config['setup']['ssh key'])
    # copy files - dont copy inputfiles
    copy_files(hosts, config['setup']['ssh key'], configfile, [])
    # update config and install programms, run hellfire
    send_ssh(client, jobs_setup, config, 'hellfire')
    return True

def get_inputfile(configfile, filename):
    config = json.load(open(configfile))
    host, _, _ = get_info_from_config(config, 'hellfire')
    filename += '.bz2'
    # retrieve input file from /root/topsites.ndjson
    host = 'root@' + str(host[0]) + ':/root/topsites.ndjson.bz2'
    call(['scp', '-i', config['setup']['ssh key'], '-o', 'StrictHostKeyChecking=no', host, filename])
    print('Successfully downloaded, decompressing')
    _ = decompress_file(filename)

def clean(jf):
    for tag in ["hellfire_lookup_attempts", "hellfire_lookup_type"]:
        jf.pop(tag, None)
    return json.dumps(jf) + '\n'

def read_lines(filename):
    with open(filename, 'r') as input:
        for line in input.readlines():
            try:
                yield json.loads(line)
            except:
                print('line is not json format')
                print(line)

def split(configfile, filename, junk_size):
    outfiles = []
    i = junk_size
    k = 0

    for line in read_lines(filename):
        if i == junk_size:
            i = 0
            k += 1
            new_outfile = os.path.splitext(filename)[0] + '_' + str(k) + os.path.splitext(filename)[1]
            outfiles.append(new_outfile)
            outfile = open(new_outfile, 'a+') 
        else:
            i += 1
            outfile.write(clean(line))

    # write files in config
    config = json.load(open(configfile))
    config['measure']['inputfile'] = outfiles
    json.dump(config, open(configfile, 'w'), indent=4)

def compress_file(filename):
    if filename.endswith(".bz2"):
        return filename
    else:
        new_filename = filename + ".bz2"
        compressionLevel = 9
        with open(filename, 'rb') as data:
            fh = open(new_filename, "wb")
            fh.write(bz2.compress(data.read(), compressionLevel))
            fh.close()
        return new_filename

def decompress_file(filename):
    '''
    decompresses file from bz2 if possible
    '''
    if not filename.endswith(".bz2"):
        return filename
    else:
        new_filename = os.path.splitext(filename)[0]
        with open(filename, 'rb') as data:
            fh = open(new_filename, "wb")
            fh.write(bz2.decompress(data.read()))
            fh.close()
        return new_filename

def comand_line_parser():
    parser = argparse.ArgumentParser(description = 'Manage automated pathspider measurements')
    parser.add_argument('--plugin', help = 'Pathspider plugin to use', metavar = 'plugin')
    parser.add_argument('--config', help = 'Path to config file', metavar = 'file-location',
                        default = 'configs/config.json')
    parser.add_argument('--key', help = 'Path to ssh authentication key', metavar = 'file-location')   
    parser.add_argument('--fetch', nargs = 2, metavar = ('filename', 'n'),
                        help = 'Downloads input, executes --split')
    parser.add_argument('--split', nargs = 2, metavar = ('filename', 'n'),
                        help = 'Splits input into n sized parts, adds them to config file')     
    args=parser.parse_args()

    config = json.load(open(args.config))
    if args.key is not None:
        config['setup']['ssh key'] = args.key
    if args.plugin is not None:
        config['measure']['plugin'] = args.plugin
    elif'plugin' not in config['measure']:
        config['measure']['plugin'] = 'droplet'
    json.dump(config, open(args.config, 'w'), indent=4)

    if args.fetch is not None:
        get_inputfile(args.config, args.fetch[0])
        split(args.config, args.fetch[0], int(args.fetch[1]))
    elif config['task']['hellfire']:
        hellfire_setup(args.config)
    else:
        if args.split is not None:
            split(args.config, args.split[0], int(args.split[1]))
        main(args.config) 