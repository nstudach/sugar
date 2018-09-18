import time
import sys
import json
import random
from subprocess import call

letters = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'

# list of packages to install
packages = [
    'python3-setuptools',
    'libssl-dev',
    'libtrace-dev',
    'libldns-dev',
    'libcurl4-openssl-dev',
    'git-core',
    'build-essential',
    'python3-dev'
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

def install_packets():
    failed_pkg = ''
    # apt-get update
    call(['apt-get', '-qq', 'update'])

    # install packages via apt-get
    for package in packages:
        if call(['apt-get', 'install', '-qq', '-y', package]) == 1:
            failed_pkg = failed_pkg + package + ' '

    # use easy_install3 to get pip3. For Debian not working with apt-get
    if call(['easy_install3', '-U', 'pip']) == 1:
        failed_pkg = failed_pkg + package + ' '

    # apt-get update
    call(['apt-get', '-qq', 'update'])

    # install packages
    for package in py_packages:
        if call([sys.executable, '-m', 'pip', 'install', '--quiet', package]) == 1:
            failed_pkg = failed_pkg + package + ' '

    # 'git clone -b uploader --single-branch https://github.com/nstudach/pathspider.git'
    ps_link = 'https://github.com/nstudach/pathspider.git'
    call(['git', 'clone', '-b', 'uploader', '--single-branch', ps_link])

    # 'git clone https://github.com/nevil-brownlee/python-libtrace.git'
    lib_link = 'https://github.com/nevil-brownlee/python-libtrace.git'
    call(['git', 'clone', lib_link])

    # '(cd python-libtrace/ && make install-py3)'
    if call('(cd python-libtrace/ && make install-py3 > /dev/null 2>&1)', shell=True) == 1:
        failed_pkg = failed_pkg + 'libtrace' + ' '

    # '(cd pathspider/ && python3 setup.py install)'
    if call('(cd pathspider/ && python3 setup.py install > /dev/null 2>&1)', shell=True) == 1:
        failed_pkg = failed_pkg + 'pathspider'

    if failed_pkg == '':
        return (True, 'Installation successful\n')
    else:
        return (False,failed_pkg)

def download_inputs():
    import requests
    
    config = json.load(open('config.json'))

    #download input file if needed
    msg = ''
    i = 0
    for file in config['measurement']['inputfile']:
        i += 1
        if file.startswith('http'):
            try:
                msg += 'Downloading inputfile from: ' + str(file) + '\n'
                r = requests.get(file)
                new_name = ''.join(['input', str(i), '.ndjson'])
                with open(new_name, 'wb') as f:
                    f.write(r.content)
                config['measurement']['inputfile'][i-1] = new_name
            except:
                msg += 'Could not download\n'
                return (False, msg)
    with open('config.json', 'w') as outfile:
        json.dump(config, outfile)
    return (True, msg)

def process_stderr(filename):
    error = ''
    file = open(filename, 'r')
    for line in file: 
        error += '\n' + line
    return error

def destroy_VM(headers,id):
    url = "https://api.digitalocean.com/v2/droplets/" + str(id)
    # delete droplet
    requests.delete(url, headers=headers)

def analyze_output(filename, plugin):
    if plugin in ['dscp', 'ecn', 'evilbit', 'h2', 'udpzero']:
        return search(filename, ['works', 'broken', 'offline', 'transient'])
    elif plugin in ['mss']:
        return search(filename, ['online', 'offline'])
    else:
        return 'Plugin not found'

def search(filename, keywords):
    '''
    Searches each line of file for one keyword
    Returns percentage of lines containig each keyword as string
    '''
    counter = {}
    counter['total'] = 0
    for keyword in keywords:
        counter[keyword]=0

    with open(filename, 'r') as input:
        for line in input.readlines():
            counter['total'] += 1
            for keyword in keywords:
                if keyword in line:
                    counter[keyword] += 1
                    break
    return json.dumps(counter)

def upload(output, plugin, location, token, campaign, stderr): 
    # Analyse output
    msg = analyze_output(output, plugin)

    # Set variables
    metadata1 = 'plugin:' + plugin
    metadata2 = 'location:' + location

    # Upload data
    if call(['pspdr', 'upload', '--metadata', metadata1, metadata2, '--token', token, '--campaign', campaign, output], stderr=open(stderr, 'w')) != 0:
        # Upload failed
        msg = 'Upload failed:\n'
        if debug:
            msg += process_stderr(stderr)
        return (False, msg)
    # Upload successful
    else:
        return (True, 'Upload successful: ' + output + '\n')  

def measure(input, output, workers, plugin, stderr):
    if call(['pspdr', 'measure', '-i', 'eth0', '--input', input, '--output', output, '-w', workers, plugin], stderr=open(stderr, 'w')) != 0:
        # Failed measurement
        msg = 'Failed measurement:\n'
        if debug:
            msg += process_stderr(stderr)
        return (False, msg)
    else:
        return (True, 'Measurement successful: ' + input + '\n')
                

if __name__ == "__main__":  
    success, msg = install_packets()
    if success:
        # import after installation
        import requests
        from slacker import Slacker
        
        # setup Slack
        config = json.load(open('config.json'))
        slackClient = Slacker(config['slack']['token'])
        channel = config['slack']['channel']

        option = config['measurement']
        debug = option['debug']

        success, report = download_inputs()
        if success:
            if not debug:
                slackClient.chat.post_message(channel, str(sys.argv[1]) + ': Setup successful\nStarting measurements')
            else:
                slackClient.chat.post_message(channel, str(sys.argv[1]) + ':\n' + msg + report)  
            #define some variables
            location = str(sys.argv[1]).split('-')[1]
            plugin = str(sys.argv[2])
            i = 0

            # start measurement for each file in config
            for file in option['inputfile']:
                i += 1
                #set identifier
                tag = str(sys.argv[1]) + 'with input ' + str(file) + ':\n'
                output = ''.join(random.sample(letters, k=5)) +'-' + location + '-' + plugin + str(i)
                # set file for stderr
                stderr = ''.join(['stderr_', str(i), '.txt'])
        
                # send debug msg
                if debug:
                    msg = ' '.join([tag, 'Started measurement:', 'pspdr', 'measure', '-i', 'eth0', '--input', file, '--output', output, '-w', option['workers'], str(sys.argv[2]),'\n'])
                    slackClient.chat.post_message(channel, msg)

                # start measurement
                success, report = measure(file, output, option['workers'], plugin, stderr)
                if not success:
                    # Measurement failed
                    slackClient.chat.post_message(channel, tag + report)
                else:
                    # Successful measurement    
                    # Analyse output
                    report += analyze_output(output, plugin)

                    if debug:
                        slackClient.chat.post_message(channel, report)
                        report = ''

                    success, temp = upload(output, plugin, location, option['token'], option['campaign'], stderr)
                    report += temp
                    if not success:
                        # Upload failed
                        slackClient.chat.post_message(channel, tag + report)   
                    else:
                        # Upload successful
                        slackClient.chat.post_message(channel, tag + report)
        else:
            if not debug:
                report = 'Could not download input files'
            slackClient.chat.post_message(channel, str(sys.argv[1]) + ':\n' + msg + report)
    else:
        # Installation failed
        try:
            # setup Slack
            config = json.load(open('config.json'))
            slackClient = Slacker(config['slack']['token'])
            channel = config['slack']['channel']  
            slackClient.chat.post_message(channel, str(sys.argv[1]) + ': Installation failed with: ' + msg)
        except:
            # Slack not installed
            pass
    
    slackClient.chat.post_message(channel, str(sys.argv[1]) + ': Destroying Droplet')
    #destroy the droplet
    destroy_VM(config['provider']['headers'], id = str(sys.argv[3]))