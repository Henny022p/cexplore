#!/usr/bin/env python3

import subprocess
import sys
import os
import argparse

parser = argparse.ArgumentParser(description='Simplified CC1 frontend')

parser.add_argument('--qinclude', action='append', help = 'Include Paths for iquote', required = False, dest='qinclude')
parser.add_argument('--binclude', action='append', help = 'Include Paths for Block Include', required = False, dest='binclude')
parser.add_argument('--cc1', action='store', help = '<Required> cc1 Path', required = False, dest='cc1')
parser.add_argument('--version', action='store', help = 'Get Version String of cc1', required = False, dest='version')
parser.add_argument('--preproc', action='store', help ='preproc path', required = False, dest='preproc')
parser.add_argument('--charmap', action='store', help ='preproc charmap', required = False)
parser.add_argument('-S', action='store_true', help='Ignore parameter as agbcc does not know it', required=False)
parser.add_argument('-o', action='store', help = 'Output Assembly file', required = False, dest='destination')

args, remainder = parser.parse_known_args()
'''
repopath = "/repos/tmc/"
agbccpath = "/agbcc_build/tools/"
agbcc = agbccpath+ "agbcc/bin/agbcc"
preproc = repopath+ "tools/preproc/preproc"
charmap = repopath+ "charmap.txt"
'''
if args.version:
    git_proc = subprocess.run(['git', '--git-dir='+args.version+'/.git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE)
    sys.stdout.write("pycc frontend for agbcc1 " + os.path.basename(args.version) + "@" + git_proc.stdout.decode('utf-8'))
    quit()
    
source = remainder[-1]
cpp_args = ["cpp", "-nostdinc", "-undef"]

# Add Block Includes and Quote Includes
if args.qinclude:
    for q in args.qinclude:
    	cpp_args += ["-iquote", q]

if args.binclude:
    for b in args.binclude:
    	cpp_args += ["-I", b]

cpp_args += [source, "-o", source+".i"]
subprocess.call(cpp_args)
if args.preproc and args.charmap:
    pprocess = subprocess.Popen([args.preproc, source+'.i', args.charmap], stdout=subprocess.PIPE)
    subprocess.call([args.cc1] + ['-o', args.destination +'.tmp']+  remainder[0:-1], stdin=pprocess.stdout)
else:
    with open(source+'.i', 'r') as a:
        subprocess.call([args.cc1] +['-o', args.destination+'.tmp']+ remainder[0:-1], stdin=a)

# Postprocess assembly to be better suited for diff
with open(args.destination+'.tmp','r') as file, open(args.destination,'w') as out:
    for line in file:
        if not line.strip(): # Remove all empty lines (TODO implement as filter?)
            continue
        if '@cond_branch' in line: # Remove cond_branch comment
            line = line.replace('@cond_branch', '')
        if '#24' in line:
            line = line.replace('#24', '#0x18')
        out.write(line)
if os.path.exists(source+'.i'):
	os.remove(source+'.i')
'''
source = sys.argv[-1]
subprocess.call(["cpp", "-nostdinc", "-undef", "-iquote", repopath + "include" , "-I", agbccpath + "agbcc", "-I", agbccpath + "agbcc/include", source, "-o", source+".i"])
pprocess = subprocess.Popen([preproc, source+".i", charmap], stdout=subprocess.PIPE)
subprocess.call([agbcc] + sys.argv[1:-1], stdin=pprocess.stdout)

if os.path.exists(source+".i"):
        os.remove(source+".i")
'''
