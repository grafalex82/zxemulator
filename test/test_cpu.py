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
    cpu._machine.write_memory_byte(0x0000, 0x00)    # NOP
    cpu.step()
    cpu._machine.reset()
    assert cpu.pc == 0x0000


# Interrupts processing

def test_interrupt_disabled(cpu):
    cpu._interrupt_mode = 0
    cpu._iff1 = False
    cpu.schedule_interrupt([0xff])                  # Schedule RST 38 as interrupt instruction
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.step()
    assert cpu.pc == 0x0001                        # Interrupts are disabled, so normal NOP is executed
    assert cpu._cycles == 4

def test_interrupt_mode0_1byte(cpu):
    cpu._interrupt_mode = 0
    cpu._iff1 = True
    cpu.schedule_interrupt([0xdf])                  # Schedule RST 18 as interrupt instruction
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0x0018                        # expecting RST 18 executed
    assert cpu._machine.read_memory_word(0x1232) == 0x0000  # Current instruction address

def test_interrupt_mode0_3byte(cpu):
    cpu._interrupt_mode = 0
    cpu._iff1 = True
    cpu.schedule_interrupt([0xcd, 0xef, 0xbe])      # Schedule CALL 0xbeef as interrupt instructions
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0xbeef                        # expecting CALL executed
    assert cpu._machine.read_memory_word(0x1232) == 0x0000  # Current instruction address

def test_interrupt_mode0_insufficient_instructions(cpu):
    cpu._interrupt_mode = 0
    cpu._iff1 = True
    cpu.schedule_interrupt([0xcd, 0xef])            # Schedule malformed interrupt instruction
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.sp = 0x1234
    with pytest.raises(InvalidInstruction):
        cpu.step()

def test_interrupt_mode1(cpu):
    cpu._interrupt_mode = 1
    cpu._iff1 = True
    cpu._iff2 = True
    cpu.schedule_interrupt([0x42])                  # Dummy value, expect RSt 38 to be executed
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0x0038                        # expecting RST 18 executed
    assert cpu._machine.read_memory_word(0x1232) == 0x0000  # Current instruction address

def test_interrupt_mode2(cpu):
    cpu._interrupt_mode = 2
    cpu._iff1 = True
    cpu._i = 0xbe       # Interrupt vector will be taken from I register(0xbe) and interrupt ID (0x42)
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu._machine.write_memory_word(0xbe42, 0xbeef)  # Interrupt vector
    cpu.schedule_interrupt([0x42])                  # Scheduling an interrupt #42
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0xbeef                        # Expecting interrupt vector executed
    assert cpu._machine.read_memory_word(0x1232) == 0x0000  # Current instruction address

def test_machine_interrupt_mode0(cpu):
    # This is another Machine class test, that is more convenient to test via CPU
    cpu._interrupt_mode = 0
    cpu._iff1 = True
    cpu._machine.schedule_interrupt()               # Machine will schedule RST 38 as interrupt instruction
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0x0038                        # expecting RST7 executed
    assert cpu._machine.read_memory_word(0x1232) == 0x0000  # Current instruction address

def test_machine_interrupt_mode1(cpu):
    # This is another Machine class test, that is more convenient to test via CPU
    cpu._interrupt_mode = 1
    cpu._iff1 = True
    cpu._machine.schedule_interrupt()               # Machine will schedule RST 38 as interrupt instruction
    cpu._machine.write_memory_byte(0x0000, 0x00)    # Instruction Opcode
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0x0038                        # expecting RST7 executed
    assert cpu._machine.read_memory_word(0x1232) == 0x0000  # Current instruction address


# CPU Control instructions tests

def test_nop(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x00)    # NOP
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu._cycles == 4


def test_ei_di(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfb)    # EI
    cpu._machine.write_memory_byte(0x0001, 0xf3)    # DI
    
    cpu.step() # EI
    assert cpu.iff1 == True
    assert cpu.iff2 == True
    assert cpu._cycles == 4

    cpu.step() # DI
    assert cpu.iff1 == False
    assert cpu.iff2 == False
    assert cpu._cycles == 8     # 4 more cycles

def test_im_0(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # IM 0
    cpu._machine.write_memory_byte(0x0001, 0x46)
    cpu.step()
    assert cpu._cycles == 8
    assert cpu._interrupt_mode == 0

def test_im_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # IM 1
    cpu._machine.write_memory_byte(0x0001, 0x56)
    cpu.step()
    assert cpu._cycles == 8
    assert cpu._interrupt_mode == 1

def test_im_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # IM 2
    cpu._machine.write_memory_byte(0x0001, 0x5e)
    cpu.step()
    assert cpu._cycles == 8
    assert cpu._interrupt_mode == 2


# I/O Input and Output instructions tests

def test_in(cpu):
    mock = MockIO()
    mock.read_byte = MagicMock(return_value=0x55)

    cpu._machine.add_io(IODevice(mock, 0x42))       # Device assigned to a port
    cpu._machine.write_memory_byte(0x0000, 0xdb)    # IN A, $42
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Operand (IO port address)
    cpu.a = 0x34   # Extra address data
    cpu.step()
    assert cpu.a == 0x55
    assert cpu._cycles == 11
    mock.read_byte.assert_called_once_with(0, 0x34) # Verify that extra address data is also delivered

def test_in_d(cpu):
    mock = MockIO()
    mock.read_byte = MagicMock(return_value=0x55)   # Data to read

    cpu._machine.add_io(IODevice(mock, 0x42))       # Device assigned to a port
    cpu._machine.write_memory_byte(0x0000, 0xed)    # IN D, (C)
    cpu._machine.write_memory_byte(0x0001, 0x50)
    cpu.c = 0x42    # IO port address
    cpu.b = 0x34    # Extra address data
    cpu.step()
    assert cpu.d == 0x55
    assert cpu._cycles == 12
    assert cpu.sign == False
    assert cpu.zero == False
    assert cpu.parity == True
    mock.read_byte.assert_called_once_with(0, 0x34) # Verify that extra address data is also delivered

def test_in_e_zero(cpu):
    mock = MockIO()
    mock.read_byte = MagicMock(return_value=0x00)   # Data to read

    cpu._machine.add_io(IODevice(mock, 0x42))       # Device assigned to a port
    cpu._machine.write_memory_byte(0x0000, 0xed)    # IN E, (C)
    cpu._machine.write_memory_byte(0x0001, 0x58)
    cpu.c = 0x42    # IO port address
    cpu.b = 0x34    # Extra address data
    cpu.step()
    assert cpu.e == 0x00
    assert cpu._cycles == 12
    assert cpu.sign == False
    assert cpu.zero == True
    assert cpu.parity == True
    mock.read_byte.assert_called_once_with(0, 0x34) # Verify that extra address data is also delivered

def test_in_flags(cpu):
    mock = MockIO()
    mock.read_byte = MagicMock(return_value=0xab)   # Data to read

    cpu._machine.add_io(IODevice(mock, 0x42))       # Device assigned to a port
    cpu._machine.write_memory_byte(0x0000, 0xed)    # IN (C)
    cpu._machine.write_memory_byte(0x0001, 0x58)    # No target register, only flags
    cpu.c = 0x42    # IO port address
    cpu.b = 0x34    # Extra address data
    cpu.step()
    assert cpu._cycles == 12
    assert cpu.sign == True
    assert cpu.zero == False
    assert cpu.parity == False
    mock.read_byte.assert_called_once_with(0, 0x34) # Verify that extra address data is also delivered

def test_out(cpu):
    mock = MockIO()
    mock.write_byte = MagicMock()

    cpu._machine.add_io(IODevice(mock, 0x42))       # Device assigned to a port
    cpu._machine.write_memory_byte(0x0000, 0xd3)    # OUT #42, A
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Operand (IO port address)
    cpu.a = 0x55
    cpu.step()

    mock.write_byte.assert_called_once_with(0, 0x55, 0x55)  # external device gets extra address data and the value on the data bus
    assert cpu._cycles == 11

def test_out_d(cpu):
    mock = MockIO()
    mock.write_byte = MagicMock()

    cpu._machine.add_io(IODevice(mock, 0x42))       # Device assigned to a port
    cpu._machine.write_memory_byte(0x0000, 0xed)    # OUT (C), D
    cpu._machine.write_memory_byte(0x0001, 0x51)
    cpu.c = 0x42    # IO port address
    cpu.b = 0x34    # Extra address data
    cpu.d = 0x55    # Value to out
    cpu.step()

    mock.write_byte.assert_called_once_with(0, 0x34, 0x55)  # external device gets extra address data and the value on the data bus
    assert cpu._cycles == 12


# 8-bit data transfer instructions tests

def test_ld_a_h(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x7c)    # LD A, H
    cpu.h = 0x42
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.a == 0x42

def test_ld_b_e(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x43)    # LD B, E
    cpu.e = 0x42
    cpu.step()
    assert cpu._cycles == 4
    assert cpu.b == 0x42

def test_ld_mem_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x72)    # LD (HL), D
    cpu.d = 0x42
    cpu.hl = 0x1234
    cpu.step()
    assert cpu._cycles == 7    # Accessing (HL) takes additional 3 cycles
    assert cpu._machine.read_memory_byte(0x1234) == 0x42

