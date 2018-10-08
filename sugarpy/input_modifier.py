#python 3.6
import json

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
            new_outfile = filename + '_' + str(k)
            outfiles.append(new_outfile)
            outfile = open(new_outfile, 'a+') 
        else:
            i += 1
            outfile.write(clean(line))

    # write files in config
    config = json.load(open(configfile))
    config['measure']['inputfile'] = outfiles
    json.dump(config, open(configfile, 'w'), indent=4)
    

