import time
import os
import sys
import json
import random
from subprocess import call
from collections import defaultdict

# global config avoids refreshes
config = json.load(open('config.json'))
# global slackClient
slackClient = None
s_channel = None

def install_packets():
    # list of packages to install
    packages = [
        'libssl-dev',
        'libtrace-dev',
        'libldns-dev',
        'libcurl4-openssl-dev',
        'git',
        'build-essential',
        'python3-dev',
        'python3-pip'
    ]

    py_packages = [
        'straight.plugin',
        'pyroute2',
        'scapy-python3',
        'stem',
        'dnslib',
        'pycurl',
        'nose',
        'python-dateutil',
        'slackClient',
        'slacker',
        'requests'
    ]
    
    failed_pkg = ''
    # apt-get update
    call(['apt-get', '-qq', 'update'])

    # install packages via apt-get
    for package in packages:
        if call(['apt-get', 'install', '-qq', '-y', package]) == 1:
            failed_pkg += package + ' '

    # apt-get update
    call(['apt-get', '-qq', 'update'])

    # install packages
    for package in py_packages:
        if call([sys.executable, '-m', 'pip', 'install', '--quiet', package]) == 1:
            failed_pkg += package + ' '

    # apt-get update
    call(['apt-get', '-qq', 'update'])

    if failed_pkg == '':
        return (True, [])
    else:
        return (False, ['Packets: ' + failed_pkg])

def install_git():   
    failed_pkg = ''
    if not os.path.isdir('pathspider'):
        ps_link = 'https://github.com/nstudach/pathspider.git'
        if call(['git', 'clone', '-b', 'uploader', '--single-branch', ps_link]) != 0:
            failed_pkg += 'Download pathspider, '
    
    if not os.path.isdir('python-libtrace'):
        lib_link = 'https://github.com/nevil-brownlee/python-libtrace.git'
        if call(['git', 'clone', lib_link]) != 0:
            failed_pkg += 'Download libtrace, '

    # '(cd python-libtrace/ && make install-py3)'
    if call('(cd python-libtrace/ && make install-py3 > /dev/null 2>&1)', shell=True) != 0:
        failed_pkg += 'libtrace, '

    # '(cd pathspider/ && python3 setup.py install)'
    if call('(cd pathspider/ && python3 setup.py install > /dev/null 2>&1)', shell=True) != 0:
        failed_pkg += 'pathspider'

    if failed_pkg == '':
        return (True, [])
    else:
        return (False, ['Git Repositories: ' + failed_pkg])

def download_inputs():
    import requests
    global config
    #download input file if needed
    msg = []
    i = 0
    for file in config['measurement']['inputfile']:
        i += 1
        if file.startswith('http'):
            try:
                msg.append('Downloaded inputfile from: ' + str(file))
                r = requests.get(file)
                new_name = ''.join(['input', str(i), '.ndjson'])
                with open(new_name, 'wb') as f:
                    f.write(r.content)
                config['measurement']['inputfile'][i-1] = new_name
            except:
                msg.append('Could not download ' + str(file))
                return (False, msg)
    write_conf(config)  
    return (True, msg)

def setup():
    packets = False
    gits = False
    inputs = False
    msg = []
    for _ in range(3):
        if not packets:
            packets, report = install_packets()
            msg.extend(report)
        if not gits:    
            gits, report = install_git()
            msg.extend(report)
        if not inputs:
            inputs, report = download_inputs()
            msg.extend(report)
        if packets and gits and input:
            return (True, msg)
        msg.extend(['Retry'])
    return(False, msg)
        
def process_stderr(filename):
    error = []
    file = open(filename, 'r')
    for line in file: 
        error.append(line)
    return error

def destroy_VM(headers, id):
    try:
        import requests
        url = "https://api.digitalocean.com/v2/droplets/" + str(id)
        # delete droplet
        requests.delete(url, headers=headers)
    except:
        #what if request not installed?
        pass

def analyze_output(filename, plugin):
    if plugin in ['dscp', 'ecn', 'evilbit', 'h2', 'udpzero']:
        return [search(filename, ['works', 'broken', 'offline', 'transient'])]
    elif plugin in ['mss']:
        return [search(filename, ['online', 'offline'])]
    else:
        return ['Plugin not found']

def search(filename, keywords):
    '''
    Searches each line of file for one keyword
    Returns percentage of lines containig each keyword as string
    '''
    counter = defaultdict(int)

    with open(filename, 'r') as input:
        for line in input.readlines():
            counter['total'] += 1
            for keyword in keywords:
                if keyword in line:
                    counter[keyword] += 1
                    break
    return json.dumps(counter)

