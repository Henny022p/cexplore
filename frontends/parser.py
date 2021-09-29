from enum import Enum
from typing import List, Optional, TextIO, Union
from weakref import ref

import antlr4

from antlr.ASMLexer import ASMLexer
from antlr.ASMParser import ASMParser
from antlr.ASMVisitor import ASMVisitor


def parse(filename: str) -> (ASMParser.AsmfileContext, bool):
    lexer = ASMLexer(antlr4.FileStream(filename))
    parser = ASMParser(antlr4.CommonTokenStream(lexer))
    tree = parser.asmfile()
    return tree, parser.getNumberOfSyntaxErrors() == 0


def suffix(suffix: str, condition: bool) -> str:
    if condition:
        return suffix
    return ''


class Operand:
    def __bool__(self):
        return False

    def __repr__(self):
        return str(self)


class Register(Operand):
    number: int

    def __init__(self, text: str):
        if text.startswith('r'):
            self.number = int(text[1:])
        elif text == 'sb':
            self.number = 9
        elif text == 'sl':
            self.number = 10
        elif text == 'ip':
            self.number = 12
        elif text == 'sp':
            self.number = 13
        elif text == 'lr':
            self.number = 14
        elif text == 'pc':
            self.number = 15
        else:
            raise ValueError(f'bad register {text}')

    def __repr__(self):
        if self.number <= 12:
            return f'r{self.number}'
        if self.number == 13:
            return 'sp'
        if self.number == 14:
            return 'lr'
        if self.number == 15:
            return 'pc'

    def __eq__(self, other):
        if isinstance(other, Register):
            return self.number == other.number
        return False

    def __bool__(self):
        return True


class Constant(Operand):
    value: int

    def __init__(self, value: Union[str, int]):
        if isinstance(value, str):
            self.value = int(value, 0)
        else:
            self.value = value

    def __repr__(self):
        return f'#{self.value:#x}'

    def __eq__(self, other):
        if isinstance(other, Constant):
            return self.value == other.value
        return False

    def __bool__(self):
        return self.value != 0


class ASTNode:
    pass


class Instruction(ASTNode):
    _prev: Optional[ref] = None
    _next: Optional[ref] = None

    @property
    def prev(self) -> Optional['Instruction']:
        if self._prev:
            return self._prev()
        return None

    @property
    def next(self) -> Optional['Instruction']:
        if self._next:
            return self._next()
        return None


class Operation(Instruction):
    rd: Register
    rn: Register
    rm: Operand
    mnemonic: str

    def __init__(self, rd: Register, rn: Register, rm: Operand):
        self.rd = rd
        self.rn = rn
        self.rm = rm

    def __repr__(self):
        if self.rd == self.rn:
            return f'{self.mnemonic} {self.rd}, {self.rm}'
        return f'{self.mnemonic} {self.rd}, {self.rn}, {self.rm}'


class LabelType(Enum):
    CODE = 0
    DATA = 1
    CASE = 2
    OTHER = 3


class LABEL(Instruction):
    name: str
    type: LabelType
    loads: List['LDR_PC']

    def __init__(self, name: str):
        self.name = name
        self.type = LabelType.OTHER
        self.loads = []

    def __repr__(self):
        return f'{self.name}:'


class DATA(Instruction):
    size: int
    data: Union[str, int]
    _target: Optional[ref]

    def __init__(self, size: int, data: Union[str, int]):
        self.size = size
        self.data = data
        self._target = None

    @property
    def target(self) -> Optional[LABEL]:
        if self._target:
            return self._target()
        return None

    def __repr__(self):
        if self.target:
            return f'.{self.size}byte {self.target.name}'
        if isinstance(self.data, int):
            return f'.{self.size}byte {self.data:#x}'
        return f'.{self.size}byte {self.data}'


class PUSH(Instruction):
    registers: List[Register]

    def __init__(self, registers: List[Register]):
        self.registers = registers

    def __repr__(self):
        return f'push {{{", ".join([str(reg) for reg in self.registers])}}}'


