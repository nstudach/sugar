import time
import sys
import json
import random
import requests
from subprocess import call
from slacker import Slacker

letters = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'

def process_stderr(filename):
    error = ''
    file = open(filename, 'r')
    for line in file: 
        error += '\n' + line
    return error

def destroy_VM(headers,id):
    url = "https://api.digitalocean.com/v2/droplets/" + str(id)
    # delete droplet
<<<<<<< HEAD
    r = requests.delete(url, headers=headers)

=======
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
>>>>>>> debian

if __name__ == "__main__":
    # setup Slack
    config = json.load(open('config.json'))
    slackClient = Slacker(config['slack']['token'])
    channel = config['slack']['channel']
    
    #define some variables
    name = str(sys.argv[1])
    location = name.split('-')[1]
    plugin = str(sys.argv[2])
<<<<<<< HEAD
    err1 = open('stderr1.txt','w')
    err2 = open('stderr2.txt','w')
    output = ''.join(random.choices(letters, k=5)) +'-' + location + '-' + plugin
    
    option = config['measurement']
    msg = name + ': Started measurment:'+' '.join(['pspdr', 'measure', '-i', 'eth0', '--input', option['inputfile'], '--output', output, '-w', option['workers'], str(sys.argv[2])])
    slackClient.chat.post_message(channel, msg)
    
    if call(['pspdr', 'measure', '-i', 'eth0', '--input', option['inputfile'], '--output', output, '-w', option['workers'], plugin], stderr=err1) != 0:
        msg = name + ': Failed measurement'
        slackClient.chat.post_message(channel, msg+process_stderr('stderr1.txt'))
    else:
        msg = str(sys.argv[1]) + ': Completed measurement'
        slackClient.chat.post_message(channel, msg)
        # Upload data
        plugin = 'plugin:'+plugin
        location = 'location:'+location
        if call(['pspdr', 'upload', '--metadata', location, plugin, '--token', option['token'], '--campaign', option['campaign'], output], stderr=err2) != 0:
            msg = str(sys.argv[1]) + ': Upload failed'
            slackClient.chat.post_message(channel, msg+process_stderr('stderr2.txt'))
        else:
            msg = str(sys.argv[1]) + ': Upload succesfull: ' + output
            slackClient.chat.post_message(channel, msg)
    msg = str(sys.argv[1]) + ': Destroying Droplet'
    slackClient.chat.post_message(channel, msg)
=======
    pre_output = ''.join(random.sample(letters, k=5)) +'-' + location + '-' + plugin
    option = config['measurement']
    err1 = open('stderr1.txt','w')
    i = 0
    debug = option['debug']

    # start measurement for each file in config
    for file in option['inputfile']:
        i += 1
        msg = name + 'with input ' + str(file) + ':\n'
        output = pre_output + str(i)
        # send debug msg
        if debug:
            msg2 = ' '.join([name, ': Started measurement:', 'pspdr', 'measure', '-i', 'eth0', '--input', file, '--output', output, '-w', option['workers'], str(sys.argv[2]),'\n'])
            slackClient.chat.post_message(channel, msg2)

        # set file for stderr
        stderr = ''.join(['stderr', str(i), '.txt'])
        # start measurement
        if call(['pspdr', 'measure', '-i', 'eth0', '--input', file, '--output', output, '-w', option['workers'], plugin], stderr=open(stderr, 'w')) != 0:
            # Failed measurement
            msg += 'Failed measurement:\n'
            if debug:
                msg += process_stderr(stderr)
            # Send progress to slack
            slackClient.chat.post_message(channel, msg)
        
        # Succesfull measurement
        else:
            if debug:
                slackClient.chat.post_message(channel, name + ' with input ' + str(file) + ': Completed measurement')
            
            # Analyse output
            msg += analyze_output(output, plugin)

            if debug:
                slackClient.chat.post_message(channel, msg)
                msg = name + 'with input ' + str(file) + ':\n'


            # Set variables
            metadata1 = 'plugin:' + plugin
            metadata2 = 'location:' + location

            # Upload data
            if call(['pspdr', 'upload', '--metadata', metadata1, metadata2, '--token', option['token'], '--campaign', option['campaign'], output], stderr=open(stderr, 'w')) != 0:
                # Upload failed
                msg += 'Upload failed:\n'
                if debug:
                    msg += process_stderr(stderr)
                # Send progress to slack
                slackClient.chat.post_message(channel, msg)
        
            # Upload succesfull
            else:
                msg += 'Upload succesfull: ' + output
                slackClient.chat.post_message(channel, msg)
    
    slackClient.chat.post_message(channel, name + ': Destroying Droplet')
>>>>>>> debian
    #destroy the droplet
    destroy_VM(config['provider']['headers'], id = str(sys.argv[3]))