def test_ld_l_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x6e)    # LD L, (HL)
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data
    cpu.hl = 0x1234
    cpu.step()
    assert cpu._cycles == 7   # Accessing (HL) takes additional 3 cycles
    assert cpu.l == 0x42

def test_ld_a_val(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3e)    # LD A, #42
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate value
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 7

def test_ld_b_val(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x06)    # LD B, #42
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate value
    cpu.step()
    assert cpu.b == 0x42
    assert cpu._cycles == 7

def test_ld_mem_val(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x36)    # LD (HL), #42
    cpu._machine.write_memory_byte(0x0001, 0x42)    # Immediate Value
    cpu.hl = 0x1234
    cpu.step()
    assert cpu._machine.read_memory_byte(0x1234) == 0x42
    assert cpu._cycles == 10

def test_ld_i_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD I, A
    cpu._machine.write_memory_byte(0x0001, 0x47)
    cpu.a = 0x42
    cpu.step()
    assert cpu.i == 0x42
    assert cpu._cycles == 9

def test_ld_r_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD R, A
    cpu._machine.write_memory_byte(0x0001, 0x4f)
    cpu.a = 0x42
    cpu.step()
    assert cpu.r == 0x42
    assert cpu._cycles == 9

def test_ld_a_i(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD A, I
    cpu._machine.write_memory_byte(0x0001, 0x57)
    cpu.i = 0x42
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 9

def test_ld_a_r(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD A, R
    cpu._machine.write_memory_byte(0x0001, 0x5f)
    cpu.r = 0x42
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 9

def test_ld_mem_a(cpu):
    cpu.a = 0x42   # Value to write
    cpu._machine.write_memory_byte(0x0000, 0x32)    # LD (#beef), A
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x42
    assert cpu._cycles == 13

def test_ld_a_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3a)    # LD A, (#beef)
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Data to read
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 13


def test_ld_reg_indexed_mem_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # LD C, (IX+05)
    cpu._machine.write_memory_byte(0x0001, 0x4e)    # C register is a destination
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Displacement
    cpu._machine.write_memory_byte(0xbeef + 0x05, 0x42) # Data to load
    cpu._ix = 0xbeef
    cpu.step()
    assert cpu.c == 0x42
    assert cpu._cycles == 19

def test_ld_reg_indexed_mem_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # LD H, (IY-05)
    cpu._machine.write_memory_byte(0x0001, 0x66)    # H register is a destination
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Negative Displacement
    cpu._machine.write_memory_byte(0xbeef - 0x05, 0x42) # Data to load
    cpu._iy = 0xbeef
    cpu.step()
    assert cpu.h == 0x42
    assert cpu._cycles == 19

def test_ld_indexed_mem_reg_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # LD (IX+05), C
    cpu._machine.write_memory_byte(0x0001, 0x71)    # C register is a source
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Displacement
    cpu._ix = 0xbeef
    cpu.c = 0x42
    cpu.step()
    assert cpu._cycles == 19
    assert cpu._machine.read_memory_byte(0xbeef + 0x05) == 0x42

def test_ld_indexed_mem_reg_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # LD (IY-05), H
    cpu._machine.write_memory_byte(0x0001, 0x74)    # H register is a source
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Negative Displacement
    cpu._iy = 0xbeef
    cpu.h = 0x42
    cpu.step()
    assert cpu._cycles == 19
    assert cpu._machine.read_memory_byte(0xbeef - 0x05) == 0x42

def test_ld_reg_indexed_mem_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # LD (IX+05), 42  
    cpu._machine.write_memory_byte(0x0001, 0x36)
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Displacement
    cpu._machine.write_memory_byte(0x0003, 0x42)    # Value
    cpu._ix = 0xbeef
    cpu.step()
    assert cpu._cycles == 19
    assert cpu._machine.read_memory_byte(0xbeef + 0x05) == 0x42

def test_ld_reg_indexed_mem_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # LD (IY-05), 42  
    cpu._machine.write_memory_byte(0x0001, 0x36)
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Negative Displacement
    cpu._machine.write_memory_byte(0x0003, 0x42)    # Value
    cpu._iy = 0xbeef
    cpu.step()
    assert cpu._cycles == 19
    assert cpu._machine.read_memory_byte(0xbeef - 0x05) == 0x42


# 16-bit data transfer instructions tests

def test_ld_a_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0a)    # LD A, (BC)
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Data to load
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 7

def test_ld_a_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1a)    # LD A, (DE)
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Data to load
    cpu.de = 0xbeef
    cpu.step()
    assert cpu.a == 0x42
    assert cpu._cycles == 7

def test_ld_bc_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x02)    # LD (BC), A
    cpu.a = 0x42
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x42
    assert cpu._cycles == 7

def test_ld_de_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x12)    # LD (DE), A
    cpu.a = 0x42
    cpu.de = 0xbeef
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x42
    assert cpu._cycles == 7

def test_ld_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x01)    # LD BC, #beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.b == 0xbe
    assert cpu.c == 0xef
    assert cpu._cycles == 10

def test_ld_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x11)    # LD DE, #beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.d == 0xbe
    assert cpu.e == 0xef
    assert cpu._cycles == 10
    
def test_ld_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x21)    # LD HL, #beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.h == 0xbe
    assert cpu.l == 0xef
    assert cpu._cycles == 10
    
def test_ld_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x31)    # LD SP, #beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0003
    assert cpu.sp == 0xbeef
    assert cpu._cycles == 10

def test_ld_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # LD IX, #dead
    cpu._machine.write_memory_byte(0x0001, 0x21)
    cpu._machine.write_memory_word(0x0002, 0xdead)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0004
    assert cpu.ix == 0xdead
    assert cpu._cycles == 14

def test_ld_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # LD IY, #beef
    cpu._machine.write_memory_byte(0x0001, 0x21)
    cpu._machine.write_memory_word(0x0002, 0xbeef)  # Immediate argument
    cpu.step() 
    assert cpu.pc == 0x0004
    assert cpu.iy == 0xbeef
    assert cpu._cycles == 14

