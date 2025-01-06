import pygame

class Keyboard:
    def __init__(self):
        self._key_map = {}

        self._key_map[pygame.K_v]       = (0xfe, 0xef)
        self._key_map[pygame.K_c]       = (0xfe, 0xf7)
        self._key_map[pygame.K_x]       = (0xfe, 0xfb)
        self._key_map[pygame.K_z]       = (0xfe, 0xfd)
        #self._key_map[pygame.K_LSHIFT]  = (0xfe, 0xfe)      # CAPS Shift

        self._key_map[pygame.K_g]       = (0xfd, 0xef)
        self._key_map[pygame.K_f]       = (0xfd, 0xf7)
        self._key_map[pygame.K_d]       = (0xfd, 0xfb)
        self._key_map[pygame.K_s]       = (0xfd, 0xfd)
        self._key_map[pygame.K_a]       = (0xfd, 0xfe)

        self._key_map[pygame.K_t]       = (0xfb, 0xef)
        self._key_map[pygame.K_r]       = (0xfb, 0xf7)
        self._key_map[pygame.K_e]       = (0xfb, 0xfb)
        self._key_map[pygame.K_w]       = (0xfb, 0xfd)
        self._key_map[pygame.K_q]       = (0xfb, 0xfe)

        self._key_map[pygame.K_5]       = (0xf7, 0xef)
        self._key_map[pygame.K_4]       = (0xf7, 0xf7)
        self._key_map[pygame.K_3]       = (0xf7, 0xfb)
        self._key_map[pygame.K_2]       = (0xf7, 0xfd)
        self._key_map[pygame.K_1]       = (0xf7, 0xfe)

        self._key_map[pygame.K_6]       = (0xef, 0xef)
        self._key_map[pygame.K_7]       = (0xef, 0xf7)
        self._key_map[pygame.K_8]       = (0xef, 0xfb)
        self._key_map[pygame.K_9]       = (0xef, 0xfd)
        self._key_map[pygame.K_0]       = (0xef, 0xfe)

        self._key_map[pygame.K_y]       = (0xdf, 0xef)
        self._key_map[pygame.K_u]       = (0xdf, 0xf7)
        self._key_map[pygame.K_i]       = (0xdf, 0xfb)
        self._key_map[pygame.K_o]       = (0xdf, 0xfd)
        self._key_map[pygame.K_p]       = (0xdf, 0xfe)

        self._key_map[pygame.K_h]       = (0xbf, 0xef)
        self._key_map[pygame.K_j]       = (0xbf, 0xf7)
        self._key_map[pygame.K_k]       = (0xbf, 0xfb)
        self._key_map[pygame.K_l]       = (0xbf, 0xfd)
        self._key_map[pygame.K_RETURN]  = (0xbf, 0xfe)

        self._key_map[pygame.K_b]       = (0x7f, 0xef)
        self._key_map[pygame.K_n]       = (0x7f, 0xf7)
        self._key_map[pygame.K_m]       = (0x7f, 0xfb)
        #self._key_map[pygame.K_RSHIFT]       = (0x7f, 0xfd)
        self._key_map[pygame.K_SPACE]   = (0x7f, 0xfe)

        self._pressed_key = (0xff, 0xff)


    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in self._key_map:
                self._pressed_key = self._key_map[event.key]
            
        if event.type == pygame.KEYUP:
            self._pressed_key = (0xff, 0xff)


    def emulate_key_press(self, key):
        self._pressed_key = key


    def read_row(self, row_mask):
        if self._pressed_key[0] == row_mask:
            return self._pressed_key[1]
        
        return 0xff
    