def upload(output, plugin, location, token, campaign, stderr): 
    # Set variables
    metadata1 = 'plugin:' + plugin
    metadata2 = 'location:' + location
    # Upload data
    if call(['pspdr', 'upload', '--metadata', metadata1, metadata2, '--token', token, '--campaign', campaign, output], stderr=open(stderr, 'w')) != 0:
        # Upload failed
        return (False, process_stderr(stderr))
    # Upload successful
    else:
        return (True, [])  

def measure(input, output, workers, plugin, stderr):
    if call(['pspdr', 'measure', '-i', 'eth0', '--input', input, '--output', output, '-w', workers, plugin], stderr=open(stderr, 'w')) != 0:
        # Failed measurement
        return (False, process_stderr(stderr))
    else:
        return (True, [])
           
def name_files(inputs, outputs, location, plugin):
    '''
    returns a list of tuple with tuple = (input, output, stderr) (names)
    '''
    letters = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'
    if len(inputs) != len(outputs):
        global config
        pre_output = ''.join(random.sample(letters, k=5)) +'-' + location + '-' + plugin
        in_out = [(inputs[i], pre_output + '-' + str(i)) for i in range(len(inputs))]
        # write new outputs in config
        config['measurement']['outputfile'] = [y for x,y in in_out]
        write_conf(config)    
    else:
        in_out = [(inputs[i], outputs[i]) for i in range(len(inputs))]
    return [(input, output, output +  '_stderr') for input, output in in_out]

def initialize_slack(token, channel):
    global slackClient
    global s_channel
    if slackClient == None:
        try:
            from slacker import Slacker
            
            slackClient = Slacker(token)
            
            s_channel = channel
            return True
        except:
            print('Could not start Slack Client')
            return False
    else:
        return True

def post(tag, lines):
    tag += ':\n'
    for line in lines:
        tag += '    ' + line + '\n'
    slackClient.chat.post_message(s_channel, tag)

def write_conf(config):
    json.dump(config, open('config.json', 'w'), indent=4)

def install():
    global config
    debug = config['setup']['debug']
    name = config['setup']['name']

    success, report = setup()
    if success:
        #successfully installed, write to config
        config['setup']['install complete'] = True
        write_conf(config)
        initialize_slack(config['slack']['token'], config['slack']['channel'])
        if not debug:
            report = []
        if config['setup']['measure']:
            report.append('Starting measurements')
        post(name, ['Setup successful'] + report)
        sys.exit([0])
    else:
        # Installation failed, write in config
        config['setup']['install complete'] = False
        write_conf(config)
        try:
            initialize_slack(config['slack']['token'], config['slack']['channel'])
            if not debug:
                report = []
            post(name, ['Setup failed'] + report)
        except:
            # Slack not installed
            pass
        sys.exit([1])

if __name__ == "__main__":
    debug = config['setup']['debug']
    #def variables
    name = config['setup']['name']
    location, plugin = name.split('-')[1:3]

    if config['setup']['install complete']:
        initialize_slack(config['slack']['token'], config['slack']['channel'])
    
        if config['setup']['measure'] or config['setup']['upload']:
            option = config['measurement']
            all_filenames = name_files(option['inputfile'], option['outputfile'], location, plugin)

    if config['setup']['measure'] and config['setup']['install complete']:
        # prepare measurement
        for filenames in all_filenames:
            input, output, stderr = filenames
            tag = name +' with ' + input
            if debug:
                temp = ' '.join(['Started measurement: pspdr measure -i eth0 --input', input, '--output', output, '-w', option['workers'], plugin,'\n'])
                post(tag, [temp])
            #run measurement
            success, report = measure(input, output, option['workers'], plugin, stderr)
            if success:
                # Analyse output
                report.extend(analyze_output(output, plugin))
                post(tag, ['Measurement successful:'] + report)
            else:
                if not debug:
                    report = []
                post(tag, ['Measurement failed:'] + report)

    if config['setup']['upload'] and config['setup']['install complete']:
        #upload file
        for filenames in all_filenames:
            input, output, stderr = filenames
            tag = name +' with ' + filenames[0]
            success, report = upload(output, plugin, location, option['token'], option['campaign'], stderr)
            if success:
                # Upload successful
                post(tag, ['Upload successful:'] + report) 
            else:
                # Upload failed
                post(tag, ['Upload failed:'] + report)  

    if config['setup']['destroy']:
        initialize_slack(config['slack']['token'], config['slack']['channel'])
        post(name, ['Destroying Droplet'])
        #destroy the droplet
        destroy_VM(config['provider']['headers'], config['setup']['id'])
        #if destruction failed this code will run
        time.sleep(300)
        post(name, ['Destruction failed'])
