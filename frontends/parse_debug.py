# Line number opcodes.
# https://github.com/gittup/binutils/blob/8db2e9c8d085222ac7b57272ee263733ae193565/elfcpp/dwarf.h#L179
DW_LNS_extended_op = 0
DW_LNS_copy = 1
DW_LNS_advance_pc = 2
DW_LNS_advance_line = 3
DW_LNS_set_file = 4
DW_LNS_set_column = 5
DW_LNS_negate_stmt = 6
DW_LNS_set_basic_block = 7
DW_LNS_const_add_pc = 8
DW_LNS_fixed_advance_pc = 9
# DWARF 3.
DW_LNS_set_prologue_end = 10
DW_LNS_set_epilogue_begin = 11
DW_LNS_set_isa = 12

# Line number extended opcodes.
# https://github.com/gittup/binutils/blob/8db2e9c8d085222ac7b57272ee263733ae193565/elfcpp/dwarf.h#L201
DW_LNE_end_sequence = 1
DW_LNE_set_address = 2
DW_LNE_define_file = 3
# HP extensions.
DW_LNE_HP_negate_is_UV_update = 0x11
DW_LNE_HP_push_context = 0x12
DW_LNE_HP_pop_context = 0x13
DW_LNE_HP_set_file_line_column = 0x14
DW_LNE_HP_set_routine_name = 0x15
DW_LNE_HP_set_sequence = 0x16
DW_LNE_HP_negate_post_semantics = 0x17
DW_LNE_HP_negate_function_exit = 0x18
DW_LNE_HP_negate_front_end_logical = 0x19
DW_LNE_HP_define_proc = 0x20


def parse_debug_line_section(f):
    debug_lines = []

    # https://github.com/gittup/binutils/blob/8db2e9c8d085222ac7b57272ee263733ae193565/bfd/dwarf2.c#L1207

    def read_4_bytes():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        assert (arr[0] == '.4byte')
        return int(arr[1], 0)

    def read_address():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        assert (arr[0] == '.4byte')
        return arr[1]

    def read_2_bytes():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        assert (arr[0] == '.2byte')
        return int(arr[1], 0)

    def read_1_byte():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        assert (arr[0] == '.byte')
        return int(arr[1], 0)

    def read_signed_leb128():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        assert (arr[0] == '.byte')

        result = 0
        shift = 0
        arr = arr[1].split(',')
        for byte in arr:
            byte = int(byte, 0)
            result |= (byte & 0x7f) << shift
            shift += 7
            if byte & 0x80 == 0:
                break

        if byte & 0x40:
            result -= (1 << shift)

        return result

    def read_unsigned_leb128():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        assert (arr[0] == '.byte')

        result = 0
        shift = 0
        arr = arr[1].split(',')
        for byte in arr:
            byte = int(byte, 0)
            result |= (byte & 0x7f) << shift
            shift += 7
            if byte & 0x80 == 0:
                break

        return result

    def read_1_signed_byte():
        return read_1_byte()

    def read_string():
        line = f.readline().strip()
        arr = line.split()
        assert (len(arr) == 2)
        if arr[0] == '.byte':
            return None
        assert (arr[0] == '.ascii')
        result = arr[1][1:-1]

        line = f.readline().strip()
        while line != '':
            arr = line.split()
            assert (len(arr) == 2)
            assert (arr[0] == '.ascii')
            result += arr[1][1:-1]
            line = f.readline().strip()

        # Remove \000
        return result[:-4]

    total_length = read_4_bytes()
    version = read_2_bytes()
    prologue_length = read_4_bytes()
    minimum_instruction_length = read_1_byte()
    default_is_stmt = read_1_byte()
    line_base = read_1_signed_byte()
    line_range = read_1_byte()
    opcode_base = read_1_byte()

    standard_opcode_lengths = [1]

    for i in range(1, opcode_base):
        standard_opcode_lengths.append(read_1_byte())

    # Read directory table.
    dirs = []
    cur_dir = read_string()
    while cur_dir is not None:
        dirs.append(cur_dir)
        cur_dir = read_string()

    # Read file name table.
    files = []
    cur_file = read_string()
    while cur_file is not None:
        files.append(cur_file)
        # The following information is not set by agbcc
        # dir
        read_unsigned_leb128()
        # time
        read_unsigned_leb128()
        # size
        read_unsigned_leb128()

        cur_file = read_string()

    # Read the statement sequences until there's nothing left.

    # Assume one sequence for now
    # while True:

    # State machine registers.
    address = 0
    filename = files[0]
    line = 1
    column = 0  # agbcc does not emit column information
    is_stmt = True  # TODO?
    end_sequence = False

    while not end_sequence:
        op_code = read_1_byte()
        if op_code >= opcode_base:
            # Special operand.
            adj_opcode = op_code - opcode_base
            # Addresses are always given with labels, so ignore address offset calculation
            # address += (adj_opcode / line_range) * minimum_instruction_length
            # offset = (adj_opcode / line_range) * minimum_instruction_length
            # if offset != 0:
            # address += '+' + str(offset)
            line += line_base + (adj_opcode % line_range)
            debug_lines.append((address, line))

        else:

            if op_code == DW_LNS_extended_op:
                # Ignore length
                read_1_byte()

                extended_op = read_1_byte()
                if extended_op == DW_LNE_set_address:
                    address = read_address()
                elif extended_op == DW_LNE_end_sequence:
                    # agbcc always outputs this, so we can use it as the loop condition
                    end_sequence = 1
                    debug_lines.append((address, line))
                    break
                else:
                    raise Exception(f'Unimplemented extended_op {extended_op}')

            elif op_code == DW_LNS_copy:
                debug_lines.append((address, line))
            elif op_code == DW_LNS_advance_line:
                line += read_signed_leb128()
            elif op_code == DW_LNS_set_file:
                id = read_unsigned_leb128()
                # The file and directory tables are 0
                # based, the references are 1 based.
                filename = files[id - 1]
            else:
                raise Exception(f'Unimplemented op_code {op_code}')
    return debug_lines


def process_debug_info(path: str) -> None:
    code = []
    debug_lines = []
    with open(path, 'r') as f:
        line = f.readline()
        while '.section' not in line and len(line) > 0:
            code.append(line)
            line = f.readline()

        while len(line) > 0:
            if '.section' in line and '.debug_line' in line:
                debug_lines = parse_debug_line_section(f)
            line = f.readline()

    line_dict = {}
    for (label, line) in debug_lines:
        line_dict[label] = line

    wrote_file_path = False
    with open(path, 'w') as f:
        # Insert debug info
        for line in code:
            if line.startswith('.') and ':' in line:  # Line is a label
                label_name = line.strip()[:-1]
                if label_name in line_dict:
                    if not wrote_file_path:
                        f.write('.file 1 "example.c"\n')
                        wrote_file_path = True
                    f.write(f'.loc 1 {line_dict[label_name]} 1\n')
            f.write(line)
