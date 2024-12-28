from utils import *

"""
    Depending on a particular HW configuration, same peripheral may be connected to a memory
    data lines, or as an I/O device. In some advanced cases devices or blocks of RAM may be
    re-condifured in runtime, and connected/disconnected to a particular address space. 

    The 2 classes in this module (IODevice and MemoryDevice) are the adapters responsible to
    assign a peripheral with a particular I/O or memory address. The peripheral class is not 
    obligated to implement a specific interface, but per duck-typing principle shall expose one
    or more of the following functions:
    - read_byte
    - read_word
    - write_byte
    - write_word

    Byte operations are typically implemented by a peripheral devices, while word operation type
    is mostly related to memory-type devices.
"""

class IODevice:
    """
        IODevice class binds a device with a particular I/O port. This class is responsible to
        translate I/O port read and write requests to the provided device object. The device class
        must expose read_byte() and/or write_byte() function.
    """
    def __init__(self, device, startaddr, endaddr=None, invertaddr=False):
        self._device = device
        self._iostartaddr = startaddr
        self._invert = invertaddr

        if endaddr:
            self._ioendaddr = endaddr
            device.set_size(endaddr - startaddr + 1)
        elif hasattr(device, "get_size"):
            self._ioendaddr = startaddr + device.get_size() - 1
        else:
            self._ioendaddr = startaddr


    def get_addr_range(self):
        return self._iostartaddr, self._ioendaddr


    def validate_io_addr(self, addr):
        if addr < self._iostartaddr or addr > self._ioendaddr:
            raise IOError(f"Incorrect IO address {addr:x}")


    def _get_offset(self, addr):
        self.validate_io_addr(addr)
        if not self._invert:
            return addr - self._iostartaddr
        else:
            return self._ioendaddr - addr

    def read_io(self, addr):
        return self._device.read_byte(self._get_offset(addr))


    def write_io(self, addr, value):
        self._device.write_byte(self._get_offset(addr), value)


    def update(self):
        pass



class MemoryDevice:
    """
        MemoryDevice class binds the peripheral with a particular memory address (or the
        address range). This class is responsible to translate memory address read and write
        requests to the provided device object. 
        
        Depending on the device type, it exposes one or more read/write functions:
        - read_byte
        - read_word
        - write_byte
        - write_word

        Typically all memory type devices connected to the Machine via memory read/write lines. 
        The CPU will reach the memory device for fetching instructions, read and write data (incl
        for stack operations). The byte and word functions are typically used by CPU to read or
        write the data, while burst functions mimic DMA transfer.
    """
    def __init__(self, device, startaddr, endaddr=None):
        self._device = device
        self._startaddr = startaddr

        if endaddr:
            self._endaddr = endaddr
            device.set_size(endaddr - startaddr + 1)
        else:
            self._endaddr = startaddr + device.get_size() - 1


    def get_addr_range(self):
        return self._startaddr, self._endaddr


    def validate_addr(self, addr):
        if addr < self._startaddr or addr > self._endaddr:
            raise MemoryError(f"Address 0x{addr:04x} is out of memory range 0x{self._startaddr:04x}-0x{self._endaddr:04x}")


    def read_byte(self, addr):
        self.validate_addr(addr)
        if not hasattr(self._device, "read_byte"):
            raise MemoryError(f"Reading byte at address 0x{addr:04x} is not supported")
        return self._device.read_byte(addr - self._startaddr)


    def read_word(self, addr):
        self.validate_addr(addr)
        if not hasattr(self._device, "read_word"):
            raise MemoryError(f"Reading word at address 0x{addr:04x} is not supported")
        return self._device.read_word(addr - self._startaddr)


    def write_byte(self, addr, value):
        self.validate_addr(addr)
        if not hasattr(self._device, "write_byte"):
            raise MemoryError(f"Writing byte ataddress 0x{addr:04x} is not supported")
        self._device.write_byte(addr - self._startaddr, value)


    def write_word(self, addr, value):
        self.validate_addr(addr)
        if not hasattr(self._device, "write_word"):
            raise MemoryError(f"Writing word at address 0x{addr:04x} is not supported")
        self._device.write_word(addr - self._startaddr, value)


    def update(self):
        pass
