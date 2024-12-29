# To run these tests install pytest, then run this command line:
# py.test -rfeEsxXwa --verbose --showlocals

import pytest
import sys
from unittest.mock import MagicMock

sys.path.append('../src')

from machine import Machine
from cpu import CPU
from rom import ROM
from ram import RAM
from interfaces import MemoryDevice, IODevice
from utils import *
from helper import MockIO


@pytest.fixture
def cpu():
    machine = Machine()
    machine.add_memory(MemoryDevice(RAM(), 0x0000, 0xffff))
    return CPU(machine) 


# General CPU class tests

def test_reset_values(cpu):
    assert cpu.a == 0x00
    assert cpu.b == 0x00
    assert cpu.c == 0x00
    assert cpu.d == 0x00
    assert cpu.e == 0x00
    assert cpu.h == 0x00
    assert cpu.l == 0x00

    assert cpu.ax == 0x00
    assert cpu.fx == 0x00
    assert cpu.bx == 0x00
    assert cpu.cx == 0x00
    assert cpu.dx == 0x00
    assert cpu.ex == 0x00
    assert cpu.hx == 0x00
    assert cpu.lx == 0x00    

    assert cpu.ix == 0x0000
    assert cpu.iy == 0x0000
    assert cpu.pc == 0x0000
    assert cpu.sp == 0x0000

    assert cpu.i == 0x00
    assert cpu.r == 0x00

    assert cpu.iff1 == False
    assert cpu.iff2 == False    

    assert cpu.sign == False
    assert cpu.zero == False
    assert cpu.half_carry == False
    assert cpu.parity == False
    assert cpu.add_subtract == False
    assert cpu.carry == False

    assert cpu._cycles == 0


def test_machine_reset(cpu):
    # This is actually a Machine test, but it is more convenient to do it here
    cpu._machine.write_memory_byte(0x0000, 0x00)    # NOP Instruction Opcode
    cpu.step()
    cpu._machine.reset()
    assert cpu.pc == 0x0000



# CPU Control instructions tests

def test_nop(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x00)    # NOP Instruction Opcode
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu._cycles == 4


def test_ei_di(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfb)    # EI Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0xf3)    # DI Instruction Opcode
    
    cpu.step() # EI
    assert cpu.iff1 == True
    assert cpu.iff2 == True
    assert cpu._cycles == 4

    cpu.step() # DI
    assert cpu.iff1 == False
    assert cpu.iff2 == False
    assert cpu._cycles == 8     # 4 more cycles

def test_in(cpu):
    mock = MockIO()
    mock.read_byte = MagicMock(return_value=0x55)

    cpu._machine.add_io(IODevice(mock, 0x42))
    cpu._machine.write_memory_byte(0x0000, 0xdb)    # IN A, $42 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Operand (IO port address)
    cpu.step()
    assert cpu.a == 0x55
    assert cpu._cycles == 11

def test_out(cpu):
    mock = MockIO()
    mock.write_byte = MagicMock()

    cpu._machine.add_io(IODevice(mock, 0x42))
    cpu._machine.write_memory_byte(0x0000, 0xd3)    # OUT #42, A Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Operand (IO port address)
    cpu.a = 0x55
    cpu.step()

    mock.write_byte.assert_called_once_with(0, 0x55)
    assert cpu._cycles == 11


# Data transfer instructions tests

def test_ld_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x01)    # LD BC, #beef Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.b == 0xbe
    assert cpu.c == 0xef
    assert cpu._cycles == 10

def test_ld_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x11)    # LD DE, #beef Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.d == 0xbe
    assert cpu.e == 0xef
    assert cpu._cycles == 10
    
def test_ld_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x21)    # LD HL, #beef Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.h == 0xbe
    assert cpu.l == 0xef
    assert cpu._cycles == 10
    
def test_ld_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x31)    # LD SP, #beef Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.sp == 0xbeef
    assert cpu._cycles == 10

def test_ld_a_h(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x7c)    # LD A, H Instruction Opcode
    cpu.h = 0x42
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.a == 0x42

def test_ld_b_e(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x43)    # LD B, E Instruction Opcode
    cpu.e = 0x42
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.b == 0x42

