from subprocess import call
import sys
import json

# list of packages to install
packages = [
    'python3-pip',
    'libssl-dev',
    'libtrace-dev',
    'libldns-dev',
    'libcurl4-openssl-dev'
]

# list of libraries to install
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

# apt-get install -y python3-pip libssl-dev libtrace-dev libldns-dev libcurl4-openssl-dev
for package in packages:
    if call(['apt-get', 'install', '-qq', '-y', package]) == 1:
        failed_pkg = failed_pkg + package + ' '

#import pip after installation
import pip

# install packages
for package in py_packages:
    if pip.main(['install','--quiet', package]) == 1:
        failed_pkg = failed_pkg + package + ' '

# 'git clone -b uploader --single-branch https://github.com/nstudach/pathspider.git'
ps_link = 'https://github.com/nstudach/pathspider.git'
call(['git', 'clone', '-b', 'uploader', '--single-branch', ps_link])

# 'git clone https://github.com/nevil-brownlee/python-libtrace.git'
lib_link = 'https://github.com/nevil-brownlee/python-libtrace.git'
call(['git', 'clone', lib_link])

print('install gits')

# '(cd python-libtrace/ && make install-py3)'
if call('(cd python-libtrace/ && make install-py3 > /dev/null 2>&1)', shell=True) == 1:
    failed_pkg = failed_pkg + 'libtrace' + ' '

# '(cd pathspider/ && python3 setup.py install)'
if call('(cd pathspider/ && python3 setup.py install > /dev/null 2>&1)', shell=True) == 1:
    failed_pkg = failed_pkg + 'pathspider'

# setup slack
from slacker import Slacker
config = json.load(open('config.json'))
slackClient = Slacker(config['slack']['token'])

#download input file if needed
if config['measurement']['inputfile'].startswith('http'):
    msg = str(sys.argv[1]) + ': Downloading inputfile from: ' + config['measurement']['inputfile']
    slackClient.chat.post_message(config['slack']['channel'], msg)
    import requests
    r = requests.get(config['measurement']['inputfile'])
    with open('input.ndjson', 'wb') as f:
        f.write(r.content)
    config['measurement']['inputfile']='input.ndjson'
    #write json file
    with open('config.json', 'w') as outfile:
        json.dump(config, outfile)

if failed_pkg == '':
    msg = str(sys.argv[1]) + ': Installation succesful'
else:
    msg = str(sys.argv[1]) + ': Installation failed with: ' + failed_pkg

slackClient.chat.post_message(config['slack']['channel'], msg)