def test_ld_mem_hl(cpu):
    cpu.hl = 0x1234   # Value to write
    cpu._machine.write_memory_byte(0x0000, 0x22)    # LD (beef), HL
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu.step()
    assert cpu._machine.read_memory_word(0xbeef) == 0x1234
    assert cpu._cycles == 16

def test_ld_mem_reg16(cpu):
    cpu.de = 0x1234   # Value to write
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD (beef), DE
    cpu._machine.write_memory_byte(0x0001, 0x53)    
    cpu._machine.write_memory_word(0x0002, 0xbeef)  # Address
    cpu.step()
    assert cpu._machine.read_memory_word(0xbeef) == 0x1234
    assert cpu._cycles == 20

def test_ld_hl_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x2a)    # LD HL, (beef)
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._machine.write_memory_word(0xbeef, 0x1234)  # Value to read
    cpu.step()
    assert cpu.hl == 0x1234
    assert cpu._cycles == 16

def test_ld_reg16_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LD BC, (beef)
    cpu._machine.write_memory_byte(0x0001, 0x4b)    
    cpu._machine.write_memory_word(0x0002, 0xbeef)  # Address
    cpu._machine.write_memory_word(0xbeef, 0x1234)  # Value to read
    cpu.step()
    assert cpu.bc == 0x1234
    assert cpu._cycles == 20

def test_ld_sp_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf9)    # LD SP, HL
    cpu.hl = 0x1234
    cpu.step()
    assert cpu.sp == 0x1234
    assert cpu._cycles == 6

def test_push_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc5)    # PUSH BC
    cpu.sp = 0x1234
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu._cycles == 11
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0xbeef

def test_push_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd5)    # PUSH DE
    cpu.sp = 0x1234
    cpu.de = 0xbeef
    cpu.step()
    assert cpu._cycles == 11
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0xbeef

def test_push_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe5)    # PUSH HL
    cpu.sp = 0x1234
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 11
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0xbeef

def test_push_af_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf5)    # PUSH AF
    cpu.sp = 0x1234
    cpu.a = 0x42
    cpu.step()
    assert cpu._cycles == 11
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x4200  # All flag bits are zero

def test_push_af_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf5)    # PUSH AF
    cpu.sp = 0x1234
    cpu.a = 0x42
    cpu.sign = True
    cpu.zero = True
    cpu.half_carry = True
    cpu.parity = True
    cpu.carry = True
    cpu.add_subtract = True
    cpu.step()
    assert cpu._cycles == 11
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x42d7 # bit1 of the PSW is always 1

def test_push_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # PUSH IX
    cpu._machine.write_memory_byte(0x0001, 0xe5)
    cpu.sp = 0x1234
    cpu.ix = 0xbeef
    cpu.step()
    assert cpu._cycles == 15
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0xbeef

def test_push_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # PUSH IY
    cpu._machine.write_memory_byte(0x0001, 0xe5)
    cpu.sp = 0x1234
    cpu.iy = 0xbeef
    cpu.step()
    assert cpu._cycles == 15
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0xbeef

def test_pop_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc1)    # POP BC
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Data to pop
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 10
    assert cpu.sp == 0x1236
    assert cpu.bc == 0xbeef

def test_pop_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd1)    # POP DE
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Data to pop
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 10
    assert cpu.sp == 0x1236
    assert cpu.de == 0xbeef

def test_pop_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe1)    # POP HL
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Data to pop
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 10
    assert cpu.sp == 0x1236
    assert cpu.hl == 0xbeef

def test_pop_af_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf1)    # POP AF
    cpu._machine.write_memory_word(0x1234, 0xbe00)  # Data to pop (A=0xbe, all flags are off)
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 10
    assert cpu.sp == 0x1236
    assert cpu.a == 0xbe
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False
    assert cpu.add_subtract == False

def test_pop_af_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf1)    # POP AF
    cpu._machine.write_memory_word(0x1234, 0xbed7)  # Data to pop (A=0xbe, all flags are on)
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 10
    assert cpu.sp == 0x1236
    assert cpu.a == 0xbe
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.zero == True
    assert cpu.sign == True
    assert cpu.parity == True
    assert cpu.add_subtract == True

def test_pop_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # POP IX
    cpu._machine.write_memory_byte(0x0001, 0xe1)
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Data to pop
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 14
    assert cpu.sp == 0x1236
    assert cpu.ix == 0xbeef

def test_pop_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # POP IY
    cpu._machine.write_memory_byte(0x0001, 0xe1)
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Data to pop
    cpu.sp = 0x1234
    cpu.step()
    assert cpu._cycles == 14
    assert cpu.sp == 0x1236
    assert cpu.iy == 0xbeef


# Exchange instructions tests

def test_ex_de_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xeb)    # EX DE, HL
    cpu.hl = 0x1234
    cpu.de = 0xbeef
    cpu.step()
    assert cpu.hl == 0xbeef
    assert cpu.de == 0x1234
    assert cpu._cycles == 4

def test_ex_stack_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe3)    # EX (SP), HL
    cpu._machine.write_memory_word(0x4321, 0xbeef)  # data to be exchanged
    cpu.hl = 0x1234
    cpu.sp = 0x4321
    cpu.step()
    assert cpu.hl == 0xbeef
    assert cpu._machine.read_memory_word(0x4321) == 0x1234
    assert cpu._cycles == 19

def test_ex_af_afx(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x08)    # EX AF, AF'
    cpu.af = 0x1234
    cpu.afx = 0xbeef
    cpu.step()
    assert cpu.af == 0xbec7     # Bits 3 and 5 of the F register are not copied
    assert cpu.afx == 0x1214    # Bits 3 and 5 of the F register are not copied
    assert cpu._cycles == 4

def test_exx(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd9)    # EXX
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

# Block transfer instructions tests

