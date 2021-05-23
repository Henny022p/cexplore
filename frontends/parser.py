import antlr4
from antlr.ASMLexer import ASMLexer
from antlr.ASMParser import ASMParser
from antlr.ASMVisitor import ASMVisitor
from typing import List, Optional
from dataclasses import dataclass


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
    pass


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

    def __str__(self):
        if self.number <= 12:
            return f'r{self.number}'
        if self.number == 13:
            return 'sp'
        if self.number == 14:
            return 'lr'
        if self.number == 15:
            return 'pc'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, Register):
            return self.number == other.number
        return False


class Constant(Operand):
    value: int

    def __init__(self, value: str):
        self.value = int(value[1:], 0)

    def __str__(self):
        return f'#{self.value:#x}'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, Constant):
            return self.value == other.value
        return False


class ASTNode:
    pass


class Instruction(ASTNode):
    pass


class Operation(Instruction):
    rd: Register
    rn: Register
    rm: Operand
    mnemonic: str

    def __init__(self, rd: Register, rn: Register, rm: Register):
        self.rd = rd
        self.rn = rn
        self.rm = rm

    def __str__(self):
        if self.rd == self.rn:
            return f'{self.mnemonic} {self.rd}, {self.rm}'
        return f'{self.mnemonic} {self.rd}, {self.rn}, {self.rm}'

    def __repr__(self):
        return str(self)


@dataclass
class LABEL(Instruction):
    name: str

    def __str__(self):
        return f'{self.name}:'

    def __repr__(self):
        return str(self)


@dataclass
class DATA(Instruction):
    size: int
    data: str

    def __str__(self):
        return f'.{self.size}byte {self.data}'

    def __repr__(self):
        return str(self)


@dataclass
class PUSH(Instruction):
    registers: List[Register]

    def __str__(self):
        return f'push {{{", ".join([str(reg) for reg in self.registers])}}}'

    def __repr__(self):
        return str(self)


@dataclass
class POP(Instruction):
    registers: List[Register]

    def __str__(self):
        return f'pop {{{", ".join([str(reg) for reg in self.registers])}}}'

    def __repr__(self):
        return str(self)


class ADD(Operation):
    mnemonic = 'add'


class SUB(Operation):
    mnemonic = 'sub'


@dataclass
class NEG(Instruction):
    rd: Register
    rm: Register

    def __str__(self):
        return f'neg {self.rd}, {self.rm}'

    def __repr__(self):
        return str(self)


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

    def __str__(self):
        if self.rd == self.rn:
            return f'mul {self.rd}, {self.rm}'
        if self.rd == self.rm:
            return f'mul {self.rd}, {self.rn}'
        return f'mul {self.rd}, {self.rn}, {self.rm}'

    def __repr__(self):
        return str(self)


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


@dataclass
class LDR_PC(Instruction):
    rt: Register
    label: str
    size: int = 4
    signed: bool = False

    def __str__(self):
        return f'ldr{suffix("s", self.signed)}{suffix("b", self.size == 1)}{suffix("h", self.size == 2)} {self.rt}, {self.label}'

    def __repr__(self):
        return str(self)


@dataclass
class LDR(Instruction):
    rt: Register
    rn: Register
    rm: Optional[Register]
    size: int = 4
    signed: bool = False

    def __str__(self):
        return f'ldr{suffix("s", self.signed)}{suffix("b", self.size == 1)}{suffix("h", self.size == 2)} {self.rt}, ' \
               f'[{self.rn}{suffix(", ", self.rm is not None)}{suffix(str(self.rm), self.rm is not None)}]'

    def __repr__(self):
        return str(self)


@dataclass
class STR(Instruction):
    rt: Register
    rn: Register
    rm: Optional[Register]
    size: int = 4

    def __str__(self):
        return f'str{suffix("b", self.size == 1)}{suffix("h", self.size == 2)} {self.rt}, ' \
               f'[{self.rn}{suffix(", ", self.rm is not None)}{suffix(str(self.rm), self.rm is not None)}]'

    def __repr__(self):
        return str(self)


@dataclass
class BL(Instruction):
    function: str

    def __str__(self):
        return f'bl {self.function}'

    def __repr__(self):
        return str(self)


@dataclass
class BX(Instruction):
    rm: Register

    def __str__(self):
        return f'bx {self.rm}'

    def __repr__(self):
        return str(self)


class Branch(Instruction):
    label: str
    condition: str

    def __init__(self, label: str):
        self.label = label

    def __str__(self):
        return f'b{self.condition} {self.label}'

    def __repr__(self):
        return str(self)


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


@dataclass
class CMP(Instruction):
    rn: Register
    rm: Operand

    def __str__(self):
        return f'cmp {self.rn}, {self.rm}'

    def __repr__(self):
        return str(self)


@dataclass
class CMN(Instruction):
    rn: Register
    rm: Operand

    def __str__(self):
        return f'cmn {self.rn}, {self.rm}'

    def __repr__(self):
        return str(self)


@dataclass
class MOV(Instruction):
    rd: Register
    rm: Operand

    def __str__(self):
        return f'mov {self.rd}, {self.rm}'

    def __repr__(self):
        return str(self)


@dataclass
class Directive(Instruction):
    text: str

    def __str__(self):
        return self.text

    def __repr__(self):
        return str(self)


@dataclass
class Function(ASTNode):
    name: str
    instructions: List[Instruction]


@dataclass
class ASMFile(ASTNode):
    functions: List[Function]


class ASTGenerator(ASMVisitor):
    def visitReg(self, ctx: ASMParser.RegContext):
        return Register(ctx.REG().symbol.text)

    def visitImm(self, ctx: ASMParser.ImmContext):
        return Constant(ctx.IMM().symbol.text)

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

    def visitFunction_header(self, ctx: ASMParser.Function_headerContext):
        return ctx.name.text

    def visitPush_multiple(self, ctx: ASMParser.Push_multipleContext):
        registers = []
        for register in ctx.reg():
            registers.append(self.visit(register))
        return PUSH(registers)

    def visitPop_multiple(self, ctx: ASMParser.Pop_multipleContext):
        registers = []
        for register in ctx.reg():
            registers.append(self.visit(register))
        return POP(registers)

    def visitLabel(self, ctx: ASMParser.LabelContext):
        return LABEL(ctx.name.text)

    def visitData1(self, ctx: ASMParser.Data1Context):
        return DATA(1, ctx.WORD().symbol.text)

    def visitData2(self, ctx: ASMParser.Data2Context):
        return DATA(2, ctx.WORD().symbol.text)

    def visitData4(self, ctx: ASMParser.Data4Context):
        return DATA(4, ctx.WORD().symbol.text)

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

    def visitLdr_pc(self, ctx: ASMParser.Ldr_pcContext):
        rt = self.visit(ctx.rt)
        label = ctx.target.text
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
        return Directive(ctx.getText())


if __name__ == '__main__':
    tree, successful = parse('test2.s')
    file = ASTGenerator().visit(tree)
    pass