def test_ld_mem_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x72)    # LD (HL), D Instruction Opcode
    cpu.d = 0x42
    cpu.hl = 0x1234
    cpu.step()
    assert cpu._cycles == 7    # Accessing (HL) takes additional 3 cycles
    assert cpu._machine.read_memory_byte(0x1234) == 0x42

def test_ld_l_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x6e)    # LD L, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data
    cpu.hl = 0x1234
    cpu.step()
    assert cpu._cycles == 7   # Accessing (HL) takes additional 3 cycles
    assert cpu.l == 0x42

def test_ld_a_val(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3e)    # LD A, #42 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate value
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 7

def test_ld_b_val(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x06)    # LD B, #42 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate value
    cpu.step()
    assert cpu.b == 0x42
    assert cpu._cycles == 7

def test_ld_mem_val(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x36)    # LD (HL), #42 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate Value
    cpu.hl = 0x1234
    cpu.step()
    assert cpu._machine.read_memory_byte(0x1234) == 0x42
    assert cpu._cycles == 10

def test_ld_i_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD I, A Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x47)
    cpu.a = 0x42
    cpu.step()
    assert cpu.i == 0x42
    assert cpu._cycles == 9

def test_ld_r_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD R, A Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x4f)
    cpu.a = 0x42
    cpu.step()
    assert cpu.r == 0x42
    assert cpu._cycles == 9

def test_ld_a_i(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD A, I Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x57)
    cpu.i = 0x42
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 9

def test_ld_a_r(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD A, R Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x5f)
    cpu.r = 0x42
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 9

def test_ld_mem_hl(cpu):
    cpu.hl = 0x1234   # Value to write
    cpu._machine.write_memory_byte(0x0000, 0x22)    # LD (beef), HL Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu.step()
    assert cpu._machine.read_memory_word(0xbeef) == 0x1234
    assert cpu._cycles == 16

def test_ld_mem_reg16(cpu):
    cpu.de = 0x1234   # Value to write
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD (beef), DE Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x53)    
    cpu._machine.write_memory_word(0x0002, 0xbeef)  # Address
    cpu.step()
    assert cpu._machine.read_memory_word(0xbeef) == 0x1234
    assert cpu._cycles == 20

def test_ld_hl_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x2a)    # LD HL, (beef) Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._machine.write_memory_word(0xbeef, 0x1234)  # Value to read
    cpu.step()
    assert cpu.hl == 0x1234
    assert cpu._cycles == 16

def test_ld_reg16_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD BC, (beef) Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x4b)    
    cpu._machine.write_memory_word(0x0002, 0xbeef)  # Address
    cpu._machine.write_memory_word(0xbeef, 0x1234)  # Value to read
    cpu.step()
    assert cpu.bc == 0x1234
    assert cpu._cycles == 20

def test_ex_de_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xeb)    # EX DE, HL Instruction Opcode
    cpu.hl = 0x1234
    cpu.de = 0xbeef
    cpu.step()
    assert cpu.hl == 0xbeef
    assert cpu.de == 0x1234
    assert cpu._cycles == 4

def test_ex_stack_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe3)    # EX (SP), HL Instruction Opcode
    cpu._machine.write_memory_word(0x4321, 0xbeef)  # data to be exchanged
    cpu.hl = 0x1234
    cpu.sp = 0x4321
    cpu.step()
    assert cpu.hl == 0xbeef
    assert cpu._machine.read_memory_word(0x4321) == 0x1234
    assert cpu._cycles == 19

def test_ex_af_afx(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x08)    # EX AF, AF' Instruction Opcode
    cpu.af = 0x1234
    cpu.afx = 0xbeef
    cpu.step()
    assert cpu.af == 0xbeef
    assert cpu.afx == 0x1234
    assert cpu._cycles == 4

def test_exx(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd9)    # EXX Instruction Opcode
    cpu.bc = 0x1234
    cpu.de = 0x5678
    cpu.hl = 0x9abc
    cpu.bcx = 0x4321
    cpu.dex = 0x8765
    cpu.hlx = 0xcba9
    cpu.step()
    assert cpu.bc == 0x4321
    assert cpu.de == 0x8765
    assert cpu.hl == 0xcba9
    assert cpu.bcx == 0x1234
    assert cpu.dex == 0x5678
    assert cpu.hlx == 0x9abc
    assert cpu._cycles == 4


