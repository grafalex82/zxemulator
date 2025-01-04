import pygame

class Keyboard:
    def __init__(self):
        self._key_map = {}
        self._key_map[pygame.K_h]       = (0xbf, 0xef)
        self._key_map[pygame.K_j]       = (0xbf, 0xf7)
        self._key_map[pygame.K_k]       = (0xbf, 0xfb)
        self._key_map[pygame.K_l]       = (0xbf, 0xfd)
        self._key_map[pygame.K_RETURN]  = (0xbf, 0xfe)

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
    
