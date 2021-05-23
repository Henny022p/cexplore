#!/usr/bin/env python3
import argparse
from parser import parse, ASTGenerator, ASTDump

parser = argparse.ArgumentParser(description='Simplified "compiler" frontend, cats any input')

parser.add_argument('--version', action='store_true', help='Get Version String of cc1', required=False, dest='version')
parser.add_argument('-o', action='store', help='Output Assembly file', required=False, dest='destination')
args, remainder = parser.parse_known_args()

if args.version:
    print("pycat frontend for cexplore")
    quit()

source = remainder[-1]

tree, success = parse(source)
if not success:
    raise ValueError('bad input file')
ast = ASTGenerator().visit(tree)
with open(args.destination, 'w') as f_dst:
    ASTDump(f_dst).visit(ast)
