import pygame

class Keyboard:
    def __init__(self):
        # Keymap below is filled with 4 numbers
        # - first two represent column/row scan code of the key
        # - second two represent column/row scan code of the CAPS or SYMBOL shift keys
        # This allows map single keys on a host computer (e.g. quote symbol) to a pair or a symbol and SHIFT key
        #
        # Symbols can be entered either with single host computer keys (if exist), or with a key combination:
        # - Shift to emulate CAPS SHIFT
        # - Ctrl to emulate SYMBOL SHIFT

        self._key_map = {}
        self._special_key_map = {}
        self._ctrl_key_map = {}

        # Small letters
        self._key_map['v']              = (0xfe, 0xef, 0xff, 0xff)
        self._key_map['c']              = (0xfe, 0xf7, 0xff, 0xff)
        self._key_map['x']              = (0xfe, 0xfb, 0xff, 0xff)
        self._key_map['z']              = (0xfe, 0xfd, 0xff, 0xff)

        self._key_map['g']              = (0xfd, 0xef, 0xff, 0xff)
        self._key_map['f']              = (0xfd, 0xf7, 0xff, 0xff)
        self._key_map['d']              = (0xfd, 0xfb, 0xff, 0xff)
        self._key_map['s']              = (0xfd, 0xfd, 0xff, 0xff)
        self._key_map['a']              = (0xfd, 0xfe, 0xff, 0xff)

        self._key_map['t']              = (0xfb, 0xef, 0xff, 0xff)
        self._key_map['r']              = (0xfb, 0xf7, 0xff, 0xff)
        self._key_map['e']              = (0xfb, 0xfb, 0xff, 0xff)
        self._key_map['w']              = (0xfb, 0xfd, 0xff, 0xff)
        self._key_map['q']              = (0xfb, 0xfe, 0xff, 0xff)

        self._key_map['5']              = (0xf7, 0xef, 0xff, 0xff)
        self._key_map['4']              = (0xf7, 0xf7, 0xff, 0xff)
        self._key_map['3']              = (0xf7, 0xfb, 0xff, 0xff)
        self._key_map['2']              = (0xf7, 0xfd, 0xff, 0xff)
        self._key_map['1']              = (0xf7, 0xfe, 0xff, 0xff)

        self._key_map['6']              = (0xef, 0xef, 0xff, 0xff)
        self._key_map['7']              = (0xef, 0xf7, 0xff, 0xff)
        self._key_map['8']              = (0xef, 0xfb, 0xff, 0xff)
        self._key_map['9']              = (0xef, 0xfd, 0xff, 0xff)
        self._key_map['0']              = (0xef, 0xfe, 0xff, 0xff)

        self._key_map['y']              = (0xdf, 0xef, 0xff, 0xff)
        self._key_map['u']              = (0xdf, 0xf7, 0xff, 0xff)
        self._key_map['i']              = (0xdf, 0xfb, 0xff, 0xff)
        self._key_map['o']              = (0xdf, 0xfd, 0xff, 0xff)
        self._key_map['p']              = (0xdf, 0xfe, 0xff, 0xff)

        self._key_map['h']              = (0xbf, 0xef, 0xff, 0xff)
        self._key_map['j']              = (0xbf, 0xf7, 0xff, 0xff)
        self._key_map['k']              = (0xbf, 0xfb, 0xff, 0xff)
        self._key_map['l']              = (0xbf, 0xfd, 0xff, 0xff)
        # self._key_map[pygame.K_RETURN]  = (0xbf, 0xfe, 0xff, 0xff)

        self._key_map['b']              = (0x7f, 0xef, 0xff, 0xff)
        self._key_map['n']              = (0x7f, 0xf7, 0xff, 0xff)
        self._key_map['m']              = (0x7f, 0xfb, 0xff, 0xff)
        self._key_map[' ']              = (0x7f, 0xfe, 0xff, 0xff)


        # Capital letters (emulating CAPS SHIFT)
        self._key_map['V']              = (0xfe, 0xef, 0xfe, 0xfe)
        self._key_map['C']              = (0xfe, 0xf7, 0xfe, 0xfe)
        self._key_map['X']              = (0xfe, 0xfb, 0xfe, 0xfe)
        self._key_map['Z']              = (0xfe, 0xfd, 0xfe, 0xfe)

        self._key_map['G']              = (0xfd, 0xef, 0xfe, 0xfe)
        self._key_map['F']              = (0xfd, 0xf7, 0xfe, 0xfe)
        self._key_map['D']              = (0xfd, 0xfb, 0xfe, 0xfe)
        self._key_map['S']              = (0xfd, 0xfd, 0xfe, 0xfe)
        self._key_map['A']              = (0xfd, 0xfe, 0xfe, 0xfe)

        self._key_map['T']              = (0xfb, 0xef, 0xfe, 0xfe)
        self._key_map['R']              = (0xfb, 0xf7, 0xfe, 0xfe)
        self._key_map['E']              = (0xfb, 0xfb, 0xfe, 0xfe)
        self._key_map['W']              = (0xfb, 0xfd, 0xfe, 0xfe)
        self._key_map['Q']              = (0xfb, 0xfe, 0xfe, 0xfe)

        # number keys when pressed with SHIFT generate special codes, which in ZX Spectrum are entered with SYMBOL SHIFT, not CAPS SHIFT
        self._key_map['%']              = (0xf7, 0xef, 0x7f, 0xfd)
        self._key_map['$']              = (0xf7, 0xf7, 0x7f, 0xfd)
        self._key_map['#']              = (0xf7, 0xfb, 0x7f, 0xfd)
        self._key_map['@']              = (0xf7, 0xfd, 0x7f, 0xfd)
        self._key_map['!']              = (0xf7, 0xfe, 0x7f, 0xfd)

        self._key_map['&']              = (0xef, 0xef, 0x7f, 0xfd)
        self._key_map["'"]              = (0xef, 0xf7, 0x7f, 0xfd)
        self._key_map['(']              = (0xef, 0xfb, 0x7f, 0xfd)
        self._key_map[')']              = (0xef, 0xfd, 0x7f, 0xfd)
        self._key_map['_']              = (0xef, 0xfe, 0x7f, 0xfd)

        self._key_map['Y']              = (0xdf, 0xef, 0xfe, 0xfe)
        self._key_map['U']              = (0xdf, 0xf7, 0xfe, 0xfe)
        self._key_map['I']              = (0xdf, 0xfb, 0xfe, 0xfe)
        self._key_map['O']              = (0xdf, 0xfd, 0xfe, 0xfe)
        self._key_map['P']              = (0xdf, 0xfe, 0xfe, 0xfe)

        self._key_map['H']              = (0xbf, 0xef, 0xfe, 0xfe)
        self._key_map['J']              = (0xbf, 0xf7, 0xfe, 0xfe)
        self._key_map['K']              = (0xbf, 0xfb, 0xfe, 0xfe)
        self._key_map['L']              = (0xbf, 0xfd, 0xfe, 0xfe)

        self._key_map['B']              = (0x7f, 0xef, 0xfe, 0xfe)
        self._key_map['N']              = (0x7f, 0xf7, 0xfe, 0xfe)
        self._key_map['M']              = (0x7f, 0xfb, 0xfe, 0xfe)


        # Scan codes for keys pressed with the Ctrl key (emulating SYMBOL SHIFT key)
        self._ctrl_key_map[pygame.K_v]          = (0xfe, 0xef, 0x7f, 0xfd)  # /
        self._ctrl_key_map[pygame.K_c]          = (0xfe, 0xf7, 0x7f, 0xfd)  # ?
        self._ctrl_key_map[pygame.K_x]          = (0xfe, 0xfb, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_z]          = (0xfe, 0xfd, 0x7f, 0xfd)  # :

        self._ctrl_key_map[pygame.K_g]          = (0xfd, 0xef, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_f]          = (0xfd, 0xf7, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_d]          = (0xfd, 0xfb, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_s]          = (0xfd, 0xfd, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_a]          = (0xfd, 0xfe, 0x7f, 0xfd)

        self._ctrl_key_map[pygame.K_t]          = (0xfb, 0xef, 0x7f, 0xfd)  # >
        self._ctrl_key_map[pygame.K_r]          = (0xfb, 0xf7, 0x7f, 0xfd)  # <
        self._ctrl_key_map[pygame.K_e]          = (0xfb, 0xfb, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_w]          = (0xfb, 0xfd, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_q]          = (0xfb, 0xfe, 0x7f, 0xfd)

        # It is easier for modern user to enter symbols above numeric keys with shift, not with Ctrl
        # Instead, when pressed with Ctrl on the host computer, it will generate scancodes with SYMBOL SHIFT, 
        # which in ZX Spectrum world will generate some control codes
        self._ctrl_key_map[pygame.K_5]          = (0xf7, 0xef, 0xfe, 0xfe)  # LEFT
        self._ctrl_key_map[pygame.K_4]          = (0xf7, 0xf7, 0xfe, 0xfe)  # INV VIDEO
        self._ctrl_key_map[pygame.K_3]          = (0xf7, 0xfb, 0xfe, 0xfe)  # TRUE VIDEO
        self._ctrl_key_map[pygame.K_2]          = (0xf7, 0xfd, 0xfe, 0xfe)  # CAPS LOCK
        self._ctrl_key_map[pygame.K_1]          = (0xf7, 0xfe, 0xfe, 0xfe)  # EDIT

        self._ctrl_key_map[pygame.K_6]          = (0xef, 0xef, 0xfe, 0xfe)  # DOWN
        self._ctrl_key_map[pygame.K_7]          = (0xef, 0xf7, 0xfe, 0xfe)  # UP
        self._ctrl_key_map[pygame.K_8]          = (0xef, 0xfb, 0xfe, 0xfe)  # RIGHT
        self._ctrl_key_map[pygame.K_9]          = (0xef, 0xfd, 0xfe, 0xfe)  # GRAPHICS
        self._ctrl_key_map[pygame.K_0]          = (0xef, 0xfe, 0xfe, 0xfe)  # DELETE/BACK

        self._ctrl_key_map[pygame.K_y]          = (0xdf, 0xef, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_u]          = (0xdf, 0xf7, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_i]          = (0xdf, 0xfb, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_o]          = (0xdf, 0xfd, 0x7f, 0xfd)  # ;
        self._ctrl_key_map[pygame.K_p]          = (0xdf, 0xfe, 0x7f, 0xfd)  # "

        self._ctrl_key_map[pygame.K_h]          = (0xbf, 0xef, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_j]          = (0xbf, 0xf7, 0x7f, 0xfd)  # -
        self._ctrl_key_map[pygame.K_k]          = (0xbf, 0xfb, 0x7f, 0xfd)  # +
        self._ctrl_key_map[pygame.K_l]          = (0xbf, 0xfd, 0x7f, 0xfd)  # =
        self._ctrl_key_map[pygame.K_RETURN]     = (0xbf, 0xfe, 0xff, 0xff)  # Normal keycode, without SYMBOL/CAPS shift

        self._ctrl_key_map[pygame.K_b]          = (0x7f, 0xef, 0x7f, 0xfd)
        self._ctrl_key_map[pygame.K_n]          = (0x7f, 0xf7, 0x7f, 0xfd)  # ,
        self._ctrl_key_map[pygame.K_m]          = (0x7f, 0xfb, 0x7f, 0xfd)  # .
        self._ctrl_key_map[pygame.K_SPACE]      = (0x7f, 0xfe, 0x7f, 0xfd)


        # Symbols and host keys to ZX key mapping
        self._special_key_map[pygame.K_BACKSPACE]  = (0xef, 0xfe, 0xfe, 0xfe)  # Same as Ctrl-0
        self._special_key_map[pygame.K_LEFT]       = (0xf7, 0xef, 0xfe, 0xfe)  # Same as Ctrl-5
        self._special_key_map[pygame.K_RIGHT]      = (0xef, 0xfb, 0xfe, 0xfe)  # Same as Ctrl-8
        self._special_key_map[pygame.K_UP]         = (0xef, 0xf7, 0xfe, 0xfe)  # Same as Ctrl-6
        self._special_key_map[pygame.K_DOWN]       = (0xef, 0xef, 0xfe, 0xfe)  # Same as Ctrl-7
        self._special_key_map[pygame.K_RETURN]     = (0xbf, 0xfe, 0xff, 0xff)
        self._special_key_map[pygame.K_SPACE]      = (0x7f, 0xfe, 0xff, 0xff)

        self._key_map[';']              = (0xdf, 0xfd, 0x7f, 0xfd)  # Same as Ctrl-O
        self._key_map[':']              = (0xfe, 0xfd, 0x7f, 0xfd)  # Same as Ctrl-Z
        self._key_map['"']              = (0xdf, 0xfe, 0x7f, 0xfd)  # Same as Ctrl-P
        self._key_map['-']              = (0xbf, 0xf7, 0x7f, 0xfd)  # Same as Ctrl-J
        self._key_map['+']              = (0xbf, 0xfb, 0x7f, 0xfd)  # Same as Ctrl-K
        self._key_map['=']              = (0xbf, 0xfd, 0x7f, 0xfd)  # Same as Ctrl-L
        self._key_map['?']              = (0xfe, 0xf7, 0x7f, 0xfd)  # Same as Ctrl-C
        self._key_map['/']              = (0xfe, 0xef, 0x7f, 0xfd)  # Same as Ctrl-V
        self._key_map[',']              = (0x7f, 0xf7, 0x7f, 0xfd)  # Same as Ctrl-N
        self._key_map['.']              = (0x7f, 0xfb, 0x7f, 0xfd)  # Same as Ctrl-M
        self._key_map['<']              = (0xfb, 0xf7, 0x7f, 0xfd)  # Same as Ctrl-R
        self._key_map['>']              = (0xfb, 0xef, 0x7f, 0xfd)  # Same as Ctrl-T


        self._pressed_key = (0xff, 0xff, 0xff, 0xff)


    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in self._ctrl_key_map and (pygame.key.get_mods() & pygame.KMOD_CTRL) != 0:
                self._pressed_key = self._ctrl_key_map[event.key]
                return

            if event.key in self._special_key_map:
                self._pressed_key = self._special_key_map[event.key]
                return

            if event.unicode in self._key_map:
                self._pressed_key = self._key_map[event.unicode]
            
        if event.type == pygame.KEYUP:
            self._pressed_key = (0xff, 0xff, 0xff, 0xff)


    def emulate_key_press(self, key):
        self._pressed_key = key


    def read_row(self, row_mask):
        # Get the key scan code, if key in the selected row is pressed
        value = 0xff
        if self._pressed_key[0] == row_mask:
            value = self._pressed_key[1]
        
        # Apply CAPS and SYMBOL shift key codes
        if self._pressed_key[2] == row_mask:
            value &= self._pressed_key[3]

        return value
    