# Execution flow instruction tests

def test_jp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc3)    # JP #beef Instruction Opcode
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Target Address
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jr(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x18)    # JR $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.step()
    assert cpu.pc == 0x0005
    assert cpu._cycles == 12

def test_jr_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x1234, 0x18)    # JR $-66 Instruction Opcode
    cpu._machine.write_memory_byte(0x1235, 0x9a)    # relative offset
    cpu.pc = 0x1234
    cpu.step()
    assert cpu.pc == 0x11d0
    assert cpu._cycles == 12

def test_jr_nz_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x20)    # JR NZ, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = False
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_nz_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x20)    # JR NZ, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = True
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_jr_z_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x28)    # JR Z, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = True
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_z_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x28)    # JR Z, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = False
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_jr_z_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x1234, 0x28)    # JR Z, $-66 Instruction Opcode
    cpu._machine.write_memory_byte(0x1235, 0x9a)    # relative offset
    cpu.zero = True
    cpu.pc = 0x1234
    cpu.step()
    assert cpu.pc == 0x11d0   
    assert cpu._cycles == 12

def test_jr_nc_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x30)    # JR NC, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = False
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_nc_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x30)    # JR NC, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = True
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_jr_c_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x38)    # JR C, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = True
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_c_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x38)    # JR C, $+5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = False
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7


# ALU instructions tests

# Below pairwise testing is used - assuming the same ALU engine is used for all instructions, various tests
# use different instruction types to cover all possible cases, as well as different argument values to test
# resulting flags

def test_add(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x80)    # ADD A, B Instruction Opcode
    cpu.a = 0x1c
    cpu.b = 0x2e
    cpu.step()
    assert cpu.a == 0x4a        # Adding 2 positive integers resulting a positive number
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_add_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x87)    # ADD A, A Instruction Opcode
    cpu.a = 0x00
    cpu.step()
    assert cpu.a == 0x00        # Adding 2 zeroes results a zero
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_add_zero2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x82)    # ADD A, D Instruction Opcode
    cpu.a = 0x42
    cpu.d = 0xbe
    cpu.step()
    assert cpu.a == 0x00        # Adding 0x42 and 0xbe results a zero
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == True
    assert cpu.half_carry == True

def test_add_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc6)    # ADD A, #2F Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x2f)    # argument
    cpu.a = 0x6c
    cpu.step()
    assert cpu.a == 0x9b        # Adding 2 positive integers resulting a negative number
    assert cpu._cycles == 7     # Immediate value takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == True     # Result is negative
    assert cpu.overflow == True # Overflow is set since the result is negative
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_add_negative_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x84)    # ADD A, H Instruction Opcode
    cpu.a = 0x9a
    cpu.h = 0xbc
    cpu.step()
    assert cpu.a == 0x56        # Adding 2 negative integers resulting a positive number
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True # Overflow is set since the result is positive
    assert cpu.carry == True    # Carry is set since the result exceeds 8 bits
    assert cpu.half_carry == True

def test_add_negative_no_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x86)    # ADD A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # operand at (HL)
    cpu.a = 0x9c
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu.a == 0xde        # Adding negative and positive integer does not result an overflow
    assert cpu._cycles == 7     # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == True     # Result is still negative
    assert cpu.overflow == False    # No overflow
    assert cpu.carry == False   # No carry
    assert cpu.half_carry == False

def test_adc_no_carry(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x89)    # ADC A, C Instruction Opcode
    cpu.a = 0x3d
    cpu.c = 0x42
    cpu._carry = False      # No carry
    cpu.step()
    assert cpu.a == 0x7f
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_adc_with_carry(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x8a)    # ADC A, D Instruction Opcode
    cpu.a = 0x3d
    cpu.d = 0x42
    cpu._carry = True       # Carry
    cpu.step()
    assert cpu.a == 0x80
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == True
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_adc_negative_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x8e)    # ADC A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0xcd)    # Argument at (HL)
    cpu.a = 0xab
    cpu.hl = 0xbeef
    cpu._carry = True       # Carry
    cpu.step()
    assert cpu.a == 0x79
    assert cpu._cycles == 7         # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.carry == True
    assert cpu.half_carry == True