class POP(Instruction):
    registers: List[Register]

    def __init__(self, registers: List[Register]):
        self.registers = registers

    def __repr__(self):
        return f'pop {{{", ".join([str(reg) for reg in self.registers])}}}'


class ADD(Operation):
    mnemonic = 'add'


class SUB(Operation):
    mnemonic = 'sub'


class NEG(Instruction):
    rd: Register
    rm: Register

    def __init__(self, rd: Register, rm: Register):
        self.rd = rd
        self.rm = rm

    def __repr__(self):
        return f'neg {self.rd}, {self.rm}'


class MUL(Instruction):
    rd: Register
    rn: Register
    rm: Register

    def __init__(self, rd: Register, rn: Register, rm: Register):
        if not (rd == rn or rd == rm):
            raise ValueError('mul destination must be equal to one of the factors')
        self.rd = rd
        self.rn = rn
        self.rm = rm

    def __repr__(self):
        if self.rd == self.rn:
            return f'mul {self.rd}, {self.rm}'
        if self.rd == self.rm:
            return f'mul {self.rd}, {self.rn}'
        return f'mul {self.rd}, {self.rn}, {self.rm}'


class AND(Operation):
    mnemonic = 'and'


class ORR(Operation):
    mnemonic = 'orr'


class EOR(Operation):
    mnemonic = 'eor'


class LSL(Operation):
    mnemonic = 'lsl'


class LSR(Operation):
    mnemonic = 'lsr'


class ASL(Operation):
    mnemonic = 'asl'


class ASR(Operation):
    mnemonic = 'asr'


class BIC(Operation):
    mnemonic = 'bic'


class LDR_PC(Instruction):
    rt: Register
    _label: str
    offset: int = 0
    size: int = 4
    signed: bool = False
    _target: Optional[ref]

    def __init__(self, rt: Register, label: str, offset: int = 0, size: int = 4, signed: bool = False):
        self.rt = rt
        self._label = label
        self.offset = offset
        self.size = size
        self.signed = signed
        self._target = None

    @property
    def target(self) -> Optional[LABEL]:
        if self._target:
            return self._target()
        return None

    @property
    def label(self) -> str:
        if self.target:
            return self.target.name
        return self._label

    def __repr__(self):
        text = f'ldr{suffix("s", self.signed)}{suffix("b", self.size == 1)}{suffix("h", self.size == 2)} {self.rt}, {self.label}'
        if self.offset != 0:
            text += f'+{self.offset:#x}'
        return text


class LDR(Instruction):
    rt: Register
    rn: Register
    rm: Optional[Operand]
    size: int = 4
    signed: bool = False

    def __init__(self, rt: Register, rn: Register, rm: Optional[Operand], size: int = 4, signed: bool = False):
        self.rt = rt
        self.rn = rn
        self.rm = rm
        self.size = size
        self.signed = signed

    def __repr__(self):
        return f'ldr{suffix("s", self.signed)}{suffix("b", self.size == 1)}{suffix("h", self.size == 2)} {self.rt}, ' \
               f'[{self.rn}{suffix(", ", self.rm)}{suffix(str(self.rm), self.rm)}]'


class STR(Instruction):
    rt: Register
    rn: Register
    rm: Optional[Operand]
    size: int = 4

    def __init__(self, rt: Register, rn: Register, rm: Optional[Operand], size: int = 4):
        self.rt = rt
        self.rn = rn
        self.rm = rm
        self.size = size

    def __repr__(self):
        return f'str{suffix("b", self.size == 1)}{suffix("h", self.size == 2)} {self.rt}, ' \
               f'[{self.rn}{suffix(", ", self.rm)}{suffix(str(self.rm), self.rm)}]'


class STM(Instruction):
    rn: Register
    reglist: List[Register]

    def __init__(self, rn: Register, reglist: List[Register]):
        self.rn = rn
        self.reglist = reglist

    def __repr__(self):
        return f'stm {self.rn}!, {{{", ".join([str(reg) for reg in self.reglist])}}}'


class BL(Instruction):
    function: str

    def __init__(self, function: str):
        self.function = function

    def __repr__(self):
        return f'bl {self.function}'


