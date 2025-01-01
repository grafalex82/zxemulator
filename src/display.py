import pygame

from utils import *
from ram import RAM

DISPLAY_WIDTH = 256
DISPLAY_HEIGHT = 192
SCALE = 2

class Display(RAM):
    def __init__(self):
        RAM.__init__(self, 0x1b00)  # Size is 256*192/8 bytes for pixels, and 256*192/(8*8) = 768 bytes for colors
        size = (DISPLAY_WIDTH * SCALE, DISPLAY_HEIGHT * SCALE)
        self._display = pygame.Surface(size)

        # ZX spectrum color palete is using GRB colors order, and the 4th bit is used for brightness
        self._colors = [
            (0x00, 0x00, 0x00), # Black
            (0x01, 0x00, 0xce), # Dark Blue
            (0xcf, 0x01, 0x00), # Dark Red
            (0xcf, 0x01, 0xce), # Dark Magenta
            (0x00, 0xcf, 0x15), # Dark Green
            (0x01, 0xcf, 0xcf), # Dark Cyan
            (0xcf, 0xcf, 0x15), # Dark Yellow
            (0xcf, 0xcf, 0xcf), # Gray  
            (0x00, 0x00, 0x00), # 'Bright' Black
            (0x02, 0x00, 0xfd), # Bright Blue
            (0xff, 0x02, 0x01), # Bright Red
            (0xff, 0x02, 0xfd), # Bright Magenta
            (0x00, 0xff, 0x1c), # Bright Green
            (0x02, 0xff, 0xff), # Bright Cyan
            (0xff, 0xff, 0x1d), # Bright Yellow
            (0xff, 0xff, 0xff), # Whote
        ]

    def _set_pixel(self, x, y, color):
        self._display.set_at((x * SCALE, y * SCALE), color)
        self._display.set_at((x * SCALE + 1, y * SCALE), color)
        self._display.set_at((x * SCALE, y * SCALE + 1), color)
        self._display.set_at((x * SCALE + 1, y * SCALE + 1), color)


    def update(self, screen):
        for y in range(DISPLAY_HEIGHT):
            for x in range(DISPLAY_WIDTH):
                color = (x + y) % 16
                self._set_pixel(x, y, self._colors[color])

        screen.blit(self._display, (0, 0))
