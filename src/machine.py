import logging
from utils import *

CPU_FREQ = 3500000  # 3.5 MHz
FRAME_FREQ = 50     # 50 Hz
TICKS_PER_FRAME = CPU_FREQ // FRAME_FREQ

logger = logging.getLogger('machine')

class MemoryMgr:
    def __init__(self):
        self._memories = []

    def add_memory(self, memory):
        startaddr, endaddr = memory.get_addr_range()
        self._memories.append((startaddr, endaddr, memory))

    def get_memory_for_addr(self, addr):
        for mem in self._memories:
            if addr >= mem[0] and addr <= mem[1]:
                return mem[2]
        return None

    def update(self):
        for mem in self._memories:
            mem[2].update()



class Machine:
    """
        Machine class emulates everything related to electrical connectivity within 
        the computer in a specific configuration. It handles all the relationships
        between the components, such as memories, I/O devices, and other devices
        not logically connected, but still a part of the system.    
    """
    def __init__(self):
        self._memories = MemoryMgr()
        self._io = {}
        self._other = []
        self._cpu = None
        self._strict = False

    def set_strict_validation(self, strict = False):
        self._strict = strict

    def set_cpu(self, cpu):
        self._cpu = cpu

    def add_memory(self, memory):
        self._memories.add_memory(memory)

    def add_io(self, io):
        start, end = io.get_addr_range()
        for addr in range(start, end+1):
            self._io[addr] = io

    def add_other_device(self, device):
        self._other.append(device)

    def update(self):
        """ 
        Updates the state of all devices in the system, allowing them to 
        act on a time-based manner
        """
        self._memories.update()

        for _, io in self._io.items():
            io.update()

        for dev in self._other:
            dev.update()

    def _get_memory(self, addr):
        mem = self._memories.get_memory_for_addr(addr)
        if not mem:
            msg = f"No memory registered for address 0x{addr:04x}"
            if self._strict:
                raise MemoryError(msg)
            else:
                logger.debug(msg)
        return mem

    def _get_io(self, addr):
        io = self._io.get(addr, None)
        if not io:
            msg = f"No IO registered for address 0x{addr:02x}"
            if self._strict:
                raise IOError(msg)
            else:
                logger.debug(msg)
        return io
        
    def reset(self):
        # Only CPU is reset during the machine reset
        # Memory data will survive
        self._cpu.reset()

    def read_memory_byte(self, addr):
        mem = self._get_memory(addr)
        if not mem:
            return 0xff
        return mem.read_byte(addr)

    def read_memory_word(self, addr):
        mem = self._get_memory(addr)
        if not mem:
            return 0xffff
        return mem.read_word(addr)

    def write_memory_byte(self, addr, value):
        mem = self._get_memory(addr)
        if mem:
            mem.write_byte(addr, value)

    def write_memory_word(self, addr, value):
        mem = self._get_memory(addr)
        if mem:
            mem.write_word(addr, value)

    def read_io(self, addr, extra_addr):
        io = self._get_io(addr)
        if not io:
            return 0xff
        return io.read_io(addr, extra_addr)
        
    def write_io(self, addr, extra_addr, value):
        io = self._get_io(addr)
        if io:
            io.write_io(addr, extra_addr, value)

    def schedule_interrupt(self):
        # Typically external devices may request an interrupt by asserting the INT line of the CPU.
        # Depending on the interrupt mode, the CPU may request additional data from the external device:
        # - In Mode 0, the CPU expects the device to provide a CPU instruction on the data bus
        # - In Mode 2, the CPU expects the device to provide a vector number on the data bus
        # 
        # In the Mode 1, though, the CPU does not request additional data, and execute a RST 38 instruction.
        # 
        # Regardless of the mode this function schedules a CPU interrupt, and supply it with interrupt data.
        self._cpu.schedule_interrupt([0xff])


    def get_time(self):
        return self._cpu._cycles / CPU_FREQ