class BX(Instruction):
    rm: Register

    def __init__(self, rm: Register):
        self.rm = rm

    def __repr__(self):
        return f'bx {self.rm}'


class Branch(Instruction):
    _label: str
    condition: str
    _target: Optional[ref]

    def __init__(self, label: str):
        self._label = label
        self._target = None

    @property
    def target(self) -> Optional[LABEL]:
        if self._target:
            return self._target()
        return None

    @property
    def label(self):
        if self.target:
            return self.target.name
        return self._label

    def __repr__(self):
        return f'b{self.condition} {self.label}'


class B(Branch):
    condition = ''


class BEQ(Branch):
    condition = 'eq'


class BNE(Branch):
    condition = 'ne'


class BHS(Branch):
    condition = 'hs'


class BLO(Branch):
    condition = 'lo'


class BMI(Branch):
    condition = 'mi'


class BPL(Branch):
    condition = 'pl'


class BVS(Branch):
    condition = 'vs'


class BVC(Branch):
    condition = 'vc'


class BHI(Branch):
    condition = 'hi'


class BLS(Branch):
    condition = 'ls'


class BGE(Branch):
    condition = 'ge'


class BLT(Branch):
    condition = 'lt'


class BGT(Branch):
    condition = 'gt'


class BLE(Branch):
    condition = 'le'


class CMP(Instruction):
    rn: Register
    rm: Operand

    def __init__(self, rn: Register, rm: Register):
        self.rn = rn
        self.rm = rm

    def __repr__(self):
        return f'cmp {self.rn}, {self.rm}'


class CMN(Instruction):
    rn: Register
    rm: Operand

    def __init__(self, rn: Register, rm: Register):
        self.rn = rn
        self.rm = rm

    def __repr__(self):
        return f'cmn {self.rn}, {self.rm}'


class MOV(Instruction):
    rd: Register
    rm: Operand

    def __init__(self, rd: Register, rm: Register):
        self.rd = rd
        self.rm = rm

    def __repr__(self):
        return f'mov {self.rd}, {self.rm}'


class Directive(Instruction):
    text: str

    def __init__(self, text: str):
        self.text = text

    def __repr__(self):
        return self.text


class Function(ASTNode):
    name: str
    instructions: List[Instruction]
    labels: List[LABEL]

    def __init__(self, name: str, instructions: List[Instruction]):
        self.name = name
        self.instructions = instructions
        self.labels = []


class ASMFile(ASTNode):
    functions: List[Function]

    def __init__(self, functions: List[Function]):
        self.functions = functions