def test_ldi(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LDI
    cpu._machine.write_memory_byte(0x0001, 0xa0)
    cpu.hl = 0x1234     # Source address
    cpu.de = 0x4321     # Destination address
    cpu.bc = 0x5678     # Number of bytes to transfer
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data to transfer
    cpu.step()
    assert cpu.hl == 0x1235     # Incremented address
    assert cpu.de == 0x4322     # Incremented address
    assert cpu.bc == 0x5677     # Decremented count
    assert cpu._machine.read_memory_byte(0x4321) == 0x42
    assert cpu._cycles == 16
    assert cpu.overflow == True # There are still bytes to copy

def test_ldi_last(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LDI
    cpu._machine.write_memory_byte(0x0001, 0xa0)
    cpu.hl = 0x1234     # Source address
    cpu.de = 0x4321     # Destination address
    cpu.bc = 0x0001     # Last byte to transfer
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data to transfer
    cpu.step()
    assert cpu.hl == 0x1235     # Incremented address
    assert cpu.de == 0x4322     # Incremented address
    assert cpu.bc == 0x0000     # Reached last byte
    assert cpu._machine.read_memory_byte(0x4321) == 0x42
    assert cpu._cycles == 16
    assert cpu.overflow == False    # Reached last byte to copy

def test_ldd(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LDD
    cpu._machine.write_memory_byte(0x0001, 0xa8)
    cpu.hl = 0x1234     # Source address
    cpu.de = 0x4321     # Destination address
    cpu.bc = 0x5678     # Number of bytes to transfer
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data to transfer
    cpu.step()
    assert cpu.hl == 0x1233     # Decremented address
    assert cpu.de == 0x4320     # Decremented address
    assert cpu.bc == 0x5677     # Decremented count
    assert cpu._machine.read_memory_byte(0x4321) == 0x42
    assert cpu._cycles == 16
    assert cpu.overflow == True # There are still bytes to copy

def test_ldd_last(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LDD
    cpu._machine.write_memory_byte(0x0001, 0xa8)
    cpu.hl = 0x1234     # Source address
    cpu.de = 0x4321     # Destination address
    cpu.bc = 0x0001     # Last byte to transfer
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data to transfer
    cpu.step()
    assert cpu.hl == 0x1233     # Decremented address
    assert cpu.de == 0x4320     # Decremented address
    assert cpu.bc == 0x0000     # Reached last byte
    assert cpu._machine.read_memory_byte(0x4321) == 0x42
    assert cpu._cycles == 16
    assert cpu.overflow == False    # Reached last byte to copy

def test_ldir(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LDIR
    cpu._machine.write_memory_byte(0x0001, 0xb0)
    cpu.hl = 0x1234     # Source address
    cpu.de = 0x4321     # Destination address
    cpu.bc = 0x0003     # Number of bytes to transfer
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data to transfer
    cpu._machine.write_memory_byte(0x1235, 0x43)
    cpu._machine.write_memory_byte(0x1236, 0x44)

    cpu.step()                  # Repeat command 3 times
    assert cpu.pc == 0x0000     # PC does not advance to the next instruction
    cpu.step()
    assert cpu.pc == 0x0000     # PC does not advance to the next instruction
    cpu.step()

    assert cpu.pc == 0x0002     # PC finally advanced to the next instruction
    assert cpu.hl == 0x1237     # Incremented address
    assert cpu.de == 0x4324     # Incremented address
    assert cpu.bc == 0x0000     # Decremented count
    assert cpu._machine.read_memory_byte(0x4321) == 0x42
    assert cpu._machine.read_memory_byte(0x4322) == 0x43
    assert cpu._machine.read_memory_byte(0x4323) == 0x44
    assert cpu._cycles == 21 + 21 + 16
    assert cpu.overflow == False    # No more bytes to copy

def test_lddr(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # LDDR
    cpu._machine.write_memory_byte(0x0001, 0xb8)
    cpu.hl = 0x1234     # Source address
    cpu.de = 0x4321     # Destination address
    cpu.bc = 0x0003     # Number of bytes to transfer
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Data to transfer
    cpu._machine.write_memory_byte(0x1233, 0x43)
    cpu._machine.write_memory_byte(0x1232, 0x44)

    cpu.step()                  # Repeat command 3 times
    assert cpu.pc == 0x0000     # PC does not advance to the next instruction
    cpu.step()
    assert cpu.pc == 0x0000     # PC does not advance to the next instruction
    cpu.step()

    assert cpu.pc == 0x0002     # PC finally advanced to the next instruction
    assert cpu.hl == 0x1231     # Decremented address
    assert cpu.de == 0x431e     # Decremented address
    assert cpu.bc == 0x0000     # Decremented count
    assert cpu._machine.read_memory_byte(0x4321) == 0x42
    assert cpu._machine.read_memory_byte(0x4320) == 0x43
    assert cpu._machine.read_memory_byte(0x431f) == 0x44
    assert cpu._cycles == 21 + 21 + 16
    assert cpu.overflow == False    # No more bytes to copy


# Execution flow instruction tests

def test_jp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc3)    # JP #beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Target Address
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe9)    # JP (HL)
    cpu.hl = 0x1234
    cpu.step()
    assert cpu.pc == 0x1234
    assert cpu._cycles == 4

def test_jp_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # JP (IX)
    cpu._machine.write_memory_byte(0x0001, 0xe9)
    cpu.ix = 0x1234
    cpu.step()
    assert cpu.pc == 0x1234
    assert cpu._cycles == 8

def test_jp_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # JP (IY)
    cpu._machine.write_memory_byte(0x0001, 0xe9)
    cpu.iy = 0x1234
    cpu.step()
    assert cpu.pc == 0x1234
    assert cpu._cycles == 8

def test_jr(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x18)    # JR $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.step()
    assert cpu.pc == 0x0005
    assert cpu._cycles == 12

def test_jr_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x1234, 0x18)    # JR $-66
    cpu._machine.write_memory_byte(0x1235, 0x9a)    # relative offset
    cpu.pc = 0x1234
    cpu.step()
    assert cpu.pc == 0x11d0
    assert cpu._cycles == 12

def test_jr_nz_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x20)    # JR NZ, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = False
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_nz_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x20)    # JR NZ, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = True
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_jr_z_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x28)    # JR Z, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = True
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_z_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x28)    # JR Z, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.zero = False
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_jr_z_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x1234, 0x28)    # JR Z, $-66
    cpu._machine.write_memory_byte(0x1235, 0x9a)    # relative offset
    cpu.zero = True
    cpu.pc = 0x1234
    cpu.step()
    assert cpu.pc == 0x11d0   
    assert cpu._cycles == 12

def test_jr_nc_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x30)    # JR NC, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = False
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_nc_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x30)    # JR NC, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = True
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_jr_c_positive(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x38)    # JR C, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = True
    cpu.step()
    assert cpu.pc == 0x0005  # Jump
    assert cpu._cycles == 12

def test_jr_c_negative(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x38)    # JR C, $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.carry = False
    cpu.step()
    assert cpu.pc == 0x0002   # No jump
    assert cpu._cycles == 7

def test_djnz_non_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x10)    # DJNZ $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.b = 0x10                # Counter will be non-zero after decrement, expect jump forward
    cpu.step()
    assert cpu.pc == 0x0005     # Jump happened
    assert cpu.b == 0x0f        # Counter decremented
    assert cpu._cycles == 13

def test_djnz_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x10)    # DJNZ $+5
    cpu._machine.write_memory_byte(0x0001, 0x03)    # relative offset
    cpu.b = 0x01                # Counter will be zero after decrement, expect no jump
    cpu.step()
    assert cpu.pc == 0x0002     # No jump happened
    assert cpu.b == 0x00        # Counter decremented
    assert cpu._cycles == 8

def test_djnz_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x1234, 0x10)    # DJNZ $-66
    cpu._machine.write_memory_byte(0x1235, 0x9a)    # relative offset
    cpu.b = 0x10                # Counter will be non-zero after decrement, expect jump backwards
    cpu.pc = 0x1234
    cpu.step()
    assert cpu.pc == 0x11d0     # Jumped backwards
    assert cpu.b == 0x0f        # Counter decremented
    assert cpu._cycles == 13

def test_call(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcd)    # CALL BEEF
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 17
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # address of the next instruction

def test_ret(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc9)    # RET
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 10

def test_jp_z_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xca)    # JP Z, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._zero = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_z_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xca)    # JP Z, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._zero = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_nz_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc2)    # JP NZ, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._zero = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_nz_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc2)    # JP NZ, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._zero = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_c_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xda)    # JP C, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._carry = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_c_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xda)    # JP C, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._carry = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_nc_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd2)    # JP NC, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._carry = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_nc_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd2)    # JP NC, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._carry = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_pe_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xea)    # JP PE, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._parity = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_pe_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xea)    # JP PE, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._parity = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_po_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe2)    # JP PO, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._parity = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_po_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe2)    # JP PO, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._parity = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_m_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfa)    # JP M, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._sign = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_jp_m_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfa)    # JP M, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._sign = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_p_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf2)    # JP P, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._sign = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu._cycles == 10

def test_jp_p_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf2)    # JP P, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Address
    cpu._sign = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu._cycles == 10

