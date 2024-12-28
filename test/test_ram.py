# To run these tests install pytest, then run this command line:
# py.test -rfeEsxXwa --verbose --showlocals

import pytest
import sys

sys.path.append('../src')

from ram import RAM
from interfaces import MemoryDevice
from utils import *

@pytest.fixture
def ram():
    return MemoryDevice(RAM(), 0x0000, 0xffff)

def test_create_by_size():
    ram = RAM(0x1000)
    device = MemoryDevice(ram, 0x2000)
    start, end = device.get_addr_range()
    assert start == 0x2000
    assert end == 0x2fff

def test_addr(ram):
    start, end = ram.get_addr_range()
    assert start == 0x0000
    assert end == 0xffff

def test_read_default_byte(ram):
    assert ram.read_byte(0x1234) == 0x00

def test_write_read_byte(ram):
    ram.write_byte(0x1234, 0x42)
    assert ram.read_byte(0x1234) == 0x42

def test_write_read_word(ram):
    ram.write_word(0x1234, 0xbeef)
    assert ram.read_word(0x1234) == 0xbeef

def test_write_read_word2(ram):
    ram.write_word(0x1234, 0xbeef)
    assert ram.read_byte(0x1234) == 0xef
    assert ram.read_byte(0x1235) == 0xbe

def test_out_of_byte_range_value(ram):
    with pytest.raises(ValueError):
        ram.write_byte(0x1234, 0xbeef)

def test_out_of_word_range_value(ram):
    with pytest.raises(ValueError):
        ram.write_word(0x1234, 0xbeef42)

def test_out_of_addr_range_byte():
    ram = MemoryDevice(RAM(), 0x5000, 0x5fff)
    with pytest.raises(MemoryError):
        ram.write_byte(0x1234, 0x42)
    with pytest.raises(MemoryError):
        ram.write_byte(0x6789, 0x42)
    with pytest.raises(MemoryError):
        ram.read_byte(0x1234)
    with pytest.raises(MemoryError):
        ram.read_byte(0x6789)

def test_out_of_addr_range_word():
    ram = MemoryDevice(RAM(), 0x5000, 0x5fff)
    with pytest.raises(MemoryError):
        ram.write_word(0x1234, 0xbeef)
    with pytest.raises(MemoryError):
        ram.write_word(0x6789, 0xbeef)
    with pytest.raises(MemoryError):
        ram.read_word(0x1234)
    with pytest.raises(MemoryError):
        ram.read_word(0x6789)