class ASTGenerator(ASMVisitor):
    def visitReg(self, ctx: ASMParser.RegContext):
        return Register(ctx.REG().symbol.text)

    def visitImm(self, ctx: ASMParser.ImmContext):
        return Constant(ctx.NUM().symbol.text)

    def visitReglist(self, ctx: ASMParser.ReglistContext):
        registers = []
        for register in ctx.reg():
            registers.append(self.visit(register))
        return registers

    def visitAsmfile(self, ctx: ASMParser.AsmfileContext):
        functions = []
        for function in ctx.function():
            functions.append(self.visit(function))
        return ASMFile(functions)

    def visitFunction(self, ctx: ASMParser.FunctionContext):
        name = self.visit(ctx.function_header())
        instructions = []
        for line in ctx.line():
            linep = self.visit(line)
            if not isinstance(linep, Instruction):
                print(f'bad line {line.getText()}')
            instructions.append(linep)
        return Function(name, instructions)

    def visitFunction_header1(self, ctx: ASMParser.Function_header1Context):
        return ctx.name.text

    def visitFunction_header2(self, ctx: ASMParser.Function_header2Context):
        return ctx.name.text

    def visitPush_multiple(self, ctx: ASMParser.Push_multipleContext):
        registers = self.visit(ctx.reglist())
        return PUSH(registers)

    def visitPop_multiple(self, ctx: ASMParser.Pop_multipleContext):
        registers = self.visit(ctx.reglist())
        return POP(registers)

    def visitLabel(self, ctx: ASMParser.LabelContext):
        return LABEL(ctx.name.text)

    def visitData1word(self, ctx: ASMParser.Data1wordContext):
        return DATA(1, ctx.const.text)

    def visitData2word(self, ctx: ASMParser.Data2wordContext):
        return DATA(2, ctx.const.text)

    def visitData4word(self, ctx: ASMParser.Data4wordContext):
        return DATA(4, ctx.const.text)

    def visitData1num(self, ctx: ASMParser.Data1numContext):
        return DATA(1, int(ctx.const.text, 0))

    def visitData2num(self, ctx: ASMParser.Data2numContext):
        return DATA(2, int(ctx.const.text, 0))

    def visitData4num(self, ctx: ASMParser.Data4numContext):
        return DATA(4, int(ctx.const.text, 0))

    def operation(self, ctx, cls):
        rd = self.visit(ctx.rd)
        rn = self.visit(ctx.rn) if ctx.rn else rd
        rm = self.visit(ctx.rm)
        return cls(rd, rn, rm)

    def visitAdd(self, ctx: ASMParser.AddContext):
        return self.operation(ctx, ADD)

    def visitSub(self, ctx: ASMParser.SubContext):
        return self.operation(ctx, SUB)

    def visitRsb(self, ctx: ASMParser.RsbContext):
        imm = self.visit(ctx.imm())
        if not imm.value == 0:
            raise ValueError('rsb only allowed with 0 immediate')
        rd = self.visit(ctx.rd)
        rn = self.visit(ctx.rn)
        return NEG(rd, rn)

    def visitNeg(self, ctx: ASMParser.NegContext):
        rd = self.visit(ctx.rd)
        rm = self.visit(ctx.rm)
        return NEG(rd, rm)

    def visitMul1(self, ctx: ASMParser.Mul1Context):
        rd = self.visit(ctx.rd)
        rn = self.visit(ctx.rn)
        return MUL(rd, rn, rd)

    def visitMul2(self, ctx: ASMParser.Mul2Context):
        rd = self.visit(ctx.rd)
        rn = self.visit(ctx.rn)
        rm = self.visit(ctx.rm)
        return MUL(rd, rn, rm)

    def visitLand(self, ctx: ASMParser.LandContext):
        return self.operation(ctx, AND)

    def visitOrr(self, ctx: ASMParser.OrrContext):
        return self.operation(ctx, ORR)

    def visitEor(self, ctx: ASMParser.EorContext):
        return self.operation(ctx, EOR)

    def visitLsl(self, ctx: ASMParser.LslContext):
        return self.operation(ctx, LSL)

    def visitLsr(self, ctx: ASMParser.LsrContext):
        return self.operation(ctx, LSR)

    def visitAsl(self, ctx: ASMParser.AslContext):
        return self.operation(ctx, ASL)

    def visitAsr(self, ctx: ASMParser.AsrContext):
        return self.operation(ctx, ASR)

    def visitBic(self, ctx: ASMParser.BicContext):
        return self.operation(ctx, BIC)

    def visitLdr_pc(self, ctx: ASMParser.Ldr_pcContext):
        rt = self.visit(ctx.rt)
        label = ctx.target.text
        if ctx.offset:
            offset = int(ctx.offset.text, 0)
            return LDR_PC(rt, label, offset)
        return LDR_PC(rt, label)

    def ldr(self, ctx, size: int = 4, signed: bool = False):
        rt = self.visit(ctx.rt)
        rn = self.visit(ctx.rn)
        rm = self.visit(ctx.rm) if ctx.rm else None
        return LDR(rt, rn, rm, size, signed)

    def visitLdr_offset(self, ctx: ASMParser.Ldr_offsetContext):
        return self.ldr(ctx)

    def visitLdrh_offset(self, ctx: ASMParser.Ldrh_offsetContext):
        return self.ldr(ctx, 2, False)

    def visitLdrsh_offset(self, ctx: ASMParser.Ldrsh_offsetContext):
        return self.ldr(ctx, 2, True)

    def visitLdrb_offset(self, ctx: ASMParser.Ldrb_offsetContext):
        return self.ldr(ctx, 1, False)

    def visitLdrsb_offset(self, ctx: ASMParser.Ldrsb_offsetContext):
        return self.ldr(ctx, 1, True)

    def str(self, ctx, size: int = 4):
        rt = self.visit(ctx.rt)
        rn = self.visit(ctx.rn)
        rm = self.visit(ctx.rm) if ctx.rm else None
        return STR(rt, rn, rm, size)

    def visitStr_offset(self, ctx: ASMParser.Str_offsetContext):
        return self.str(ctx)

    def visitStrh_offset(self, ctx: ASMParser.Strh_offsetContext):
        return self.str(ctx, 2)

    def visitStrb_offset(self, ctx: ASMParser.Strb_offsetContext):
        return self.str(ctx, 1)

    def visitStm(self, ctx: ASMParser.StmContext):
        rn = self.visit(ctx.rn)
        registers = self.visit(ctx.reglist())
        return STM(rn, registers)

    def visitBl(self, ctx: ASMParser.BlContext):
        return BL(ctx.target.text)

    def visitBx(self, ctx: ASMParser.BxContext):
        return BX(self.visit(ctx.rm))

    def visitB(self, ctx: ASMParser.BContext):
        return B(ctx.target.text)

    def visitBeq(self, ctx: ASMParser.BeqContext):
        return BEQ(ctx.target.text)

    def visitBne(self, ctx: ASMParser.BneContext):
        return BNE(ctx.target.text)

    def visitBhs(self, ctx: ASMParser.BhsContext):
        return BHS(ctx.target.text)

    def visitBlo(self, ctx: ASMParser.BloContext):
        return BLO(ctx.target.text)

    def visitBmi(self, ctx: ASMParser.BmiContext):
        return BMI(ctx.target.text)

    def visitBpl(self, ctx: ASMParser.BplContext):
        return BPL(ctx.target.text)

    def visitBvs(self, ctx: ASMParser.BvsContext):
        return BVS(ctx.target.text)

    def visitBvc(self, ctx: ASMParser.BvcContext):
        return BVC(ctx.target.text)

    def visitBhi(self, ctx: ASMParser.BhiContext):
        return BHI(ctx.target.text)

    def visitBls(self, ctx: ASMParser.BlsContext):
        return BLS(ctx.target.text)

    def visitBge(self, ctx: ASMParser.BgeContext):
        return BGE(ctx.target.text)

    def visitBlt(self, ctx: ASMParser.BltContext):
        return BLT(ctx.target.text)

    def visitBgt(self, ctx: ASMParser.BgtContext):
        return BGT(ctx.target.text)

    def visitBle(self, ctx: ASMParser.BleContext):
        return BLE(ctx.target.text)

    def visitCmp(self, ctx: ASMParser.CmpContext):
        rn = self.visit(ctx.rn)
        rm = self.visit(ctx.rm)
        return CMP(rn, rm)

    def visitCmn(self, ctx: ASMParser.CmnContext):
        rn = self.visit(ctx.rn)
        rm = self.visit(ctx.rm)
        return CMN(rn, rm)

    def visitMov(self, ctx: ASMParser.MovContext):
        rd = self.visit(ctx.rd)
        rm = self.visit(ctx.rm)
        return MOV(rd, rm)

    def visitAlign(self, ctx: ASMParser.AlignContext):
        return Directive('.align 2, 0')

    def visitDir_code(self, ctx: ASMParser.Dir_codeContext):
        return Directive('')

    def visitDir_size(self, ctx: ASMParser.Dir_sizeContext):
        return Directive('')


