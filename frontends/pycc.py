#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from shutil import copyfile

from parser import parse, generate_ast, apply_transformations, ASTDump
from parse_debug import process_debug_info

def parse_args(argv):
    parser = argparse.ArgumentParser(description='Simplified CC1 frontend')
    parser.add_argument('--qinclude', action='append', help='Include Paths for iquote', required=False)
    parser.add_argument('--binclude', action='append', help='Include Paths for Block Include', required=False)
    parser.add_argument('--cc1', help='<Required> cc1 Path', required=False)
    parser.add_argument('--version', help='Get Version String of cc1', required=False)
    parser.add_argument('--preproc', help='preproc path', required=False)
    parser.add_argument('--charmap', help='preproc charmap', required=False)
    parser.add_argument('-S', action='store_true', help='Ignore parameter as agbcc does not know it', required=False)
    parser.add_argument('-o', help='Output Assembly file', required=False, dest='destination')
    parser.add_argument('--no-parse', action='store_true', help='disable parsing of agbcc output (debug option)',
                        required=False)
    return parser.parse_known_args(argv)


def compile(source, output_filename, args, remainder):
    cpp_args = ["cpp", "-nostdinc", "-undef"]

    # Add Block Includes and Quote Includes
    if args.qinclude:
        for q in args.qinclude:
            cpp_args += ["-iquote", q]

    if args.binclude:
        for b in args.binclude:
            cpp_args += ["-I", b]

    cpp_args += [source, "-o", source + ".i"]
    subprocess.call(cpp_args)
    if args.preproc and args.charmap:
        pprocess = subprocess.Popen([args.preproc, source + '.i', args.charmap], stdout=subprocess.PIPE)
        subprocess.call([args.cc1] + ['-o', output_filename] + remainder, stdin=pprocess.stdout)
    else:
        with open(source + '.i', 'r') as a:
            subprocess.call([args.cc1] + ['-o', output_filename] + remainder, stdin=a)


def process_asm(input_filename, output_filename):
    tree, success = parse(input_filename)
    if not success:
        raise ValueError('could not parse file')
    ast = generate_ast(tree)
    apply_transformations(ast)
    with open(output_filename, 'w') as destination_file:
        ASTDump(destination_file).visit(ast)


def cleanup(args, source):
    for file in [f'{source}.i', f'{args.destination}.tmp']:
        if os.path.exists(file):
            os.remove(file)


def main(argv):
    status_code = 0
    args, remainder = parse_args(argv)
    if args.version:
        git_proc = subprocess.run(['git', '--git-dir=' + args.version + '/.git', 'rev-parse', '--short', 'HEAD'],
                                  stdout=subprocess.PIPE)
        print("pycc frontend for agbcc1 " + os.path.basename(args.version) + "@" + git_proc.stdout.decode('utf-8'))
        exit(0)
    source = remainder.pop(-1)
    try:
        if source.endswith('.c'):
            asm_file = args.destination + '.tmp'
            compile(source, asm_file, args, remainder)
            process_debug_info(asm_file)
        else:
            asm_file = source

        if not args.no_parse:
            try:
                process_asm(asm_file, args.destination)
            except Exception as e:
                print(f'error cleaning assembly code: {e}\nOutputting unprocessed assembly', file=sys.stderr)
                copyfile(asm_file, args.destination)
                status_code = 1
        else:
            copyfile(asm_file, args.destination)
    finally:
        cleanup(args, source)
    exit(status_code)


if __name__ == '__main__':
    main(sys.argv[1:])
