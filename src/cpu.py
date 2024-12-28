import logging
from utils import *

logger = logging.getLogger('cpu')

class CPU:
    """
        Zilog Z80 CPU emulator

        This class is responsible for handling CPU registers, emulating CPU instructions, as well as
        handling interrupts.

        The class is intentionally not aware about what I/O devices and memories are connected to the
        CPU. In order to read a byte a real (hardware) CPU would be setting a desired address on the
        address bus, and read the value through the data bus. It is up to a particular machine implementation
        to connect the needed device to the bus. Similar to the hardware, the CPU class is working with
        the Machine object, requesting the memory or I/O data transfer. Devices and memories installed
        in a particular Machine will respond to the request.
    """
    def __init__(self, machine):
        self._machine = machine
        machine.set_cpu(self)

        self.reset()

        # Instructions and execution
        self._cycles = 0
        self._current_inst = 0  # current instruction
        self._instructions = [None] * 0x100
        self.init_instruction_table();
    
        self._registers_logging = False


    def reset(self):
        """
        Resets registers and flags
        """
        self._pc = 0
        self._sp = 0

        # Registers
        self._a = 0     # Accumulator
        self._f = 0     # Flags register
        self._b = 0
        self._c = 0
        self._d = 0
        self._e = 0
        self._h = 0
        self._l = 0

        # Alternate Registers
        self._ax = 0    # Accumulator
        self._fx = 0    # Flags register
        self._bx = 0
        self._cx = 0
        self._dx = 0
        self._ex = 0
        self._hx = 0
        self._lx = 0

        # Index registers
        self._ix = 0
        self._iy = 0

        # Interrupt flags
        self._iff1 = False
        self._iff2 = False


    # Registers

    def _validate_byte_value(self, value):
        assert value >= 0x00 and value <= 0xff

    def _validate_word_value(self, value):
        assert value >= 0x0000 and value <= 0xffff

    def get_pc(self):
        return self._pc
    
    def set_pc(self, value):
        self._validate_word_value(value)
        self._pc = value

    def get_sp(self):
        return self._sp
    
    def set_sp(self, value):
        self._validate_word_value(value)
        self._sp = value

    def get_a(self):
        return self._a
    
    def set_a(self, value):
        self._validate_byte_value(value)
        self._a = value

    def get_f(self):
        return self._f

    def set_f(self, value):
        self._validate_byte_value(value)
        self._f = value

    def get_b(self):
        return self._b
    
    def set_b(self, value):
        self._validate_byte_value(value)
        self._b = value
    
    def get_c(self):
        return self._c
    
    def set_c(self, value):
        self._validate_byte_value(value)
        self._c = value

    def get_d(self):
        return self._d
    
    def set_d(self, value):
        self._validate_byte_value(value)
        self._d = value

    def get_e(self):
        return self._e
    
    def set_e(self, value):
        self._validate_byte_value(value)
        self._e = value

    def get_h(self):
        return self._h
    
    def set_h(self, value):
        self._validate_byte_value(value)
        self._h = value

    def get_l(self):
        return self._l
    
    def set_l(self, value):
        self._validate_byte_value(value)
        self._l = value

    def get_bc(self):
        return (self._b << 8) | self._c
    
    def set_bc(self, value):
        self._validate_word_value(value)
        self._b = value >> 8
        self._c = value & 0xff

    def get_de(self):
        return (self._d << 8) | self._e
    
    def set_de(self, value):
        self._validate_word_value(value)
        self._d = value >> 8
        self._e = value & 0xff

    def get_hl(self):
        return (self._h << 8) | self._l
    
    def set_hl(self, value):
        self._validate_word_value(value)
        self._h = value >> 8
        self._l = value & 0xff

    def get_af(self):
        return (self._a << 8) | self._f
    
    def set_af(self, value):
        self._validate_word_value(value)
        self._a = value >> 8
        self._f = value & 0xff


    def get_ax(self):
        return self._ax
    
    def set_ax(self, value):
        self._validate_byte_value(value)
        self._ax = value

    def get_fx(self):
        return self._fx
    
    def set_fx(self, value):
        self._validate_byte_value(value)
        self._fx = value

    def get_bx(self):
        return self._bx
    
    def set_bx(self, value):
        self._validate_byte_value(value)
        self._bx = value

    def get_cx(self):
        return self._cx
    
    def set_cx(self, value):
        self._validate_byte_value(value)
        self._cx = value

    def get_dx(self):
        return self._dx
    
    def set_dx(self, value):
        self._validate_byte_value(value)
        self._dx = value

    def get_ex(self):
        return self._ex
    
    def set_ex(self, value):
        self._validate_byte_value(value)
        self._ex = value

    def get_hx(self):
        return self._hx
    
    def set_hx(self, value):
        self._validate_byte_value(value)
        self._hx = value

    def get_lx(self):
        return self._lx
    
    def set_lx(self, value):
        self._validate_byte_value(value)
        self._lx = value

    def get_bcx(self):
        return (self._bx << 8) | self._cx
    
    def set_bcx(self, value):
        self._validate_word_value(value)
        self._bx = value >> 8
        self._cx = value & 0xff

    def get_dex(self):
        return (self._dx << 8) | self._ex
    
    def set_dex(self, value):
        self._validate_word_value(value)
        self._dx = value >> 8
        self._ex = value & 0xff

    def get_hlx(self):
        return (self._hx << 8) | self._lx
    
    def set_hlx(self, value):
        self._validate_word_value(value)
        self._hx = value >> 8
        self._lx = value & 0xff

    def get_afx(self):
        return (self._ax << 8) | self._fx
    
    def set_afx(self, value):
        self._validate_word_value(value)
        self._ax = value >> 8
        self._fx = value & 0xff

    def get_ix(self):
        return self._ix
    
    def set_ix(self, value):
        self._validate_word_value(value)
        self._ix = value

    def get_iy(self):
        return self._iy
    
    def set_iy(self, value):
        self._validate_word_value(value)
        self._iy = value

    a = property(get_a, set_a)
    f = property(get_f, set_f)
    b = property(get_b, set_b)
    c = property(get_c, set_c)
    d = property(get_d, set_d)
    e = property(get_e, set_e)
    h = property(get_h, set_h)
    l = property(get_l, set_l)
    bc = property(get_bc, set_bc)
    de = property(get_de, set_de)
    hl = property(get_hl, set_hl)
    af = property(get_af, set_af)

    ax = property(get_ax, set_ax)
    fx = property(get_fx, set_fx)
    bx = property(get_bx, set_bx)
    cx = property(get_cx, set_cx)
    dx = property(get_dx, set_dx)
    ex = property(get_ex, set_ex)
    hx = property(get_hx, set_hx)
    lx = property(get_lx, set_lx)
    bcx = property(get_bcx, set_bcx)
    dex = property(get_dex, set_dex)
    hlx = property(get_hlx, set_hlx)
    afx = property(get_afx, set_afx)

    ix = property(get_ix, set_ix)
    iy = property(get_iy, set_iy)

    sp = property(get_sp, set_sp)
    pc = property(get_pc, set_pc)


    # Flags

    def get_iff1(self):
        return self._iff1

    def set_iff1(self, value):
        self._iff1 = value

    def get_iff2(self):
        return self._iff2

    def set_iff2(self, value):
        self._iff2 = value

    iff1 = property(get_iff1, set_iff1)
    iff2 = property(get_iff2, set_iff2)


    # CPU Memory functions

    def _fetch_next_byte(self):
        data = self._machine.read_memory_byte(self._pc)
        self._pc += 1
        return data


    def _fetch_next_word(self):
        data = self._machine.read_memory_word(self._pc)
        self._pc += 2
        return data


    def _push_to_stack(self, value):
        self._sp -= 2
        self._machine.write_stack(self._sp, value)


    def _pop_from_stack(self):
        value = self._machine.read_stack(self._sp)
        self._sp += 2
        return value


    # Emulation

    def step(self):
        """
        Executes an instruction and updates processor state
        """
        self._current_inst = self._fetch_next_byte()
        instruction = self._instructions[self._current_inst]
        if instruction is not None:
            instruction()
        else:
            raise InvalidInstruction(f"Incorrect OPCODE 0x{self._current_inst:02x} (at addr 0x{(self._pc - 1):04x})")


    # Logging

    def enable_registers_logging(self, value):
        self._registers_logging = value


    def _log_1b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 1
        log_str = f' {addr:04x}  {self._current_inst:02x}         {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:35} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_2b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 2
        param = self._machine.read_memory_byte(self._pc - 1)
        log_str = f' {addr:04x}  {self._current_inst:02x} {param:02x}      {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:35} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_3b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 3
        param1 = self._machine.read_memory_byte(self._pc - 2)
        param2 = self._machine.read_memory_byte(self._pc - 1)

        log_str = f' {addr:04x}  {self._current_inst:02x} {param1:02x} {param2:02x}   {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:35} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)



    # Instructions

    def _nop(self):
        """ Do nothing """
        self._cycles += 4

        self._log_1b_instruction("NOP")


    # Flags and modes instructions

    def _ei(self):
        """ Enable interrupts """
        self._iff1 = True
        self._iff2 = True
        self._cycles += 4

        self._log_1b_instruction("EI")


    def _di(self):
        """ Disable interrupts """
        self._iff1 = False
        self._iff2 = False
        self._cycles += 4

        self._log_1b_instruction("DI")


    # Instruction table

    def init_instruction_table(self):
        self._instructions[0x00] = self._nop
        self._instructions[0x01] = None
        self._instructions[0x02] = None
        self._instructions[0x03] = None
        self._instructions[0x04] = None
        self._instructions[0x05] = None
        self._instructions[0x06] = None
        self._instructions[0x07] = None
        self._instructions[0x08] = None
        self._instructions[0x09] = None
        self._instructions[0x0a] = None
        self._instructions[0x0b] = None
        self._instructions[0x0c] = None
        self._instructions[0x0d] = None
        self._instructions[0x0e] = None
        self._instructions[0x0f] = None

        self._instructions[0x10] = None
        self._instructions[0x11] = None
        self._instructions[0x12] = None
        self._instructions[0x13] = None
        self._instructions[0x14] = None
        self._instructions[0x15] = None
        self._instructions[0x16] = None
        self._instructions[0x17] = None
        self._instructions[0x18] = None
        self._instructions[0x19] = None
        self._instructions[0x1a] = None
        self._instructions[0x1b] = None
        self._instructions[0x1c] = None
        self._instructions[0x1d] = None
        self._instructions[0x1e] = None
        self._instructions[0x1f] = None

        self._instructions[0x20] = None
        self._instructions[0x21] = None
        self._instructions[0x22] = None
        self._instructions[0x23] = None
        self._instructions[0x24] = None
        self._instructions[0x25] = None
        self._instructions[0x26] = None
        self._instructions[0x27] = None
        self._instructions[0x28] = None
        self._instructions[0x29] = None
        self._instructions[0x2a] = None
        self._instructions[0x2b] = None
        self._instructions[0x2c] = None
        self._instructions[0x2d] = None
        self._instructions[0x2e] = None
        self._instructions[0x2f] = None

        self._instructions[0x30] = None
        self._instructions[0x31] = None
        self._instructions[0x32] = None
        self._instructions[0x33] = None
        self._instructions[0x34] = None
        self._instructions[0x35] = None
        self._instructions[0x36] = None
        self._instructions[0x37] = None
        self._instructions[0x38] = None
        self._instructions[0x39] = None
        self._instructions[0x3a] = None
        self._instructions[0x3b] = None
        self._instructions[0x3c] = None
        self._instructions[0x3d] = None
        self._instructions[0x3e] = None
        self._instructions[0x3f] = None

        self._instructions[0x40] = None
        self._instructions[0x41] = None
        self._instructions[0x42] = None
        self._instructions[0x43] = None
        self._instructions[0x44] = None
        self._instructions[0x45] = None
        self._instructions[0x46] = None
        self._instructions[0x47] = None
        self._instructions[0x48] = None
        self._instructions[0x49] = None
        self._instructions[0x4a] = None
        self._instructions[0x4b] = None
        self._instructions[0x4c] = None
        self._instructions[0x4d] = None
        self._instructions[0x4e] = None
        self._instructions[0x4f] = None

        self._instructions[0x50] = None
        self._instructions[0x51] = None
        self._instructions[0x52] = None
        self._instructions[0x53] = None
        self._instructions[0x54] = None
        self._instructions[0x55] = None
        self._instructions[0x56] = None
        self._instructions[0x57] = None
        self._instructions[0x58] = None
        self._instructions[0x59] = None
        self._instructions[0x5a] = None
        self._instructions[0x5b] = None
        self._instructions[0x5c] = None
        self._instructions[0x5d] = None
        self._instructions[0x5e] = None
        self._instructions[0x5f] = None

        self._instructions[0x60] = None
        self._instructions[0x61] = None
        self._instructions[0x62] = None
        self._instructions[0x63] = None
        self._instructions[0x64] = None
        self._instructions[0x65] = None
        self._instructions[0x66] = None
        self._instructions[0x67] = None
        self._instructions[0x68] = None
        self._instructions[0x69] = None
        self._instructions[0x6a] = None
        self._instructions[0x6b] = None
        self._instructions[0x6c] = None
        self._instructions[0x6d] = None
        self._instructions[0x6e] = None
        self._instructions[0x6f] = None

        self._instructions[0x70] = None
        self._instructions[0x71] = None
        self._instructions[0x72] = None
        self._instructions[0x73] = None
        self._instructions[0x74] = None
        self._instructions[0x75] = None
        self._instructions[0x76] = None
        self._instructions[0x77] = None
        self._instructions[0x78] = None
        self._instructions[0x79] = None
        self._instructions[0x7a] = None
        self._instructions[0x7b] = None
        self._instructions[0x7c] = None
        self._instructions[0x7d] = None
        self._instructions[0x7e] = None
        self._instructions[0x7f] = None

        self._instructions[0x80] = None
        self._instructions[0x81] = None
        self._instructions[0x82] = None
        self._instructions[0x83] = None
        self._instructions[0x84] = None
        self._instructions[0x85] = None
        self._instructions[0x86] = None
        self._instructions[0x87] = None
        self._instructions[0x88] = None
        self._instructions[0x89] = None
        self._instructions[0x8a] = None
        self._instructions[0x8b] = None
        self._instructions[0x8c] = None
        self._instructions[0x8d] = None
        self._instructions[0x8e] = None
        self._instructions[0x8f] = None

        self._instructions[0x90] = None
        self._instructions[0x91] = None
        self._instructions[0x92] = None
        self._instructions[0x93] = None
        self._instructions[0x94] = None
        self._instructions[0x95] = None
        self._instructions[0x96] = None
        self._instructions[0x97] = None
        self._instructions[0x98] = None
        self._instructions[0x99] = None
        self._instructions[0x9a] = None
        self._instructions[0x9b] = None
        self._instructions[0x9c] = None
        self._instructions[0x9d] = None
        self._instructions[0x9e] = None
        self._instructions[0x9f] = None

        self._instructions[0xa0] = None
        self._instructions[0xa1] = None
        self._instructions[0xa2] = None
        self._instructions[0xa3] = None
        self._instructions[0xa4] = None
        self._instructions[0xa5] = None
        self._instructions[0xa6] = None
        self._instructions[0xa7] = None
        self._instructions[0xa8] = None
        self._instructions[0xa9] = None
        self._instructions[0xaa] = None
        self._instructions[0xab] = None
        self._instructions[0xac] = None
        self._instructions[0xad] = None
        self._instructions[0xae] = None
        self._instructions[0xaf] = None

        self._instructions[0xb0] = None
        self._instructions[0xb1] = None
        self._instructions[0xb2] = None
        self._instructions[0xb3] = None
        self._instructions[0xb4] = None
        self._instructions[0xb5] = None
        self._instructions[0xb6] = None
        self._instructions[0xb7] = None
        self._instructions[0xb8] = None
        self._instructions[0xb9] = None
        self._instructions[0xba] = None
        self._instructions[0xbb] = None
        self._instructions[0xbc] = None
        self._instructions[0xbd] = None
        self._instructions[0xbe] = None
        self._instructions[0xbf] = None

        self._instructions[0xc0] = None
        self._instructions[0xc1] = None
        self._instructions[0xc2] = None
        self._instructions[0xc3] = None
        self._instructions[0xc4] = None
        self._instructions[0xc5] = None
        self._instructions[0xc6] = None
        self._instructions[0xc7] = None
        self._instructions[0xc8] = None
        self._instructions[0xc9] = None
        self._instructions[0xca] = None
        self._instructions[0xcb] = None
        self._instructions[0xcc] = None
        self._instructions[0xcd] = None
        self._instructions[0xce] = None
        self._instructions[0xcf] = None

        self._instructions[0xd0] = None
        self._instructions[0xd1] = None
        self._instructions[0xd2] = None
        self._instructions[0xd3] = None
        self._instructions[0xd4] = None
        self._instructions[0xd5] = None
        self._instructions[0xd6] = None
        self._instructions[0xd7] = None
        self._instructions[0xd8] = None
        self._instructions[0xd9] = None
        self._instructions[0xda] = None
        self._instructions[0xdb] = None
        self._instructions[0xdc] = None
        self._instructions[0xdd] = None
        self._instructions[0xde] = None
        self._instructions[0xdf] = None

        self._instructions[0xe0] = None
        self._instructions[0xe1] = None
        self._instructions[0xe2] = None
        self._instructions[0xe3] = None
        self._instructions[0xe4] = None
        self._instructions[0xe5] = None
        self._instructions[0xe6] = None
        self._instructions[0xe7] = None
        self._instructions[0xe8] = None
        self._instructions[0xe9] = None
        self._instructions[0xea] = None
        self._instructions[0xeb] = None
        self._instructions[0xec] = None
        self._instructions[0xed] = None
        self._instructions[0xee] = None
        self._instructions[0xef] = None

        self._instructions[0xf0] = None
        self._instructions[0xf1] = None
        self._instructions[0xf2] = None
        self._instructions[0xf3] = self._di
        self._instructions[0xf4] = None
        self._instructions[0xf5] = None
        self._instructions[0xf6] = None
        self._instructions[0xf7] = None
        self._instructions[0xf8] = None
        self._instructions[0xf9] = None
        self._instructions[0xfa] = None
        self._instructions[0xfb] = self._ei
        self._instructions[0xfc] = None
        self._instructions[0xfd] = None
        self._instructions[0xfe] = None
        self._instructions[0xff] = None