def test_adc_negative_no_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x88)    # ADC A, B Instruction Opcode
    cpu.a = 0x42
    cpu.b = 0x9a
    cpu._carry = True       # Carry
    cpu.step()
    assert cpu.a == 0xdd
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False    # Result is still negative, no overflow
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_adc_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x88)    # ADC A, B Instruction Opcode
    cpu.a = 0x54
    cpu.b = 0xab
    cpu._carry = True       # Carry
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False     # ??? Not really sure whether this is correct
    assert cpu.carry == True
    assert cpu.half_carry == True

def test_adc_immediate(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xce)    # ADC A, #42 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # value
    cpu.a = 0x14
    cpu._carry = True
    cpu.step()
    assert cpu.a == 0x57
    assert cpu._cycles == 7
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_sub(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x90)    # SUB A, B Instruction Opcode
    cpu.a = 0x56
    cpu.b = 0x42
    cpu.step()
    assert cpu.a == 0x14
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sub_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x97)    # SUB A, A Instruction Opcode
    cpu.a = 0x42
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False        
    assert cpu.half_carry == True   # ??? Not really sure whether this is correct

def test_sub_zero_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x95)    # SUB A, E Instruction Opcode
    cpu.a = 0x00
    cpu.e = 0x00
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_sub_negative_no_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x96)    # SUB A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x14)    # second operand at (HL)
    cpu.a = 0xab
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu.a == 0x97
    assert cpu._cycles == 7         # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False
    assert cpu.carry == False        
    assert cpu.half_carry == True

def test_sub_negative_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd6)    # SUB A, #42 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate operand
    cpu.a = 0xab
    cpu.step()
    assert cpu.a == 0x69
    assert cpu._cycles == 7         # Immediate value takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_no_carry(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x9b)    # SBC A, E Instruction Opcode
    cpu.a = 0x04
    cpu.e = 0x02
    cpu._carry = False
    cpu.step()
    assert cpu.a == 0x02
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_with_carry(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x9c)    # SBC A, H Instruction Opcode
    cpu.a = 0x04
    cpu.h = 0x02
    cpu._carry = True
    cpu.step()
    assert cpu.a == 0x01
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_negative_no_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xde)    # SBC A, #24 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x24)    # Immadiate operand
    cpu.a = 0xbc
    cpu._carry = True
    cpu.step()
    assert cpu.a == 0x97
    assert cpu._cycles == 7        # Immediate value takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_negative_overflow(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x9e)    # SBC A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # data operand
    cpu.a = 0xbc
    cpu.hl = 0xbeef
    cpu._carry = True
    cpu.step()
    assert cpu.a == 0x79
    assert cpu._cycles == 7         # Fetching (HL) takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x9c)    # SBC A, H Instruction Opcode
    cpu.a = 0x42
    cpu.h = 0x41
    cpu._carry = True
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_and(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xa5)    # AND A, L Instruction Opcode
    cpu.a = 0xfc
    cpu.l = 0x0f
    cpu.step()
    assert cpu.a == 0x0c
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_and_memory(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xa6)    # AND A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x14)    # Operand at (HL)
    cpu.a = 0x73
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu.a == 0x10
    assert cpu._cycles == 7    # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_and_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe6)    # AND A, #13 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x13)    # Immediate operand
    cpu.a = 0xec
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 7     # Immediate value takes additional 3 cycles
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_xor(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xac)    # XOR A, H Instruction Opcode
    cpu.a = 0x5c
    cpu.h = 0x78
    cpu.step()
    assert cpu.a == 0x24
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_xor_same_values(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xae)    # XOR A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Operand at (HL)
    cpu.a = 0x42
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 7    # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_xor_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xee)    # XOR A, #55 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x55)    # Immediate operand
    cpu.a = 0xaa
    cpu.step()
    assert cpu.a == 0xff
    assert cpu._cycles == 7    # Immediate value takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_or(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xb6)    # OR A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0x1234, 0x0f)    # Operand at (HL)
    cpu.a = 0x33
    cpu.hl = 0x1234
    cpu.step()
    assert cpu.a == 0x3f
    assert cpu._cycles == 7   # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_or_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xb7)    # OR A, A Instruction Opcode
    cpu.a = 0x00
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 4
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_or_all_ones(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf6)    # OR A, #55 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x55)    # Immediate operand
    cpu.a = 0xaa
    cpu.step()
    assert cpu.a == 0xff
    assert cpu._cycles == 7    # Immediate value takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_cmp_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xb8)    # CP A, B Instruction Opcode
    cpu.a = 0x0a
    cpu.b = 0x05
    cpu.step()
    assert cpu.a == 0x0a # Does not change
    assert cpu._cycles == 4
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_cmp_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfe)    # CP a, #5 Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0xb8)    # Immediate operand
    cpu.a = 0x02
    cpu.step()
    assert cpu.a == 0x02        # Does not change
    assert cpu._cycles == 7     # Immediate value takes additional 3 cycles
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == True
    assert cpu.half_carry == False

