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
        self._instruction_prefix = None
        self._current_inst = 0              # current instruction
        self._displacement = 0              # Parsed displacement for IX- and IY-based operations

        self._init_instruction_table()       # Main instruction set
        self._init_ed_instruction_table()    # Additional instruction set
        self._init_cb_instruction_table()    # Bit instructions
        self._init_dd_instruction_table()    # IX instructions
        self._init_ddcb_instruction_table()  # IX bit instructions
        self._init_fd_instruction_table()    # IY instructions
        self._init_fdcb_instruction_table()  # IY bit instructions
    
        self._registers_logging = False


    def reset(self):
        """
        Resets registers and flags
        """
        self._pc = 0
        self._sp = 0

        # Registers
        self._a = 0     # Accumulator
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

        # Special purpose registers
        self._i = 0
        self._r = 0

        # Interrupt flags
        self._iff1 = False
        self._iff2 = False
        self._interrupt_mode = 0    # Not really a register, but rather a selected interrupt mode
        self._interrupt_instructions = []

        # ALU Flags
        self._sign = False                      # Bit 7
        self._zero = False                      # Bit 6
        self._half_carry = False                # Bit 4
        self._parity_overflow = False           # Bit 2
        self._add_subtract = False              # Bit 1
        self._carry = False                     # Bit 0


    def schedule_interrupt(self, instructions):
        """
        Trigger the interrupt execution.
        
        For Mode 0 (aka Intel 8080 mode):
        Typically an interrupt controller will aquire the data bus, and feed the
        CPU up to 3 instructions. This function allows emulating this behavior by
        adding passed instructions to the instruction fetch queue.

        this function will simply remember data bytes that would be requested by the 
        processor during the interrupt handling. these instructions will be fetched by the CPU during the next
        instruction fetch cycle via _fetch* functions.

        For Modes 1:
        Processor will generate an RST 38 instruction

        For Mode 2:
        Processor will fetch an interrupt ID from the bus. This function will save interrupt ID to be processed
        by the step() function
        """
        # do not even schedule an interrupt if interrupts are disabled
        if not self._iff1:
            return

        logger.debug(f"Scheduling an interrupt in mode {self._interrupt_mode}")
        match self._interrupt_mode:
            case 0:
                logger.debug(f"Scheduling instructions {instructions}")
                self._interrupt_instructions = instructions
            case 1:
                logger.debug("Simulating RST 38 instruction")
                self._interrupt_instructions = [0xff]  # RST 38
            case 2:
                vector_addr = self._i << 8 | (instructions[0] & 0xfe)
                handler_addr = self._machine.read_memory_word(vector_addr)
                logger.debug(f"Interrupt vector addr {vector_addr:04x}. Simulating CALL {handler_addr:04x} instruction")
                self._interrupt_instructions = [0xcd, handler_addr & 0xff, handler_addr >> 8]
            case _:
                raise InvalidInstruction(f"Invalid interrupt mode: {self._interrupt_mode}")


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
        flags = 0
        if self._sign: flags = set_bit(flags, 7)
        if self._zero: flags = set_bit(flags, 6)
        if self._half_carry: flags = set_bit(flags, 4)
        if self._parity_overflow: flags = set_bit(flags, 2)
        if self._add_subtract: flags = set_bit(flags, 1)
        if self._carry: flags = set_bit(flags, 0)
        return flags

    def set_f(self, value):
        self._validate_byte_value(value)
        self._sign = is_bit_set(value, 7)
        self._zero = is_bit_set(value, 6)
        self._half_carry = is_bit_set(value, 4)
        self._parity_overflow = is_bit_set(value, 2)
        self._add_subtract = is_bit_set(value, 1)
        self._carry = is_bit_set(value, 0)

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
        return (self._a << 8) | self.f
    
    def set_af(self, value):
        self._validate_word_value(value)
        self._a = value >> 8
        self.f = value & 0xff


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

    def get_i(self):
        return self._i
    
    def set_i(self, value):
        self._validate_byte_value(value)
        self._i = value

    def get_r(self):
        return self._r
    
    def set_r(self, value):
        self._validate_byte_value(value)
        self._r = value


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

    i = property(get_i, set_i)
    r = property(get_r, set_r)

    sp = property(get_sp, set_sp)
    pc = property(get_pc, set_pc)


    # Register internal access

    def _get_register(self, reg_idx):
        if reg_idx == 0:
            return self._b
        if reg_idx == 1:
            return self._c
        if reg_idx == 2:
            return self._d
        if reg_idx == 3:
            return self._e
        if reg_idx == 4:
            return self._h
        if reg_idx == 5:
            return self._l
        if reg_idx == 6:
            return self._machine.read_memory_byte(self.hl)
        if reg_idx == 7:
            return self._a

    def _set_register(self, reg_idx, value):
        assert value >= 0x00 and value <= 0xff
        if reg_idx == 0:
            self._b = value
        if reg_idx == 1:
            self._c = value
        if reg_idx == 2:
            self._d = value
        if reg_idx == 3:
            self._e = value
        if reg_idx == 4:
            self._h = value
        if reg_idx == 5:
            self._l = value
        if reg_idx == 6:
            self._machine.write_memory_byte(self.hl, value)
        if reg_idx == 7:
            self._a = value

    def _reg_symb(self, reg_idx):
        return ["B", "C", "D", "E", "H", "L", "(HL)", "A"][reg_idx]

    def _set_register_pair(self, reg_pair, value):
        if reg_pair == 0:
            self.bc = value
        if reg_pair == 1:
            self.de = value
        if reg_pair == 2:
            self.hl = value
        if reg_pair == 3:
            self.sp = value

    def _get_register_pair(self, reg_pair):
        if reg_pair == 0:
            return self.bc
        if reg_pair == 1:
            return self.de
        if reg_pair == 2:
            return self.hl
        if reg_pair == 3:
            return self.sp

    def _reg_pair_symb(self, reg_pair):
        return ["BC", "DE", "HL", "SP"][reg_pair]


    def _get_index_reg(self):
        prefix = self._instruction_prefix if self._instruction_prefix < 0x100 else self._instruction_prefix >> 8
        return self._ix if prefix == 0xdd else self._iy

    def _get_index_reg_symb(self):
        prefix = self._instruction_prefix if self._instruction_prefix < 0x100 else self._instruction_prefix >> 8
        return "IX" if prefix == 0xdd else "IY"


    # ALU flags

    def get_sign(self):
        return self._sign
        
    def set_sign(self, value):
        self._sign = value

    def get_zero(self):
        return self._zero
    
    def set_zero(self, value):
        self._zero = value

    def get_half_carry(self):
        return self._half_carry
    
    def set_half_carry(self, value):
        self._half_carry = value

    def get_parity(self):
        return self._parity_overflow

    def set_parity(self, value):
        self._parity_overflow = value

    def get_add_subtract(self):
        return self._add_subtract
    
    def set_add_subtract(self, value):
        self._add_subtract = value

    def get_carry(self):
        return self._carry

    def set_carry(self, value):
        self._carry = value

    sign = property(get_sign, set_sign)
    zero = property(get_zero, set_zero)
    half_carry = property(get_half_carry, set_half_carry)
    parity = property(get_parity, set_parity)
    overflow = property(get_parity, set_parity)     # Overflow flag shares the same bit as parity
    add_subtract = property(get_add_subtract, set_add_subtract)
    carry = property(get_carry, set_carry)

    # Interrupt Flags

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
        if self._iff1 and self._interrupt_instructions:
            data = self._interrupt_instructions[0]
            del self._interrupt_instructions[0]
        else:
            data = self._machine.read_memory_byte(self._pc)
            self._pc += 1
        return data


    def _fetch_next_word(self):
        if self._iff1 and self._interrupt_instructions:
            if len(self._interrupt_instructions) < 2:
                raise InvalidInstruction(f"Insufficient interrupt instructions (expecting 2, only 1 given)")            
            data = self._interrupt_instructions[0] | (self._interrupt_instructions[1] << 8)
            del self._interrupt_instructions[0]
            del self._interrupt_instructions[0]
        else:
            data = self._machine.read_memory_word(self._pc)
            self._pc += 2
        return data


    def _fetch_displacement(self):
        data = self._machine.read_memory_byte(self._pc)
        self._pc += 1
        if data >= 0x80:
            return data - 0x100
        return data


    def _push_to_stack(self, value):
        self._sp -= 2
        self._machine.write_memory_word(self._sp, value)


    def _pop_from_stack(self):
        value = self._machine.read_memory_word(self._sp)
        self._sp += 2
        return value


    # Emulation
    def step(self):
        """
        Executes an instruction and updates processor state
        """
        # Fetch the next instruction, and parse prefix bytes if needed
        pc = self._pc
        b = self._fetch_next_byte()
        if b in [0xed, 0xcb, 0xdd, 0xfd]:
            self._instruction_prefix = b
            self._current_inst = self._fetch_next_byte()

            # Handle double prefixes such as 0xDDCB and 0xFDCB
            # In these instructions3rd byte is a displacement, and 4th byte is the opcode
            if self._current_inst == 0xcb:
                self._instruction_prefix <<= 8
                self._instruction_prefix |= self._current_inst
                self._displacement = self._fetch_displacement()
                self._current_inst = self._fetch_next_byte()
        else:
            self._instruction_prefix = None
            self._current_inst = b

        # Depending on instruction prefix, select the correct instruction table
        match self._instruction_prefix:
            case 0xed:
                instruction = self._instructions_0xed[self._current_inst]
            case 0xcb:
                instruction = self._instructions_0xcb[self._current_inst]
            case 0xdd:
                instruction = self._instructions_0xdd[self._current_inst]
            case 0xddcb:
                instruction = self._instructions_0xddcb[self._current_inst]
            case 0xfd:
                instruction = self._instructions_0xfd[self._current_inst]
            case 0xfdcb:
                instruction = self._instructions_0xfdcb[self._current_inst]
            case _:
                instruction = self._instructions[self._current_inst]

        # Execute the instruction
        if instruction is not None:
            instruction()
        else:
            if self._instruction_prefix == None:
                prefix = ""
            elif self._instruction_prefix >= 0x100:
                h = self._instruction_prefix >> 8
                l = self._instruction_prefix & 0xff
                prefix = f"{h:02x} {l:02x} {self._displacement:02x} "
            else:
                prefix = f"{self._instruction_prefix:02x} "
            raise InvalidInstruction(f"Incorrect OPCODE {prefix}{self._current_inst:02x} (at addr 0x{pc:04x})")


    # Logging

    def enable_registers_logging(self, value):
        self._registers_logging = value

    def _get_cpu_state_str(self):
        res = f"A={self._a:02x} BC={self.bc:04x} DE={self.de:04x} "
        res += f"HL={self.hl:04x} SP={self._sp:04x} IX={self.ix:04x} IY={self.iy:04x} "
        res += f"AFx={self.afx:04x} BCx={self.bcx:04x} DEx={self.dex:04x} HLx={self.hlx:04x} "
        res += f"I={self._i:02x} R={self._r:02x} "
        res += f"{'Z' if self._zero else '-'}"
        res += f"{'S' if self._sign else '-'}"
        res += f"{'C' if self._carry else '-'}"
        res += f"{'H' if self._half_carry else '-'}"
        res += f"{'P' if self._parity_overflow else '-'}"
        res += f"{'N' if self._add_subtract else '-'}"
        res += f"{'I' if self._iff1 else '-'}"
        return res


    def _prepare_log_prefix(self):
        if self._instruction_prefix == None:
            return "  "

        if self._instruction_prefix >= 0x100:
            return f"{(self._instruction_prefix >> 8):02x}"

        return f"{self._instruction_prefix:02x}"


    def _log_1b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 1
        if self._instruction_prefix:
            addr -= 1
        log_str = f' {addr:04x}  {self._prepare_log_prefix()} {self._current_inst:02x}         {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_2b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 2
        if self._instruction_prefix:
            addr -= 1
        param = self._machine.read_memory_byte(self._pc - 1)
        log_str = f' {addr:04x}  {self._prepare_log_prefix()} {self._current_inst:02x} {param:02x}      {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_3b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 3
        if self._instruction_prefix:
            addr -= 1
        param1 = self._machine.read_memory_byte(self._pc - 2)
        param2 = self._machine.read_memory_byte(self._pc - 1)
        log_str = f' {addr:04x}  {self._prepare_log_prefix()} {self._current_inst:02x} {param1:02x} {param2:02x}   {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_3b_bit_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 4
        log_str = f' {addr:04x}  {self._instruction_prefix >> 8:02x} {(self._instruction_prefix & 0xff):02x} {self._displacement:02x} {self._current_inst:02x}   {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)



    # CPU control instructions

    def _nop(self):
        """ Do nothing """
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("NOP")


    def _ei(self):
        """ Enable interrupts """
        # TODO: As per the datasheet, the EI instruction is delayed by one instruction to let the interrupt
        # routine execute RET instruction before the next interrupt

        self._iff1 = True
        self._iff2 = True
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("EI")


    def _di(self):
        """ Disable interrupts """
        self._iff1 = False
        self._iff2 = False
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("DI")


    def _im(self):
        """ Set Interrupt Mode """
        mode = (self._current_inst & 0x18) >> 3
        self._interrupt_mode = mode - 1 if mode != 0 else 0     # Opcode 0x46 -> mode 0, 0x56 -> mode 1, 0x5e -> mode 2

        self._cycles += 8

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"IM {self._interrupt_mode}")


    def _in(self):
        """ IO Input """
        addr = self._fetch_next_byte()

        self._a = self._machine.read_io(addr)
        self._cycles += 11

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"IN A, {addr:02x}")


    def _out(self):
        """ IO Output """
        addr = self._fetch_next_byte()

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"OUT {addr:02x}, A")

        self._machine.write_io(addr, self._a)
        self._cycles += 11



    # 8-bit data transfer instructions

    def _load_reg8_to_reg8(self):
        """ Move a byte between 2 registers """
        dst = (self._current_inst & 0x38) >> 3
        src = self._current_inst & 0x07
        value = self._get_register(src)
        self._set_register(dst, value)

        self._cycles += 4
        if src == 6 or dst == 6:
            self._cycles += 3

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"LD {self._reg_symb(dst)}, {self._reg_symb(src)}")


    def _load_reg8_immediate(self):
        """ Load 8-bit register from immediate argument """
        reg = (self._current_inst & 0x38) >> 3
        value = self._fetch_next_byte()
        self._set_register(reg, value)
        self._cycles += (7 if reg != 6 else 10)

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"LD {self._reg_symb(reg)}, {value:02x}")


    def _load_a_from_i_r_registers(self):
        """ Load accumulator from I or R registers """
        self._a = self._r if (self._current_inst & 0x08) else self._i

        self._cycles += 9

        if logger.level <= logging.DEBUG:
            reg_symb = "R" if (self._current_inst & 0x08) else "I"
            self._log_1b_instruction(f"LD A, {reg_symb}")


    def _load_i_r_register_from_a(self):
        """ Load I or R register from accumulator """
        if self._current_inst & 0x08:
            self._r = self._a
        else:
            self._i = self._a

        self._cycles += 9

        if logger.level <= logging.DEBUG:
            reg_symb = "R" if (self._current_inst & 0x08) else "I"
            self._log_1b_instruction(f"LD {reg_symb}, A")


    def _store_a_to_mem(self):
        """ Store accumulator to memory pointed by immediate argument """
        addr = self._fetch_next_word()
        self._machine.write_memory_byte(addr, self._a)
        self._cycles += 13

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD ({addr:04x}), A")


    def _load_a_from_mem(self):
        """ Load accumulator from memory pointed by immediate argument """
        addr = self._fetch_next_word()
        self._a = self._machine.read_memory_byte(addr)
        self._cycles += 13

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD A, ({addr:04x})")


    def _store_reg_to_indexed_mem(self):
        """ Store a 8-bit register to a memory indexed by IX/IY registers """
        displacement = self._fetch_displacement()
        src = self._current_inst & 0x07
        addr = self._get_index_reg() + displacement
        value = self._get_register(src)
        self._machine.write_memory_byte(addr, value)

        self._cycles += 19

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"LD ({self._get_index_reg_symb()}{displacement:+03x}), {self._reg_symb(src)}")


    def _load_reg_from_indexed_mem(self):
        """ Load a 8-bit register from a memory indexed by IX/IY registers """
        displacement = self._fetch_displacement()
        dst = (self._current_inst & 0x38) >> 3
        addr = self._get_index_reg() + displacement
        value = self._machine.read_memory_byte(addr)
        self._set_register(dst, value)

        self._cycles += 19

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"LD {self._reg_symb(dst)}, ({self._get_index_reg_symb()}{displacement:+03x})")


    def _store_value_to_indexed_mem(self):
        """ Store immediate 8-bit value to memory indexed by IX/IY registers """
        displacement = self._fetch_displacement()
        value = self._fetch_next_byte()

        addr = self._get_index_reg() + displacement
        self._machine.write_memory_byte(addr, value)

        self._cycles += 19

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD ({self._get_index_reg_symb()}{displacement:+03x}), {value:02x}")



    # 16-bit data transfer instructions

    def _ld_a_mem_regpair(self):
        """ Load accumulator from memory pointed by a regpair """
        reg_pair = (self._current_inst & 0x10) >> 4
        addr = self._get_register_pair(reg_pair)
        self._a = self._machine.read_memory_byte(addr)
        self._cycles += 7

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"LD A, ({self._reg_pair_symb(reg_pair)})")


    def _ld_mem_regpair_a(self):
        """ Store accumulator to memory pointed by a regpair """
        reg_pair = (self._current_inst & 0x10) >> 4
        addr = self._get_register_pair(reg_pair)
        self._machine.write_memory_byte(addr, self._a)
        self._cycles += 7

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"LD ({self._reg_pair_symb(reg_pair)}), A")


    def _load_immediate_16b(self):
        """ Load register pair with immediate value"""
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._fetch_next_word()
        if reg_pair == 3:
            self._sp = value
        else: 
            self._set_register_pair(reg_pair, value)
        self._cycles += 10

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD {self._reg_pair_symb(reg_pair)}, {value:04x}")


    def _load_iy_immediate(self):
        """ Load IY register with immediate value"""
        value = self._fetch_next_word()
        self._iy = value
        self._cycles += 14

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD IY, {value:04x}")


    def _store_hl_to_memory(self):
        """ Store H and L to memory at immediate address """
        addr = self._fetch_next_word()
        self._machine.write_memory_word(addr, self.hl)
        self._cycles += 16

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD ({addr:04x}), HL")


    def _store_reg16_to_memory(self):
        """ Store register pair to memory at immediate address """
        reg_pair = (self._current_inst & 0x30) >> 4
        addr = self._fetch_next_word()
        self._machine.write_memory_word(addr, self._get_register_pair(reg_pair))
        self._cycles += 20

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD ({addr:04x}), {self._reg_pair_symb(reg_pair)}")


    def _load_hl_from_memory(self):
        """ Load H and L from memory at immediate address """
        addr = self._fetch_next_word()
        self.hl = self._machine.read_memory_word(addr)
        self._cycles += 16

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD HL, ({addr:04x})")


    def _load_reg16_from_memory(self):
        """ Load register pair from memory at immediate address """
        reg_pair = (self._current_inst & 0x30) >> 4
        addr = self._fetch_next_word()
        value = self._machine.read_memory_word(addr)
        self._set_register_pair(reg_pair, value)
        self._cycles += 20

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"LD {self._reg_pair_symb(reg_pair)}, ({addr:04x})")


    def _ld_sp_hl(self):
        """ Load HL value to SP register """
        self._sp = self.hl
        self._cycles += 6

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"LD SP, HL")


    def _push(self):
        """ Push register pair to stack """
        reg_pair = (self._current_inst & 0x30) >> 4

        if reg_pair != 3:
            reg_pair_name = self._reg_pair_symb(reg_pair)
            value = self._get_register_pair(reg_pair)
        else:
            reg_pair_name = "AF"
            value = self.af

        self._push_to_stack(value)
        self._cycles += 11

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"PUSH {reg_pair_name}")


    def _pop(self):
        """ Pop register pair from stack """
        reg_pair = (self._current_inst & 0x30) >> 4

        value = self._pop_from_stack()

        if reg_pair != 3:
            reg_pair_name = self._reg_pair_symb(reg_pair)
            self._set_register_pair(reg_pair, value)
        else:
            reg_pair_name = "AF"
            self.af = value

        self._cycles += 10

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"POP {reg_pair_name}")


    # Exchange instructions

    def _exchange_de_hl(self):
        """ Exchange DE and HL register pairs """
        tmp = self.de
        self.de = self.hl
        self.hl = tmp

        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"EX DE, HL")


    def _exchange_hl_stack(self):
        """ Exchange HL and 2 bytes on the stack """
        value = self.hl
        self.hl = self._machine.read_memory_word(self._sp)
        self._machine.write_memory_word(self._sp, value)
        self._cycles += 19

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"EX (SP), HL")


    def _exchange_af_afx(self):
        """ Exchange AF register pair with alternate registers set """
        tmp = self.afx
        self.afx = self.af
        self.af = tmp

        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"EX AF, AF'")


    def _exchange_register_set(self):
        """ Exchange register set with alternate register set """
        tmp = self.bcx
        self.bcx = self.bc
        self.bc = tmp

        tmp = self.dex
        self.dex = self.de
        self.de = tmp

        tmp = self.hlx
        self.hlx = self.hl
        self.hl = tmp

        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"EXX")

    # Block transfer instructions

    def _ldd(self):
        """ Copy byte from (HL) to (DE) and decrement HL and DE, decrement BC """
        value = self._machine.read_memory_byte(self.hl)
        self._machine.write_memory_byte(self.de, value)
        self.hl = (self.hl - 1) & 0xffff
        self.de = (self.de - 1) & 0xffff
        self.bc = (self.bc - 1) & 0xffff

        self._half_carry = False
        self._parity_overflow = self.bc != 0x0000
        self._add_subtract = False

        self._cycles += 16

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("LDD")


    def _lddr(self):
        """ Copy byte from (HL) to (DE) and decrement HL and DE. Repeat until BC is zero"""
        value = self._machine.read_memory_byte(self.hl)
        self._machine.write_memory_byte(self.de, value)
        self.hl = (self.hl - 1) & 0xffff
        self.de = (self.de - 1) & 0xffff
        self.bc = (self.bc - 1) & 0xffff

        self._half_carry = False
        self._parity_overflow = self.bc != 0x0000
        self._add_subtract = False

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("LDDR")

        if self.bc != 0:
            self._pc -= 2
            self._cycles += 21
        else:
            self._cycles += 16


    def _ldi(self):
        """ Copy byte from (HL) to (DE) and increment HL and DE, decrement BC """
        value = self._machine.read_memory_byte(self.hl)
        self._machine.write_memory_byte(self.de, value)
        self.hl = (self.hl + 1) & 0xffff
        self.de = (self.de + 1) & 0xffff
        self.bc = (self.bc - 1) & 0xffff

        self._half_carry = False
        self._parity_overflow = self.bc != 0x0000
        self._add_subtract = False

        self._cycles += 16

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("LDI")


    def _ldir(self):
        """ Copy byte from (HL) to (DE) and increment HL and DE. Repeat until BC is zero"""
        value = self._machine.read_memory_byte(self.hl)
        self._machine.write_memory_byte(self.de, value)
        self.hl = (self.hl + 1) & 0xffff
        self.de = (self.de + 1) & 0xffff
        self.bc = (self.bc - 1) & 0xffff

        self._half_carry = False
        self._parity_overflow = self.bc != 0x0000
        self._add_subtract = False

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction("LDIR")

        if self.bc != 0:
            self._pc -= 2
            self._cycles += 21
        else:
            self._cycles += 16



    # Execution flow instructions

    def _jp(self):
        """ Unconditional jump to an absolute address """
        addr = self._fetch_next_word()

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"JP {addr:04x}")

        self._pc = addr
        self._cycles += 10


    def _jp_hl(self):
        """ Jump to address in HL """
        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"JP (HL)")

        self._pc = self.hl
        self._cycles += 4


    def _jr(self):
        """ Unconditional relative jump """
        displacement = self._fetch_displacement()

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"JR {displacement + 2:+03x} ({self._pc + displacement:04x})")

        self._pc += displacement
        self._cycles += 12


    def _jr_cond(self):
        """ Conditional relative jump """
        displacement = self._fetch_displacement()

        condition_code = (self._current_inst & 0x18)
        if condition_code == 0x00:
            condition = not self._zero
            condition_code = "NZ"
        elif condition_code == 0x08:
            condition = self._zero
            condition_code = "Z"
        elif condition_code == 0x10:
            condition = not self._carry
            condition_code = "NC"
        elif condition_code == 0x18:
            condition = self._carry
            condition_code = "C"

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"JR {condition_code}, {displacement + 2:+03x} ({(self._pc + displacement):04x})")

        if condition:
            self._pc += displacement
            self._cycles += 12
        else:
            self._cycles += 7


    def _djnz(self):
        """ Decrease counter and jump if not zero """
        self._b = (self._b - 1) & 0xff

        displacement = self._fetch_displacement()

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"DJNZ {displacement + 2:+03x} ({self._pc + displacement:04x})")

        if self._b != 0:
            self._pc += displacement
            self._cycles += 13
        else:
            self._cycles += 8


    def _call(self):
        """ Call a subroutine """
        addr = self._fetch_next_word()

        if logger.level <= logging.DEBUG:
            self._log_3b_instruction(f"CALL {addr:04x}")

        self._push_to_stack(self._pc)
        self._pc = addr
        self._cycles += 17


    def _ret(self):
        """ Return from a subroutine """

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"RET")

        self._pc = self._pop_from_stack()
        self._cycles += 10


    def _check_condition(self, op):
        """ Helper function to check condition on conditional JP, CALL, and RET """
        if op == 0:
            return not self._zero
        if op == 1:
            return self._zero
        if op == 2:
            return not self._carry
        if op == 3:
            return self._carry
        if op == 4:
            return not self._parity
        if op == 5:
            return self._parity
        if op == 6:
            return not self._sign
        if op == 7:
            return self._sign


    def _jmp_cond(self):
        """ Conditional jump """
        addr = self._fetch_next_word()
        op = (self._current_inst & 0x38) >> 3

        if logger.level <= logging.DEBUG:
            op_symb = ["JP NZ", "JP Z", "JP NC", "JP C", "JP PO", "JP PE", "JP P", "JP M"][op]
            self._log_3b_instruction(f"{op_symb}, {addr:04x}")

        if self._check_condition(op):
            self._pc = addr

        self._cycles += 10


    def _call_cond(self):
        """ Conditional call """
        addr = self._fetch_next_word()
        op = (self._current_inst & 0x38) >> 3

        if logger.level <= logging.DEBUG:
            op_symb = ["CALL NZ", "CALL Z", "CALL NC", "CALL C", "CALL PO", "CALL PE", "CALL P", "CALL M"][op]
            self._log_3b_instruction(f"{op_symb}, {addr:04x}")

        if self._check_condition(op):
            self._push_to_stack(self._pc)
            self._pc = addr
            self._cycles += 17
        else:
            self._cycles += 10


    def _ret_cond(self):
        """ Conditional return """
        op = (self._current_inst & 0x38) >> 3

        if logger.level <= logging.DEBUG:
            op_symb = ["RET NZ", "RET Z", "RET NC", "RET C", "RET PO", "RET PE", "RET P", "RET M"][op]
            self._log_1b_instruction(f"{op_symb}")

        if self._check_condition(op):
            self._pc = self._pop_from_stack()
            self._cycles += 11
        else:
            self._cycles += 5


    def _rst(self):
        """ Restart (special subroutine call) """
        rst_addr = self._current_inst & 0x38
        
        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"RST {rst_addr:02x}")

        self._push_to_stack(self._pc)
        self._pc = rst_addr
        self._cycles += 11


    # ALU instructions

    def _count_bits(self, n):
        """ Return number of set bits """
        if (n == 0):
            return 0
        else:
            return 1 + self._count_bits(n & (n - 1))


    def _alu_op(self, op, value):
        """ Internal implementation of an ALU operation between the accumulator and value.
        The function updates flags as a result of the operation """

        # Perform the operation
        if op == 0: # ADD
            res = self._a + value
            self._carry = res > 0xff
            self._half_carry = ((self._a & 0x0f) + (value & 0x0f)) > 0x0f
            self._add_subtract = False
            self._parity_overflow = ((self._a ^ value) < 0x80) and ((self._a ^ res) > 0x7f) and (self._a != 0) and (value != 0)
        if op == 1: # ADC
            carry = 1 if self._carry else 0
            res = self._a + value + carry
            self._carry = res > 0xff
            self._half_carry = ((self._a & 0x0f) + (value & 0x0f) + carry) > 0x0f
            self._add_subtract = False
            self._parity_overflow = ((self._a ^ (value + carry)) < 0x80) and ((self._a ^ res) > 0x7f) and (self._a != 0) and (value + carry != 0)
        if op == 2 or op == 7: # SUB and CMP
            res = self._a - value
            self._carry = res < 0
            neg_value = ~value + 1
            self._half_carry = ((self._a & 0x0f) + (neg_value & 0x0f)) > 0x0f
            self._add_subtract = True
            self._parity_overflow = ((self._a ^ neg_value) < 0x80) and ((self._a ^ res) > 0x7f) and (self._a != 0) and (neg_value != 0)
        if op == 3: # SBB
            carry = 1 if self._carry else 0
            res = self._a - value - carry
            self._carry = res < 0 
            neg_value = ~value + 1
            self._half_carry = ((self._a & 0x0f) + ((neg_value - carry) & 0x0f)) > 0x0f
            self._add_subtract = True
            self._parity_overflow = ((self._a ^ (neg_value - carry)) < 0x80) and ((self._a ^ res) > 0x7f) and (self._a != 0) and ((neg_value - carry) != 0)
        if op == 4: # AND
            res = self._a & value
        if op == 5: # XOR
            res = self._a ^ value
        if op == 6: # OR
            res = self._a | value

        res &= 0xff

        # Store result for all operations, except for CMP
        if op != 7:
            self._a = res

        # Update common flags
        if op >= 4 and op < 7: 
            self._carry = False
            self._half_carry = False
            self._parity_overflow = self._count_bits(res) % 2 == 0
            self._add_subtract = False
        self._zero = res == 0        
        self._sign = (res & 0x80) != 0


    def _alu(self):
        """ 
        Implementation of the following instructions:
            - ADD - add a register to the accumulator
            - ADC - add a register to the accumulator with carry
            - SUB - subtract a register from the accumulator
            - SBC - subtract a register from the accumulator with carry
            - AND - logical AND a register with the accumulator
            - XOR - logical XOR a register with the accumulator
            - OR  - logical OR a register with the accumulator
            - CP  - compare a register with the accumulator (set flags, but not change accumulator)
        """
        op = (self._current_inst & 0x38) >> 3
        reg = self._current_inst & 0x07
        value = self._get_register(reg)

        self._alu_op(op, value)
        self._cycles += 4 if reg != 6 else 7

        if logger.level <= logging.DEBUG:
            op_name = ["ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR ", "CP "][op]
            self._log_1b_instruction(f"{op_name} {self._reg_symb(reg)}")


    def _alu_immediate(self):
        """ 
        Implementation of ALU instructions between the accumulator register and 
        immediate operand:
            - ADD - add the operand to the accumulator
            - ADC - add the operand to the accumulator with carry
            - SUB - subtract the operand from the accumulator
            - SBC - subtract the operand from the accumulator with carry
            - AND - logical AND the operand with the accumulator
            - XOR - logical XOR the operand with the accumulator
            - OR  - logical OR the operand with the accumulator
            - CP  - compare the operand with the accumulator (set flags, but not change accumulator)
        """
        op = (self._current_inst & 0x38) >> 3
        value = self._fetch_next_byte()

        self._alu_op(op, value)
        self._cycles += 7

        if logger.level <= logging.DEBUG:
            op_name = ["ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR ", "CP "][op]
            self._log_2b_instruction(f"{op_name} {value:02x}")


    def _alu_mem_indexed(self):
        """ Perform ALU operation between accumulator and memory indexed by IX/IY register
            - ADD - add a memory value to the accumulator
            - ADC - add a memory value to the accumulator with carry
            - SUB - subtract a memory value from the accumulator
            - SBC - subtract a memory value from the accumulator with carry
            - AND - logical AND a memory value with the accumulator
            - XOR - logical XOR a memory value with the accumulator
            - OR  - logical OR a memory value with the accumulator
            - CP  - compare a memory value with the accumulator (set flags, but not change accumulator)
        """
        op = (self._current_inst & 0x38) >> 3
        addr = self._get_index_reg() + self._fetch_displacement()
        value = self._machine.read_memory_byte(addr)

        self._alu_op(op, value)
        self._cycles += 19

        if logger.level <= logging.DEBUG:
            op_name = ["ADD A,", "ADC A,", "SUB", "SBC A,", "AND", "XOR", "OR", "CP"][op]
            self._log_2b_instruction(f"{op_name} ({self._get_index_reg_symb()}{self._displacement:+03x})")
        

    def _inc_8bit_value(self, value):
        """ Increment a 8-bit value and update flags """
        value = (value + 1) & 0xff

        self._zero = (value & 0xff) == 0
        self._parity = self._count_bits(value) % 2 == 0
        self._sign = (value & 0x80) != 0
        self._half_carry = (value & 0xf) == 0x0
        self._add_subtract = False
        self._parity_overflow = value == 0x80

        return value


    def _dec_8bit_value(self, value):
        """ Decrement a 8-bit value and update flags """
        value = (value - 1) & 0xff

        self._zero = (value & 0xff) == 0
        self._parity = self._count_bits(value) % 2 == 0
        self._sign = (value & 0x80) != 0
        self._half_carry = value == 0x0f
        self._add_subtract = True
        self._parity_overflow = value == 0x7f

        return value


    def _inc_reg8(self):
        """ Increment a 8-bit register """
        reg = (self._current_inst & 0x38) >> 3
        value = self._inc_8bit_value(self._get_register(reg))
        self._set_register(reg, value)

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"INC {self._reg_symb(reg)}")

        self._cycles += 11 if reg == 6 else 4

    
    def _dec_reg8(self):
        """ Decrement a 8-bit register """
        reg = (self._current_inst & 0x38) >> 3
        value = self._dec_8bit_value(self._get_register(reg))
        self._set_register(reg, value)

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"DEC {self._reg_symb(reg)}")

        self._cycles += 11 if reg == 6 else 4


    def _inc_mem_indexed(self):
        """ Increment 8-bit value pointed by IX/IY-based index """
        displacement = self._fetch_displacement()
        addr = self._get_index_reg() + displacement
        value = self._machine.read_memory_byte(addr)
        value = self._inc_8bit_value(value)
        self._machine.write_memory_byte(addr, value)

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"INC ({self._get_index_reg_symb()}{displacement:+03x})")

        self._cycles += 23


    def _dec_mem_indexed(self):
        """ Deccrement 8-bit value pointed by IX/IY-based index """
        displacement = self._fetch_displacement()
        addr = self._get_index_reg() + displacement
        value = self._machine.read_memory_byte(addr)
        value = self._dec_8bit_value(value)
        self._machine.write_memory_byte(addr, value)

        if logger.level <= logging.DEBUG:
            self._log_2b_instruction(f"DEC ({self._get_index_reg_symb()}{displacement:+03x})")

        self._cycles += 23


    def _dec16(self):
        """ Decrement a register pair """
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._get_register_pair(reg_pair)
        self._set_register_pair(reg_pair, (value - 1) & 0xffff)
        self._cycles += 6

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"DEC {self._reg_pair_symb(reg_pair)}")


    def _inc16(self):
        """ Increment a register pair """
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._get_register_pair(reg_pair)
        self._set_register_pair(reg_pair, (value + 1) & 0xffff)
        self._cycles += 6

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"INC {self._reg_pair_symb(reg_pair)}")


    def _add_hl(self):
        """ Add register pairs """
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._get_register_pair(reg_pair)
        res = self.hl + value
        self._carry = (res >= 0x10000)
        self._half_carry = ((self.hl & 0x0fff) + (value & 0x0fff)) >= 0x1000
        self._add_subtract = False
        self.hl = res & 0xffff

        self._cycles += 11

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"ADD HL, {self._reg_pair_symb(reg_pair)}")


    def _adc_hl(self):
        """ Add register pairs with carry """
        reg_pair = (self._current_inst & 0x30) >> 4
        hl = self.hl
        value = self._get_register_pair(reg_pair)
        carry = 1 if self._carry else 0
        res = hl + value + carry
        self._sign = (res & 0x8000) != 0
        self._zero = (res & 0xffff) == 0
        self._parity_overflow = ((hl ^ value) < 0x8000) and ((hl ^ res) > 0x7fff) and (hl != 0) and (value != 0)
        self._carry = (res >= 0x10000)
        self._half_carry = ((self.hl & 0x0fff) + (value & 0x0fff) + carry) >= 0x1000
        self._add_subtract = False
        self.hl = res & 0xffff

        self._cycles += 15

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"ADC HL, {self._reg_pair_symb(reg_pair)}")


    def _sbc_hl(self):
        """ Subtract register pairs with carry """
        reg_pair = (self._current_inst & 0x30) >> 4
        hl = self.hl
        value = self._get_register_pair(reg_pair)
        carry = 1 if self._carry else 0
        res = hl - value - carry
        neg_value = (~value + 1) & 0xffff
        self._sign = (res & 0x8000) != 0
        self._zero = (res & 0xffff) == 0
        self._parity_overflow = ((hl ^ neg_value) < 0x8000) and ((hl ^ res) > 0x7fff) and (hl != 0) and (neg_value != 0)
        self._carry = (res >= 0x10000)
        self._half_carry = ((self.hl & 0x0fff) + (neg_value & 0x0fff) + carry) >= 0x1000
        self._add_subtract = False
        self.hl = res & 0xffff

        self._cycles += 15

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"SBC HL, {self._reg_pair_symb(reg_pair)}")



    # Rotate and shift instructions

    def _rlca(self):
        """ Rotate accumulator left """
        self._carry = is_bit_set(self._a, 7)
        self._a = ((self._a << 1) & 0xff) | (self._a >> 7)
        self._half_carry = False
        self._add_subtract = False

        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"RLCA")


    def _rrca(self):
        """ Rotate accumulator right """
        self._carry = is_bit_set(self._a, 0)
        self._a = ((self._a >> 1) & 0xff) | ((self._a << 7) & 0xff)
        self._half_carry = False
        self._add_subtract = False

        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"RRCA")


    def _rla(self):
        """ Rotate accumulator left through carry """
        temp = self._a
        self._a = (self._a << 1) & 0xff
        if self._carry: self._a = set_bit(self._a, 0)
        self._carry = is_bit_set(temp, 7)
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"RLA")


    def _rra(self):
        """ Rotate accumulator right through carry """
        temp = self._a
        self._a >>= 1
        if self._carry: self._a = set_bit(self._a, 7)
        self._carry = is_bit_set(temp, 0)
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"RRA")
    


    # Bit instructions

    def _cpl(self):
        """ Complement accumulator """
        self._a = (~self._a) & 0xff
        self._cycles += 4
        self._half_carry = True
        self._add_subtract = True

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"CPL")


    def _scf(self):
        """ Set carry flag """
        self._carry = True
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"SCF")
        

    def _ccf(self):
        """ Complement carry flag """
        self._half_carry = self._carry
        self._carry = not self._carry
        self._cycles += 4

        if logger.level <= logging.DEBUG:
            self._log_1b_instruction(f"CCF")


    def _get_bit(self):
        """ Get bit from a register """
        bit = (self._current_inst & 0x38) >> 3
        mask = 1 << bit
        reg = self._current_inst & 0x07
        value = self._get_register(reg)

        self._zero = (value & mask == 0)

        self._cycles += 12 if reg == 6 else 8
        
        if logger.level <= logging.DEBUG:
            self._log_3b_bit_instruction(f"BIT {bit}, {self._reg_symb(reg)}")


    def _get_bit_indexed(self):
        """ Get bit from a memory byte addressed via IX/IY index registers """
        bit = (self._current_inst & 0x38) >> 3
        mask = 1 << bit
        addr = self._get_index_reg() + self._displacement

        value = self._machine.read_memory_byte(addr)
        self._zero = (value & mask == 0)

        self._cycles += 20
        
        if logger.level <= logging.DEBUG:
            self._log_3b_bit_instruction(f"BIT {bit}, ({self._get_index_reg_symb()}{self._displacement:+03x})")


    def _set_bit(self):
        """ Set bit in a register """
        bit = (self._current_inst & 0x38) >> 3
        mask = 1 << bit
        reg = self._current_inst & 0x07
        value = self._get_register(reg)
        self._set_register(reg, value | mask)

        self._cycles += 15 if reg == 6 else 8
        
        if logger.level <= logging.DEBUG:
            self._log_3b_bit_instruction(f"SET {bit}, {self._reg_symb(reg)}")


    def _set_bit_indexed(self):
        """ Set bit on a memory byte addressed via IX/IY index registers """
        bit = (self._current_inst & 0x38) >> 3
        mask = 1 << bit
        addr = self._get_index_reg() + self._displacement

        value = self._machine.read_memory_byte(addr)
        self._machine.write_memory_byte(addr, value | mask)

        self._cycles += 23
        
        if logger.level <= logging.DEBUG:
            self._log_3b_bit_instruction(f"SET {bit}, ({self._get_index_reg_symb()}{self._displacement:+03x})")


    def _reset_bit(self):
        """ Reset bit in a register """
        bit = (self._current_inst & 0x38) >> 3
        mask = 1 << bit
        reg = self._current_inst & 0x07
        value = self._get_register(reg)
        self._set_register(reg, value & ~mask)

        self._cycles += 15 if reg == 6 else 8
        
        if logger.level <= logging.DEBUG:
            self._log_3b_bit_instruction(f"RES {bit}, {self._reg_symb(reg)}")


    def _reset_bit_indexed(self):
        """ Reset bit on a memory byte addressed via IX/IY index registers """

        bit = (self._current_inst & 0x38) >> 3
        mask = 1 << bit
        addr = self._get_index_reg() + self._displacement

        value = self._machine.read_memory_byte(addr)
        self._machine.write_memory_byte(addr, value & ~mask)

        self._cycles += 23
        
        if logger.level <= logging.DEBUG:
            self._log_3b_bit_instruction(f"RES {bit}, ({self._get_index_reg_symb()}{self._displacement:+03x})")


    # Instruction tables

    def _init_instruction_table(self):
        """ Initialize main instruction set """

        self._instructions = [None] * 0x100

        self._instructions[0x00] = self._nop                    # NOP
        self._instructions[0x01] = self._load_immediate_16b     # LD BC, nn
        self._instructions[0x02] = self._ld_mem_regpair_a       # LD (BC), A
        self._instructions[0x03] = self._inc16                  # INC BC
        self._instructions[0x04] = self._inc_reg8               # INC B
        self._instructions[0x05] = self._dec_reg8               # DEC B
        self._instructions[0x06] = self._load_reg8_immediate    # LD B, n
        self._instructions[0x07] = self._rlca                   # RLCA
        self._instructions[0x08] = self._exchange_af_afx        # EX AF, AF'
        self._instructions[0x09] = self._add_hl                 # ADD HL, BC
        self._instructions[0x0a] = self._ld_a_mem_regpair       # LD A, (BC)
        self._instructions[0x0b] = self._dec16                  # DEC BC
        self._instructions[0x0c] = self._inc_reg8               # INC C
        self._instructions[0x0d] = self._dec_reg8               # DEC C
        self._instructions[0x0e] = self._load_reg8_immediate    # LD C, n
        self._instructions[0x0f] = self._rrca                   # RRCA

        self._instructions[0x10] = self._djnz                   # DJNZ d
        self._instructions[0x11] = self._load_immediate_16b     # LD DE, nn
        self._instructions[0x12] = self._ld_mem_regpair_a       # LD (DE), A
        self._instructions[0x13] = self._inc16                  # INC DE
        self._instructions[0x14] = self._inc_reg8               # INC D
        self._instructions[0x15] = self._dec_reg8               # DEC D
        self._instructions[0x16] = self._load_reg8_immediate    # LD D, n
        self._instructions[0x17] = self._rla                    # RLA
        self._instructions[0x18] = self._jr                     # JR d
        self._instructions[0x19] = self._add_hl                 # ADD HL, DE
        self._instructions[0x1a] = self._ld_a_mem_regpair       # LD A, (DE)
        self._instructions[0x1b] = self._dec16                  # DEC DE
        self._instructions[0x1c] = self._inc_reg8               # INC E
        self._instructions[0x1d] = self._dec_reg8               # DEC E
        self._instructions[0x1e] = self._load_reg8_immediate    # LD E, n
        self._instructions[0x1f] = self._rra                    # RRA

        self._instructions[0x20] = self._jr_cond                # JR NZ, d
        self._instructions[0x21] = self._load_immediate_16b     # LD HL, nn
        self._instructions[0x22] = self._store_hl_to_memory     # LD (nn), HL
        self._instructions[0x23] = self._inc16                  # INC HL
        self._instructions[0x24] = self._inc_reg8               # INC H
        self._instructions[0x25] = self._dec_reg8               # DEC H
        self._instructions[0x26] = self._load_reg8_immediate    # LD H, n
        self._instructions[0x27] = None                         # DAA
        self._instructions[0x28] = self._jr_cond                # JR Z, d
        self._instructions[0x29] = self._add_hl                 # ADD HL, HL
        self._instructions[0x2a] = self._load_hl_from_memory    # LD HL, (nn)
        self._instructions[0x2b] = self._dec16                  # DEC HL
        self._instructions[0x2c] = self._inc_reg8               # INC L
        self._instructions[0x2d] = self._dec_reg8               # DEC L
        self._instructions[0x2e] = self._load_reg8_immediate    # LD L, n
        self._instructions[0x2f] = self._cpl                    # CPL

        self._instructions[0x30] = self._jr_cond                # JR JC, d
        self._instructions[0x31] = self._load_immediate_16b     # LD SP, nn
        self._instructions[0x32] = self._store_a_to_mem         # LD (nn), A
        self._instructions[0x33] = self._inc16                  # INC SP
        self._instructions[0x34] = self._inc_reg8               # INC (HL)
        self._instructions[0x35] = self._dec_reg8               # DEC (HL)
        self._instructions[0x36] = self._load_reg8_immediate    # LD (HL), n
        self._instructions[0x37] = self._scf                    # SCF
        self._instructions[0x38] = self._jr_cond                # JR C, d
        self._instructions[0x39] = self._add_hl                 # ADD HL, SP
        self._instructions[0x3a] = self._load_a_from_mem        # LD A, (nn)
        self._instructions[0x3b] = self._dec16                  # DEC SP
        self._instructions[0x3c] = self._inc_reg8               # INC A
        self._instructions[0x3d] = self._dec_reg8               # DEC A
        self._instructions[0x3e] = self._load_reg8_immediate    # LD A, n
        self._instructions[0x3f] = self._ccf                    # CCF

        self._instructions[0x40] = self._load_reg8_to_reg8      # LD B, B
        self._instructions[0x41] = self._load_reg8_to_reg8      # LD B, C
        self._instructions[0x42] = self._load_reg8_to_reg8      # LD B, D
        self._instructions[0x43] = self._load_reg8_to_reg8      # LD B, E
        self._instructions[0x44] = self._load_reg8_to_reg8      # LD B, H
        self._instructions[0x45] = self._load_reg8_to_reg8      # LD B, L
        self._instructions[0x46] = self._load_reg8_to_reg8      # LD B, (HL)
        self._instructions[0x47] = self._load_reg8_to_reg8      # LD B, A
        self._instructions[0x48] = self._load_reg8_to_reg8      # LD C, B
        self._instructions[0x49] = self._load_reg8_to_reg8      # LD C, C
        self._instructions[0x4a] = self._load_reg8_to_reg8      # LD C, D
        self._instructions[0x4b] = self._load_reg8_to_reg8      # LD C, E
        self._instructions[0x4c] = self._load_reg8_to_reg8      # LD C, H
        self._instructions[0x4d] = self._load_reg8_to_reg8      # LD C, L
        self._instructions[0x4e] = self._load_reg8_to_reg8      # LD C, (HL)
        self._instructions[0x4f] = self._load_reg8_to_reg8      # LD C, A

        self._instructions[0x50] = self._load_reg8_to_reg8      # LD D, B
        self._instructions[0x51] = self._load_reg8_to_reg8      # LD D, C
        self._instructions[0x52] = self._load_reg8_to_reg8      # LD D, D
        self._instructions[0x53] = self._load_reg8_to_reg8      # LD D, E
        self._instructions[0x54] = self._load_reg8_to_reg8      # LD D, H
        self._instructions[0x55] = self._load_reg8_to_reg8      # LD D, L
        self._instructions[0x56] = self._load_reg8_to_reg8      # LD D, (HL)
        self._instructions[0x57] = self._load_reg8_to_reg8      # LD D, A
        self._instructions[0x58] = self._load_reg8_to_reg8      # LD E, B
        self._instructions[0x59] = self._load_reg8_to_reg8      # LD E, C
        self._instructions[0x5a] = self._load_reg8_to_reg8      # LD E, D
        self._instructions[0x5b] = self._load_reg8_to_reg8      # LD E, E
        self._instructions[0x5c] = self._load_reg8_to_reg8      # LD E, H
        self._instructions[0x5d] = self._load_reg8_to_reg8      # LD E, L
        self._instructions[0x5e] = self._load_reg8_to_reg8      # LD E, (HL)
        self._instructions[0x5f] = self._load_reg8_to_reg8      # LD E, A

        self._instructions[0x60] = self._load_reg8_to_reg8      # LD H, B
        self._instructions[0x61] = self._load_reg8_to_reg8      # LD H, C
        self._instructions[0x62] = self._load_reg8_to_reg8      # LD H, D
        self._instructions[0x63] = self._load_reg8_to_reg8      # LD H, E
        self._instructions[0x64] = self._load_reg8_to_reg8      # LD H, H
        self._instructions[0x65] = self._load_reg8_to_reg8      # LD H, L
        self._instructions[0x66] = self._load_reg8_to_reg8      # LD H, (HL)
        self._instructions[0x67] = self._load_reg8_to_reg8      # LD H, A
        self._instructions[0x68] = self._load_reg8_to_reg8      # LD L, B
        self._instructions[0x69] = self._load_reg8_to_reg8      # LD L, C
        self._instructions[0x6a] = self._load_reg8_to_reg8      # LD L, D
        self._instructions[0x6b] = self._load_reg8_to_reg8      # LD L, E
        self._instructions[0x6c] = self._load_reg8_to_reg8      # LD L, H
        self._instructions[0x6d] = self._load_reg8_to_reg8      # LD L, L
        self._instructions[0x6e] = self._load_reg8_to_reg8      # LD L, (HL)
        self._instructions[0x6f] = self._load_reg8_to_reg8      # LD L, A

        self._instructions[0x70] = self._load_reg8_to_reg8      # LD (HL), B
        self._instructions[0x71] = self._load_reg8_to_reg8      # LD (HL), C
        self._instructions[0x72] = self._load_reg8_to_reg8      # LD (HL), D
        self._instructions[0x73] = self._load_reg8_to_reg8      # LD (HL), E
        self._instructions[0x74] = self._load_reg8_to_reg8      # LD (HL), H
        self._instructions[0x75] = self._load_reg8_to_reg8      # LD (HL), L
        self._instructions[0x76] = None                         # HALT
        self._instructions[0x77] = self._load_reg8_to_reg8      # LD (HL), A
        self._instructions[0x78] = self._load_reg8_to_reg8      # LD A, B
        self._instructions[0x79] = self._load_reg8_to_reg8      # LD A, C
        self._instructions[0x7a] = self._load_reg8_to_reg8      # LD A, D
        self._instructions[0x7b] = self._load_reg8_to_reg8      # LD A, E
        self._instructions[0x7c] = self._load_reg8_to_reg8      # LD A, H
        self._instructions[0x7d] = self._load_reg8_to_reg8      # LD A, L
        self._instructions[0x7e] = self._load_reg8_to_reg8      # LD A, (HL)
        self._instructions[0x7f] = self._load_reg8_to_reg8      # LD A, A

        self._instructions[0x80] = self._alu                    # ADD A, B
        self._instructions[0x81] = self._alu                    # ADD A, C
        self._instructions[0x82] = self._alu                    # ADD A, D
        self._instructions[0x83] = self._alu                    # ADD A, E
        self._instructions[0x84] = self._alu                    # ADD A, H
        self._instructions[0x85] = self._alu                    # ADD A, L
        self._instructions[0x86] = self._alu                    # ADD A, (HL)
        self._instructions[0x87] = self._alu                    # ADD A, A
        self._instructions[0x88] = self._alu                    # ADC A, B
        self._instructions[0x89] = self._alu                    # ADC A, C
        self._instructions[0x8a] = self._alu                    # ADC A, D
        self._instructions[0x8b] = self._alu                    # ADC A, E
        self._instructions[0x8c] = self._alu                    # ADC A, H
        self._instructions[0x8d] = self._alu                    # ADC A, L
        self._instructions[0x8e] = self._alu                    # ADC A, (HL)
        self._instructions[0x8f] = self._alu                    # ADC A, A

        self._instructions[0x90] = self._alu                    # SUB B
        self._instructions[0x91] = self._alu                    # SUB C
        self._instructions[0x92] = self._alu                    # SUB D
        self._instructions[0x93] = self._alu                    # SUB E
        self._instructions[0x94] = self._alu                    # SUB H
        self._instructions[0x95] = self._alu                    # SUB L
        self._instructions[0x96] = self._alu                    # SUB (HL)
        self._instructions[0x97] = self._alu                    # SUB A
        self._instructions[0x98] = self._alu                    # SBC A, B
        self._instructions[0x99] = self._alu                    # SBC A, C
        self._instructions[0x9a] = self._alu                    # SBC A, D
        self._instructions[0x9b] = self._alu                    # SBC A, E
        self._instructions[0x9c] = self._alu                    # SBC A, H
        self._instructions[0x9d] = self._alu                    # SBC A, L
        self._instructions[0x9e] = self._alu                    # SBC A, (HL)
        self._instructions[0x9f] = self._alu                    # SBC A, A

        self._instructions[0xa0] = self._alu                    # AND B
        self._instructions[0xa1] = self._alu                    # AND C
        self._instructions[0xa2] = self._alu                    # AND D
        self._instructions[0xa3] = self._alu                    # AND E
        self._instructions[0xa4] = self._alu                    # AND H
        self._instructions[0xa5] = self._alu                    # AND L
        self._instructions[0xa6] = self._alu                    # AND (HL)
        self._instructions[0xa7] = self._alu                    # AND A
        self._instructions[0xa8] = self._alu                    # XOR B
        self._instructions[0xa9] = self._alu                    # XOR C
        self._instructions[0xaa] = self._alu                    # XOR D
        self._instructions[0xab] = self._alu                    # XOR E
        self._instructions[0xac] = self._alu                    # XOR H
        self._instructions[0xad] = self._alu                    # XOR L
        self._instructions[0xae] = self._alu                    # XOR (HL)
        self._instructions[0xaf] = self._alu                    # XOR A

        self._instructions[0xb0] = self._alu                    # OR B
        self._instructions[0xb1] = self._alu                    # OR C
        self._instructions[0xb2] = self._alu                    # OR D
        self._instructions[0xb3] = self._alu                    # OR E
        self._instructions[0xb4] = self._alu                    # OR H
        self._instructions[0xb5] = self._alu                    # OR L
        self._instructions[0xb6] = self._alu                    # OR (HL)
        self._instructions[0xb7] = self._alu                    # OR A
        self._instructions[0xb8] = self._alu                    # CP B
        self._instructions[0xb9] = self._alu                    # CP C
        self._instructions[0xba] = self._alu                    # CP D
        self._instructions[0xbb] = self._alu                    # CP E
        self._instructions[0xbc] = self._alu                    # CP H
        self._instructions[0xbd] = self._alu                    # CP L
        self._instructions[0xbe] = self._alu                    # CP (HL)
        self._instructions[0xbf] = self._alu                    # CP A

        self._instructions[0xc0] = self._ret_cond               # RET NZ
        self._instructions[0xc1] = self._pop                    # POP BC
        self._instructions[0xc2] = self._jmp_cond               # JP NZ, nn
        self._instructions[0xc3] = self._jp                     # JP nn
        self._instructions[0xc4] = self._call_cond              # CALL NZ, nn
        self._instructions[0xc5] = self._push                   # PUSH BC
        self._instructions[0xc6] = self._alu_immediate          # ADD A, n
        self._instructions[0xc7] = self._rst                    # RST 00
        self._instructions[0xc8] = self._ret_cond               # RET Z
        self._instructions[0xc9] = self._ret                    # RET
        self._instructions[0xca] = self._jmp_cond               # JP Z, nn
        self._instructions[0xcb] = None                         # Bit instruction set
        self._instructions[0xcc] = self._call_cond              # CALL Z, nn
        self._instructions[0xcd] = self._call                   # CALL nn
        self._instructions[0xce] = self._alu_immediate          # ADC A, n
        self._instructions[0xcf] = self._rst                    # RST 08

        self._instructions[0xd0] = self._ret_cond               # RET NC
        self._instructions[0xd1] = self._pop                    # POP DE
        self._instructions[0xd2] = self._jmp_cond               # JP NC, nn
        self._instructions[0xd3] = self._out                    # OUT (n), A
        self._instructions[0xd4] = self._call_cond              # CALL NC, nn
        self._instructions[0xd5] = self._push                   # PUSH DE
        self._instructions[0xd6] = self._alu_immediate          # SUB n
        self._instructions[0xd7] = self._rst                    # RST 10
        self._instructions[0xd8] = self._ret_cond               # RET C
        self._instructions[0xd9] = self._exchange_register_set  # EXX
        self._instructions[0xda] = self._jmp_cond               # JP C, nn
        self._instructions[0xdb] = self._in                     # IN A, (n)
        self._instructions[0xdc] = self._call_cond              # CALL C, nn
        self._instructions[0xdd] = None                         # IX instructions set
        self._instructions[0xde] = self._alu_immediate          # SBC A, n
        self._instructions[0xdf] = self._rst                    # RST 18

        self._instructions[0xe0] = self._ret_cond               # RET PO
        self._instructions[0xe1] = self._pop                    # POP HL
        self._instructions[0xe2] = self._jmp_cond               # JP PO, nn
        self._instructions[0xe3] = self._exchange_hl_stack      # EX (SP), HL
        self._instructions[0xe4] = self._call_cond              # CALL PO, nn
        self._instructions[0xe5] = self._push                   # PUSH HL
        self._instructions[0xe6] = self._alu_immediate          # AND n
        self._instructions[0xe7] = self._rst                    # RST 20
        self._instructions[0xe8] = self._ret_cond               # RET PE
        self._instructions[0xe9] = self._jp_hl                  # JP (HL)
        self._instructions[0xea] = self._jmp_cond               # JP PE, nn
        self._instructions[0xeb] = self._exchange_de_hl         # EX DE, HL
        self._instructions[0xec] = self._call_cond              # CALL PE, nn
        self._instructions[0xed] = None                         # Advanced instruction set
        self._instructions[0xee] = self._alu_immediate          # XOR n
        self._instructions[0xef] = self._rst                    # RST 28

        self._instructions[0xf0] = self._ret_cond               # RET P
        self._instructions[0xf1] = self._pop                    # POP AF
        self._instructions[0xf2] = self._jmp_cond               # JP P, nn
        self._instructions[0xf3] = self._di                     # DI
        self._instructions[0xf4] = self._call_cond              # CALL P, nn
        self._instructions[0xf5] = self._push                   # PUSH AF
        self._instructions[0xf6] = self._alu_immediate          # OR n
        self._instructions[0xf7] = self._rst                    # RST 30
        self._instructions[0xf8] = self._ret_cond               # RET M
        self._instructions[0xf9] = self._ld_sp_hl               # LD SP, HL
        self._instructions[0xfa] = self._jmp_cond               # JP M, nn
        self._instructions[0xfb] = self._ei                     # EI
        self._instructions[0xfc] = self._call_cond              # CALL M, nn
        self._instructions[0xfd] = None                         # IY instruction set
        self._instructions[0xfe] = self._alu_immediate          # CP n
        self._instructions[0xff] = self._rst                    # RST 38


    def _init_ed_instruction_table(self):
        """ Initialize additional instruction set with 0xED prefix """

        self._instructions_0xed = [None] * 0x100

        self._instructions_0xed[0x00] = None            # IN0 B, (n)
        self._instructions_0xed[0x01] = None            # OUT0 (n), B
        self._instructions_0xed[0x02] = None
        self._instructions_0xed[0x03] = None
        self._instructions_0xed[0x04] = None            # TST B
        self._instructions_0xed[0x05] = None
        self._instructions_0xed[0x06] = None
        self._instructions_0xed[0x07] = None
        self._instructions_0xed[0x08] = None            # IN0 C, (n)
        self._instructions_0xed[0x09] = None            # OUT0 (n), C
        self._instructions_0xed[0x0a] = None
        self._instructions_0xed[0x0b] = None
        self._instructions_0xed[0x0c] = None            # TST C
        self._instructions_0xed[0x0d] = None
        self._instructions_0xed[0x0e] = None
        self._instructions_0xed[0x0f] = None

        self._instructions_0xed[0x10] = None            # IN0 D, (n)
        self._instructions_0xed[0x11] = None            # OUT0 (n), D
        self._instructions_0xed[0x12] = None
        self._instructions_0xed[0x13] = None
        self._instructions_0xed[0x14] = None            # TST D
        self._instructions_0xed[0x15] = None
        self._instructions_0xed[0x16] = None
        self._instructions_0xed[0x17] = None
        self._instructions_0xed[0x18] = None            # IN0 E, (n)
        self._instructions_0xed[0x19] = None            # OUT0 (n), E
        self._instructions_0xed[0x1a] = None
        self._instructions_0xed[0x1b] = None
        self._instructions_0xed[0x1c] = None            # TST E
        self._instructions_0xed[0x1d] = None
        self._instructions_0xed[0x1e] = None
        self._instructions_0xed[0x1f] = None

        self._instructions_0xed[0x20] = None            # IN0 H, (n)
        self._instructions_0xed[0x21] = None            # OUT0 (n), H
        self._instructions_0xed[0x22] = None
        self._instructions_0xed[0x23] = None
        self._instructions_0xed[0x24] = None            # TST H
        self._instructions_0xed[0x25] = None
        self._instructions_0xed[0x26] = None
        self._instructions_0xed[0x27] = None
        self._instructions_0xed[0x28] = None            # IN0 L, (n)
        self._instructions_0xed[0x29] = None            # OUT0 (n), L
        self._instructions_0xed[0x2a] = None
        self._instructions_0xed[0x2b] = None
        self._instructions_0xed[0x2c] = None            # TST L
        self._instructions_0xed[0x2d] = None
        self._instructions_0xed[0x2e] = None
        self._instructions_0xed[0x2f] = None

        self._instructions_0xed[0x30] = None
        self._instructions_0xed[0x31] = None
        self._instructions_0xed[0x32] = None
        self._instructions_0xed[0x33] = None
        self._instructions_0xed[0x34] = None            # TST (HL)
        self._instructions_0xed[0x35] = None
        self._instructions_0xed[0x36] = None
        self._instructions_0xed[0x37] = None
        self._instructions_0xed[0x38] = None            # IN0 A, (n)
        self._instructions_0xed[0x39] = None            # OUT0 (n), A
        self._instructions_0xed[0x3a] = None
        self._instructions_0xed[0x3b] = None
        self._instructions_0xed[0x3c] = None            # TST A
        self._instructions_0xed[0x3d] = None
        self._instructions_0xed[0x3e] = None
        self._instructions_0xed[0x3f] = None

        self._instructions_0xed[0x40] = None            # IN B, (C)
        self._instructions_0xed[0x41] = None            # OUT (C), B
        self._instructions_0xed[0x42] = self._sbc_hl
        self._instructions_0xed[0x43] = self._store_reg16_to_memory
        self._instructions_0xed[0x44] = None            # NEG
        self._instructions_0xed[0x45] = None            # RETN
        self._instructions_0xed[0x46] = self._im
        self._instructions_0xed[0x47] = self._load_i_r_register_from_a
        self._instructions_0xed[0x48] = None            # IN C, (C)
        self._instructions_0xed[0x49] = None            # OUT (C), C
        self._instructions_0xed[0x4a] = self._adc_hl
        self._instructions_0xed[0x4b] = self._load_reg16_from_memory
        self._instructions_0xed[0x4c] = None            # MLT BC
        self._instructions_0xed[0x4d] = None            # RETI
        self._instructions_0xed[0x4e] = None
        self._instructions_0xed[0x4f] = self._load_i_r_register_from_a

        self._instructions_0xed[0x50] = None            # IN D, (C)
        self._instructions_0xed[0x51] = None            # OUT (C), D
        self._instructions_0xed[0x52] = self._sbc_hl
        self._instructions_0xed[0x53] = self._store_reg16_to_memory
        self._instructions_0xed[0x54] = None
        self._instructions_0xed[0x55] = None
        self._instructions_0xed[0x56] = self._im
        self._instructions_0xed[0x57] = self._load_a_from_i_r_registers
        self._instructions_0xed[0x58] = None            # IN E, (C)
        self._instructions_0xed[0x59] = None            # OUT (C), E
        self._instructions_0xed[0x5a] = self._adc_hl
        self._instructions_0xed[0x5b] = self._load_reg16_from_memory
        self._instructions_0xed[0x5c] = None            # MLT DE
        self._instructions_0xed[0x5d] = None
        self._instructions_0xed[0x5e] = self._im
        self._instructions_0xed[0x5f] = self._load_a_from_i_r_registers

        self._instructions_0xed[0x60] = None            # IN H, (C)
        self._instructions_0xed[0x61] = None            # OUT (C), H
        self._instructions_0xed[0x62] = self._sbc_hl
        self._instructions_0xed[0x63] = self._store_reg16_to_memory
        self._instructions_0xed[0x64] = None            # TST n
        self._instructions_0xed[0x65] = None
        self._instructions_0xed[0x66] = None
        self._instructions_0xed[0x67] = None            # RRD
        self._instructions_0xed[0x68] = None            # IN L, (C)
        self._instructions_0xed[0x69] = None            # OUT (C), L
        self._instructions_0xed[0x6a] = self._adc_hl
        self._instructions_0xed[0x6b] = self._load_reg16_from_memory
        self._instructions_0xed[0x6c] = None            # MLT HL
        self._instructions_0xed[0x6d] = None
        self._instructions_0xed[0x6e] = None
        self._instructions_0xed[0x6f] = None            # RLD

        self._instructions_0xed[0x70] = None            # IN (C)
        self._instructions_0xed[0x71] = None            # OUT (C), 0
        self._instructions_0xed[0x72] = self._sbc_hl
        self._instructions_0xed[0x73] = self._store_reg16_to_memory
        self._instructions_0xed[0x74] = None            # TSTIO n
        self._instructions_0xed[0x75] = None
        self._instructions_0xed[0x76] = None            # SLP
        self._instructions_0xed[0x77] = None
        self._instructions_0xed[0x78] = None            # IN A, (C)
        self._instructions_0xed[0x79] = None            # OUT (C), A
        self._instructions_0xed[0x7a] = self._adc_hl
        self._instructions_0xed[0x7b] = self._load_reg16_from_memory
        self._instructions_0xed[0x7c] = None            # MLT SP
        self._instructions_0xed[0x7d] = None
        self._instructions_0xed[0x7e] = None
        self._instructions_0xed[0x7f] = None

        self._instructions_0xed[0x80] = None
        self._instructions_0xed[0x81] = None
        self._instructions_0xed[0x82] = None
        self._instructions_0xed[0x83] = None            # OTIM
        self._instructions_0xed[0x84] = None
        self._instructions_0xed[0x85] = None
        self._instructions_0xed[0x86] = None
        self._instructions_0xed[0x87] = None
        self._instructions_0xed[0x88] = None
        self._instructions_0xed[0x89] = None
        self._instructions_0xed[0x8a] = None
        self._instructions_0xed[0x8b] = None            # OTDM
        self._instructions_0xed[0x8c] = None
        self._instructions_0xed[0x8d] = None
        self._instructions_0xed[0x8e] = None
        self._instructions_0xed[0x8f] = None

        self._instructions_0xed[0x90] = None
        self._instructions_0xed[0x91] = None
        self._instructions_0xed[0x92] = None
        self._instructions_0xed[0x93] = None            # OTIMR
        self._instructions_0xed[0x94] = None
        self._instructions_0xed[0x95] = None
        self._instructions_0xed[0x96] = None
        self._instructions_0xed[0x97] = None
        self._instructions_0xed[0x98] = None
        self._instructions_0xed[0x99] = None
        self._instructions_0xed[0x9a] = None
        self._instructions_0xed[0x9b] = None            # OTDMR
        self._instructions_0xed[0x9c] = None
        self._instructions_0xed[0x9d] = None
        self._instructions_0xed[0x9e] = None
        self._instructions_0xed[0x9f] = None

        self._instructions_0xed[0xa0] = self._ldi
        self._instructions_0xed[0xa1] = None            # CPI
        self._instructions_0xed[0xa2] = None            # INI
        self._instructions_0xed[0xa3] = None            # OUTI
        self._instructions_0xed[0xa4] = None
        self._instructions_0xed[0xa5] = None
        self._instructions_0xed[0xa6] = None
        self._instructions_0xed[0xa7] = None
        self._instructions_0xed[0xa8] = self._ldd
        self._instructions_0xed[0xa9] = None            # CPD
        self._instructions_0xed[0xaa] = None            # IND
        self._instructions_0xed[0xab] = None            # OUTD
        self._instructions_0xed[0xac] = None
        self._instructions_0xed[0xad] = None
        self._instructions_0xed[0xae] = None
        self._instructions_0xed[0xaf] = None

        self._instructions_0xed[0xb0] = self._ldir
        self._instructions_0xed[0xb1] = None            # CPIR
        self._instructions_0xed[0xb2] = None            # INIR
        self._instructions_0xed[0xb3] = None            # OTIR
        self._instructions_0xed[0xb4] = None
        self._instructions_0xed[0xb5] = None
        self._instructions_0xed[0xb6] = None
        self._instructions_0xed[0xb7] = None
        self._instructions_0xed[0xb8] = self._lddr
        self._instructions_0xed[0xb9] = None            # CPDR
        self._instructions_0xed[0xba] = None            # INDR
        self._instructions_0xed[0xbb] = None            # OTDR
        self._instructions_0xed[0xbc] = None
        self._instructions_0xed[0xbd] = None
        self._instructions_0xed[0xbe] = None
        self._instructions_0xed[0xbf] = None

        self._instructions_0xed[0xc0] = None
        self._instructions_0xed[0xc1] = None
        self._instructions_0xed[0xc2] = None
        self._instructions_0xed[0xc3] = None
        self._instructions_0xed[0xc4] = None
        self._instructions_0xed[0xc5] = None
        self._instructions_0xed[0xc6] = None
        self._instructions_0xed[0xc7] = None
        self._instructions_0xed[0xc8] = None
        self._instructions_0xed[0xc9] = None
        self._instructions_0xed[0xca] = None
        self._instructions_0xed[0xcb] = None
        self._instructions_0xed[0xcc] = None
        self._instructions_0xed[0xcd] = None
        self._instructions_0xed[0xce] = None
        self._instructions_0xed[0xcf] = None

        self._instructions_0xed[0xd0] = None
        self._instructions_0xed[0xd1] = None
        self._instructions_0xed[0xd2] = None
        self._instructions_0xed[0xd3] = None
        self._instructions_0xed[0xd4] = None
        self._instructions_0xed[0xd5] = None
        self._instructions_0xed[0xd6] = None
        self._instructions_0xed[0xd7] = None
        self._instructions_0xed[0xd8] = None
        self._instructions_0xed[0xd9] = None
        self._instructions_0xed[0xda] = None
        self._instructions_0xed[0xdb] = None
        self._instructions_0xed[0xdc] = None
        self._instructions_0xed[0xdd] = None
        self._instructions_0xed[0xde] = None
        self._instructions_0xed[0xdf] = None

        self._instructions_0xed[0xe0] = None
        self._instructions_0xed[0xe1] = None
        self._instructions_0xed[0xe2] = None
        self._instructions_0xed[0xe3] = None
        self._instructions_0xed[0xe4] = None
        self._instructions_0xed[0xe5] = None
        self._instructions_0xed[0xe6] = None
        self._instructions_0xed[0xe7] = None
        self._instructions_0xed[0xe8] = None
        self._instructions_0xed[0xe9] = None
        self._instructions_0xed[0xea] = None
        self._instructions_0xed[0xeb] = None
        self._instructions_0xed[0xec] = None
        self._instructions_0xed[0xed] = None
        self._instructions_0xed[0xee] = None
        self._instructions_0xed[0xef] = None

        self._instructions_0xed[0xf0] = None
        self._instructions_0xed[0xf1] = None
        self._instructions_0xed[0xf2] = None
        self._instructions_0xed[0xf3] = None
        self._instructions_0xed[0xf4] = None
        self._instructions_0xed[0xf5] = None
        self._instructions_0xed[0xf6] = None
        self._instructions_0xed[0xf7] = None
        self._instructions_0xed[0xf8] = None
        self._instructions_0xed[0xf9] = None
        self._instructions_0xed[0xfa] = None
        self._instructions_0xed[0xfb] = None
        self._instructions_0xed[0xfc] = None
        self._instructions_0xed[0xfd] = None
        self._instructions_0xed[0xfe] = None
        self._instructions_0xed[0xff] = None


    def _init_cb_instruction_table(self):
        """ Initialize bit instruction set with 0xCB prefix """
        
        self._instructions_0xcb = [None] * 0x100

        self._instructions_0xcb[0x00] = None        # RLC B
        self._instructions_0xcb[0x01] = None        # RLC C
        self._instructions_0xcb[0x02] = None        # RLC D
        self._instructions_0xcb[0x03] = None        # RLC E
        self._instructions_0xcb[0x04] = None        # RLC H
        self._instructions_0xcb[0x05] = None        # RLC L
        self._instructions_0xcb[0x06] = None        # RLC (HL)
        self._instructions_0xcb[0x07] = None        # RLC A
        self._instructions_0xcb[0x08] = None        # RRC B
        self._instructions_0xcb[0x09] = None        # RRC C
        self._instructions_0xcb[0x0a] = None        # RRC D
        self._instructions_0xcb[0x0b] = None        # RRC E
        self._instructions_0xcb[0x0c] = None        # RRC H
        self._instructions_0xcb[0x0d] = None        # RRC L
        self._instructions_0xcb[0x0e] = None        # RRC (HL)
        self._instructions_0xcb[0x0f] = None        # RRC A

        self._instructions_0xcb[0x10] = None        # RL B
        self._instructions_0xcb[0x11] = None        # RL C
        self._instructions_0xcb[0x12] = None        # RL D
        self._instructions_0xcb[0x13] = None        # RL E
        self._instructions_0xcb[0x14] = None        # RL H
        self._instructions_0xcb[0x15] = None        # RL L
        self._instructions_0xcb[0x16] = None        # RL (HL)
        self._instructions_0xcb[0x17] = None        # RL A
        self._instructions_0xcb[0x18] = None        # RR B
        self._instructions_0xcb[0x19] = None        # RR C
        self._instructions_0xcb[0x1a] = None        # RR D
        self._instructions_0xcb[0x1b] = None        # RR E
        self._instructions_0xcb[0x1c] = None        # RR H
        self._instructions_0xcb[0x1d] = None        # RR L
        self._instructions_0xcb[0x1e] = None        # RR (HL)
        self._instructions_0xcb[0x1f] = None        # RR A

        self._instructions_0xcb[0x20] = None        # SLA B
        self._instructions_0xcb[0x21] = None        # SLA C
        self._instructions_0xcb[0x22] = None        # SLA D
        self._instructions_0xcb[0x23] = None        # SLA E
        self._instructions_0xcb[0x24] = None        # SLA H
        self._instructions_0xcb[0x25] = None        # SLA L
        self._instructions_0xcb[0x26] = None        # SLA (HL)
        self._instructions_0xcb[0x27] = None        # SLA A
        self._instructions_0xcb[0x28] = None        # SRA B
        self._instructions_0xcb[0x29] = None        # SRA C
        self._instructions_0xcb[0x2a] = None        # SRA D
        self._instructions_0xcb[0x2b] = None        # SRA E
        self._instructions_0xcb[0x2c] = None        # SRA H
        self._instructions_0xcb[0x2d] = None        # SRA L
        self._instructions_0xcb[0x2e] = None        # SRA (HL)
        self._instructions_0xcb[0x2f] = None        # SRA A

        self._instructions_0xcb[0x30] = None        # SLL B
        self._instructions_0xcb[0x31] = None        # SLL C
        self._instructions_0xcb[0x32] = None        # SLL D
        self._instructions_0xcb[0x33] = None        # SLL E
        self._instructions_0xcb[0x34] = None        # SLL H
        self._instructions_0xcb[0x35] = None        # SLL L
        self._instructions_0xcb[0x36] = None        # SLL (HL)
        self._instructions_0xcb[0x37] = None        # SLL A
        self._instructions_0xcb[0x38] = None        # SRL B
        self._instructions_0xcb[0x39] = None        # SRL C
        self._instructions_0xcb[0x3a] = None        # SRL D
        self._instructions_0xcb[0x3b] = None        # SRL E
        self._instructions_0xcb[0x3c] = None        # SRL H
        self._instructions_0xcb[0x3d] = None        # SRL L
        self._instructions_0xcb[0x3e] = None        # SRL (HL)
        self._instructions_0xcb[0x3f] = None        # SRL A

        self._instructions_0xcb[0x40] = self._get_bit       # BIT 0, B
        self._instructions_0xcb[0x41] = self._get_bit       # BIT 0, C
        self._instructions_0xcb[0x42] = self._get_bit       # BIT 0, D
        self._instructions_0xcb[0x43] = self._get_bit       # BIT 0, E
        self._instructions_0xcb[0x44] = self._get_bit       # BIT 0, H
        self._instructions_0xcb[0x45] = self._get_bit       # BIT 0, L
        self._instructions_0xcb[0x46] = self._get_bit       # BIT 0, (HL)
        self._instructions_0xcb[0x47] = self._get_bit       # BIT 0, A
        self._instructions_0xcb[0x48] = self._get_bit       # BIT 1, B
        self._instructions_0xcb[0x49] = self._get_bit       # BIT 1, C
        self._instructions_0xcb[0x4a] = self._get_bit       # BIT 1, D
        self._instructions_0xcb[0x4b] = self._get_bit       # BIT 1, E
        self._instructions_0xcb[0x4c] = self._get_bit       # BIT 1, H
        self._instructions_0xcb[0x4d] = self._get_bit       # BIT 1, L
        self._instructions_0xcb[0x4e] = self._get_bit       # BIT 1, (HL)
        self._instructions_0xcb[0x4f] = self._get_bit       # BIT 1, A

        self._instructions_0xcb[0x50] = self._get_bit       # BIT 2, B
        self._instructions_0xcb[0x51] = self._get_bit       # BIT 2, C
        self._instructions_0xcb[0x52] = self._get_bit       # BIT 2, D
        self._instructions_0xcb[0x53] = self._get_bit       # BIT 2, E
        self._instructions_0xcb[0x54] = self._get_bit       # BIT 2, H
        self._instructions_0xcb[0x55] = self._get_bit       # BIT 2, L
        self._instructions_0xcb[0x56] = self._get_bit       # BIT 2, (HL)
        self._instructions_0xcb[0x57] = self._get_bit       # BIT 2, A
        self._instructions_0xcb[0x58] = self._get_bit       # BIT 3, B
        self._instructions_0xcb[0x59] = self._get_bit       # BIT 3, C
        self._instructions_0xcb[0x5a] = self._get_bit       # BIT 3, D
        self._instructions_0xcb[0x5b] = self._get_bit       # BIT 3, E
        self._instructions_0xcb[0x5c] = self._get_bit       # BIT 3, H
        self._instructions_0xcb[0x5d] = self._get_bit       # BIT 3, L
        self._instructions_0xcb[0x5e] = self._get_bit       # BIT 3, (HL)
        self._instructions_0xcb[0x5f] = self._get_bit       # BIT 3, A

        self._instructions_0xcb[0x60] = self._get_bit       # BIT 4, B
        self._instructions_0xcb[0x61] = self._get_bit       # BIT 4, C
        self._instructions_0xcb[0x62] = self._get_bit       # BIT 4, D
        self._instructions_0xcb[0x63] = self._get_bit       # BIT 4, E
        self._instructions_0xcb[0x64] = self._get_bit       # BIT 4, H
        self._instructions_0xcb[0x65] = self._get_bit       # BIT 4, L
        self._instructions_0xcb[0x66] = self._get_bit       # BIT 4, (HL)
        self._instructions_0xcb[0x67] = self._get_bit       # BIT 4, A
        self._instructions_0xcb[0x68] = self._get_bit       # BIT 5, B
        self._instructions_0xcb[0x69] = self._get_bit       # BIT 5, C
        self._instructions_0xcb[0x6a] = self._get_bit       # BIT 5, D
        self._instructions_0xcb[0x6b] = self._get_bit       # BIT 5, E
        self._instructions_0xcb[0x6c] = self._get_bit       # BIT 5, H
        self._instructions_0xcb[0x6d] = self._get_bit       # BIT 5, L
        self._instructions_0xcb[0x6e] = self._get_bit       # BIT 5, (HL)
        self._instructions_0xcb[0x6f] = self._get_bit       # BIT 5, A

        self._instructions_0xcb[0x70] = self._get_bit       # BIT 6, B
        self._instructions_0xcb[0x71] = self._get_bit       # BIT 6, C
        self._instructions_0xcb[0x72] = self._get_bit       # BIT 6, D
        self._instructions_0xcb[0x73] = self._get_bit       # BIT 6, E
        self._instructions_0xcb[0x74] = self._get_bit       # BIT 6, H
        self._instructions_0xcb[0x75] = self._get_bit       # BIT 6, L
        self._instructions_0xcb[0x76] = self._get_bit       # BIT 6, (HL)
        self._instructions_0xcb[0x77] = self._get_bit       # BIT 6, A
        self._instructions_0xcb[0x78] = self._get_bit       # BIT 7, B
        self._instructions_0xcb[0x79] = self._get_bit       # BIT 7, C
        self._instructions_0xcb[0x7a] = self._get_bit       # BIT 7, D
        self._instructions_0xcb[0x7b] = self._get_bit       # BIT 7, E
        self._instructions_0xcb[0x7c] = self._get_bit       # BIT 7, H
        self._instructions_0xcb[0x7d] = self._get_bit       # BIT 7, L
        self._instructions_0xcb[0x7e] = self._get_bit       # BIT 7, (HL)
        self._instructions_0xcb[0x7f] = self._get_bit       # BIT 7, A

        self._instructions_0xcb[0x80] = self._reset_bit     # RES 0, B
        self._instructions_0xcb[0x81] = self._reset_bit     # RES 0, C
        self._instructions_0xcb[0x82] = self._reset_bit     # RES 0, D
        self._instructions_0xcb[0x83] = self._reset_bit     # RES 0, E
        self._instructions_0xcb[0x84] = self._reset_bit     # RES 0, H
        self._instructions_0xcb[0x85] = self._reset_bit     # RES 0, L
        self._instructions_0xcb[0x86] = self._reset_bit     # RES 0, (HL)
        self._instructions_0xcb[0x87] = self._reset_bit     # RES 0, A
        self._instructions_0xcb[0x88] = self._reset_bit     # RES 1, B
        self._instructions_0xcb[0x89] = self._reset_bit     # RES 1, C
        self._instructions_0xcb[0x8a] = self._reset_bit     # RES 1, D
        self._instructions_0xcb[0x8b] = self._reset_bit     # RES 1, E
        self._instructions_0xcb[0x8c] = self._reset_bit     # RES 1, H
        self._instructions_0xcb[0x8d] = self._reset_bit     # RES 1, L
        self._instructions_0xcb[0x8e] = self._reset_bit     # RES 1, (HL)
        self._instructions_0xcb[0x8f] = self._reset_bit     # RES 1, A

        self._instructions_0xcb[0x90] = self._reset_bit     # RES 2, B
        self._instructions_0xcb[0x91] = self._reset_bit     # RES 2, C
        self._instructions_0xcb[0x92] = self._reset_bit     # RES 2, D
        self._instructions_0xcb[0x93] = self._reset_bit     # RES 2, E
        self._instructions_0xcb[0x94] = self._reset_bit     # RES 2, H
        self._instructions_0xcb[0x95] = self._reset_bit     # RES 2, L
        self._instructions_0xcb[0x96] = self._reset_bit     # RES 2, (HL)
        self._instructions_0xcb[0x97] = self._reset_bit     # RES 2, A
        self._instructions_0xcb[0x98] = self._reset_bit     # RES 3, B
        self._instructions_0xcb[0x99] = self._reset_bit     # RES 3, C
        self._instructions_0xcb[0x9a] = self._reset_bit     # RES 3, D
        self._instructions_0xcb[0x9b] = self._reset_bit     # RES 3, E
        self._instructions_0xcb[0x9c] = self._reset_bit     # RES 3, H
        self._instructions_0xcb[0x9d] = self._reset_bit     # RES 3, L
        self._instructions_0xcb[0x9e] = self._reset_bit     # RES 3, (HL)
        self._instructions_0xcb[0x9f] = self._reset_bit     # RES 3, A

        self._instructions_0xcb[0xa0] = self._reset_bit     # RES 4, B
        self._instructions_0xcb[0xa1] = self._reset_bit     # RES 4, C
        self._instructions_0xcb[0xa2] = self._reset_bit     # RES 4, D
        self._instructions_0xcb[0xa3] = self._reset_bit     # RES 4, E
        self._instructions_0xcb[0xa4] = self._reset_bit     # RES 4, H
        self._instructions_0xcb[0xa5] = self._reset_bit     # RES 4, L
        self._instructions_0xcb[0xa6] = self._reset_bit     # RES 4, (HL)
        self._instructions_0xcb[0xa7] = self._reset_bit     # RES 4, A
        self._instructions_0xcb[0xa8] = self._reset_bit     # RES 5, B
        self._instructions_0xcb[0xa9] = self._reset_bit     # RES 5, C
        self._instructions_0xcb[0xaa] = self._reset_bit     # RES 5, D
        self._instructions_0xcb[0xab] = self._reset_bit     # RES 5, E
        self._instructions_0xcb[0xac] = self._reset_bit     # RES 5, H
        self._instructions_0xcb[0xad] = self._reset_bit     # RES 5, L
        self._instructions_0xcb[0xae] = self._reset_bit     # RES 5, (HL)
        self._instructions_0xcb[0xaf] = self._reset_bit     # RES 5, A

        self._instructions_0xcb[0xb0] = self._reset_bit     # RES 6, B
        self._instructions_0xcb[0xb1] = self._reset_bit     # RES 6, C
        self._instructions_0xcb[0xb2] = self._reset_bit     # RES 6, D
        self._instructions_0xcb[0xb3] = self._reset_bit     # RES 6, E
        self._instructions_0xcb[0xb4] = self._reset_bit     # RES 6, H
        self._instructions_0xcb[0xb5] = self._reset_bit     # RES 6, L
        self._instructions_0xcb[0xb6] = self._reset_bit     # RES 6, (HL)
        self._instructions_0xcb[0xb7] = self._reset_bit     # RES 6, A
        self._instructions_0xcb[0xb8] = self._reset_bit     # RES 7, B
        self._instructions_0xcb[0xb9] = self._reset_bit     # RES 7, C
        self._instructions_0xcb[0xba] = self._reset_bit     # RES 7, D
        self._instructions_0xcb[0xbb] = self._reset_bit     # RES 7, E
        self._instructions_0xcb[0xbc] = self._reset_bit     # RES 7, H
        self._instructions_0xcb[0xbd] = self._reset_bit     # RES 7, L
        self._instructions_0xcb[0xbe] = self._reset_bit     # RES 7, (HL)
        self._instructions_0xcb[0xbf] = self._reset_bit     # RES 7, A

        self._instructions_0xcb[0xc0] = self._set_bit       # SET 0, B
        self._instructions_0xcb[0xc1] = self._set_bit       # SET 0, C
        self._instructions_0xcb[0xc2] = self._set_bit       # SET 0, D
        self._instructions_0xcb[0xc3] = self._set_bit       # SET 0, E
        self._instructions_0xcb[0xc4] = self._set_bit       # SET 0, H
        self._instructions_0xcb[0xc5] = self._set_bit       # SET 0, L
        self._instructions_0xcb[0xc6] = self._set_bit       # SET 0, (HL)
        self._instructions_0xcb[0xc7] = self._set_bit       # SET 0, A
        self._instructions_0xcb[0xc8] = self._set_bit       # SET 1, B
        self._instructions_0xcb[0xc9] = self._set_bit       # SET 1, C
        self._instructions_0xcb[0xca] = self._set_bit       # SET 1, D
        self._instructions_0xcb[0xcb] = self._set_bit       # SET 1, E
        self._instructions_0xcb[0xcc] = self._set_bit       # SET 1, H
        self._instructions_0xcb[0xcd] = self._set_bit       # SET 1, L
        self._instructions_0xcb[0xce] = self._set_bit       # SET 1, (HL)
        self._instructions_0xcb[0xcf] = self._set_bit       # SET 1, A

        self._instructions_0xcb[0xd0] = self._set_bit       # SET 2, B
        self._instructions_0xcb[0xd1] = self._set_bit       # SET 2, C
        self._instructions_0xcb[0xd2] = self._set_bit       # SET 2, D
        self._instructions_0xcb[0xd3] = self._set_bit       # SET 2, E
        self._instructions_0xcb[0xd4] = self._set_bit       # SET 2, H
        self._instructions_0xcb[0xd5] = self._set_bit       # SET 2, L
        self._instructions_0xcb[0xd6] = self._set_bit       # SET 2, (HL)
        self._instructions_0xcb[0xd7] = self._set_bit       # SET 2, A
        self._instructions_0xcb[0xd8] = self._set_bit       # SET 3, B
        self._instructions_0xcb[0xd9] = self._set_bit       # SET 3, C
        self._instructions_0xcb[0xda] = self._set_bit       # SET 3, D
        self._instructions_0xcb[0xdb] = self._set_bit       # SET 3, E
        self._instructions_0xcb[0xdc] = self._set_bit       # SET 3, H
        self._instructions_0xcb[0xdd] = self._set_bit       # SET 3, L
        self._instructions_0xcb[0xde] = self._set_bit       # SET 3, (HL)
        self._instructions_0xcb[0xdf] = self._set_bit       # SET 3, A

        self._instructions_0xcb[0xe0] = self._set_bit       # SET 4, B
        self._instructions_0xcb[0xe1] = self._set_bit       # SET 4, C
        self._instructions_0xcb[0xe2] = self._set_bit       # SET 4, D
        self._instructions_0xcb[0xe3] = self._set_bit       # SET 4, E
        self._instructions_0xcb[0xe4] = self._set_bit       # SET 4, H
        self._instructions_0xcb[0xe5] = self._set_bit       # SET 4, L
        self._instructions_0xcb[0xe6] = self._set_bit       # SET 4, (HL)
        self._instructions_0xcb[0xe7] = self._set_bit       # SET 4, A
        self._instructions_0xcb[0xe8] = self._set_bit       # SET 5, B
        self._instructions_0xcb[0xe9] = self._set_bit       # SET 5, C
        self._instructions_0xcb[0xea] = self._set_bit       # SET 5, D
        self._instructions_0xcb[0xeb] = self._set_bit       # SET 5, E
        self._instructions_0xcb[0xec] = self._set_bit       # SET 5, H
        self._instructions_0xcb[0xed] = self._set_bit       # SET 5, L
        self._instructions_0xcb[0xee] = self._set_bit       # SET 5, (HL)
        self._instructions_0xcb[0xef] = self._set_bit       # SET 5, A

        self._instructions_0xcb[0xf0] = self._set_bit       # SET 6, B
        self._instructions_0xcb[0xf1] = self._set_bit       # SET 6, C
        self._instructions_0xcb[0xf2] = self._set_bit       # SET 6, D
        self._instructions_0xcb[0xf3] = self._set_bit       # SET 6, E
        self._instructions_0xcb[0xf4] = self._set_bit       # SET 6, H
        self._instructions_0xcb[0xf5] = self._set_bit       # SET 6, L
        self._instructions_0xcb[0xf6] = self._set_bit       # SET 6, (HL)
        self._instructions_0xcb[0xf7] = self._set_bit       # SET 6, A
        self._instructions_0xcb[0xf8] = self._set_bit       # SET 7, B
        self._instructions_0xcb[0xf9] = self._set_bit       # SET 7, C
        self._instructions_0xcb[0xfa] = self._set_bit       # SET 7, D
        self._instructions_0xcb[0xfb] = self._set_bit       # SET 7, E
        self._instructions_0xcb[0xfc] = self._set_bit       # SET 7, H
        self._instructions_0xcb[0xfd] = self._set_bit       # SET 7, L
        self._instructions_0xcb[0xfe] = self._set_bit       # SET 7, (HL)
        self._instructions_0xcb[0xff] = self._set_bit       # SET 7, A


    def _init_dd_instruction_table(self):
        """ Initialize IX instruction set with 0xDD prefix """
        
        self._instructions_0xdd = [None] * 0x100

        self._instructions_0xdd[0x00] = None
        self._instructions_0xdd[0x01] = None
        self._instructions_0xdd[0x02] = None
        self._instructions_0xdd[0x03] = None
        self._instructions_0xdd[0x04] = None
        self._instructions_0xdd[0x05] = None
        self._instructions_0xdd[0x06] = None
        self._instructions_0xdd[0x07] = None
        self._instructions_0xdd[0x08] = None
        self._instructions_0xdd[0x09] = None
        self._instructions_0xdd[0x0a] = None
        self._instructions_0xdd[0x0b] = None
        self._instructions_0xdd[0x0c] = None
        self._instructions_0xdd[0x0d] = None
        self._instructions_0xdd[0x0e] = None
        self._instructions_0xdd[0x0f] = None

        self._instructions_0xdd[0x10] = None
        self._instructions_0xdd[0x11] = None
        self._instructions_0xdd[0x12] = None
        self._instructions_0xdd[0x13] = None
        self._instructions_0xdd[0x14] = None
        self._instructions_0xdd[0x15] = None
        self._instructions_0xdd[0x16] = None
        self._instructions_0xdd[0x17] = None
        self._instructions_0xdd[0x18] = None
        self._instructions_0xdd[0x19] = None
        self._instructions_0xdd[0x1a] = None
        self._instructions_0xdd[0x1b] = None
        self._instructions_0xdd[0x1c] = None
        self._instructions_0xdd[0x1d] = None
        self._instructions_0xdd[0x1e] = None
        self._instructions_0xdd[0x1f] = None

        self._instructions_0xdd[0x20] = None
        self._instructions_0xdd[0x21] = None
        self._instructions_0xdd[0x22] = None
        self._instructions_0xdd[0x23] = None
        self._instructions_0xdd[0x24] = None
        self._instructions_0xdd[0x25] = None
        self._instructions_0xdd[0x26] = None
        self._instructions_0xdd[0x27] = None
        self._instructions_0xdd[0x28] = None
        self._instructions_0xdd[0x29] = None
        self._instructions_0xdd[0x2a] = None
        self._instructions_0xdd[0x2b] = None
        self._instructions_0xdd[0x2c] = None
        self._instructions_0xdd[0x2d] = None
        self._instructions_0xdd[0x2e] = None
        self._instructions_0xdd[0x2f] = None

        self._instructions_0xcb[0x30] = None
        self._instructions_0xdd[0x31] = None
        self._instructions_0xdd[0x32] = None
        self._instructions_0xdd[0x33] = None
        self._instructions_0xdd[0x34] = self._inc_mem_indexed
        self._instructions_0xdd[0x35] = self._dec_mem_indexed
        self._instructions_0xdd[0x36] = self._store_value_to_indexed_mem
        self._instructions_0xdd[0x37] = None
        self._instructions_0xdd[0x38] = None
        self._instructions_0xdd[0x39] = None
        self._instructions_0xdd[0x3a] = None
        self._instructions_0xdd[0x3b] = None
        self._instructions_0xdd[0x3c] = None
        self._instructions_0xdd[0x3d] = None
        self._instructions_0xdd[0x3e] = None
        self._instructions_0xdd[0x3f] = None

        self._instructions_0xcb[0x40] = None
        self._instructions_0xdd[0x41] = None
        self._instructions_0xdd[0x42] = None
        self._instructions_0xdd[0x43] = None
        self._instructions_0xdd[0x44] = None
        self._instructions_0xdd[0x45] = None
        self._instructions_0xdd[0x46] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x47] = None
        self._instructions_0xdd[0x48] = None
        self._instructions_0xdd[0x49] = None
        self._instructions_0xdd[0x4a] = None
        self._instructions_0xdd[0x4b] = None
        self._instructions_0xdd[0x4c] = None
        self._instructions_0xdd[0x4d] = None
        self._instructions_0xdd[0x4e] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x4f] = None

        self._instructions_0xdd[0x50] = None
        self._instructions_0xdd[0x51] = None
        self._instructions_0xdd[0x52] = None
        self._instructions_0xdd[0x53] = None
        self._instructions_0xdd[0x54] = None
        self._instructions_0xdd[0x55] = None
        self._instructions_0xdd[0x56] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x57] = None
        self._instructions_0xdd[0x58] = None
        self._instructions_0xdd[0x59] = None
        self._instructions_0xdd[0x5a] = None
        self._instructions_0xdd[0x5b] = None
        self._instructions_0xdd[0x5c] = None
        self._instructions_0xdd[0x5d] = None
        self._instructions_0xdd[0x5e] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x5f] = None

        self._instructions_0xdd[0x60] = None
        self._instructions_0xdd[0x61] = None
        self._instructions_0xdd[0x62] = None
        self._instructions_0xdd[0x63] = None
        self._instructions_0xdd[0x64] = None
        self._instructions_0xdd[0x65] = None
        self._instructions_0xdd[0x66] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x67] = None
        self._instructions_0xdd[0x68] = None
        self._instructions_0xdd[0x69] = None
        self._instructions_0xdd[0x6a] = None
        self._instructions_0xdd[0x6b] = None
        self._instructions_0xdd[0x6c] = None
        self._instructions_0xdd[0x6d] = None
        self._instructions_0xdd[0x6e] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x6f] = None

        self._instructions_0xdd[0x70] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x71] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x72] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x73] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x74] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x75] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x76] = None
        self._instructions_0xdd[0x77] = self._store_reg_to_indexed_mem
        self._instructions_0xdd[0x78] = None
        self._instructions_0xdd[0x79] = None
        self._instructions_0xdd[0x7a] = None
        self._instructions_0xdd[0x7b] = None
        self._instructions_0xdd[0x7c] = None
        self._instructions_0xdd[0x7d] = None
        self._instructions_0xdd[0x7e] = self._load_reg_from_indexed_mem
        self._instructions_0xdd[0x7f] = None

        self._instructions_0xdd[0x80] = None
        self._instructions_0xdd[0x81] = None
        self._instructions_0xdd[0x82] = None
        self._instructions_0xdd[0x83] = None
        self._instructions_0xdd[0x84] = None
        self._instructions_0xdd[0x85] = None
        self._instructions_0xdd[0x86] = self._alu_mem_indexed
        self._instructions_0xdd[0x87] = None
        self._instructions_0xdd[0x88] = None
        self._instructions_0xdd[0x89] = None
        self._instructions_0xdd[0x8a] = None
        self._instructions_0xdd[0x8b] = None
        self._instructions_0xdd[0x8c] = None
        self._instructions_0xdd[0x8d] = None
        self._instructions_0xdd[0x8e] = self._alu_mem_indexed
        self._instructions_0xdd[0x8f] = None

        self._instructions_0xdd[0x90] = None
        self._instructions_0xdd[0x91] = None
        self._instructions_0xdd[0x92] = None
        self._instructions_0xdd[0x93] = None
        self._instructions_0xdd[0x94] = None
        self._instructions_0xdd[0x95] = None
        self._instructions_0xdd[0x96] = self._alu_mem_indexed
        self._instructions_0xdd[0x97] = None
        self._instructions_0xdd[0x98] = None
        self._instructions_0xdd[0x99] = None
        self._instructions_0xdd[0x9a] = None
        self._instructions_0xdd[0x9b] = None
        self._instructions_0xdd[0x9c] = None
        self._instructions_0xdd[0x9d] = None
        self._instructions_0xdd[0x9e] = self._alu_mem_indexed
        self._instructions_0xdd[0x9f] = None

        self._instructions_0xdd[0xa0] = None
        self._instructions_0xdd[0xa1] = None
        self._instructions_0xdd[0xa2] = None
        self._instructions_0xdd[0xa3] = None
        self._instructions_0xdd[0xa4] = None
        self._instructions_0xdd[0xa5] = None
        self._instructions_0xdd[0xa6] = self._alu_mem_indexed
        self._instructions_0xdd[0xa7] = None
        self._instructions_0xdd[0xa8] = None
        self._instructions_0xdd[0xa9] = None
        self._instructions_0xdd[0xaa] = None
        self._instructions_0xdd[0xab] = None
        self._instructions_0xdd[0xac] = None
        self._instructions_0xdd[0xad] = None
        self._instructions_0xdd[0xae] = self._alu_mem_indexed
        self._instructions_0xdd[0xaf] = None

        self._instructions_0xdd[0xb0] = None
        self._instructions_0xdd[0xb1] = None
        self._instructions_0xdd[0xb2] = None
        self._instructions_0xdd[0xb3] = None
        self._instructions_0xdd[0xb4] = None
        self._instructions_0xdd[0xb5] = None
        self._instructions_0xdd[0xb6] = self._alu_mem_indexed
        self._instructions_0xdd[0xb7] = None
        self._instructions_0xdd[0xb8] = None
        self._instructions_0xdd[0xb9] = None
        self._instructions_0xdd[0xba] = None
        self._instructions_0xdd[0xbb] = None
        self._instructions_0xdd[0xbc] = None
        self._instructions_0xdd[0xbd] = None
        self._instructions_0xdd[0xbe] = self._alu_mem_indexed
        self._instructions_0xdd[0xbf] = None

        self._instructions_0xdd[0xc0] = None
        self._instructions_0xdd[0xc1] = None
        self._instructions_0xdd[0xc2] = None
        self._instructions_0xdd[0xc3] = None
        self._instructions_0xdd[0xc4] = None
        self._instructions_0xdd[0xc5] = None
        self._instructions_0xdd[0xc6] = None
        self._instructions_0xdd[0xc7] = None
        self._instructions_0xdd[0xc8] = None
        self._instructions_0xdd[0xc9] = None
        self._instructions_0xdd[0xca] = None
        self._instructions_0xdd[0xcb] = None
        self._instructions_0xdd[0xcc] = None
        self._instructions_0xdd[0xcd] = None
        self._instructions_0xdd[0xce] = None
        self._instructions_0xdd[0xcf] = None

        self._instructions_0xdd[0xd0] = None
        self._instructions_0xdd[0xd1] = None
        self._instructions_0xdd[0xd2] = None
        self._instructions_0xdd[0xd3] = None
        self._instructions_0xdd[0xd4] = None
        self._instructions_0xdd[0xd5] = None
        self._instructions_0xdd[0xd6] = None
        self._instructions_0xdd[0xd7] = None
        self._instructions_0xdd[0xd8] = None
        self._instructions_0xdd[0xd9] = None
        self._instructions_0xdd[0xda] = None
        self._instructions_0xdd[0xdb] = None
        self._instructions_0xdd[0xdc] = None
        self._instructions_0xdd[0xdd] = None
        self._instructions_0xdd[0xde] = None
        self._instructions_0xdd[0xdf] = None

        self._instructions_0xdd[0xe0] = None
        self._instructions_0xdd[0xe1] = None
        self._instructions_0xdd[0xe2] = None
        self._instructions_0xdd[0xe3] = None
        self._instructions_0xdd[0xe4] = None
        self._instructions_0xdd[0xe5] = None
        self._instructions_0xdd[0xe6] = None
        self._instructions_0xdd[0xe7] = None
        self._instructions_0xdd[0xe8] = None
        self._instructions_0xdd[0xe9] = None
        self._instructions_0xdd[0xea] = None
        self._instructions_0xdd[0xeb] = None
        self._instructions_0xdd[0xec] = None
        self._instructions_0xdd[0xed] = None
        self._instructions_0xdd[0xee] = None
        self._instructions_0xdd[0xef] = None

        self._instructions_0xdd[0xf0] = None
        self._instructions_0xdd[0xf1] = None
        self._instructions_0xdd[0xf2] = None
        self._instructions_0xdd[0xf3] = None
        self._instructions_0xdd[0xf4] = None
        self._instructions_0xdd[0xf5] = None
        self._instructions_0xdd[0xf6] = None
        self._instructions_0xdd[0xf7] = None
        self._instructions_0xdd[0xf8] = None
        self._instructions_0xdd[0xf9] = None
        self._instructions_0xdd[0xfa] = None
        self._instructions_0xdd[0xfb] = None
        self._instructions_0xdd[0xfc] = None
        self._instructions_0xdd[0xfd] = None
        self._instructions_0xdd[0xfe] = None
        self._instructions_0xdd[0xff] = None


    def _init_ddcb_instruction_table(self):
        """ Initialize IX bit instruction set with 0xDD 0xCB prefix """
        
        self._instructions_0xddcb = [None] * 0x100

        self._instructions_0xddcb[0x00] = None
        self._instructions_0xddcb[0x01] = None
        self._instructions_0xddcb[0x02] = None
        self._instructions_0xddcb[0x03] = None
        self._instructions_0xddcb[0x04] = None
        self._instructions_0xddcb[0x05] = None
        self._instructions_0xddcb[0x06] = None
        self._instructions_0xddcb[0x07] = None
        self._instructions_0xddcb[0x08] = None
        self._instructions_0xddcb[0x09] = None
        self._instructions_0xddcb[0x0a] = None
        self._instructions_0xddcb[0x0b] = None
        self._instructions_0xddcb[0x0c] = None
        self._instructions_0xddcb[0x0d] = None
        self._instructions_0xddcb[0x0e] = None
        self._instructions_0xddcb[0x0f] = None

        self._instructions_0xddcb[0x10] = None
        self._instructions_0xddcb[0x11] = None
        self._instructions_0xddcb[0x12] = None
        self._instructions_0xddcb[0x13] = None
        self._instructions_0xddcb[0x14] = None
        self._instructions_0xddcb[0x15] = None
        self._instructions_0xddcb[0x16] = None
        self._instructions_0xddcb[0x17] = None
        self._instructions_0xddcb[0x18] = None
        self._instructions_0xddcb[0x19] = None
        self._instructions_0xddcb[0x1a] = None
        self._instructions_0xddcb[0x1b] = None
        self._instructions_0xddcb[0x1c] = None
        self._instructions_0xddcb[0x1d] = None
        self._instructions_0xddcb[0x1e] = None
        self._instructions_0xddcb[0x1f] = None

        self._instructions_0xddcb[0x20] = None
        self._instructions_0xddcb[0x21] = None
        self._instructions_0xddcb[0x22] = None
        self._instructions_0xddcb[0x23] = None
        self._instructions_0xddcb[0x24] = None
        self._instructions_0xddcb[0x25] = None
        self._instructions_0xddcb[0x26] = None
        self._instructions_0xddcb[0x27] = None
        self._instructions_0xddcb[0x28] = None
        self._instructions_0xddcb[0x29] = None
        self._instructions_0xddcb[0x2a] = None
        self._instructions_0xddcb[0x2b] = None
        self._instructions_0xddcb[0x2c] = None
        self._instructions_0xddcb[0x2d] = None
        self._instructions_0xddcb[0x2e] = None
        self._instructions_0xddcb[0x2f] = None

        self._instructions_0xddcb[0x30] = None
        self._instructions_0xddcb[0x31] = None
        self._instructions_0xddcb[0x32] = None
        self._instructions_0xddcb[0x33] = None
        self._instructions_0xddcb[0x34] = None
        self._instructions_0xddcb[0x35] = None
        self._instructions_0xddcb[0x36] = None
        self._instructions_0xddcb[0x37] = None
        self._instructions_0xddcb[0x38] = None
        self._instructions_0xddcb[0x39] = None
        self._instructions_0xddcb[0x3a] = None
        self._instructions_0xddcb[0x3b] = None
        self._instructions_0xddcb[0x3c] = None
        self._instructions_0xddcb[0x3d] = None
        self._instructions_0xddcb[0x3e] = None
        self._instructions_0xddcb[0x3f] = None

        self._instructions_0xddcb[0x40] = None
        self._instructions_0xddcb[0x41] = None
        self._instructions_0xddcb[0x42] = None
        self._instructions_0xddcb[0x43] = None
        self._instructions_0xddcb[0x44] = None
        self._instructions_0xddcb[0x45] = None
        self._instructions_0xddcb[0x46] = self._get_bit_indexed
        self._instructions_0xddcb[0x47] = None
        self._instructions_0xddcb[0x48] = None
        self._instructions_0xddcb[0x49] = None
        self._instructions_0xddcb[0x4a] = None
        self._instructions_0xddcb[0x4b] = None
        self._instructions_0xddcb[0x4c] = None
        self._instructions_0xddcb[0x4d] = None
        self._instructions_0xddcb[0x4e] = self._get_bit_indexed
        self._instructions_0xddcb[0x4f] = None

        self._instructions_0xddcb[0x50] = None
        self._instructions_0xddcb[0x51] = None
        self._instructions_0xddcb[0x52] = None
        self._instructions_0xddcb[0x53] = None
        self._instructions_0xddcb[0x54] = None
        self._instructions_0xddcb[0x55] = None
        self._instructions_0xddcb[0x56] = self._get_bit_indexed
        self._instructions_0xddcb[0x57] = None
        self._instructions_0xddcb[0x58] = None
        self._instructions_0xddcb[0x59] = None
        self._instructions_0xddcb[0x5a] = None
        self._instructions_0xddcb[0x5b] = None
        self._instructions_0xddcb[0x5c] = None
        self._instructions_0xddcb[0x5d] = None
        self._instructions_0xddcb[0x5e] = self._get_bit_indexed
        self._instructions_0xddcb[0x5f] = None

        self._instructions_0xddcb[0x60] = None
        self._instructions_0xddcb[0x61] = None
        self._instructions_0xddcb[0x62] = None
        self._instructions_0xddcb[0x63] = None
        self._instructions_0xddcb[0x64] = None
        self._instructions_0xddcb[0x65] = None
        self._instructions_0xddcb[0x66] = self._get_bit_indexed
        self._instructions_0xddcb[0x67] = None
        self._instructions_0xddcb[0x68] = None
        self._instructions_0xddcb[0x69] = None
        self._instructions_0xddcb[0x6a] = None
        self._instructions_0xddcb[0x6b] = None
        self._instructions_0xddcb[0x6c] = None
        self._instructions_0xddcb[0x6d] = None
        self._instructions_0xddcb[0x6e] = self._get_bit_indexed
        self._instructions_0xddcb[0x6f] = None

        self._instructions_0xddcb[0x70] = None
        self._instructions_0xddcb[0x71] = None
        self._instructions_0xddcb[0x72] = None
        self._instructions_0xddcb[0x73] = None
        self._instructions_0xddcb[0x74] = None
        self._instructions_0xddcb[0x75] = None
        self._instructions_0xddcb[0x76] = self._get_bit_indexed
        self._instructions_0xddcb[0x77] = None
        self._instructions_0xddcb[0x78] = None
        self._instructions_0xddcb[0x79] = None
        self._instructions_0xddcb[0x7a] = None
        self._instructions_0xddcb[0x7b] = None
        self._instructions_0xddcb[0x7c] = None
        self._instructions_0xddcb[0x7d] = None
        self._instructions_0xddcb[0x7e] = self._get_bit_indexed
        self._instructions_0xddcb[0x7f] = None

        self._instructions_0xddcb[0x80] = None
        self._instructions_0xddcb[0x81] = None
        self._instructions_0xddcb[0x82] = None
        self._instructions_0xddcb[0x83] = None
        self._instructions_0xddcb[0x84] = None
        self._instructions_0xddcb[0x85] = None
        self._instructions_0xddcb[0x86] = self._reset_bit_indexed
        self._instructions_0xddcb[0x87] = None
        self._instructions_0xddcb[0x88] = None
        self._instructions_0xddcb[0x89] = None
        self._instructions_0xddcb[0x8a] = None
        self._instructions_0xddcb[0x8b] = None
        self._instructions_0xddcb[0x8c] = None
        self._instructions_0xddcb[0x8d] = None
        self._instructions_0xddcb[0x8e] = self._reset_bit_indexed
        self._instructions_0xddcb[0x8f] = None

        self._instructions_0xddcb[0x90] = None
        self._instructions_0xddcb[0x91] = None
        self._instructions_0xddcb[0x92] = None
        self._instructions_0xddcb[0x93] = None
        self._instructions_0xddcb[0x94] = None
        self._instructions_0xddcb[0x95] = None
        self._instructions_0xddcb[0x96] = self._reset_bit_indexed
        self._instructions_0xddcb[0x97] = None
        self._instructions_0xddcb[0x98] = None
        self._instructions_0xddcb[0x99] = None
        self._instructions_0xddcb[0x9a] = None
        self._instructions_0xddcb[0x9b] = None
        self._instructions_0xddcb[0x9c] = None
        self._instructions_0xddcb[0x9d] = None
        self._instructions_0xddcb[0x9e] = self._reset_bit_indexed
        self._instructions_0xddcb[0x9f] = None

        self._instructions_0xddcb[0xa0] = None
        self._instructions_0xddcb[0xa1] = None
        self._instructions_0xddcb[0xa2] = None
        self._instructions_0xddcb[0xa3] = None
        self._instructions_0xddcb[0xa4] = None
        self._instructions_0xddcb[0xa5] = None
        self._instructions_0xddcb[0xa6] = self._reset_bit_indexed
        self._instructions_0xddcb[0xa7] = None
        self._instructions_0xddcb[0xa8] = None
        self._instructions_0xddcb[0xa9] = None
        self._instructions_0xddcb[0xaa] = None
        self._instructions_0xddcb[0xab] = None
        self._instructions_0xddcb[0xac] = None
        self._instructions_0xddcb[0xad] = None
        self._instructions_0xddcb[0xae] = self._reset_bit_indexed
        self._instructions_0xddcb[0xaf] = None

        self._instructions_0xddcb[0xb0] = None
        self._instructions_0xddcb[0xb1] = None
        self._instructions_0xddcb[0xb2] = None
        self._instructions_0xddcb[0xb3] = None
        self._instructions_0xddcb[0xb4] = None
        self._instructions_0xddcb[0xb5] = None
        self._instructions_0xddcb[0xb6] = self._reset_bit_indexed
        self._instructions_0xddcb[0xb7] = None
        self._instructions_0xddcb[0xb8] = None
        self._instructions_0xddcb[0xb9] = None
        self._instructions_0xddcb[0xba] = None
        self._instructions_0xddcb[0xbb] = None
        self._instructions_0xddcb[0xbc] = None
        self._instructions_0xddcb[0xbd] = None
        self._instructions_0xddcb[0xbe] = self._reset_bit_indexed
        self._instructions_0xddcb[0xbf] = None

        self._instructions_0xddcb[0xc0] = None
        self._instructions_0xddcb[0xc1] = None
        self._instructions_0xddcb[0xc2] = None
        self._instructions_0xddcb[0xc3] = None
        self._instructions_0xddcb[0xc4] = None
        self._instructions_0xddcb[0xc5] = None
        self._instructions_0xddcb[0xc6] = self._set_bit_indexed
        self._instructions_0xddcb[0xc7] = None
        self._instructions_0xddcb[0xc8] = None
        self._instructions_0xddcb[0xc9] = None
        self._instructions_0xddcb[0xca] = None
        self._instructions_0xddcb[0xcb] = None
        self._instructions_0xddcb[0xcc] = None
        self._instructions_0xddcb[0xcd] = None
        self._instructions_0xddcb[0xce] = self._set_bit_indexed
        self._instructions_0xddcb[0xcf] = None

        self._instructions_0xddcb[0xd0] = None
        self._instructions_0xddcb[0xd1] = None
        self._instructions_0xddcb[0xd2] = None
        self._instructions_0xddcb[0xd3] = None
        self._instructions_0xddcb[0xd4] = None
        self._instructions_0xddcb[0xd5] = None
        self._instructions_0xddcb[0xd6] = self._set_bit_indexed
        self._instructions_0xddcb[0xd7] = None
        self._instructions_0xddcb[0xd8] = None
        self._instructions_0xddcb[0xd9] = None
        self._instructions_0xddcb[0xda] = None
        self._instructions_0xddcb[0xdb] = None
        self._instructions_0xddcb[0xdc] = None
        self._instructions_0xddcb[0xdd] = None
        self._instructions_0xddcb[0xde] = self._set_bit_indexed
        self._instructions_0xddcb[0xdf] = None

        self._instructions_0xddcb[0xe0] = None
        self._instructions_0xddcb[0xe1] = None
        self._instructions_0xddcb[0xe2] = None
        self._instructions_0xddcb[0xe3] = None
        self._instructions_0xddcb[0xe4] = None
        self._instructions_0xddcb[0xe5] = None
        self._instructions_0xddcb[0xe6] = self._set_bit_indexed
        self._instructions_0xddcb[0xe7] = None
        self._instructions_0xddcb[0xe8] = None
        self._instructions_0xddcb[0xe9] = None
        self._instructions_0xddcb[0xea] = None
        self._instructions_0xddcb[0xeb] = None
        self._instructions_0xddcb[0xec] = None
        self._instructions_0xddcb[0xed] = None
        self._instructions_0xddcb[0xee] = self._set_bit_indexed
        self._instructions_0xddcb[0xef] = None

        self._instructions_0xddcb[0xf0] = None
        self._instructions_0xddcb[0xf1] = None
        self._instructions_0xddcb[0xf2] = None
        self._instructions_0xddcb[0xf3] = None
        self._instructions_0xddcb[0xf4] = None
        self._instructions_0xddcb[0xf5] = None
        self._instructions_0xddcb[0xf6] = self._set_bit_indexed
        self._instructions_0xddcb[0xf7] = None
        self._instructions_0xddcb[0xf8] = None
        self._instructions_0xddcb[0xf9] = None
        self._instructions_0xddcb[0xfa] = None
        self._instructions_0xddcb[0xfb] = None
        self._instructions_0xddcb[0xfc] = None
        self._instructions_0xddcb[0xfd] = None
        self._instructions_0xddcb[0xfe] = self._set_bit_indexed
        self._instructions_0xddcb[0xff] = None


    def _init_fd_instruction_table(self):
        """ Initialize IY instruction set with 0xFD prefix """
        
        self._instructions_0xfd = [None] * 0x100

        self._instructions_0xfd[0x00] = None
        self._instructions_0xfd[0x01] = None
        self._instructions_0xfd[0x02] = None
        self._instructions_0xfd[0x03] = None
        self._instructions_0xfd[0x04] = None
        self._instructions_0xfd[0x05] = None
        self._instructions_0xfd[0x06] = None
        self._instructions_0xfd[0x07] = None
        self._instructions_0xfd[0x08] = None
        self._instructions_0xfd[0x09] = None
        self._instructions_0xfd[0x0a] = None
        self._instructions_0xfd[0x0b] = None
        self._instructions_0xfd[0x0c] = None
        self._instructions_0xfd[0x0d] = None
        self._instructions_0xfd[0x0e] = None
        self._instructions_0xfd[0x0f] = None

        self._instructions_0xfd[0x10] = None
        self._instructions_0xfd[0x11] = None
        self._instructions_0xfd[0x12] = None
        self._instructions_0xfd[0x13] = None
        self._instructions_0xfd[0x14] = None
        self._instructions_0xfd[0x15] = None
        self._instructions_0xfd[0x16] = None
        self._instructions_0xfd[0x17] = None
        self._instructions_0xfd[0x18] = None
        self._instructions_0xfd[0x19] = None
        self._instructions_0xfd[0x1a] = None
        self._instructions_0xfd[0x1b] = None
        self._instructions_0xfd[0x1c] = None
        self._instructions_0xfd[0x1d] = None
        self._instructions_0xfd[0x1e] = None
        self._instructions_0xfd[0x1f] = None

        self._instructions_0xfd[0x20] = None
        self._instructions_0xfd[0x21] = self._load_iy_immediate
        self._instructions_0xfd[0x22] = None
        self._instructions_0xfd[0x23] = None
        self._instructions_0xfd[0x24] = None
        self._instructions_0xfd[0x25] = None
        self._instructions_0xfd[0x26] = None
        self._instructions_0xfd[0x27] = None
        self._instructions_0xfd[0x28] = None
        self._instructions_0xfd[0x29] = None
        self._instructions_0xfd[0x2a] = None
        self._instructions_0xfd[0x2b] = None
        self._instructions_0xfd[0x2c] = None
        self._instructions_0xfd[0x2d] = None
        self._instructions_0xfd[0x2e] = None
        self._instructions_0xfd[0x2f] = None

        self._instructions_0xfd[0x30] = None
        self._instructions_0xfd[0x31] = None
        self._instructions_0xfd[0x32] = None
        self._instructions_0xfd[0x33] = None
        self._instructions_0xfd[0x34] = self._inc_mem_indexed
        self._instructions_0xfd[0x35] = self._dec_mem_indexed
        self._instructions_0xfd[0x36] = self._store_value_to_indexed_mem
        self._instructions_0xfd[0x37] = None
        self._instructions_0xfd[0x38] = None
        self._instructions_0xfd[0x39] = None
        self._instructions_0xfd[0x3a] = None
        self._instructions_0xfd[0x3b] = None
        self._instructions_0xfd[0x3c] = None
        self._instructions_0xfd[0x3d] = None
        self._instructions_0xfd[0x3e] = None
        self._instructions_0xfd[0x3f] = None

        self._instructions_0xfd[0x40] = None
        self._instructions_0xfd[0x41] = None
        self._instructions_0xfd[0x42] = None
        self._instructions_0xfd[0x43] = None
        self._instructions_0xfd[0x44] = None
        self._instructions_0xfd[0x45] = None
        self._instructions_0xfd[0x46] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x47] = None
        self._instructions_0xfd[0x48] = None
        self._instructions_0xfd[0x49] = None
        self._instructions_0xfd[0x4a] = None
        self._instructions_0xfd[0x4b] = None
        self._instructions_0xfd[0x4c] = None
        self._instructions_0xfd[0x4d] = None
        self._instructions_0xfd[0x4e] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x4f] = None

        self._instructions_0xfd[0x50] = None
        self._instructions_0xfd[0x51] = None
        self._instructions_0xfd[0x52] = None
        self._instructions_0xfd[0x53] = None
        self._instructions_0xfd[0x54] = None
        self._instructions_0xfd[0x55] = None
        self._instructions_0xfd[0x56] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x57] = None
        self._instructions_0xfd[0x58] = None
        self._instructions_0xfd[0x59] = None
        self._instructions_0xfd[0x5a] = None
        self._instructions_0xfd[0x5b] = None
        self._instructions_0xfd[0x5c] = None
        self._instructions_0xfd[0x5d] = None
        self._instructions_0xfd[0x5e] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x5f] = None

        self._instructions_0xfd[0x60] = None
        self._instructions_0xfd[0x61] = None
        self._instructions_0xfd[0x62] = None
        self._instructions_0xfd[0x63] = None
        self._instructions_0xfd[0x64] = None
        self._instructions_0xfd[0x65] = None
        self._instructions_0xfd[0x66] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x67] = None
        self._instructions_0xfd[0x68] = None
        self._instructions_0xfd[0x69] = None
        self._instructions_0xfd[0x6a] = None
        self._instructions_0xfd[0x6b] = None
        self._instructions_0xfd[0x6c] = None
        self._instructions_0xfd[0x6d] = None
        self._instructions_0xfd[0x6e] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x6f] = None

        self._instructions_0xfd[0x70] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x71] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x72] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x73] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x74] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x75] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x76] = None
        self._instructions_0xfd[0x77] = self._store_reg_to_indexed_mem
        self._instructions_0xfd[0x78] = None
        self._instructions_0xfd[0x79] = None
        self._instructions_0xfd[0x7a] = None
        self._instructions_0xfd[0x7b] = None
        self._instructions_0xfd[0x7c] = None
        self._instructions_0xfd[0x7d] = None
        self._instructions_0xfd[0x7e] = self._load_reg_from_indexed_mem
        self._instructions_0xfd[0x7f] = None

        self._instructions_0xfd[0x80] = None
        self._instructions_0xfd[0x81] = None
        self._instructions_0xfd[0x82] = None
        self._instructions_0xfd[0x83] = None
        self._instructions_0xfd[0x84] = None
        self._instructions_0xfd[0x85] = None
        self._instructions_0xfd[0x86] = self._alu_mem_indexed
        self._instructions_0xfd[0x87] = None
        self._instructions_0xfd[0x88] = None
        self._instructions_0xfd[0x89] = None
        self._instructions_0xfd[0x8a] = None
        self._instructions_0xfd[0x8b] = None
        self._instructions_0xfd[0x8c] = None
        self._instructions_0xfd[0x8d] = None
        self._instructions_0xfd[0x8e] = self._alu_mem_indexed
        self._instructions_0xfd[0x8f] = None

        self._instructions_0xfd[0x90] = None
        self._instructions_0xfd[0x91] = None
        self._instructions_0xfd[0x92] = None
        self._instructions_0xfd[0x93] = None
        self._instructions_0xfd[0x94] = None
        self._instructions_0xfd[0x95] = None
        self._instructions_0xfd[0x96] = self._alu_mem_indexed
        self._instructions_0xfd[0x97] = None
        self._instructions_0xfd[0x98] = None
        self._instructions_0xfd[0x99] = None
        self._instructions_0xfd[0x9a] = None
        self._instructions_0xfd[0x9b] = None
        self._instructions_0xfd[0x9c] = None
        self._instructions_0xfd[0x9d] = None
        self._instructions_0xfd[0x9e] = self._alu_mem_indexed
        self._instructions_0xfd[0x9f] = None

        self._instructions_0xfd[0xa0] = None
        self._instructions_0xfd[0xa1] = None
        self._instructions_0xfd[0xa2] = None
        self._instructions_0xfd[0xa3] = None
        self._instructions_0xfd[0xa4] = None
        self._instructions_0xfd[0xa5] = None
        self._instructions_0xfd[0xa6] = self._alu_mem_indexed
        self._instructions_0xfd[0xa7] = None
        self._instructions_0xfd[0xa8] = None
        self._instructions_0xfd[0xa9] = None
        self._instructions_0xfd[0xaa] = None
        self._instructions_0xfd[0xab] = None
        self._instructions_0xfd[0xac] = None
        self._instructions_0xfd[0xad] = None
        self._instructions_0xfd[0xae] = self._alu_mem_indexed
        self._instructions_0xfd[0xaf] = None

        self._instructions_0xfd[0xb0] = None
        self._instructions_0xfd[0xb1] = None
        self._instructions_0xfd[0xb2] = None
        self._instructions_0xfd[0xb3] = None
        self._instructions_0xfd[0xb4] = None
        self._instructions_0xfd[0xb5] = None
        self._instructions_0xfd[0xb6] = self._alu_mem_indexed
        self._instructions_0xfd[0xb7] = None
        self._instructions_0xfd[0xb8] = None
        self._instructions_0xfd[0xb9] = None
        self._instructions_0xfd[0xba] = None
        self._instructions_0xfd[0xbb] = None
        self._instructions_0xfd[0xbc] = None
        self._instructions_0xfd[0xbd] = None
        self._instructions_0xfd[0xbe] = self._alu_mem_indexed
        self._instructions_0xfd[0xbf] = None

        self._instructions_0xfd[0xc0] = None
        self._instructions_0xfd[0xc1] = None
        self._instructions_0xfd[0xc2] = None
        self._instructions_0xfd[0xc3] = None
        self._instructions_0xfd[0xc4] = None
        self._instructions_0xfd[0xc5] = None
        self._instructions_0xfd[0xc6] = None
        self._instructions_0xfd[0xc7] = None
        self._instructions_0xfd[0xc8] = None
        self._instructions_0xfd[0xc9] = None
        self._instructions_0xfd[0xca] = None
        self._instructions_0xfd[0xcb] = None
        self._instructions_0xfd[0xcc] = None
        self._instructions_0xfd[0xcd] = None
        self._instructions_0xfd[0xce] = None
        self._instructions_0xfd[0xcf] = None

        self._instructions_0xfd[0xd0] = None
        self._instructions_0xfd[0xd1] = None
        self._instructions_0xfd[0xd2] = None
        self._instructions_0xfd[0xd3] = None
        self._instructions_0xfd[0xd4] = None
        self._instructions_0xfd[0xd5] = None
        self._instructions_0xfd[0xd6] = None
        self._instructions_0xfd[0xd7] = None
        self._instructions_0xfd[0xd8] = None
        self._instructions_0xfd[0xd9] = None
        self._instructions_0xfd[0xda] = None
        self._instructions_0xfd[0xdb] = None
        self._instructions_0xfd[0xdc] = None
        self._instructions_0xfd[0xdd] = None
        self._instructions_0xfd[0xde] = None
        self._instructions_0xfd[0xdf] = None

        self._instructions_0xfd[0xe0] = None
        self._instructions_0xfd[0xe1] = None
        self._instructions_0xfd[0xe2] = None
        self._instructions_0xfd[0xe3] = None
        self._instructions_0xfd[0xe4] = None
        self._instructions_0xfd[0xe5] = None
        self._instructions_0xfd[0xe6] = None
        self._instructions_0xfd[0xe7] = None
        self._instructions_0xfd[0xe8] = None
        self._instructions_0xfd[0xe9] = None
        self._instructions_0xfd[0xea] = None
        self._instructions_0xfd[0xeb] = None
        self._instructions_0xfd[0xec] = None
        self._instructions_0xfd[0xed] = None
        self._instructions_0xfd[0xee] = None
        self._instructions_0xfd[0xef] = None

        self._instructions_0xfd[0xf0] = None
        self._instructions_0xfd[0xf1] = None
        self._instructions_0xfd[0xf2] = None
        self._instructions_0xfd[0xf3] = None
        self._instructions_0xfd[0xf4] = None
        self._instructions_0xfd[0xf5] = None
        self._instructions_0xfd[0xf6] = None
        self._instructions_0xfd[0xf7] = None
        self._instructions_0xfd[0xf8] = None
        self._instructions_0xfd[0xf9] = None
        self._instructions_0xfd[0xfa] = None
        self._instructions_0xfd[0xfb] = None
        self._instructions_0xfd[0xfc] = None
        self._instructions_0xfd[0xfd] = None
        self._instructions_0xfd[0xfe] = None
        self._instructions_0xfd[0xff] = None


    def _init_fdcb_instruction_table(self):
        """ Initialize IY bit instruction set with 0xFD 0xCB prefix """
        
        self._instructions_0xfdcb = [None] * 0x100

        self._instructions_0xfdcb[0x00] = None
        self._instructions_0xfdcb[0x01] = None
        self._instructions_0xfdcb[0x02] = None
        self._instructions_0xfdcb[0x03] = None
        self._instructions_0xfdcb[0x04] = None
        self._instructions_0xfdcb[0x05] = None
        self._instructions_0xfdcb[0x06] = None
        self._instructions_0xfdcb[0x07] = None
        self._instructions_0xfdcb[0x08] = None
        self._instructions_0xfdcb[0x09] = None
        self._instructions_0xfdcb[0x0a] = None
        self._instructions_0xfdcb[0x0b] = None
        self._instructions_0xfdcb[0x0c] = None
        self._instructions_0xfdcb[0x0d] = None
        self._instructions_0xfdcb[0x0e] = None
        self._instructions_0xfdcb[0x0f] = None

        self._instructions_0xfdcb[0x10] = None
        self._instructions_0xfdcb[0x11] = None
        self._instructions_0xfdcb[0x12] = None
        self._instructions_0xfdcb[0x13] = None
        self._instructions_0xfdcb[0x14] = None
        self._instructions_0xfdcb[0x15] = None
        self._instructions_0xfdcb[0x16] = None
        self._instructions_0xfdcb[0x17] = None
        self._instructions_0xfdcb[0x18] = None
        self._instructions_0xfdcb[0x19] = None
        self._instructions_0xfdcb[0x1a] = None
        self._instructions_0xfdcb[0x1b] = None
        self._instructions_0xfdcb[0x1c] = None
        self._instructions_0xfdcb[0x1d] = None
        self._instructions_0xfdcb[0x1e] = None
        self._instructions_0xfdcb[0x1f] = None

        self._instructions_0xfdcb[0x20] = None
        self._instructions_0xfdcb[0x21] = None
        self._instructions_0xfdcb[0x22] = None
        self._instructions_0xfdcb[0x23] = None
        self._instructions_0xfdcb[0x24] = None
        self._instructions_0xfdcb[0x25] = None
        self._instructions_0xfdcb[0x26] = None
        self._instructions_0xfdcb[0x27] = None
        self._instructions_0xfdcb[0x28] = None
        self._instructions_0xfdcb[0x29] = None
        self._instructions_0xfdcb[0x2a] = None
        self._instructions_0xfdcb[0x2b] = None
        self._instructions_0xfdcb[0x2c] = None
        self._instructions_0xfdcb[0x2d] = None
        self._instructions_0xfdcb[0x2e] = None
        self._instructions_0xfdcb[0x2f] = None

        self._instructions_0xfdcb[0x30] = None
        self._instructions_0xfdcb[0x31] = None
        self._instructions_0xfdcb[0x32] = None
        self._instructions_0xfdcb[0x33] = None
        self._instructions_0xfdcb[0x34] = None
        self._instructions_0xfdcb[0x35] = None
        self._instructions_0xfdcb[0x36] = None
        self._instructions_0xfdcb[0x37] = None
        self._instructions_0xfdcb[0x38] = None
        self._instructions_0xfdcb[0x39] = None
        self._instructions_0xfdcb[0x3a] = None
        self._instructions_0xfdcb[0x3b] = None
        self._instructions_0xfdcb[0x3c] = None
        self._instructions_0xfdcb[0x3d] = None
        self._instructions_0xfdcb[0x3e] = None
        self._instructions_0xfdcb[0x3f] = None

        self._instructions_0xfdcb[0x40] = None
        self._instructions_0xfdcb[0x41] = None
        self._instructions_0xfdcb[0x42] = None
        self._instructions_0xfdcb[0x43] = None
        self._instructions_0xfdcb[0x44] = None
        self._instructions_0xfdcb[0x45] = None
        self._instructions_0xfdcb[0x46] = self._get_bit_indexed
        self._instructions_0xfdcb[0x47] = None
        self._instructions_0xfdcb[0x48] = None
        self._instructions_0xfdcb[0x49] = None
        self._instructions_0xfdcb[0x4a] = None
        self._instructions_0xfdcb[0x4b] = None
        self._instructions_0xfdcb[0x4c] = None
        self._instructions_0xfdcb[0x4d] = None
        self._instructions_0xfdcb[0x4e] = self._get_bit_indexed
        self._instructions_0xfdcb[0x4f] = None

        self._instructions_0xfdcb[0x50] = None
        self._instructions_0xfdcb[0x51] = None
        self._instructions_0xfdcb[0x52] = None
        self._instructions_0xfdcb[0x53] = None
        self._instructions_0xfdcb[0x54] = None
        self._instructions_0xfdcb[0x55] = None
        self._instructions_0xfdcb[0x56] = self._get_bit_indexed
        self._instructions_0xfdcb[0x57] = None
        self._instructions_0xfdcb[0x58] = None
        self._instructions_0xfdcb[0x59] = None
        self._instructions_0xfdcb[0x5a] = None
        self._instructions_0xfdcb[0x5b] = None
        self._instructions_0xfdcb[0x5c] = None
        self._instructions_0xfdcb[0x5d] = None
        self._instructions_0xfdcb[0x5e] = self._get_bit_indexed
        self._instructions_0xfdcb[0x5f] = None

        self._instructions_0xfdcb[0x60] = None
        self._instructions_0xfdcb[0x61] = None
        self._instructions_0xfdcb[0x62] = None
        self._instructions_0xfdcb[0x63] = None
        self._instructions_0xfdcb[0x64] = None
        self._instructions_0xfdcb[0x65] = None
        self._instructions_0xfdcb[0x66] = self._get_bit_indexed
        self._instructions_0xfdcb[0x67] = None
        self._instructions_0xfdcb[0x68] = None
        self._instructions_0xfdcb[0x69] = None
        self._instructions_0xfdcb[0x6a] = None
        self._instructions_0xfdcb[0x6b] = None
        self._instructions_0xfdcb[0x6c] = None
        self._instructions_0xfdcb[0x6d] = None
        self._instructions_0xfdcb[0x6e] = self._get_bit_indexed
        self._instructions_0xfdcb[0x6f] = None

        self._instructions_0xfdcb[0x70] = None
        self._instructions_0xfdcb[0x71] = None
        self._instructions_0xfdcb[0x72] = None
        self._instructions_0xfdcb[0x73] = None
        self._instructions_0xfdcb[0x74] = None
        self._instructions_0xfdcb[0x75] = None
        self._instructions_0xfdcb[0x76] = self._get_bit_indexed
        self._instructions_0xfdcb[0x77] = None
        self._instructions_0xfdcb[0x78] = None
        self._instructions_0xfdcb[0x79] = None
        self._instructions_0xfdcb[0x7a] = None
        self._instructions_0xfdcb[0x7b] = None
        self._instructions_0xfdcb[0x7c] = None
        self._instructions_0xfdcb[0x7d] = None
        self._instructions_0xfdcb[0x7e] = self._get_bit_indexed
        self._instructions_0xfdcb[0x7f] = None

        self._instructions_0xfdcb[0x80] = None
        self._instructions_0xfdcb[0x81] = None
        self._instructions_0xfdcb[0x82] = None
        self._instructions_0xfdcb[0x83] = None
        self._instructions_0xfdcb[0x84] = None
        self._instructions_0xfdcb[0x85] = None
        self._instructions_0xfdcb[0x86] = self._reset_bit_indexed
        self._instructions_0xfdcb[0x87] = None
        self._instructions_0xfdcb[0x88] = None
        self._instructions_0xfdcb[0x89] = None
        self._instructions_0xfdcb[0x8a] = None
        self._instructions_0xfdcb[0x8b] = None
        self._instructions_0xfdcb[0x8c] = None
        self._instructions_0xfdcb[0x8d] = None
        self._instructions_0xfdcb[0x8e] = self._reset_bit_indexed
        self._instructions_0xfdcb[0x8f] = None

        self._instructions_0xfdcb[0x90] = None
        self._instructions_0xfdcb[0x91] = None
        self._instructions_0xfdcb[0x92] = None
        self._instructions_0xfdcb[0x93] = None
        self._instructions_0xfdcb[0x94] = None
        self._instructions_0xfdcb[0x95] = None
        self._instructions_0xfdcb[0x96] = self._reset_bit_indexed
        self._instructions_0xfdcb[0x97] = None
        self._instructions_0xfdcb[0x98] = None
        self._instructions_0xfdcb[0x99] = None
        self._instructions_0xfdcb[0x9a] = None
        self._instructions_0xfdcb[0x9b] = None
        self._instructions_0xfdcb[0x9c] = None
        self._instructions_0xfdcb[0x9d] = None
        self._instructions_0xfdcb[0x9e] = self._reset_bit_indexed
        self._instructions_0xfdcb[0x9f] = None

        self._instructions_0xfdcb[0xa0] = None
        self._instructions_0xfdcb[0xa1] = None
        self._instructions_0xfdcb[0xa2] = None
        self._instructions_0xfdcb[0xa3] = None
        self._instructions_0xfdcb[0xa4] = None
        self._instructions_0xfdcb[0xa5] = None
        self._instructions_0xfdcb[0xa6] = self._reset_bit_indexed
        self._instructions_0xfdcb[0xa7] = None
        self._instructions_0xfdcb[0xa8] = None
        self._instructions_0xfdcb[0xa9] = None
        self._instructions_0xfdcb[0xaa] = None
        self._instructions_0xfdcb[0xab] = None
        self._instructions_0xfdcb[0xac] = None
        self._instructions_0xfdcb[0xad] = None
        self._instructions_0xfdcb[0xae] = self._reset_bit_indexed
        self._instructions_0xfdcb[0xaf] = None

        self._instructions_0xfdcb[0xb0] = None
        self._instructions_0xfdcb[0xb1] = None
        self._instructions_0xfdcb[0xb2] = None
        self._instructions_0xfdcb[0xb3] = None
        self._instructions_0xfdcb[0xb4] = None
        self._instructions_0xfdcb[0xb5] = None
        self._instructions_0xfdcb[0xb6] = self._reset_bit_indexed
        self._instructions_0xfdcb[0xb7] = None
        self._instructions_0xfdcb[0xb8] = None
        self._instructions_0xfdcb[0xb9] = None
        self._instructions_0xfdcb[0xba] = None
        self._instructions_0xfdcb[0xbb] = None
        self._instructions_0xfdcb[0xbc] = None
        self._instructions_0xfdcb[0xbd] = None
        self._instructions_0xfdcb[0xbe] = self._reset_bit_indexed
        self._instructions_0xfdcb[0xbf] = None

        self._instructions_0xfdcb[0xc0] = None
        self._instructions_0xfdcb[0xc1] = None
        self._instructions_0xfdcb[0xc2] = None
        self._instructions_0xfdcb[0xc3] = None
        self._instructions_0xfdcb[0xc4] = None
        self._instructions_0xfdcb[0xc5] = None
        self._instructions_0xfdcb[0xc6] = self._set_bit_indexed
        self._instructions_0xfdcb[0xc7] = None
        self._instructions_0xfdcb[0xc8] = None
        self._instructions_0xfdcb[0xc9] = None
        self._instructions_0xfdcb[0xca] = None
        self._instructions_0xfdcb[0xcb] = None
        self._instructions_0xfdcb[0xcc] = None
        self._instructions_0xfdcb[0xcd] = None
        self._instructions_0xfdcb[0xce] = self._set_bit_indexed
        self._instructions_0xfdcb[0xcf] = None

        self._instructions_0xfdcb[0xd0] = None
        self._instructions_0xfdcb[0xd1] = None
        self._instructions_0xfdcb[0xd2] = None
        self._instructions_0xfdcb[0xd3] = None
        self._instructions_0xfdcb[0xd4] = None
        self._instructions_0xfdcb[0xd5] = None
        self._instructions_0xfdcb[0xd6] = self._set_bit_indexed
        self._instructions_0xfdcb[0xd7] = None
        self._instructions_0xfdcb[0xd8] = None
        self._instructions_0xfdcb[0xd9] = None
        self._instructions_0xfdcb[0xda] = None
        self._instructions_0xfdcb[0xdb] = None
        self._instructions_0xfdcb[0xdc] = None
        self._instructions_0xfdcb[0xdd] = None
        self._instructions_0xfdcb[0xde] = self._set_bit_indexed
        self._instructions_0xfdcb[0xdf] = None

        self._instructions_0xfdcb[0xe0] = None
        self._instructions_0xfdcb[0xe1] = None
        self._instructions_0xfdcb[0xe2] = None
        self._instructions_0xfdcb[0xe3] = None
        self._instructions_0xfdcb[0xe4] = None
        self._instructions_0xfdcb[0xe5] = None
        self._instructions_0xfdcb[0xe6] = self._set_bit_indexed
        self._instructions_0xfdcb[0xe7] = None
        self._instructions_0xfdcb[0xe8] = None
        self._instructions_0xfdcb[0xe9] = None
        self._instructions_0xfdcb[0xea] = None
        self._instructions_0xfdcb[0xeb] = None
        self._instructions_0xfdcb[0xec] = None
        self._instructions_0xfdcb[0xed] = None
        self._instructions_0xfdcb[0xee] = self._set_bit_indexed
        self._instructions_0xfdcb[0xef] = None

        self._instructions_0xfdcb[0xf0] = None
        self._instructions_0xfdcb[0xf1] = None
        self._instructions_0xfdcb[0xf2] = None
        self._instructions_0xfdcb[0xf3] = None
        self._instructions_0xfdcb[0xf4] = None
        self._instructions_0xfdcb[0xf5] = None
        self._instructions_0xfdcb[0xf6] = self._set_bit_indexed
        self._instructions_0xfdcb[0xf7] = None
        self._instructions_0xfdcb[0xf8] = None
        self._instructions_0xfdcb[0xf9] = None
        self._instructions_0xfdcb[0xfa] = None
        self._instructions_0xfdcb[0xfb] = None
        self._instructions_0xfdcb[0xfc] = None
        self._instructions_0xfdcb[0xfd] = None
        self._instructions_0xfdcb[0xfe] = self._set_bit_indexed
        self._instructions_0xfdcb[0xff] = None

