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
    r = requests.delete(url, headers=headers)


if __name__ == "__main__":
    # setup Slack
    config = json.load(open('config.json'))
    slackClient = Slacker(config['slack']['token'])
    channel = config['slack']['channel']
    
    #define some variables
    name = str(sys.argv[1])
    location = name.split('-')[1]
    plugin = str(sys.argv[2])
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
    #destroy the droplet
    destroy_VM(config['provider']['headers'], id = str(sys.argv[3]))