def test_call_nz_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc4)    # CALL NZ, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._zero = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_nz_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc4)    # CALL NZ, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._zero = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_z_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcc)    # CALL Z, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._zero = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_z_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcc)    # CALL Z, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._zero = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_nc_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd4)    # CALL NC, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._carry = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_nc_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd4)    # CALL NC, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._carry = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_c_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdc)    # CALL C, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._carry = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_c_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdc)    # CALL C, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._carry = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_po_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe4)    # CALL PO, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._parity = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_po_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe4)    # CALL PO, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._parity = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_pe_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xec)    # CALL PE, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._parity = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_pe_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xec)    # CALL PE, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._parity = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_p_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf4)    # CALL P, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._sign = True
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_p_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf4)    # CALL P, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._sign = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_call_m_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfc)    # CALL M, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._sign = False
    cpu.step()
    assert cpu.pc == 0x0003
    assert cpu.sp == 0x1234
    assert cpu._cycles == 10

def test_call_m_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfc)    # CALL M, beef
    cpu._machine.write_memory_word(0x0001, 0xbeef)  # Subroutine address
    cpu.sp = 0x1234
    cpu._sign = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0003 # Return address
    assert cpu._cycles == 17

def test_ret_nz_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc0)    # RET NZ
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._zero = True
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_nz_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc0)    # RET NZ
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._zero = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_z_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc8)    # RET Z
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._zero = False
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_z_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xc8)    # RET Z
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._zero = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_nc_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd0)    # RET NC
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._carry = True
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_nc_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd0)    # RET NC
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._carry = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_c_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd8)    # RET C
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._carry = False
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_c_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xd8)    # RET C
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._carry = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_po_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe0)    # RET PO
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._parity = True
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_po_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe0)    # RET PO
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._parity = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_pe_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe8)    # RET PE
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._parity = False
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_pe_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xe8)    # RET PE
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._parity = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_p_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf0)    # RET P
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._sign = True
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_p_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf0)    # RET P
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._sign = False
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

def test_ret_m_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf8)    # RET M
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._sign = False
    cpu.step()
    assert cpu.pc == 0x0001
    assert cpu.sp == 0x1234
    assert cpu._cycles == 5

def test_ret_m_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xf8)    # RET M
    cpu._machine.write_memory_word(0x1234, 0xbeef)  # Return address
    cpu.sp = 0x1234
    cpu._sign = True
    cpu.step()
    assert cpu.pc == 0xbeef
    assert cpu.sp == 0x1236
    assert cpu._cycles == 11

@pytest.mark.parametrize("opcode, rstaddr", 
    [(0xc7, 0x0000), (0xcf, 0x0008), (0xd7, 0x0010), (0xdf, 0x0018),
     (0xe7, 0x0020), (0xef, 0x0028), (0xf7, 0x0030), (0xff, 0x0038)])
def test_rst(cpu, opcode, rstaddr):
    cpu._machine.write_memory_byte(0x0000, opcode)    # RST nn
    cpu.sp = 0x1234
    cpu.step()
    assert cpu.pc == rstaddr
    assert cpu._cycles == 11
    assert cpu.sp == 0x1232
    assert cpu._machine.read_memory_word(0x1232) == 0x0001 # address of the next instruction


# ALU instructions tests

# Below pairwise testing is used - assuming the same ALU engine is used for all instructions, various tests
# use different instruction types to cover all possible cases, as well as different argument values to test
# resulting flags

def test_add(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x80)    # ADD A, B
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
    cpu._machine.write_memory_byte(0x0000, 0x87)    # ADD A, A
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
    cpu._machine.write_memory_byte(0x0000, 0x82)    # ADD A, D
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
    cpu._machine.write_memory_byte(0x0000, 0xc6)    # ADD A, #2F
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
    cpu._machine.write_memory_byte(0x0000, 0x84)    # ADD A, H
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
    cpu._machine.write_memory_byte(0x0000, 0x86)    # ADD A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0x89)    # ADC A, C
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
    cpu._machine.write_memory_byte(0x0000, 0x8a)    # ADC A, D
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
    cpu._machine.write_memory_byte(0x0000, 0x8e)    # ADC A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0x88)    # ADC A, B
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
    cpu._machine.write_memory_byte(0x0000, 0x88)    # ADC A, B
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
    cpu._machine.write_memory_byte(0x0000, 0xce)    # ADC A, #42
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
    cpu._machine.write_memory_byte(0x0000, 0x90)    # SUB A, B
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
    cpu._machine.write_memory_byte(0x0000, 0x97)    # SUB A, A
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
    cpu._machine.write_memory_byte(0x0000, 0x95)    # SUB A, E
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
    cpu._machine.write_memory_byte(0x0000, 0x96)    # SUB A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0xd6)    # SUB A, #42
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
    cpu._machine.write_memory_byte(0x0000, 0x9b)    # SBC A, E
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
    cpu._machine.write_memory_byte(0x0000, 0x9c)    # SBC A, H
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
    cpu._machine.write_memory_byte(0x0000, 0xde)    # SBC A, #24
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
    cpu._machine.write_memory_byte(0x0000, 0x9e)    # SBC A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0x9c)    # SBC A, H
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
    cpu._machine.write_memory_byte(0x0000, 0xa5)    # AND A, L
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
    cpu._machine.write_memory_byte(0x0000, 0xa6)    # AND A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0xe6)    # AND A, #13
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
    cpu._machine.write_memory_byte(0x0000, 0xac)    # XOR A, H
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
    cpu._machine.write_memory_byte(0x0000, 0xae)    # XOR A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0xee)    # XOR A, #55
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
    cpu._machine.write_memory_byte(0x0000, 0xb6)    # OR A, (HL)
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
    cpu._machine.write_memory_byte(0x0000, 0xb7)    # OR A, A
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
    cpu._machine.write_memory_byte(0x0000, 0xf6)    # OR A, #55
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
    cpu._machine.write_memory_byte(0x0000, 0xb8)    # CP A, B
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
    cpu._machine.write_memory_byte(0x0000, 0xfe)    # CP a, #5
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
    cpu._machine.write_memory_byte(0x0000, 0xbe)    # CP A, (HL)
    cpu._machine.write_memory_byte(0x1234, 0x42)    # CP A, (HL)
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

def test_add_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # ADD A, (IX + 5)
    cpu._machine.write_memory_byte(0x0001, 0x86)    
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x14)    # Operand at IX + 5

    cpu.a = 0x1c
    cpu.ix = 0x1234
    cpu.step()

    assert cpu.a == 0x30        # Adding 2 positive integers resulting a positive number
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_add_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # ADD A, (IY - 5)
    cpu._machine.write_memory_byte(0x0001, 0x86)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0xcd)    # Operand at IX + 5

    cpu.a = 0xab
    cpu.iy = 0x1234
    cpu.step()

    assert cpu.a == 0x78        # Adding 2 positive integers resulting a positive number
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.carry == True
    assert cpu.half_carry == True

def test_adc_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # ADC A, (IX - 5)
    cpu._machine.write_memory_byte(0x0001, 0x8e)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0xab)    # Operand at IX + 5

    cpu.a = 0x54
    cpu.ix = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x00        # Adding positive and negative integers resulting a zero
    assert cpu._cycles == 19
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == True
    assert cpu.half_carry == True

def test_adc_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # ADC A, (IY + 5)
    cpu._machine.write_memory_byte(0x0001, 0x8e)    
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0xcd)    # Operand at IX + 5

    cpu.a = 0xab
    cpu.iy = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x79        # Adding 2 negative integers resulting an overflow
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.carry == True
    assert cpu.half_carry == True
 
