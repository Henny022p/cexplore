#!/usr/bin/env python3

import os
import argparse
import shutil
import re
import sys

parser = argparse.ArgumentParser(description='Simplified "compiler" frontend, cats any input')

parser.add_argument('--version', action='store_true', help='Get Version String of cc1', required=False, dest='version')
parser.add_argument('-o', action='store', help='Output Assembly file', required=False, dest='destination')
args, remainder = parser.parse_known_args()

if args.version:
    print("pycat frontend for cexplore")
    quit()

source = remainder[-1]

with open(source, 'r') as f_src, open(args.destination, 'w') as f_dst:
    outstring = ''
    jump_labels = []
    switch_labels = []
    data_labels = {}
    prev_data_label = None
    last_label = None
    n_data_labels = 0
    n_data_labels_group = 0
    for line in f_src:
        line = line.strip()
        if '@' in line:
            line = line.split('@')[0].strip()
        if 'thumb_func_start' in line:
            _, name = line.split()
            line = '\t.align 2, 0\n\t.global {name}\n\t.thumb\n\t.thumb_func\n\t.type {name}, function' \
                .format(name=name)
        elif line and ':' not in line and not line.startswith('@') and not line.startswith('//'):
            instruction = line.split(maxsplit=1)
            if len(instruction) > 1:
                opcode, operand = instruction

                # Remove s suffix from most opcodes
                if opcode.endswith('s') and opcode != 'bls' and opcode != 'bhs' and opcode != 'bcs':
                    opcode = opcode[:-1]

                # Fix bhs -> bcs and blo -> bcc
                if opcode == 'bhs':
                    opcode = 'bcs'
                if opcode == 'blo':
                    opcode = 'bcc'

                # find label to rename them later
                if opcode in ['b', 'beq', 'bne', 'bgt', 'blt', 'bge', 'ble', 'bcs', 'bhs', 'bcc', 'blo', 'bmi', 'bpl',
                              'bvs', 'bvc', 'bhi', 'bls']:
                    jump_labels.append(operand)

                # remove comments from ldr
                if opcode == 'ldr':
                    operand = operand.split('@')[0]

                rx_ry = re.search(r'r\d{1,2}-r\d{1,2}', operand, re.I)
                if rx_ry:
                    rx_ry = rx_ry.group(0)
                    pos = rx_ry.find('-')
                    x = int(rx_ry[1:pos])
                    y = int(rx_ry[pos + 2:])
                    operands = operand.split(rx_ry, 1)
                    operand = operands[0]
                    for i in range(x, y + 1):
                        operand += 'r{}, '.format(i)
                    operand = operand[:-2] + operands[1]
                dec_num = re.search(r'#\-?\d+', operand, re.I)
                if dec_num:
                    dec_num = dec_num.group(0)
                    if dec_num[1] != '-':
                        value = int(dec_num[1:])
                        if value != 0:
                            s = operand.split(dec_num, 1)
                            operand = '{}#0x{:x}{}'.format(s[0], value, s[1])
                    else:
                        value = int(dec_num[2:])
                        if value != 0:
                            s = operand.split(dec_num, 1)
                            operand = '{}#-0x{:x}{}'.format(s[0], value, s[1])

                if opcode in ('add', 'sub', 'lsl', 'lsr', 'asr', 'ror', 'and', 'orr', 'eor'):
                    operands = operand.split(',')
                    if len(operands) == 2:
                        operand = operands[0] + ', ' + operand

                # Rename sb to r9
                operands = operand.split(', ')
                operands = map(lambda x: 'r9' if x == 'sb' else x, operands)
                operand = ', '.join(operands)

                # fix movs rX, #0 -> mov rX, #0x0
                if opcode == 'mov':
                    operands = operand.split(', ')
                    if operands[1] == '#0':
                        operand = operands[0] + ', #0x0'
                # rsb rn, rn, #0 -> neg rn, rn
                if opcode == 'rsb':
                    operands = operand.split(', ')
                    if operands[2] == '#0':
                        opcode = 'neg'
                        operand = operands[0] + ', ' + operands[1]

                line = '\t{}\t{}'.format(opcode, operand)
        elif ':' in line:
            last_label = line.strip(':')

        if '.4byte' in line:
            if ':' in line:
                thing = line.split(' ')
                label = thing[0].strip(':')
                line = ''
                if not prev_data_label:
                    line += '{}:\n'.format(label)
                    prev_data_label = label
                    n_data_labels += 1
                    data_labels[label] = '_data{}'.format(n_data_labels)
                else:
                    data_labels[label] = '_data{}+{}'.format(n_data_labels, hex(4 * n_data_labels_group))
                n_data_labels_group += 1
                value = thing[2]
                if value.startswith('0x'):
                    value = int(value, 16)
                    if value >= 1 << 31:
                        value = -((1 << 32) - value)
                    value = hex(value)
                line += '\t.word\t{}'.format(value)
            else:  # switch jumptable
                label = line.split('\t')[2]
                switch_labels.append(label)
                line = line.replace('.4byte', '.word')
                if not last_label:
                    print('found data without label: {}'.format(line), file=sys.stderr)
                if last_label and last_label not in data_labels:
                    n_data_labels += 1
                    data_labels[last_label] = '_data{}'.format(n_data_labels)
        else:
            prev_data_label = None
            n_data_labels_group = 0

        outstring += line + '\n'

    for i, label in enumerate(jump_labels):
        outstring = outstring.replace(label, '.code{}'.format(i))
    for i, label in enumerate(switch_labels):
        outstring = outstring.replace(label, '.case{}'.format(i))
    for current, new in data_labels.items():
        outstring = outstring.replace(current, new)
    f_dst.write(outstring)
