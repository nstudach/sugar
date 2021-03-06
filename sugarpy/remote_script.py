import time
import os
import re
import sys
import bz2
import json
import string
import random
from subprocess import call
from subprocess import Popen
from collections import defaultdict

# global config avoids refreshes
config = json.load(open('config.json'))
# global slackClient
slackClient = None
s_channel = None

##################################################################
# INSTALLATION FUNCTIONS
##################################################################

def install_all():
    global config
    debug = config['task']['debug']
    name = config['slack']['name']

    success, report = setup()
    if success:
        #successfully installed, write to config
        config['install']['install complete'] = True
        write_conf(config)
        initialize_slack(config['slack']['token'], config['slack']['channel'])
        if not debug:
            report = []
        if config['task']['measure']:
            report.append('Starting measurements')
        post(name, ['Setup successful'] + report)
        sys.exit([0])
    else:
        # Installation failed, write in config
        config['install']['install complete'] = False
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

def install_packets():
    failed_pkg = ''
    # apt-get update
    call(['apt-get', '-qq', 'update'])

    # install packages via apt-get
    for package in config['install']['packages']:
        if call(['apt-get', 'install', '-qq', '-y', package]) == 1:
            failed_pkg += package + ' '

    # apt-get update
    call(['apt-get', '-qq', 'update'])

    # install packages
    for package in config['install']['py_packages']:
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
        if call(['git', 'clone', '-b', 'uploader_v2', '--single-branch', ps_link]) != 0:
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
    for file in config['measure']['inputfile']:
        i += 1
        if file.startswith('http'):
            try:
                msg.append('Downloaded inputfile from: ' + str(file))
                r = requests.get(file)
                # extract name
                new_name = re.findall('="(.+)"', r.headers['content-disposition'])
                if new_name == []:
                    new_name = ''.join(['input', str(i), '.ndjson'])
                else:
                    new_name = new_name[0]
                with open(new_name, 'wb') as f:
                    f.write(r.content)
                config['measure']['inputfile'][i-1] = new_name
            except:
                msg.append('Could not download ' + str(file))
                return (False, msg)
        else:
            # remove path before filename and add .bz2
            config['measure']['inputfile'][i-1] = os.path.basename(file) + '.bz2'
        config['measure']['inputfile'][i-1] = decompress_file(config['measure']['inputfile'][i-1])
    write_conf(config)  
    return (True, msg)

##################################################################
# HELLFIRE FUNCTIONS
##################################################################

def install_go():
    msg = []
    link = 'https://dl.google.com/go/go1.11.linux-amd64.tar.gz'
    name = 'go.tar.gz'

    if not os.path.isfile(name):
        import requests
        r = requests.get(link)
        open(name, 'wb').write(r.content)
        msg.append('Downloaded %s as file %s' % (link, name))
    else:
        msg.append(name + ' already downloaded')

    if not os.path.isdir('/root/go'):
        if call(['tar', 'xvf', name]) == 0:
            msg.append('Extracted ' + name)
            return (True, msg)
        else:
            msg.append('Go extraction failed')
            return (False, msg)
    else:
        msg.append('Go already installed')
        return (True, msg)
    return (False, ['Code should not get here'])
    
def install_canid():
    # download canid
    if call(['mkdir', '-p', '/root/work/src/github.com/britram/']) == 0:
        link = 'https://github.com/britram/canid.git'
        if not os.path.isdir('/root/work/src/github.com/britram/canid/'):
            if call(['git', 'clone', link, '/root/work/src/github.com/britram/canid/']) != 0:
                return (False, ['Could not download canid'])
    # install canid
    if call(['/root/go/bin/go', 'install', 'github.com/britram/canid/canid'], env={'GOPATH': '/root/work/'}) == 0:
        return (True, ['Installed canid'])
    else:
        return (False, ['Installing canid failed'])

def install_hellfire():
    path = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/go/bin:/root/work/bin'
    if call(['/root/go/bin/go', 'get', 'pathspider.net/hellfire/...'], env={'GOPATH': '/root/work/', 'GOROOT':'/root/go/', 'PATH':path}) == 0:
        return (True, ['Installed Hellfire'])
    return (False, ['Installing Hellfire failed'])

def setup_hellfire():
    debug = config['task']['debug']
    name = config['slack']['name']

    success, msg = install_packets()
    if success:
        success, report = install_go()
        msg += report
        if success:
            success, report = install_canid()
            msg += report
            if success:
                success, report = install_hellfire()
                msg += report
                if success:
                    #successfully installed, write to config
                    initialize_slack(config['slack']['token'], config['slack']['channel'])
                    if not debug:
                        msg = []
                    post(name, ['Setup successful'] + msg)
                    sys.exit([0])
    # Installation of packets failed
    try:
        initialize_slack(config['slack']['token'], config['slack']['channel'])
        if not debug:
            msg = []
        post(name, ['Setup failed'] + msg)
    except:
        # Slack not installed
        pass
    sys.exit([1])