def link_instructions(asmfile: ASMFile):
    for function in asmfile.functions:
        prev_insn: Optional[Instruction] = None
        for instruction in function.instructions:
            if prev_insn is not None:
                instruction._prev = ref(prev_insn)
                prev_insn._next = ref(instruction)
            prev_insn = instruction
            if isinstance(instruction, Branch):
                for label in function.instructions:
                    if isinstance(label, LABEL):
                        if label.name == instruction.label:
                            instruction._target = ref(label)
            if isinstance(instruction, LDR_PC):
                for label in function.instructions:
                    if isinstance(label, LABEL):
                        if label.name == instruction.label:
                            instruction._target = ref(label)
                            label.loads.append(instruction)


class ASTVisitor:
    def visit(self, node: ASTNode):
        name = type(node).__name__
        return getattr(self, f'visit_{name.lower()}')(node)

    def visit_asmfile(self, asmfile: ASMFile):
        ret = []
        for function in asmfile.functions:
            ret.append(self.visit(function))
        return ret

    def visit_function(self, function: Function):
        ret = []
        for instruction in function.instructions:
            ret.append(self.visit(instruction))
        return ret

    def instruction(self, instruction: Instruction):
        pass

    def operation(self, operation: Operation):
        return self.instruction(operation)

    def branch(self, branch: Branch):
        return self.instruction(branch)

    def visit_label(self, label: LABEL):
        return self.instruction(label)

    def visit_data(self, data: DATA):
        return self.instruction(data)

    def visit_push(self, push: PUSH):
        return self.instruction(push)

    def visit_pop(self, pop: POP):
        return self.instruction(pop)

    def visit_add(self, add: ADD):
        return self.operation(add)

    def visit_sub(self, sub: SUB):
        return self.operation(sub)

    def visit_neg(self, neg: NEG):
        return self.instruction(neg)

    def visit_mul(self, mul: MUL):
        return self.instruction(mul)

    def visit_and(self, land: AND):
        return self.operation(land)

    def visit_orr(self, orr: ORR):
        return self.operation(orr)

    def visit_eor(self, eor: EOR):
        return self.operation(eor)

    def visit_lsl(self, lsl: LSL):
        return self.operation(lsl)

    def visit_lsr(self, lsr: LSR):
        return self.operation(lsr)

    def visit_asl(self, asl: ASL):
        return self.operation(asl)

    def visit_asr(self, asr: ASR):
        return self.operation(asr)

    def visit_bic(self, bic: BIC):
        return self.operation(bic)

    def visit_ldr_pc(self, ldr_pc: LDR_PC):
        return self.instruction(ldr_pc)

    def visit_ldr(self, ldr: LDR):
        return self.instruction(ldr)

    def visit_str(self, store: STR):
        return self.instruction(store)

    def visit_stm(self, stm: STM):
        return self.instruction(stm)

    def visit_bl(self, bl: BL):
        return self.instruction(bl)

    def visit_bx(self, bx: BX):
        return self.instruction(bx)

    def visit_b(self, b: B):
        return self.branch(b)

    def visit_beq(self, beq: BEQ):
        return self.branch(beq)

    def visit_bne(self, bne: BNE):
        return self.branch(bne)

    def visit_bhs(self, bhs: BHS):
        return self.branch(bhs)

    def visit_blo(self, blo: BLO):
        return self.branch(blo)

    def visit_bmi(self, bmi: BMI):
        return self.branch(bmi)

    def visit_bpl(self, bpl: BPL):
        return self.branch(bpl)

    def visit_bvs(self, bvs: BVS):
        return self.branch(bvs)

    def visit_bvc(self, bvc: BVC):
        return self.branch(bvc)

    def visit_bhi(self, bhi: BHI):
        return self.branch(bhi)

    def visit_bls(self, bls: BLS):
        return self.branch(bls)

    def visit_bge(self, bge: BGE):
        return self.branch(bge)

    def visit_blt(self, blt: BLT):
        return self.branch(blt)

    def visit_bgt(self, bgt: BGT):
        return self.branch(bgt)

    def visit_ble(self, ble: BLE):
        return self.branch(ble)

    def visit_cmp(self, cmp: CMP):
        return self.instruction(cmp)

    def visit_cmn(self, cmn: CMN):
        return self.instruction(cmn)

    def visit_mov(self, mov: MOV):
        return self.instruction(mov)

    def visit_directive(self, directive: Directive):
        return self.instruction(directive)


