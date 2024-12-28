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



# Instructions tests

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
