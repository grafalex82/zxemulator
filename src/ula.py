from utils import *

class ULA:
    def __init__(self):
        self._keyboard = None

    def set_keyboard(self, keyboard):
        self._keyboard = keyboard

    def update(self):
        pass

    def read_byte(self, addr, extra_addr):
        if extra_addr != 0xff:
            return self._keyboard.read_row(extra_addr)
        
        # TODO: Handle reading tape recorder here
        return 0xff
    
    def write_byte(self, addr, extra_addr, value):
        # TODO: handle tape recorder here, as well as border color
        pass