def test_sub_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # SUB A, (IX + 5)
    cpu._machine.write_memory_byte(0x0001, 0x96)    
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x42)    # Operand at IX + 5

    cpu.a = 0x56
    cpu.ix = 0x1234
    cpu.step()

    assert cpu.a == 0x14
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sub_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # SUB A, (IY - 5)
    cpu._machine.write_memory_byte(0x0001, 0x96)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0x42)    # Operand at IY - 5

    cpu.a = 0x42
    cpu.iy = 0x1234
    cpu.step()

    assert cpu.a == 0x00
    assert cpu._cycles == 19
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # SBC A, (IX - 5)
    cpu._machine.write_memory_byte(0x0001, 0x9e)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0x24)    # Operand at IX - 5

    cpu.a = 0xbc
    cpu.ix = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x97        # Subtracting positive and negative integers resulting no overflow
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_sbc_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # SBC A, (IY + 5)
    cpu._machine.write_memory_byte(0x0001, 0x9e)    
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x42)    # Operand at IY + 5

    cpu.a = 0xbc
    cpu.iy = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x79        # Subtracting positive from negative may result an overflow
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_and_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # AND (IX + 5)
    cpu._machine.write_memory_byte(0x0001, 0xa6)    
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x0f)    # Operand at IX + 5

    cpu.a = 0xfc
    cpu.ix = 0x1234
    cpu.step()

    assert cpu.a == 0x0c
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_and_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # AND (IY - 5)
    cpu._machine.write_memory_byte(0x0001, 0xa6)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0x14)    # Operand at IY - 5

    cpu.a = 0x73
    cpu.iy = 0x1234
    cpu.step()

    assert cpu.a == 0x10
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_xor_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # XOR (IX - 5)
    cpu._machine.write_memory_byte(0x0001, 0xae)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0x78)    # Operand at IX - 5

    cpu.a = 0x5c
    cpu.ix = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x24
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_xor_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # XOR (IY + 5)
    cpu._machine.write_memory_byte(0x0001, 0xae)
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x42)    # Operand at IY + 5

    cpu.a = 0x42
    cpu.iy = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x00
    assert cpu._cycles == 19
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_or_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # OR (IX + 5)
    cpu._machine.write_memory_byte(0x0001, 0xb6)    
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x0f)    # Operand at IX + 5

    cpu.a = 0x33
    cpu.ix = 0x1234
    cpu.step()

    assert cpu.a == 0x3f
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_or_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # OR (IY - 5)
    cpu._machine.write_memory_byte(0x0001, 0xb6)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0x55)    # Operand at IY - 5

    cpu.a = 0xaa
    cpu.iy = 0x1234
    cpu.step()

    assert cpu.a == 0xff
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == True
    assert cpu.carry == False
    assert cpu.half_carry == False

def test_cp_indexed_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # CP (IX - 5)
    cpu._machine.write_memory_byte(0x0001, 0xbe)    
    cpu._machine.write_memory_byte(0x0002, 0xfb)    # Offset
    cpu._machine.write_memory_byte(0x1234 - 0x05, 0x42)    # Operand at IX - 5

    cpu.a = 0x43
    cpu.ix = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x43    # Does not change
    assert cpu._cycles == 19
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True

def test_cp_indexed_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # CP (IY + 5)
    cpu._machine.write_memory_byte(0x0001, 0xbe)
    cpu._machine.write_memory_byte(0x0002, 0x05)    # Offset
    cpu._machine.write_memory_byte(0x1234 + 0x05, 0x42)    # Operand at IY + 5

    cpu.a = 0x42
    cpu.iy = 0x1234
    cpu.carry = True
    cpu.step()

    assert cpu.a == 0x42
    assert cpu._cycles == 19
    assert cpu.zero == True         # Operands are equal
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.carry == False
    assert cpu.half_carry == True


def test_dec_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3d)    # DEC A
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
    cpu._machine.write_memory_byte(0x0000, 0x05)    # DEC B
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
    cpu._machine.write_memory_byte(0x0000, 0x0d)    # DEC C
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
    cpu._machine.write_memory_byte(0x0000, 0x15)    # DEC D
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
    cpu._machine.write_memory_byte(0x0000, 0x1d)    # DEC E
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
    cpu._machine.write_memory_byte(0x0000, 0x25)    # DEC H
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
    cpu._machine.write_memory_byte(0x0000, 0x35)    # DEC (HL)
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

def test_dec_iy_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # DEC (IY + 5)
    cpu._machine.write_memory_byte(0x0001, 0x35)
    cpu._machine.write_memory_byte(0x0002, 0x05)
    cpu._machine.write_memory_byte(0x1234 + 5, 0x42)    # Data byte
    cpu.iy = 0x1234
    cpu.step()
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0x1234 + 5) == 0x41
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == True

def test_dec_iy_d_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # DEC (IY - 5)
    cpu._machine.write_memory_byte(0x0001, 0x35)
    cpu._machine.write_memory_byte(0x0002, 0xfb)
    cpu._machine.write_memory_byte(0x1234 - 5, 0x80)    # Data byte
    cpu.iy = 0x1234
    cpu.step()
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0x1234 - 5) == 0x7f
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == True
    assert cpu.add_subtract == True

def test_inc_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3c)    # INC A
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
    cpu._machine.write_memory_byte(0x0000, 0x04)    # INC B
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
    cpu._machine.write_memory_byte(0x0000, 0x0c)    # INC C
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
    cpu._machine.write_memory_byte(0x0000, 0x14)    # INC D
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
    cpu._machine.write_memory_byte(0x0000, 0x1c)    # INC E
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
    cpu._machine.write_memory_byte(0x0000, 0x24)    # INC H
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
    cpu._machine.write_memory_byte(0x0000, 0x34)    # INC (HL)
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

def test_inc_ix_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # INC (IX + 5)
    cpu._machine.write_memory_byte(0x0001, 0x34)
    cpu._machine.write_memory_byte(0x0002, 0x05)
    cpu._machine.write_memory_byte(0x1234 + 5, 0x42)    # Data byte
    cpu.ix = 0x1234
    cpu.step()
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0x1234 + 5) == 0x43
    assert cpu.half_carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.overflow == False
    assert cpu.add_subtract == False

def test_inc_iy_d_negative_offset(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # INC (IY - 5)
    cpu._machine.write_memory_byte(0x0001, 0x34)
    cpu._machine.write_memory_byte(0x0002, 0xfb)
    cpu._machine.write_memory_byte(0x1234 - 5, 0x7f)    # Data byte
    cpu.iy = 0x1234
    cpu.step()
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0x1234 - 5) == 0x80
    assert cpu.half_carry == True
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.overflow == True
    assert cpu.add_subtract == False

def test_dec_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0b)    # DEC BC
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.b == 0xbe
    assert cpu.c == 0xee

def test_dec_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1b)    # DEC DE
    cpu.de = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.d == 0xbe
    assert cpu.e == 0xee

def test_dec_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x2b)    # DEC HL
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.h == 0xbe
    assert cpu.l == 0xee

def test_dec_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3b)    # DEC SP
    cpu.sp = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.sp == 0xbeee

def test_inc_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x03)    # INC BC
    cpu.bc = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.b == 0xbe
    assert cpu.c == 0xf0

def test_inc_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x13)    # INC DE
    cpu.de = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.d == 0xbe
    assert cpu.e == 0xf0

def test_inc_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x23)    # INC HL
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.h == 0xbe
    assert cpu.l == 0xf0

def test_inc_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x33)    # INC SP
    cpu.sp = 0xbeef
    cpu.step()
    assert cpu._cycles == 6
    assert cpu.sp == 0xbef0

def test_add_hl_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x09)    # ADD HL, BC
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
    cpu._machine.write_memory_byte(0x0000, 0x19)    # ADD HL, DE
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
    cpu._machine.write_memory_byte(0x0000, 0x29)    # ADD HL, HL
    cpu.hl = 0xbeef
    cpu.carry = True    # Shall be ignored
    cpu.step()
    assert cpu.hl == 0x7dde
    assert cpu._cycles == 11
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False

