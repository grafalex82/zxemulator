# To run these tests install pytest, then run this command line:
# py.test -rfeEsxXwa --verbose --showlocals

import pytest
import sys

sys.path.append('../src')

from cpu import CPU

@pytest.fixture
def cpu():
    return CPU(None) 

def test_reset_values(cpu):
    assert cpu.a == 0x00
    assert cpu.f == 0x00
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
