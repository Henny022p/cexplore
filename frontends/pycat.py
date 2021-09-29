#!/usr/bin/env python3
import argparse
import sys

from parser import parse, generate_ast, apply_transformations, ASTDump


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Simplified "compiler" frontend, cats any input')
    parser.add_argument('--version', action='store_true', help='Get Version String', required=False)
    parser.add_argument('-o', action='store', help='Output Assembly file', required=False, dest='destination')
    return parser.parse_known_args(argv)


def main(argv):
    args, remainder = parse_args(argv)
    if args.version:
        print("pycat frontend for cexplore")
        quit()

    source = remainder[-1]

    tree, success = parse(source)
    if not success:
        raise ValueError('bad input file')
    ast = generate_ast(tree)
    apply_transformations(ast)
    with open(args.destination, 'w') as f_dst:
        ASTDump(f_dst).visit(ast)


if __name__ == '__main__':
    main(sys.argv[1:])