def test_add_hl_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x39)    # ADD HL, SP
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, BC
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, DE
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, HL
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, HL
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, SP
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # ADC HL, SP
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
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, BC
    cpu._machine.write_memory_byte(0x0001, 0x42)
    cpu.hl = 0xa17b     # Negative - Positive result an overflow
    cpu.bc = 0x339f
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x6ddb
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == True
    assert cpu.overflow == True
    assert cpu.zero == False

def test_sbc_hl_de(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, DE
    cpu._machine.write_memory_byte(0x0001, 0x52)
    cpu.hl = 0xabcd     # Negative - negative result no overflow
    cpu.de = 0xef12
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xbcba
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == False
    assert cpu.add_subtract == True
    assert cpu.overflow == False
    assert cpu.zero == False

def test_sbc_hl_hl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, HL
    cpu._machine.write_memory_byte(0x0001, 0x62)
    cpu.hl = 0x4567     # Positive - positive result no overflow
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xffff
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == True
    assert cpu.overflow == False
    assert cpu.zero == False

def test_sbc_hl_hl_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, HL
    cpu._machine.write_memory_byte(0x0001, 0x62)
    cpu.hl = 0x0000     # Zero + zero result no overflow
    cpu.carry = False   # No carry
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == True
    assert cpu.overflow == False
    assert cpu.zero == True

def test_sbc_hl_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, SP
    cpu._machine.write_memory_byte(0x0001, 0x72)
    cpu.hl = 0x4567     # Positive - negative result no overflow
    cpu.sp = 0x89ab
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0xbbbb
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == False
    assert cpu.add_subtract == True
    assert cpu.overflow == False
    assert cpu.zero == False

def test_sbc_hl_sp_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # SBC HL, SP
    cpu._machine.write_memory_byte(0x0001, 0x72)
    cpu.hl = 0x4567     # Positive - negative result no overflow
    cpu.sp = 0x4566
    cpu.carry = True    # Shall be processed
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == True
    assert cpu.add_subtract == True
    assert cpu.overflow == False
    assert cpu.zero == True

def test_add_ix_bc(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # ADD IX, BC
    cpu._machine.write_memory_byte(0x0001, 0x09)
    cpu.ix = 0x1234
    cpu.bc = 0x4567
    cpu.step()
    assert cpu.ix == 0x579B
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.half_carry == False
    assert cpu.add_subtract == False

def test_add_ix_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # ADD IX, IX
    cpu._machine.write_memory_byte(0x0001, 0x29)
    cpu.ix = 0xabcd
    cpu.step()
    assert cpu.ix == 0x579a
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False

def test_add_iy_sp(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # ADD IY, SP
    cpu._machine.write_memory_byte(0x0001, 0x39)
    cpu.iy = 0x5432
    cpu.sp = 0xabce
    cpu.step()
    assert cpu.iy == 0x0000
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.half_carry == True
    assert cpu.add_subtract == False



# Rotate and shift instructions tests

def test_rlca_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x07)    # RLCA
    cpu.a = 0x5a
    cpu.step()
    assert cpu.a == 0xb4
    assert cpu._cycles == 4
    assert cpu._carry == False

def test_rlca_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x07)    # RLCA
    cpu.a = 0xa5
    cpu.step()
    assert cpu.a == 0x4b
    assert cpu._cycles == 4
    assert cpu._carry == True

def test_rlc_d(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RLC D
    cpu._machine.write_memory_byte(0x0001, 0x02)
    cpu.d = 0x5a
    cpu.step()
    assert cpu.d == 0xb4
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == False

def test_rlc_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RLC (HL)
    cpu._machine.write_memory_byte(0x0001, 0x06)
    cpu._machine.write_memory_byte(0xbeef, 0xa5)    # Data byte
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x4b
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False

def test_rrca_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0f)    # RRCA
    cpu.a = 0x5a
    cpu.step()
    assert cpu.a == 0x2d
    assert cpu._cycles == 4
    assert cpu.carry == False

def test_rrca_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x0f)    # RRCA
    cpu.a = 0xa5
    cpu.step()
    assert cpu.a == 0xd2
    assert cpu._cycles == 4
    assert cpu.carry == True

def test_rrc_e(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RRC E
    cpu._machine.write_memory_byte(0x0001, 0x0b)
    cpu.e = 0x5a
    cpu.step()
    assert cpu.e == 0x2d
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False

def test_rrc_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RRC (HL)
    cpu._machine.write_memory_byte(0x0001, 0x0e)
    cpu._machine.write_memory_byte(0xbeef, 0xa5)    # data byte
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0xd2
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == False

def test_rla_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x17)    # RLA
    cpu.a = 0x5a
    cpu.carry = True
    cpu.step()
    assert cpu.a == 0xb5
    assert cpu._cycles == 4
    assert cpu.carry == False

def test_rla_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x17)    # RLA
    cpu.a = 0xa5
    cpu.carry = False
    cpu.step()
    assert cpu.a == 0x4a
    assert cpu._cycles == 4
    assert cpu.carry == True

def test_rla_h(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RL H
    cpu._machine.write_memory_byte(0x0001, 0x14)
    cpu.h = 0x5a
    cpu.carry = True
    cpu.step()
    assert cpu.h == 0xb5
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == False

def test_rla_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RL (HL)
    cpu._machine.write_memory_byte(0x0001, 0x16)
    cpu._machine.write_memory_byte(0xbeef, 0xa5)    # Data byte
    cpu.carry = False
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x4a
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False

def test_rra_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1f)    # RRA
    cpu.a = 0x5a
    cpu.carry = True
    cpu.step()
    assert cpu.a == 0xad
    assert cpu._cycles == 4
    assert cpu.carry == False

def test_rra_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x1f)    # RRA
    cpu.a = 0xa5
    cpu.carry = False
    cpu.step()
    assert cpu.a == 0x52
    assert cpu._cycles == 4
    assert cpu.carry == True