class CollectLabels(ASTVisitor):
    current_function: Function

    def visit_function(self, function: Function):
        self.current_function = function
        super(CollectLabels, self).visit_function(function)

    def visit_label(self, label: LABEL):
        self.current_function.labels.append(label)


class ClassifyLabels(ASTVisitor):
    current_function: Function

    def visit_function(self, function: Function):
        self.current_function = function
        super(ClassifyLabels, self).visit_function(function)

    def visit_label(self, label: LABEL):
        if isinstance(label.next, DATA):
            label.type = LabelType.DATA

    def branch(self, branch: Branch):
        branch.target.type = LabelType.CODE

    def visit_data(self, data: DATA):
        for label in self.current_function.labels:
            if label.name == data.data:
                label.type = LabelType.CASE
                data._target = ref(label)


class RenameLabels(ASTVisitor):
    ncode = 0
    ndata = 0
    ncase = 0
    nother = 0
    nfunction = 0

    def visit_function(self, function: Function):
        self.ncode = 0
        self.ndata = 0
        self.ncase = 0
        self.nother = 0
        super(RenameLabels, self).visit_function(function)
        self.nfunction += 1

    def visit_label(self, label: LABEL):
        if label.type == LabelType.CODE:
            label.name = f'_code{self.nfunction}_{self.ncode}'
            self.ncode += 1
        if label.type == LabelType.CASE:
            label.name = f'_case{self.nfunction}_{self.ncase}'
            self.ncase += 1
        if label.type == LabelType.DATA:
            label.name = f'_data{self.nfunction}_{self.ndata}'
            self.ndata += 1
        if label.type == LabelType.OTHER:
            label.name = f'_other{self.nfunction}_{self.nother}'
            self.nother += 1