def test_cmp_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xbe)    # CP A, (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0x1234, 0x42)    # CP A, (HL) Instruction Opcode
    cpu.a = 0x42
    cpu.hl = 0x1234
    cpu.step()
    assert cpu.a == 0x42        # Does not change
    assert cpu._cycles == 7     # Accessing (HL) takes additional 3 cycles
    assert cpu.zero == True     # Operands are equal
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_dec_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3d)    # DEC A Instruction Opcode
    cpu.a = 0x42
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.a == 0x41
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_dec_b(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x05)    # DEC B Instruction Opcode
    cpu.b = 0xa2
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.b == 0xa1
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_dec_c(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0d)    # DEC C Instruction Opcode
    cpu.c = 0x01
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.c == 0x00
    assert cpu.half_carry == False
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_dec_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x15)    # DEC D Instruction Opcode
    cpu.d = 0x00
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.d == 0xff
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_dec_e(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1d)    # DEC E Instruction Opcode
    cpu.e = 0x10
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.e == 0x0f
    assert cpu.half_carry == True
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_dec_h(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x25)    # DEC H Instruction Opcode
    cpu.h = 0x80
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.h == 0x7f
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.add_subtract == True

def test_dec_m(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x35)    # DEC (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Data byte
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 11
    assert cpu._machine.read_memory_byte(0xbeef) == 0x41
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_inc_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3c)    # INC A Instruction Opcode
    cpu.a = 0x42
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.a == 0x43
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_inc_b(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x04)    # INC B Instruction Opcode
    cpu.b = 0xa2
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.b == 0xa3
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_inc_c(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0c)    # INC C Instruction Opcode
    cpu.c = 0xff
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.c == 0x00
    assert cpu.half_carry == True
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_inc_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x14)    # INC D Instruction Opcode
    cpu.d = 0x00
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.d == 0x01
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_inc_e(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1c)    # INC E Instruction Opcode
    cpu.e = 0x3f
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.e == 0x40
    assert cpu.half_carry == True
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_inc_h(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x24)    # INC H Instruction Opcode
    cpu.h = 0x7f
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.h == 0x80
    assert cpu.half_carry == True
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == True
    assert cpu.add_subtract == False

def test_inc_m(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x34)    # INC (HL) Instruction Opcode
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Data byte
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 11
    assert cpu._machine.read_memory_byte(0xbeef) == 0x43
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_dec_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0b)    # DEC BC Instruction Opcode
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.b == 0xbe
    assert cpu.c == 0xee

def test_dec_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1b)    # DEC DE Instruction Opcode
    cpu.de = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.d == 0xbe
    assert cpu.e == 0xee

def test_dec_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x2b)    # DEC HL Instruction Opcode
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.h == 0xbe
    assert cpu.l == 0xee

def test_dec_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3b)    # DEC SP Instruction Opcode
    cpu.sp = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.sp == 0xbeee

