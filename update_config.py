import sys
import json

options = ['debug', 'install', 'measure', 'upload', 'destroy']

def update_setup(file, fields):
    config = read_config(file)
    for field in fields:
        tag, value = field.split('=')
        if tag == 'all':
            for option in options:
                config['setup'][option] = value
        else:
            config['setup'][tag] = value
    write_config(file, config)

def clean_config(file):
    config = read_config(file)
    config.pop('droplet', None)
    config['provider'].pop('regions', None)
    for tag in ['host info', 'create', 'hellfire']:
        config['setup'].pop(tag, None)
    write_config(file, config)

def write_config(file, config):
    json.dump(config, open(file, 'w'), indent=4)

def read_config(filename):
    return json.load(open(filename))

if __name__ == "__main__":
    filename = 'config.json'
    # remove unused fields from config
    clean_config(filename)
    # update local config file
    update_setup(filename,sys.argv[1:])
