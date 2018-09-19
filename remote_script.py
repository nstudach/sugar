import time
import sys
import json
import random
from subprocess import call

letters = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'

# list of packages to install
packages = [
    'libssl-dev',
    'libtrace-dev',
    'libldns-dev',
    'libcurl4-openssl-dev',
    'git-core',
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

def install_packets():
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
        return (True, '')
    else:
        return (False, 'Packets: ' + failed_pkg +'\n')

def install_git():
    failed_pkg = ''

    # 'git clone -b uploader --single-branch https://github.com/nstudach/pathspider.git'
    ps_link = 'https://github.com/nstudach/pathspider.git'
    call(['git', 'clone', '-b', 'uploader', '--single-branch', ps_link])

    # 'git clone https://github.com/nevil-brownlee/python-libtrace.git'
    lib_link = 'https://github.com/nevil-brownlee/python-libtrace.git'
    call(['git', 'clone', lib_link])

    # '(cd python-libtrace/ && make install-py3)'
    if call('(cd python-libtrace/ && make install-py3 > /dev/null 2>&1)', shell=True) != 0:
        failed_pkg += 'libtrace' + ' '

    # '(cd pathspider/ && python3 setup.py install)'
    if call('(cd pathspider/ && python3 setup.py install > /dev/null 2>&1)', shell=True) != 0:
        failed_pkg += 'pathspider'

    if failed_pkg == '':
        return (True, '')
    else:
        return (False, 'Git Repositories: ' + failed_pkg +'\n')

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
                msg += 'Downloaded inputfile from: ' + str(file) + '\n'
                r = requests.get(file)
                new_name = ''.join(['input', str(i), '.ndjson'])
                with open(new_name, 'wb') as f:
                    f.write(r.content)
                config['measurement']['inputfile'][i-1] = new_name
            except:
                msg += 'Could not download ' + str(file) + '\n'
                return (False, msg)
    with open('config.json', 'w') as outfile:
        json.dump(config, outfile)
    return (True, msg)

def setup(debug):
    success, msg = install_packets()
    if success:
        success, report = install_git()
        msg += report
        if success:
            success, report = download_inputs()
            if not debug:
                msg = '' 
            return (True, 'Setup successful\n' + msg)
    if not debug:
        msg = ''
    return(False, 'Setup failed with\n' + msg)

def process_stderr(filename):
    error = ''
    file = open(filename, 'r')
    for line in file: 
        error += '\n' + line
    return error

def destroy_VM(headers,id):
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
    #read config.json
    config = json.load(open('config.json'))
    option = config['measurement']
    debug = option['debug']

    success, msg = setup(debug)
    if success:
        # import after installation
        from slacker import Slacker
        # setup Slack
        slackClient = Slacker(config['slack']['token'])
        channel = config['slack']['channel']

        slackClient.chat.post_message(channel, str(sys.argv[1]) + ':\n' + msg + 'Starting measurements')

        #define some variables
        location = str(sys.argv[1]).split('-')[1]
        plugin = str(sys.argv[1]).split('-')[2]
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
                msg = ' '.join([tag, 'Started measurement:', 'pspdr', 'measure', '-i', 'eth0', '--input', file, '--output', output, '-w', option['workers'], plugin,'\n'])
                slackClient.chat.post_message(channel, msg)

            # start measurement
            success, msg = measure(file, output, option['workers'], plugin, stderr)
            if not success:
                # Measurement failed
                slackClient.chat.post_message(channel, tag + msg)
            else:
                # Successful measurement    
                # Analyse output
                msg += analyze_output(output, plugin) + '\n'

                if debug:
                    slackClient.chat.post_message(channel, msg)
                    msg = ''

                success, report = upload(output, plugin, location, option['token'], option['campaign'], stderr)
                msg += report
                if not success:
                    # Upload failed
                    slackClient.chat.post_message(channel, tag + msg)   
                else:
                    # Upload successful
                    slackClient.chat.post_message(channel, tag + msg)
    else:
        # Installation failed
        try:
            from slacker import Slacker
            # setup Slack
            config = json.load(open('config.json'))
            slackClient = Slacker(config['slack']['token'])
            channel = config['slack']['channel']  
            slackClient.chat.post_message(channel, str(sys.argv[1]) + ':\n' + msg)
        except:
            # Slack not installed
            pass
    
    slackClient.chat.post_message(channel, str(sys.argv[1]) + ': Destroying Droplet')
    #destroy the droplet
    destroy_VM(config['provider']['headers'], id = str(sys.argv[2]))
    #if destruction failed this code will run
    time.sleep(300)
    slackClient.chat.post_message(channel, str(sys.argv[1]) + ': Destruction failed')