#python 3.6
import json
import sys

def clean(jf):
    if 'dp' in jf:
        return json.dumps({'dip':jf['dip'], 'domain':jf['domain'], 'dp':jf['dp']}) + '\n'
    else:
        return json.dumps({'dip':jf['dip'], 'domain':jf['domain']}) + '\n'        

def read_lines(filename):
    '''
    returns each line of file as json object
    '''
    with open(filename, 'r') as input:
        for line in input.readlines():
            try:
                yield json.loads(line)
            except:
                print('line is not json format')
                print(line)


if __name__ == "__main__":

    # ARGs
    # 1: Inputfile
    # 2: Outputfile
    # 3: Mode (clean, split, both)
    # 4: Junk size for mode = split, both

    mode = sys.argv[3]

    if mode == 'clean':
        print('clean')
        ranks = []
        with open(sys.argv[2], 'w') as outfile:
            for line in read_lines(sys.argv[1]):
                if line['rank'] not in ranks:
                    ranks.append(line['rank'])
                    outfile.write(clean(line))

    elif mode == 'split':
        print('split')
        junk_size = int(sys.argv[4])
        #entry counter
        i = 0
        # file counter
        k = 1
        outfile = open(sys.argv[2] + '_' + str(k), 'a+') 
        for line in read_lines(sys.argv[1]):
            if i < junk_size:
                i += 1
                outfile.write(json.dumps(line) + '\n')
            else:
                i = 0
                k += 1
                outfile = open(sys.argv[2] + '_' + str(k), 'a+')

    elif mode == 'both':
        print('both')
        junk_size = int(sys.argv[4])
        #entry counter
        i = 0
        # file counter
        k = 1
        outfile = open(sys.argv[2] + '_' + str(k), 'a+') 
        ranks = []
        for line in read_lines(sys.argv[1]):
            if i < junk_size:
                if line['rank'] not in ranks:
                    ranks.append(line['rank'])
                    i += 1
                    outfile.write(clean(line))
            else:
                i = 0
                #reset ranks for speed
                ranks = []
                k += 1
                outfile = open(sys.argv[2] + '_' + str(k), 'a+')

    else:
        print('mode' + mode + ' not found')
