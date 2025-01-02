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
        self._display.fill((0, 0, 0))

        # Pixmap
        self._pixmap = [0] * (DISPLAY_WIDTH * DISPLAY_HEIGHT)

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


    def _update_pixels(self, offset, value):
        # Address is calculated as bit shuffle as follows:
        # a12 a11 a10 a9  a8   a7  a6  a5  a4  a3  a2  a1  a0
        # y7  y6  y2  y1  y0   y5  y4  y3  x4  x3  x2  x1  x0
        # see http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/screen-memory-layout
        #
        # Here we need a reverse shuffling, to get the x and y coordinates from the address
        # X: a4 a3 a2 a1 a0
        # Y: a12 a11 a7 a6 a5 a10 a9 a8
        x_block = offset & 0x1f
        y = ((offset & 0x700) >> 8) | ((offset & 0xe0) >> (5-3)) | ((offset & 0x1800) >> (11-6))

        # Get color attributes for the block
        color_addr = 0x1800 + (y // 8) * (DISPLAY_WIDTH // 8) + x_block
        attr = self.read_byte(color_addr)
        bg = (attr & 0x78) >> 3
        bg_color = self._colors[bg]
        fg = attr & 0x7 | ((attr & 0x40) >> 3)
        fg_color = self._colors[fg]

        # Update pixels in the corresponding block
        for bit in range(8):
            x = x_block * 8 + bit
            mask = 1 << (7 - bit)
            pixel = value & mask != 0

            self._pixmap[y * DISPLAY_WIDTH + x] = pixel
            self._set_pixel(x, y, fg_color if pixel else bg_color)


    def _update_colors(self, attr_offset, value):
        # Get coordinates of the 8x8 block
        x_block = attr_offset % 32
        y_block = attr_offset // 32
        
        # Get color attributes for the block
        bg = (value & 0x78) >> 3
        bg_color = self._colors[bg]
        fg = value & 0x7 | ((value & 0x40) >> 3)
        fg_color = self._colors[fg]

        # Update pixel colors in the corresponding block
        for x_bit in range(8):
            x = x_block * 8 + x_bit
            for y_bit in range(8):
                y = y_block * 8 + y_bit
                pixel = self._pixmap[y * DISPLAY_WIDTH + x]
                self._set_pixel(x, y, fg_color if pixel else bg_color)


    def write_byte(self, offset, value):
        # Update the RAM value as usual
        RAM.write_byte(self, offset, value)

        # Then update corresponding pixels on the screen
        # Note that offset is relative to 0x4000 video memory start
        if offset < 0x1800:
            self._update_pixels(offset, value)
        else:
            self._update_colors(offset - 0x1800, value)


    def update(self, screen):
        screen.blit(self._display, (0, 0))
