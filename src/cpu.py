import logging

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
        self.reset()


    def reset(self):
        """
        Resets registers and flags
        """
        self._pc = 0
        self._sp = 0

        # Registers
        self._a = 0     # Accumulator
        self._f = 0    # Flags register
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