##################################################################
# REPORTING FUNCTIONS
##################################################################

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
        tag += '    ' + str(line) + '\n'
    slackClient.chat.post_message(s_channel, tag)

def process_stderr(filename):
    error = []
    file = open(filename, 'r')
    for line in file: 
        error.append(line)
    return error

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

##################################################################
# TASK FUNCTIONS
##################################################################

def measure(input, output, workers, plugin, stderr):
    if call(['pspdr', 'measure', '-i', 'eth0', '--input', input, '--output', output, '-w', workers, plugin], stderr=open(stderr, 'w')) != 0:
        # Failed measurement
        return (False, process_stderr(stderr))
    else:
        return (True, [])

def upload(output, plugin, location, token, campaign, stderr): 
    # Set variables
    metadata1 = 'plugin:' + plugin
    metadata2 = 'location:' + location
    # Upload data
    if call(['pspdr', 'upload', '--add', metadata1, metadata2, '--token', token, '--campaign', campaign, output], stderr=open(stderr, 'w')) != 0:
        # Upload failed
        return (False, process_stderr(stderr))
    # Upload successful
    else:
        return (True, []) 

def destroy_VM(headers, id):
    try:
        import requests
        url = "https://api.digitalocean.com/v2/droplets/" + str(id)
        # delete droplet
        requests.delete(url, headers=headers)
    except:
        #what if request not installed?
        pass

##################################################################
# HELPER FUNCTIONS
##################################################################

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

def name_files(inputs, outputs, location, plugin):
    '''
    returns a list of tuple with tuple = (input, output, stderr) (names)
    '''
    letters = string.ascii_letters + string.digits
    if len(inputs) != len(outputs):
        global config
        if len(outputs) == 1:
            pre_output = outputs[0]
        else:
            pre_output = ''.join(random.sample(letters, k=5)) +'-' + location + '-' + plugin
        in_out = [(inputs[i], pre_output + '-' + str(i+1) + '.ndjson') for i in range(len(inputs))]
        # write new outputs in config
        config['measure']['outputfile'] = [y for x,y in in_out]
        write_conf(config)    
    else:
        # assume there is an input when task measure active, prevent renaming of prev named names
        if location + '-' not in outputs[0]:
            in_out = [(inputs[i], location + '-' + outputs[i]) for i in range(len(inputs))]
    return [(input, output, 'stderr_' + output) for input, output in in_out]

def write_conf(config):
    json.dump(config, open('config.json', 'w'), indent=4)

##################################################################
# MAIN
##################################################################

if __name__ == "__main__":
    debug = config['task']['debug']
    name = config['slack']['name']

    # Run hellfire or pathspider, not both
    if config['task']['hellfire']:
        path = {'GOPATH': '/root/work/',
                'GOROOT':'/root/go/',
                'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/go/bin:/root/work/bin'
                } 
        # run canid
        Popen(['setsid', 'canid', '-port', '8043'], env = path)
        time.sleep(60)
        # run hellfire, save as /root/topsites.ndjson
        call('hellfire --topsites --canid localhost:8043 > topsites.ndjson 2> helf.txt', shell=True, env=path)
        _ = compress_file('topsites.ndjson')
        initialize_slack(config['slack']['token'], config['slack']['channel'])
        post(name, ['Inputfile ready'])

    elif config['install']['install complete']:
        initialize_slack(config['slack']['token'], config['slack']['channel'])
    
        if config['task']['measure'] or config['task']['upload']:
            option = config['measure']
            plugin = option['plugin']
            location = config['upload']['location']

            for filenames in name_files(option['inputfile'], option['outputfile'], location, plugin):
                input, output, stderr = filenames
                tag = name +' with ' + input
                
                if config['task']['measure']:
                    if debug:
                        temp = ' '.join(['Started measurement: pspdr measure -i eth0 --input', input, '--output', output, '-w', option['workers'], plugin,'\n'])
                        post(tag, [temp])
                    #run measurement
                    success, report = measure(input, output, option['workers'], plugin, stderr)
                    if success:
                        report.extend(analyze_output(output, plugin))
                        post(tag, ['Measurement successful:'] + report)
                    else:
                        if not debug: report = []
                        post(tag, ['Measurement failed:'] + report)
                        continue

                if config['task']['upload']:
                    option = config['upload']
                    success, report = upload(output, plugin, location, option['token'], option['campaign'], stderr)
                    if success:
                        post(tag, ['Upload successful:'] + report) 
                    else:
                        post(tag, ['Upload failed:'] + report)
    else:
        # VM not set up properly
        pass

    if config['task']['destroy']:
        initialize_slack(config['slack']['token'], config['slack']['channel'])
        post(name, ['Destroying Droplet'])
        #destroy the droplet
        destroy_VM(config['provider']['headers'], config['destroy']['id'])
        #if destruction failed this code will run
        time.sleep(300)
        post(name, ['Destruction failed'])