def test_inc_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x03)    # INC BC Instruction Opcode
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.b == 0xbe
    assert cpu.c == 0xf0

def test_inc_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x13)    # INC DE Instruction Opcode
    cpu.de = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.d == 0xbe
    assert cpu.e == 0xf0

def test_inc_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x23)    # INC HL Instruction Opcode
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.h == 0xbe
    assert cpu.l == 0xf0

def test_inc_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x33)    # INC SP Instruction Opcode
    cpu.sp = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.sp == 0xbef0

def test_add_hl_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x09)    # ADD HL, BC Instruction Opcode
    cpu.hl = 0xa17b
    cpu.bc = 0x339f
    cpu.carry = True    # Shall be ignored
    cpu.step()
    assert cpu.hl == 0xd51a
    assert cpu._cycles == 11
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False

def test_add_hl_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x19)    # ADD HL, DE Instruction Opcode
    cpu.hl = 0xa17b
    cpu.de = 0xbeef
    cpu.carry = True    # Shall be ignored
    cpu.step()
    assert cpu.hl == 0x606a
    assert cpu._cycles == 11
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False

def test_add_hl_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x29)    # ADD HL, HL Instruction Opcode
    cpu.hl = 0xbeef
    cpu.carry = True    # Shall be ignored
    cpu.step()
    assert cpu.hl == 0x7dde
    assert cpu._cycles == 11
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False

def test_add_hl_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x39)    # ADD HL, SP Instruction Opcode
    cpu.hl = 0x1234
    cpu.sp = 0xbeef
    cpu.carry = True    # Shall be ignored
    cpu.step()
    assert cpu.hl == 0xd123
    assert cpu._cycles == 11
    assert cpu.carry == False
    assert cpu.half_carry == True
    assert cpu.add_subtract == False

def test_adc_hl_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, BC Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x4a)
    cpu.hl = 0xa17b     # Negative + Positive result no overflow
    cpu.bc = 0x339f
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xd51b
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == False

def test_adc_hl_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, DE Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x5a)
    cpu.hl = 0xabcd     # Negative + negative result an overflow
    cpu.de = 0xef12
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x9ae0
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False
    assert cpu.overflow == True
    assert cpu.zero == False

def test_adc_hl_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, HL Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x6a)
    cpu.hl = 0x4567     # Positive + positive result an overflow
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x8acf
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == True
    assert cpu.zero == False

def test_adc_hl_hl_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, HL Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x6a)
    cpu.hl = 0x0000     # Zero + zero result no overflow
    cpu.carry = False   # No carry
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == True

def test_adc_hl_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, SP Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x7a)
    cpu.hl = 0x4567     # Positive + negative result no overflow
    cpu.sp = 0x89ab
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xcf13
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == False

def test_adc_hl_sp_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, SP Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x7a)
    cpu.hl = 0x4567     # Positive + negative result no overflow
    cpu.sp = 0xba98
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == True

def test_sbc_hl_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, BC Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x42)
    cpu.hl = 0xa17b     # Negative - Positive result an overflow
    cpu.bc = 0x339f
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x6ddb
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == True
    assert cpu.zero == False

def test_sbc_hl_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, DE Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x52)
    cpu.hl = 0xabcd     # Negative - negative result no overflow
    cpu.de = 0xef12
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xbcba
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == False

def test_sbc_hl_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, HL Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x62)
    cpu.hl = 0x4567     # Positive - positive result no overflow
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xffff
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == True
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == False

def test_sbc_hl_hl_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, HL Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x62)
    cpu.hl = 0x0000     # Zero + zero result no overflow
    cpu.carry = False   # No carry
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == True

def test_sbc_hl_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, SP Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x72)
    cpu.hl = 0x4567     # Positive - negative result no overflow
    cpu.sp = 0x89ab
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xbbbb
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == False

def test_sbc_hl_sp_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, SP Instruction Opcode
    cpu._machine.write_memory_byte(0x0001, 0x72)
    cpu.hl = 0x4567     # Positive - negative result no overflow
    cpu.sp = 0x4566
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == True
    assert cpu.add_subtract == False
    assert cpu.overflow == False
    assert cpu.zero == True
