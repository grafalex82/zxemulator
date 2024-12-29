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
        self._current_inst = 0  # current instruction
        self._instructions = [None] * 0x100
        self._instructions_0xed = [None] * 0x100
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

        # ALU Flags
        self._sign = False                      # Bit 7
        self._zero = False                      # Bit 6
        self._half_carry = False                # Bit 4
        self._parity_overflow = False           # Bit 2
        self._add_subtract = False              # Bit 1
        self._carry = False                     # Bit 0



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
        flags = 2 # bit1 is always 1 (at least in i8080)
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
        # Fetch the next instruction, take into account the instruction prefix
        pc = self._pc
        b = self._fetch_next_byte()
        if b == 0xed:
            self._instruction_prefix = 0xed
            self._current_inst = self._fetch_next_byte()
        else:
            self._instruction_prefix = None
            self._current_inst = b

        # Depending on instruction prefix, select the correct instruction table
        if self._instruction_prefix == 0xed:
            instruction = self._instructions_0xed[self._current_inst]
        else:
            instruction = self._instructions[self._current_inst]

        # Execute the instruction
        if instruction is not None:
            instruction()
        else:
            prefix = f"0x{self._instruction_prefix:02x} " if self._instruction_prefix else ""
            raise InvalidInstruction(f"Incorrect OPCODE {prefix}0x{self._current_inst:02x} (at addr 0x{pc:04x})")


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


    def _log_1b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 1
        prefix = f"{self._instruction_prefix:02x}" if self._instruction_prefix else "  "
        log_str = f' {addr:04x}  {prefix} {self._current_inst:02x}         {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_2b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 2
        param = self._machine.read_memory_byte(self._pc - 1)
        prefix = f"{self._instruction_prefix:02x}" if self._instruction_prefix else "  "
        log_str = f' {addr:04x}  {prefix} {self._current_inst:02x} {param:02x}      {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)


    def _log_3b_instruction(self, mnemonic):
        if logger.level > logging.DEBUG:
            return

        addr = self._pc - 3
        param1 = self._machine.read_memory_byte(self._pc - 2)
        param2 = self._machine.read_memory_byte(self._pc - 1)
        prefix = f"{self._instruction_prefix:02x}" if self._instruction_prefix else "  "
        log_str = f' {addr:04x}  {prefix} {self._current_inst:02x} {param1:02x} {param2:02x}   {mnemonic}'

        if self._registers_logging:
            log_str = f"{log_str:40} {self._get_cpu_state_str()}"
            
        logger.debug(log_str)



    # CPU control instructions

    def _nop(self):
        """ Do nothing """
        self._cycles += 4

        self._log_1b_instruction("NOP")


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


    def _in(self):
        """ IO Input """
        addr = self._fetch_next_byte()

        self._a = self._machine.read_io(addr)
        self._cycles += 11

        self._log_2b_instruction(f"IN A, {addr:02x}")


    def _out(self):
        """ IO Output """
        addr = self._fetch_next_byte()
        self._log_2b_instruction(f"OUT {addr:02x}, A")

        self._machine.write_io(addr, self._a)
        self._cycles += 11



    # Data transfer instructions

    def _load_immediate_16b(self):
        """ Load register pair with immediate value"""
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._fetch_next_word()
        if reg_pair == 3:
            self._sp = value
        else: 
            self._set_register_pair(reg_pair, value)
        self._cycles += 10

        self._log_3b_instruction(f"LD {self._reg_pair_symb(reg_pair)}, {value:04x}")

    def _load_register_to_register(self):
        """ Move a byte between 2 registers """
        dst = (self._current_inst & 0x38) >> 3
        src = self._current_inst & 0x07
        value = self._get_register(src)
        self._set_register(dst, value)

        self._cycles += 4
        if src == 6 or dst == 6:
            self._cycles += 3

        self._log_1b_instruction(f"LD {self._reg_symb(dst)}, {self._reg_symb(src)}")

    def _load_8b_immediate_to_register(self):
        """ Move immediate to register or memory """
        reg = (self._current_inst & 0x38) >> 3
        value = self._fetch_next_byte()
        self._set_register(reg, value)
        self._cycles += (7 if reg != 6 else 10)

        self._log_2b_instruction(f"LD {self._reg_symb(reg)}, {value:02x}")

    def _load_a_from_i_r_registers(self):
        """ Load accumulator from I or R registers """
        self._a = self._r if (self._current_inst & 0x08) else self._i

        self._cycles += 9
        reg_symb = "R" if (self._current_inst & 0x08) else "I"
        self._log_1b_instruction(f"LD A, {reg_symb}")

    def _load_i_r_register_from_a(self):
        """ Load I or R register from accumulator """
        if self._current_inst & 0x08:
            self._r = self._a
        else:
            self._i = self._a

        self._cycles += 9
        reg_symb = "R" if (self._current_inst & 0x08) else "I"
        self._log_1b_instruction(f"LD {reg_symb}, A")


    # Execution flow instructions

    def _jp(self):
        """ Unconditional jump to an absolute address """
        addr = self._fetch_next_word()

        self._log_3b_instruction(f"JP {addr:04x}")

        self._pc = addr
        self._cycles += 10

    def _jr(self):
        """ Unconditional relative jump """
        displacement = self._fetch_next_byte()
        if displacement > 0x7f:
            displacement = -(0x100 - displacement)
        self._pc += displacement

        log_displacement = displacement+2
        displacement_str = f"${'+' if log_displacement >= 0 else '-'}{abs(log_displacement):02x}"
        self._log_2b_instruction(f"JR {displacement_str} ({self._pc:04x})")

        self._cycles += 12

    def _jr_cond(self):
        """ Conditional relative jump """
        displacement = self._fetch_next_byte()
        if displacement > 0x7f:
            displacement = -(0x100 - displacement)

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

        log_displacement = displacement + 2
        displacement_str = f"${'+' if log_displacement >= 0 else '-'}{abs(log_displacement):02x}"
        self._log_2b_instruction(f"JR {condition_code}, {displacement_str} ({(self._pc + displacement):04x})")

        if condition:
            self._pc += displacement
            self._cycles += 12
        else:
            self._cycles += 7


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
        op_name = ["ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR ", "CP "][op]
        reg = self._current_inst & 0x07
        value = self._get_register(reg)

        self._alu_op(op, value)
        self._cycles += 4 if reg != 6 else 7

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
        op_name = ["ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR ", "CP "][op]
        value = self._fetch_next_byte()

        self._alu_op(op, value)
        self._cycles += 7

        self._log_2b_instruction(f"{op_name} {value:02x}")


    def _dec8(self):
        """ Decrement a 8-bit register """
        reg = (self._current_inst & 0x38) >> 3
        value = (self._get_register(reg) - 1) & 0xff
        self._set_register(reg, value)

        self._zero = (value & 0xff) == 0
        self._parity = self._count_bits(value) % 2 == 0
        self._sign = (value & 0x80) != 0
        self._half_carry = value == 0x0f
        self._add_subtract = True
        self._parity_overflow = value == 0x7f

        self._log_1b_instruction(f"DEC {self._reg_symb(reg)}")
        self._cycles += 11 if reg == 6 else 4


    def _inc8(self):
        """ Increment a 8-bit register """
        reg = (self._current_inst & 0x38) >> 3
        value = (self._get_register(reg) + 1) & 0xff
        self._set_register(reg, value)

        self._zero = (value & 0xff) == 0
        self._parity = self._count_bits(value) % 2 == 0
        self._sign = (value & 0x80) != 0
        self._half_carry = (value & 0xf) == 0x0
        self._add_subtract = False
        self._parity_overflow = value == 0x80

        self._log_1b_instruction(f"INC {self._reg_symb(reg)}")
        self._cycles += 11 if reg == 6 else 4


    def _dec16(self):
        """ Decrement a register pair """
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._get_register_pair(reg_pair)
        self._set_register_pair(reg_pair, (value - 1) & 0xffff)
        self._cycles += 6

        self._log_1b_instruction(f"DEC {self._reg_pair_symb(reg_pair)}")


    def _inc16(self):
        """ Increment a register pair """
        reg_pair = (self._current_inst & 0x30) >> 4
        value = self._get_register_pair(reg_pair)
        self._set_register_pair(reg_pair, (value + 1) & 0xffff)
        self._cycles += 6

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

        self._log_1b_instruction(f"SBC HL, {self._reg_pair_symb(reg_pair)}")



    # Instruction table

    def init_instruction_table(self):
        self._instructions[0x00] = self._nop
        self._instructions[0x01] = self._load_immediate_16b
        self._instructions[0x02] = None
        self._instructions[0x03] = self._inc16
        self._instructions[0x04] = self._inc8
        self._instructions[0x05] = self._dec8
        self._instructions[0x06] = self._load_8b_immediate_to_register
        self._instructions[0x07] = None
        self._instructions[0x08] = None
        self._instructions[0x09] = self._add_hl
        self._instructions[0x0a] = None
        self._instructions[0x0b] = self._dec16
        self._instructions[0x0c] = self._inc8
        self._instructions[0x0d] = self._dec8
        self._instructions[0x0e] = self._load_8b_immediate_to_register
        self._instructions[0x0f] = None

        self._instructions[0x10] = None
        self._instructions[0x11] = self._load_immediate_16b
        self._instructions[0x12] = None
        self._instructions[0x13] = self._inc16
        self._instructions[0x14] = self._inc8
        self._instructions[0x15] = self._dec8
        self._instructions[0x16] = self._load_8b_immediate_to_register
        self._instructions[0x17] = None
        self._instructions[0x18] = self._jr
        self._instructions[0x19] = self._add_hl
        self._instructions[0x1a] = None
        self._instructions[0x1b] = self._dec16
        self._instructions[0x1c] = self._inc8
        self._instructions[0x1d] = self._dec8
        self._instructions[0x1e] = self._load_8b_immediate_to_register
        self._instructions[0x1f] = None

        self._instructions[0x20] = self._jr_cond
        self._instructions[0x21] = self._load_immediate_16b
        self._instructions[0x22] = None
        self._instructions[0x23] = self._inc16
        self._instructions[0x24] = self._inc8
        self._instructions[0x25] = self._dec8
        self._instructions[0x26] = self._load_8b_immediate_to_register
        self._instructions[0x27] = None
        self._instructions[0x28] = self._jr_cond
        self._instructions[0x29] = self._add_hl
        self._instructions[0x2a] = None
        self._instructions[0x2b] = self._dec16
        self._instructions[0x2c] = self._inc8
        self._instructions[0x2d] = self._dec8
        self._instructions[0x2e] = self._load_8b_immediate_to_register
        self._instructions[0x2f] = None

        self._instructions[0x30] = self._jr_cond
        self._instructions[0x31] = self._load_immediate_16b
        self._instructions[0x32] = None
        self._instructions[0x33] = self._inc16
        self._instructions[0x34] = self._inc8
        self._instructions[0x35] = self._dec8
        self._instructions[0x36] = self._load_8b_immediate_to_register
        self._instructions[0x37] = None
        self._instructions[0x38] = self._jr_cond
        self._instructions[0x39] = self._add_hl
        self._instructions[0x3a] = None
        self._instructions[0x3b] = self._dec16
        self._instructions[0x3c] = self._inc8
        self._instructions[0x3d] = self._dec8
        self._instructions[0x3e] = self._load_8b_immediate_to_register
        self._instructions[0x3f] = None

        self._instructions[0x40] = self._load_register_to_register
        self._instructions[0x41] = self._load_register_to_register
        self._instructions[0x42] = self._load_register_to_register
        self._instructions[0x43] = self._load_register_to_register
        self._instructions[0x44] = self._load_register_to_register
        self._instructions[0x45] = self._load_register_to_register
        self._instructions[0x46] = self._load_register_to_register
        self._instructions[0x47] = self._load_register_to_register
        self._instructions[0x48] = self._load_register_to_register
        self._instructions[0x49] = self._load_register_to_register
        self._instructions[0x4a] = self._load_register_to_register
        self._instructions[0x4b] = self._load_register_to_register
        self._instructions[0x4c] = self._load_register_to_register
        self._instructions[0x4d] = self._load_register_to_register
        self._instructions[0x4e] = self._load_register_to_register
        self._instructions[0x4f] = self._load_register_to_register

        self._instructions[0x50] = self._load_register_to_register
        self._instructions[0x51] = self._load_register_to_register
        self._instructions[0x52] = self._load_register_to_register
        self._instructions[0x53] = self._load_register_to_register
        self._instructions[0x54] = self._load_register_to_register
        self._instructions[0x55] = self._load_register_to_register
        self._instructions[0x56] = self._load_register_to_register
        self._instructions[0x57] = self._load_register_to_register
        self._instructions[0x58] = self._load_register_to_register
        self._instructions[0x59] = self._load_register_to_register
        self._instructions[0x5a] = self._load_register_to_register
        self._instructions[0x5b] = self._load_register_to_register
        self._instructions[0x5c] = self._load_register_to_register
        self._instructions[0x5d] = self._load_register_to_register
        self._instructions[0x5e] = self._load_register_to_register
        self._instructions[0x5f] = self._load_register_to_register

        self._instructions[0x60] = self._load_register_to_register
        self._instructions[0x61] = self._load_register_to_register
        self._instructions[0x62] = self._load_register_to_register
        self._instructions[0x63] = self._load_register_to_register
        self._instructions[0x64] = self._load_register_to_register
        self._instructions[0x65] = self._load_register_to_register
        self._instructions[0x66] = self._load_register_to_register
        self._instructions[0x67] = self._load_register_to_register
        self._instructions[0x68] = self._load_register_to_register
        self._instructions[0x69] = self._load_register_to_register
        self._instructions[0x6a] = self._load_register_to_register
        self._instructions[0x6b] = self._load_register_to_register
        self._instructions[0x6c] = self._load_register_to_register
        self._instructions[0x6d] = self._load_register_to_register
        self._instructions[0x6e] = self._load_register_to_register
        self._instructions[0x6f] = self._load_register_to_register

        self._instructions[0x70] = self._load_register_to_register
        self._instructions[0x71] = self._load_register_to_register
        self._instructions[0x72] = self._load_register_to_register
        self._instructions[0x73] = self._load_register_to_register
        self._instructions[0x74] = self._load_register_to_register
        self._instructions[0x75] = self._load_register_to_register
        self._instructions[0x76] = None
        self._instructions[0x77] = self._load_register_to_register
        self._instructions[0x78] = self._load_register_to_register
        self._instructions[0x79] = self._load_register_to_register
        self._instructions[0x7a] = self._load_register_to_register
        self._instructions[0x7b] = self._load_register_to_register
        self._instructions[0x7c] = self._load_register_to_register
        self._instructions[0x7d] = self._load_register_to_register
        self._instructions[0x7e] = self._load_register_to_register
        self._instructions[0x7f] = self._load_register_to_register

        self._instructions[0x80] = self._alu
        self._instructions[0x81] = self._alu
        self._instructions[0x82] = self._alu
        self._instructions[0x83] = self._alu
        self._instructions[0x84] = self._alu
        self._instructions[0x85] = self._alu
        self._instructions[0x86] = self._alu
        self._instructions[0x87] = self._alu
        self._instructions[0x88] = self._alu
        self._instructions[0x89] = self._alu
        self._instructions[0x8a] = self._alu
        self._instructions[0x8b] = self._alu
        self._instructions[0x8c] = self._alu
        self._instructions[0x8d] = self._alu
        self._instructions[0x8e] = self._alu
        self._instructions[0x8f] = self._alu

        self._instructions[0x90] = self._alu
        self._instructions[0x91] = self._alu
        self._instructions[0x92] = self._alu
        self._instructions[0x93] = self._alu
        self._instructions[0x94] = self._alu
        self._instructions[0x95] = self._alu
        self._instructions[0x96] = self._alu
        self._instructions[0x97] = self._alu
        self._instructions[0x98] = self._alu
        self._instructions[0x99] = self._alu
        self._instructions[0x9a] = self._alu
        self._instructions[0x9b] = self._alu
        self._instructions[0x9c] = self._alu
        self._instructions[0x9d] = self._alu
        self._instructions[0x9e] = self._alu
        self._instructions[0x9f] = self._alu

        self._instructions[0xa0] = self._alu
        self._instructions[0xa1] = self._alu
        self._instructions[0xa2] = self._alu
        self._instructions[0xa3] = self._alu
        self._instructions[0xa4] = self._alu
        self._instructions[0xa5] = self._alu
        self._instructions[0xa6] = self._alu
        self._instructions[0xa7] = self._alu
        self._instructions[0xa8] = self._alu
        self._instructions[0xa9] = self._alu
        self._instructions[0xaa] = self._alu
        self._instructions[0xab] = self._alu
        self._instructions[0xac] = self._alu
        self._instructions[0xad] = self._alu
        self._instructions[0xae] = self._alu
        self._instructions[0xaf] = self._alu

        self._instructions[0xb0] = self._alu
        self._instructions[0xb1] = self._alu
        self._instructions[0xb2] = self._alu
        self._instructions[0xb3] = self._alu
        self._instructions[0xb4] = self._alu
        self._instructions[0xb5] = self._alu
        self._instructions[0xb6] = self._alu
        self._instructions[0xb7] = self._alu
        self._instructions[0xb8] = self._alu
        self._instructions[0xb9] = self._alu
        self._instructions[0xba] = self._alu
        self._instructions[0xbb] = self._alu
        self._instructions[0xbc] = self._alu
        self._instructions[0xbd] = self._alu
        self._instructions[0xbe] = self._alu
        self._instructions[0xbf] = self._alu

        self._instructions[0xc0] = None
        self._instructions[0xc1] = None
        self._instructions[0xc2] = None
        self._instructions[0xc3] = self._jp
        self._instructions[0xc4] = None
        self._instructions[0xc5] = None
        self._instructions[0xc6] = self._alu_immediate
        self._instructions[0xc7] = None
        self._instructions[0xc8] = None
        self._instructions[0xc9] = None
        self._instructions[0xca] = None
        self._instructions[0xcb] = None
        self._instructions[0xcc] = None
        self._instructions[0xcd] = None
        self._instructions[0xce] = self._alu_immediate
        self._instructions[0xcf] = None

        self._instructions[0xd0] = None
        self._instructions[0xd1] = None
        self._instructions[0xd2] = None
        self._instructions[0xd3] = self._out
        self._instructions[0xd4] = None
        self._instructions[0xd5] = None
        self._instructions[0xd6] = self._alu_immediate
        self._instructions[0xd7] = None
        self._instructions[0xd8] = None
        self._instructions[0xd9] = None
        self._instructions[0xda] = None
        self._instructions[0xdb] = self._in
        self._instructions[0xdc] = None
        self._instructions[0xdd] = None
        self._instructions[0xde] = self._alu_immediate
        self._instructions[0xdf] = None

        self._instructions[0xe0] = None
        self._instructions[0xe1] = None
        self._instructions[0xe2] = None
        self._instructions[0xe3] = None
        self._instructions[0xe4] = None
        self._instructions[0xe5] = None
        self._instructions[0xe6] = self._alu_immediate
        self._instructions[0xe7] = None
        self._instructions[0xe8] = None
        self._instructions[0xe9] = None
        self._instructions[0xea] = None
        self._instructions[0xeb] = None
        self._instructions[0xec] = None
        self._instructions[0xed] = None
        self._instructions[0xee] = self._alu_immediate
        self._instructions[0xef] = None

        self._instructions[0xf0] = None
        self._instructions[0xf1] = None
        self._instructions[0xf2] = None
        self._instructions[0xf3] = self._di
        self._instructions[0xf4] = None
        self._instructions[0xf5] = None
        self._instructions[0xf6] = self._alu_immediate
        self._instructions[0xf7] = None
        self._instructions[0xf8] = None
        self._instructions[0xf9] = None
        self._instructions[0xfa] = None
        self._instructions[0xfb] = self._ei
        self._instructions[0xfc] = None
        self._instructions[0xfd] = None
        self._instructions[0xfe] = self._alu_immediate
        self._instructions[0xff] = None


        # Extended instruction set with 0xed prefix

        self._instructions_0xed[0x00] = None
        self._instructions_0xed[0x01] = None
        self._instructions_0xed[0x02] = None
        self._instructions_0xed[0x03] = None
        self._instructions_0xed[0x04] = None
        self._instructions_0xed[0x05] = None
        self._instructions_0xed[0x06] = None
        self._instructions_0xed[0x07] = None
        self._instructions_0xed[0x08] = None
        self._instructions_0xed[0x09] = None
        self._instructions_0xed[0x0a] = None
        self._instructions_0xed[0x0b] = None
        self._instructions_0xed[0x0c] = None
        self._instructions_0xed[0x0d] = None
        self._instructions_0xed[0x0e] = None
        self._instructions_0xed[0x0f] = None

        self._instructions_0xed[0x10] = None
        self._instructions_0xed[0x11] = None
        self._instructions_0xed[0x12] = None
        self._instructions_0xed[0x13] = None
        self._instructions_0xed[0x14] = None
        self._instructions_0xed[0x15] = None
        self._instructions_0xed[0x16] = None
        self._instructions_0xed[0x17] = None
        self._instructions_0xed[0x18] = None
        self._instructions_0xed[0x19] = None
        self._instructions_0xed[0x1a] = None
        self._instructions_0xed[0x1b] = None
        self._instructions_0xed[0x1c] = None
        self._instructions_0xed[0x1d] = None
        self._instructions_0xed[0x1e] = None
        self._instructions_0xed[0x1f] = None

        self._instructions_0xed[0x20] = None
        self._instructions_0xed[0x21] = None
        self._instructions_0xed[0x22] = None
        self._instructions_0xed[0x23] = None
        self._instructions_0xed[0x24] = None
        self._instructions_0xed[0x25] = None
        self._instructions_0xed[0x26] = None
        self._instructions_0xed[0x27] = None
        self._instructions_0xed[0x28] = None
        self._instructions_0xed[0x29] = None
        self._instructions_0xed[0x2a] = None
        self._instructions_0xed[0x2b] = None
        self._instructions_0xed[0x2c] = None
        self._instructions_0xed[0x2d] = None
        self._instructions_0xed[0x2e] = None
        self._instructions_0xed[0x2f] = None

        self._instructions_0xed[0x30] = None
        self._instructions_0xed[0x31] = None
        self._instructions_0xed[0x32] = None
        self._instructions_0xed[0x33] = None
        self._instructions_0xed[0x34] = None
        self._instructions_0xed[0x35] = None
        self._instructions_0xed[0x36] = None
        self._instructions_0xed[0x37] = None
        self._instructions_0xed[0x38] = None
        self._instructions_0xed[0x39] = None
        self._instructions_0xed[0x3a] = None
        self._instructions_0xed[0x3b] = None
        self._instructions_0xed[0x3c] = None
        self._instructions_0xed[0x3d] = None
        self._instructions_0xed[0x3e] = None
        self._instructions_0xed[0x3f] = None

        self._instructions_0xed[0x40] = None
        self._instructions_0xed[0x41] = None
        self._instructions_0xed[0x42] = self._sbc_hl
        self._instructions_0xed[0x43] = None
        self._instructions_0xed[0x44] = None
        self._instructions_0xed[0x45] = None
        self._instructions_0xed[0x46] = None
        self._instructions_0xed[0x47] = self._load_i_r_register_from_a
        self._instructions_0xed[0x48] = None
        self._instructions_0xed[0x49] = None
        self._instructions_0xed[0x4a] = self._adc_hl
        self._instructions_0xed[0x4b] = None
        self._instructions_0xed[0x4c] = None
        self._instructions_0xed[0x4d] = None
        self._instructions_0xed[0x4e] = None
        self._instructions_0xed[0x4f] = self._load_i_r_register_from_a

        self._instructions_0xed[0x50] = None
        self._instructions_0xed[0x51] = None
        self._instructions_0xed[0x52] = self._sbc_hl
        self._instructions_0xed[0x53] = None
        self._instructions_0xed[0x54] = None
        self._instructions_0xed[0x55] = None
        self._instructions_0xed[0x56] = None
        self._instructions_0xed[0x57] = self._load_a_from_i_r_registers
        self._instructions_0xed[0x58] = None
        self._instructions_0xed[0x59] = None
        self._instructions_0xed[0x5a] = self._adc_hl
        self._instructions_0xed[0x5b] = None
        self._instructions_0xed[0x5c] = None
        self._instructions_0xed[0x5d] = None
        self._instructions_0xed[0x5e] = None
        self._instructions_0xed[0x5f] = self._load_a_from_i_r_registers

        self._instructions_0xed[0x60] = None
        self._instructions_0xed[0x61] = None
        self._instructions_0xed[0x62] = self._sbc_hl
        self._instructions_0xed[0x63] = None
        self._instructions_0xed[0x64] = None
        self._instructions_0xed[0x65] = None
        self._instructions_0xed[0x66] = None
        self._instructions_0xed[0x67] = None
        self._instructions_0xed[0x68] = None
        self._instructions_0xed[0x69] = None
        self._instructions_0xed[0x6a] = self._adc_hl
        self._instructions_0xed[0x6b] = None
        self._instructions_0xed[0x6c] = None
        self._instructions_0xed[0x6d] = None
        self._instructions_0xed[0x6e] = None
        self._instructions_0xed[0x6f] = None

        self._instructions_0xed[0x70] = None
        self._instructions_0xed[0x71] = None
        self._instructions_0xed[0x72] = self._sbc_hl
        self._instructions_0xed[0x73] = None
        self._instructions_0xed[0x74] = None
        self._instructions_0xed[0x75] = None
        self._instructions_0xed[0x76] = None
        self._instructions_0xed[0x77] = None
        self._instructions_0xed[0x78] = None
        self._instructions_0xed[0x79] = None
        self._instructions_0xed[0x7a] = self._adc_hl
        self._instructions_0xed[0x7b] = None
        self._instructions_0xed[0x7c] = None
        self._instructions_0xed[0x7d] = None
        self._instructions_0xed[0x7e] = None
        self._instructions_0xed[0x7f] = None

        self._instructions_0xed[0x80] = None
        self._instructions_0xed[0x81] = None
        self._instructions_0xed[0x82] = None
        self._instructions_0xed[0x83] = None
        self._instructions_0xed[0x84] = None
        self._instructions_0xed[0x85] = None
        self._instructions_0xed[0x86] = None
        self._instructions_0xed[0x87] = None
        self._instructions_0xed[0x88] = None
        self._instructions_0xed[0x89] = None
        self._instructions_0xed[0x8a] = None
        self._instructions_0xed[0x8b] = None
        self._instructions_0xed[0x8c] = None
        self._instructions_0xed[0x8d] = None
        self._instructions_0xed[0x8e] = None
        self._instructions_0xed[0x8f] = None

        self._instructions_0xed[0x90] = None
        self._instructions_0xed[0x91] = None
        self._instructions_0xed[0x92] = None
        self._instructions_0xed[0x93] = None
        self._instructions_0xed[0x94] = None
        self._instructions_0xed[0x95] = None
        self._instructions_0xed[0x96] = None
        self._instructions_0xed[0x97] = None
        self._instructions_0xed[0x98] = None
        self._instructions_0xed[0x99] = None
        self._instructions_0xed[0x9a] = None
        self._instructions_0xed[0x9b] = None
        self._instructions_0xed[0x9c] = None
        self._instructions_0xed[0x9d] = None
        self._instructions_0xed[0x9e] = None
        self._instructions_0xed[0x9f] = None

        self._instructions_0xed[0xa0] = None
        self._instructions_0xed[0xa1] = None
        self._instructions_0xed[0xa2] = None
        self._instructions_0xed[0xa3] = None
        self._instructions_0xed[0xa4] = None
        self._instructions_0xed[0xa5] = None
        self._instructions_0xed[0xa6] = None
        self._instructions_0xed[0xa7] = None
        self._instructions_0xed[0xa8] = None
        self._instructions_0xed[0xa9] = None
        self._instructions_0xed[0xaa] = None
        self._instructions_0xed[0xab] = None
        self._instructions_0xed[0xac] = None
        self._instructions_0xed[0xad] = None
        self._instructions_0xed[0xae] = None
        self._instructions_0xed[0xaf] = None

        self._instructions_0xed[0xb0] = None
        self._instructions_0xed[0xb1] = None
        self._instructions_0xed[0xb2] = None
        self._instructions_0xed[0xb3] = None
        self._instructions_0xed[0xb4] = None
        self._instructions_0xed[0xb5] = None
        self._instructions_0xed[0xb6] = None
        self._instructions_0xed[0xb7] = None
        self._instructions_0xed[0xb8] = None
        self._instructions_0xed[0xb9] = None
        self._instructions_0xed[0xba] = None
        self._instructions_0xed[0xbb] = None
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


