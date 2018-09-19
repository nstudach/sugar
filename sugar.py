import requests
import json
import time
import sys
from pssh.clients import ParallelSSHClient
from pssh.utils import enable_logger, logger
from gevent import joinall

def ssh_stuff(hosts, jobs, inputfiles):
    '''
    Copys local files to remote hosts
    Installs packages and libraries
    Executes pathspider in servers background
    Disconnects ssh_connection
    
    :param hosts: Contains IP adresses of VM machines
    :type hosts: list(str)
    :param jobs: Contains Commands for VM machines (orderd)
    :type jobs: list(str)
    :param inputfile: Location of pathspider jobs ndjson file
    '''
    enable_logger(logger)
    
    client = ParallelSSHClient(hosts, user = 'root', pkey = 'keys/id_rsa')

    # copy remote_script, input file, config file
    print('start copying files')
    cmds = client.copy_file('remote_script.py', 'remote_script.py')
    joinall(cmds, raise_error=True)
    cmds = client.copy_file('config.json', 'config.json')
    joinall(cmds, raise_error=True)
    for inputfile in inputfiles:
        if not inputfile.startswith('http'):
            cmds = client.copy_file(inputfile, inputfile)
            joinall(cmds, raise_error=True)
    
    sleep(10)
    
    print('Letting the machine sleep')
    output = client.run_command('sleep 2m')
    #wait until finished
    client.join(output, consume_output=False, timeout=None)
    
    #remote execute remote_script
    print('Starting deployment script')
    print(jobs)
    client.run_command('%s', host_args = jobs, use_pty = False)
    
    sleep(20)
    
    print('closing connections')

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
        sleep(20)
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
        print(data)
        print ('retry')
        sleep(20)
        r = requests.get(url, headers=headers)
        data= r.json()
        return data['droplet']['networks']['v4'][0]['ip_address']

def sleep(seconds):
    print('Sleeping for %d sec' % seconds)
    time.sleep(seconds)

if __name__ == "__main__":
        
    plugin = str(sys.argv[1])
    #read_conf
    config = json.load(open('config.json'))
    droplet_config = config['droplet']
    regions = config['provider']['regions']
    headers = config['provider']['headers']
    
    hosts = []
    jobs = []
    ids = []
    
    for region in regions:
        id, name = create_VM(headers, region, plugin, droplet_config)
        time.sleep(10)
        ip = get_IP(headers, id)
        print(name+':'+ip)
        hosts.append(ip)
        jobs.append('setsid python3 remote_script.py ' + name + ' ' + str(id))
        ids.append(id)
        
    # for testing purpouse
    with open('delete_commands_'+plugin, 'a') as fuckup:
        fuckup.write(str(hosts) + '\n')
        for id in ids:
            fuckup.write('curl -X DELETE -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" "https://api.digitalocean.com/v2/droplets/'+str(id)+'"\n')

    #may want to wait a bit for host to start
    sleep(50)

    ssh_stuff(hosts, jobs, config['measurement']['inputfile'])
    print('Disconnected from hosts! Progress will be displayed on the slack channel.')