def test_rr_l(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RR L
    cpu._machine.write_memory_byte(0x0001, 0x1d)
    cpu.l = 0x5a
    cpu.carry = True
    cpu.step()
    assert cpu.l == 0xad
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.sign == True
    assert cpu.parity == False

def test_rr_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RR (HL)
    cpu._machine.write_memory_byte(0x0001, 0x1e)
    cpu._machine.write_memory_byte(0xbeef, 0xa5)    # Data byte
    cpu.hl = 0xbeef
    cpu.carry = False
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x52
    assert cpu._cycles == 15
    assert cpu.carry == True
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == False

def test_srl_b(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # SRL B
    cpu._machine.write_memory_byte(0x0001, 0x38)
    cpu.b = 0xaa
    cpu.carry = True
    cpu.step()
    assert cpu.b == 0x55
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True

def test_srl_c_zero(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # SRL C
    cpu._machine.write_memory_byte(0x0001, 0x39)
    cpu.c = 0x01
    cpu.carry = True
    cpu.step()
    assert cpu.c == 0x00
    assert cpu._cycles == 8
    assert cpu.carry == True
    assert cpu.zero == True
    assert cpu.sign == False
    assert cpu.parity == True

def test_srl_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # SRL (HL)
    cpu._machine.write_memory_byte(0x0001, 0x3e)
    cpu._machine.write_memory_byte(0xbeef, 0x42)    # Data byte
    cpu.hl = 0xbeef
    cpu.step()
    assert cpu._machine.read_memory_byte(0xbeef) == 0x21
    assert cpu._cycles == 15
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.sign == False
    assert cpu.parity == True


# Bit instructions tests

def test_cpl(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x2f)    # CPL
    cpu.a = 0x51
    cpu.step()
    assert cpu.a == 0xae
    assert cpu._cycles == 4
    assert cpu.add_subtract == True
    assert cpu.half_carry == True

def test_cpl_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x2f)    # CPL
    cpu.a = 0x51
    cpu.step()
    assert cpu.a == 0xae
    assert cpu._cycles == 4
    assert cpu.add_subtract == True
    assert cpu.half_carry == True

def test_neg_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # NEG
    cpu._machine.write_memory_byte(0x0001, 0x44)
    cpu.a = 0x51
    cpu.step()
    assert cpu.a == 0xaf
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.overflow == False
    assert cpu.add_subtract == True
    assert cpu.half_carry == True

def test_neg_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # NEG
    cpu._machine.write_memory_byte(0x0001, 0x44)
    cpu.a = 0x00
    cpu.step()
    assert cpu.a == 0x00
    assert cpu._cycles == 8
    assert cpu.carry == True
    assert cpu.zero == True
    assert cpu.overflow == False
    assert cpu.add_subtract == True
    assert cpu.half_carry == False

def test_neg_3(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xed)    # NEG
    cpu._machine.write_memory_byte(0x0001, 0x44)
    cpu.a = 0x80
    cpu.step()
    assert cpu.a == 0x80
    assert cpu._cycles == 8
    assert cpu.carry == False
    assert cpu.zero == False
    assert cpu.overflow == True
    assert cpu.add_subtract == True
    assert cpu.half_carry == False

def test_scf(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x37)    # SCF
    cpu.step()
    assert cpu.carry == True
    assert cpu._cycles == 4

def test_ccf_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3f)    # CCF
    cpu._carry = False
    cpu.step()
    assert cpu.carry == True
    assert cpu.half_carry == False
    assert cpu._cycles == 4

def test_ccf_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0x3f)    # CCF
    cpu._carry = True
    cpu.step()
    assert cpu.carry == False
    assert cpu.half_carry == True
    assert cpu._cycles == 4

def test_get_bit_a(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # BIT 3, A
    cpu._machine.write_memory_byte(0x0001, 0x5f)

    cpu.a = 0x08
    cpu.step()

    assert cpu._cycles == 8
    assert cpu.zero == False                        # Bit is set (non-zero)

def test_get_bit_h(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # BIT 5, H
    cpu._machine.write_memory_byte(0x0001, 0x6c)

    cpu.h = 0x42
    cpu.step()

    assert cpu._cycles == 8
    assert cpu.zero == True                         # Bit is not set (zero)

def test_get_bit_mem_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # BIT 7, (HL)
    cpu._machine.write_memory_byte(0x0001, 0x7e)
    cpu._machine.write_memory_byte(0x1234, 0x42)    # Bit 7 is not set
    cpu.hl = 0x1234
    cpu.step()

    assert cpu._cycles == 12
    assert cpu.zero == True                         # Bit is not set (zero)

def test_get_bit_mem_2(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # BIT 7, (HL)
    cpu._machine.write_memory_byte(0x0001, 0x7e)
    cpu._machine.write_memory_byte(0x1234, 0x80)    # Bit 7 is set
    cpu.hl = 0x1234
    cpu.step()

    assert cpu._cycles == 12
    assert cpu.zero == False                         # Bit is set (non-zero)

def test_get_bit_ix_1(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # BIT 3, (IX+42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0x42)    # Positive displacement
    cpu._machine.write_memory_byte(0x0003, 0x5e)    # Get bit 3

    cpu._machine.write_memory_byte(0xbeef + 0x42, 0x08)     # Data bit is set

    cpu.ix = 0xbeef
    cpu.step()

    assert cpu._cycles == 20
    assert cpu.zero == False                        # Bit is set (non-zero)

def test_get_bit_ix_0(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # BIT 3, (IX+42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0x42)    # Positive displacement
    cpu._machine.write_memory_byte(0x0003, 0x5e)    # Get bit 3

    cpu._machine.write_memory_byte(0xbeef + 0x42, 0xf7)     # Data bit is not set

    cpu.ix = 0xbeef
    cpu.step()

    assert cpu._cycles == 20
    assert cpu.zero == True                        # Bit is reset (zero)

def test_set_bit_b(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # SET 2, B
    cpu._machine.write_memory_byte(0x0001, 0xd0)

    cpu.b = 0x42
    cpu.step()

    assert cpu._cycles == 8
    assert cpu.b == 0x46

def test_set_bit_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # BIT 4, (HL)
    cpu._machine.write_memory_byte(0x0001, 0xe6)
    cpu._machine.write_memory_byte(0x1234, 0x24)

    cpu.hl = 0x1234
    cpu.step()

    assert cpu._cycles == 15
    assert cpu._machine.read_memory_byte(0x1234) == 0x34

def test_set_bit_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # SET 3, (IY-42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0xbe)    # Negative displacement (-0x42)
    cpu._machine.write_memory_byte(0x0003, 0x76)    # Get bit 6

    cpu._machine.write_memory_byte(0xbeef - 0x42, 0x40)     # Initial data

    cpu.iy = 0xbeef
    cpu.step()

    assert cpu._cycles == 23
    assert cpu.zero == False                        # Bit is set (non-zero)

def test_set_bit_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # SET 3, (IX+42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0x42)    # Positive displacement
    cpu._machine.write_memory_byte(0x0003, 0xde)    # Set bit 3

    cpu._machine.write_memory_byte(0xbeef + 0x42, 0x11)     # Initial data

    cpu.ix = 0xbeef
    cpu.step()
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0xbeef + 0x42) == 0x19     # Bit 3 is now set

def test_set_bit_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # SET 3, (IY-42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0xbe)    # Negative displacement (-0x42)
    cpu._machine.write_memory_byte(0x0003, 0xf6)    # Set bit 6

    cpu._machine.write_memory_byte(0xbeef - 0x42, 0x11)     # Initial data

    cpu.iy = 0xbeef
    cpu.step()

    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0xbeef - 0x42) == 0x51     # Bit 6 is now set

def test_res_bit_b(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # RES 0, E
    cpu._machine.write_memory_byte(0x0001, 0x83)

    cpu.e = 0x43
    cpu.step()

    assert cpu._cycles == 8
    assert cpu.e == 0x42

def test_res_bit_mem(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xcb)    # BIT 7, (HL)
    cpu._machine.write_memory_byte(0x0001, 0xbe)
    cpu._machine.write_memory_byte(0x1234, 0xab)

    cpu.hl = 0x1234
    cpu.step()

    assert cpu._cycles == 15
    assert cpu._machine.read_memory_byte(0x1234) == 0x2b

def test_res_bit_ix(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xdd)    # RES 3, (IX+42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0x42)    # Positive displacement
    cpu._machine.write_memory_byte(0x0003, 0x9e)    # Reset bit 3

    cpu._machine.write_memory_byte(0xbeef + 0x42, 0x19)     # Initial data

    cpu.ix = 0xbeef
    cpu.step()
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0xbeef + 0x42) == 0x11     # Bit 3 is now reset

def test_res_bit_iy(cpu):
    cpu._machine.write_memory_byte(0x0000, 0xfd)    # RES 3, (IY-42)
    cpu._machine.write_memory_byte(0x0001, 0xcb)
    cpu._machine.write_memory_byte(0x0002, 0xbe)    # Negative displacement (-0x42)
    cpu._machine.write_memory_byte(0x0003, 0xb6)    # Reset bit 6

    cpu._machine.write_memory_byte(0xbeef - 0x42, 0x51)     # Initial data

    cpu.iy = 0xbeef
    cpu.step()
    
    assert cpu._cycles == 23
    assert cpu._machine.read_memory_byte(0xbeef - 0x42) == 0x11     # Bit 6 is now reset
