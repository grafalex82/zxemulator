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