def merge_data_labels(ast: ASMFile):
    for function in ast.functions:
        instruction = function.instructions[0]
        current_data: Optional[LABEL] = None
        ndata = 0
        while instruction is not None:
            if isinstance(instruction, LABEL):
                if instruction.type == LabelType.DATA:
                    if current_data:
                        for load in instruction.loads:
                            load._target = ref(current_data)
                            load.offset += ndata * 4
                        instruction.type = LabelType.OTHER
                    else:
                        current_data = instruction
            elif isinstance(instruction, DATA):
                ndata += 1
            else:
                current_data = None
                ndata = 0
            instruction = instruction.next


class PatchInstructions(ASTVisitor):
    def visit_function(self, function: Function):
        news = []
        prev: Optional[Instruction] = None
        for i, instruction in enumerate(function.instructions):
            new: Optional[Instruction] = self.visit(instruction)
            if new:
                if prev:
                    prev._next = ref(new)
                    new._prev = ref(prev)
                else:
                    new._prev = None
                prev = new
                news.append(new)
        if prev:
            prev._next = None
        function.instructions = news

    def instruction(self, instruction: Instruction):
        return instruction

    def visit_add(self, add: ADD):
        if isinstance(add.rm, Constant):
            if add.rm.value == 0:
                return MOV(add.rd, add.rn)
            elif add.rm.value < 0:
                return SUB(add.rd, add.rn, Constant(-add.rm.value))
        return add

    def visit_sub(self, sub: SUB):
        if isinstance(sub.rm, Constant):
            if sub.rm.value < 0:
                return ADD(sub.rd, sub.rn, Constant(-sub.rm.value))
        return sub

    def visit_directive(self, directive: Directive):
        return None


def apply_transformations(ast: ASMFile):
    PatchInstructions().visit(ast)
    merge_data_labels(ast)
    RenameLabels().visit(ast)


class ASTDump(ASTVisitor):
    file: TextIO

    def __init__(self, file: TextIO):
        self.file = file

    def visit_function(self, function: Function):
        self.file.write(f'\n\tthumb_func_start {function.name}\n{function.name}:\n')
        super(ASTDump, self).visit_function(function)

    def visit_label(self, label: LABEL):
        self.file.write(f'{label.name}:\n')

    def instruction(self, instruction: Instruction):
        self.file.write(f'\t{instruction}\n')


def generate_ast(tree: ASMParser.AsmfileContext) -> ASMFile:
    ast = ASTGenerator().visit(tree)
    link_instructions(ast)
    CollectLabels().visit(ast)
    ClassifyLabels().visit(ast)
    return ast
