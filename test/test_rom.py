# To run these tests install pytest, then run this command line:
# py.test -rfeEsxXwa --verbose --showlocals

import pytest
import sys

sys.path.append('../src')

from rom import ROM
from utils import *
from interfaces import MemoryDevice

@pytest.fixture
def rom():
    return MemoryDevice(ROM("../resources/spectrum48.rom"), 0x4000)

def test_addr(rom):
    start, end = rom.get_addr_range()
    assert start == 0x4000
    assert end == 0x7fff

def test_read_byte(rom):
    assert rom.read_byte(0x4042) == 0xb5

def test_read_word(rom):
    assert rom.read_word(0x4242) == 0xb9b3

def test_out_of_addr_range_byte(rom):
    with pytest.raises(MemoryError):
        rom.read_byte(0x1234)
    with pytest.raises(MemoryError):
        rom.read_byte(0x9876)

def test_out_of_addr_range_word(rom):
    with pytest.raises(MemoryError):
        rom.read_word(0x1234)
    with pytest.raises(MemoryError):
        rom.read_word(0x9876)
