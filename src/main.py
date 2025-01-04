import os
import logging
import pygame
import argparse
from tkinter import filedialog

from emulator import Emulator
from machine import Machine
from interfaces import MemoryDevice, IODevice
from ram import RAM
from rom import ROM
from utils import NestedLogger
from display import *
from ula import ULA
from keyboard import Keyboard

resources_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
tapes_dir = os.path.join(os.path.dirname(__file__), "..", "tapes")


def breakpoint():
    logging.disable(logging.NOTSET)


def dump(machine):
    with open("dump.bin", "wb") as f:
        for b in range(65536):
            f.write(bytes([machine.read_memory_byte(b)]))

class Configuration:
    def __init__(self):
        self._screen = pygame.display.set_mode(self.get_screen_size())
        self._clock = pygame.time.Clock()

        self._machine = Machine()
        self._emulator = Emulator(self._machine)

        self._emulator.set_start_addr(self.get_start_address())

        self.create_memories()
        self.create_peripherals()

        self._emulator._cpu.enable_registers_logging(True)
        self._logger = NestedLogger()
        self._emulator.add_breakpoint(self.get_start_address(), lambda: self._logger.reset())
        self._suppressed_logs = []

        self.configure_logging()
        self.setup_special_breakpoints()


    def create_memories(self):
        pass


    def create_peripherals(self):
        pass


    def configure_logging(self):
        pass


    def setup_special_breakpoints(self):
        pass


    def get_start_address(self):
        return 0x0000


    def run(self):
        self._emulator.reset()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exit()

                self.handle_event(event)
            
            self._emulator.run1frame()

            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                self._emulator.reset()

            self._machine.update()

            surface = pygame.display.get_surface()
            surface.fill(pygame.Color('black'))
            self.update(surface)

            pygame.display.flip()
            self._clock.tick(60)
            pygame.display.set_caption(f"ZX Spectrum Emulator (FPS={self._clock.get_fps()})")


    def suppress_logging(self, startaddr, endaddr, msg):
        self._suppressed_logs.append((startaddr, endaddr, msg))


    def enable_logging(self, enable):
        class LoggerEnterFunctor:
            def __init__(self, logger, msg):
                self._logger = logger
                self._msg = msg

            def __call__(self):
                self._logger.enter(self._msg)

        class LoggerExitFunctor:
            def __init__(self, logger, msg):
                self._logger = logger
                self._msg = msg

            def __call__(self):
                self._logger.exit()

        if enable:
            logging.basicConfig(level=logging.DEBUG)

            for startaddr, endaddr, msg in self._suppressed_logs:
                enter = LoggerEnterFunctor(self._logger, msg)
                self._emulator.add_breakpoint(startaddr, enter)

                exit = LoggerExitFunctor(self._logger, msg)
                self._emulator.add_breakpoint(endaddr, exit)


    def handle_event(self, event):
        pass


class Spectrum48K(Configuration):
    def __init__(self):
        Configuration.__init__(self)
 

    def create_memories(self):
        self._machine.add_memory(MemoryDevice(RAM(), 0x5b00, 0xffff))
        self._machine.add_memory(MemoryDevice(ROM(f"{resources_dir}/spectrum48.rom"), 0x0000))


    def create_peripherals(self):
        self._display = Display()
        self._machine.add_memory(MemoryDevice(self._display, 0x4000))

        self._ula = ULA()
        self._machine.add_io(IODevice(self._ula, 0xfe))

        self._keyboard = Keyboard()
        self._ula.set_keyboard(self._keyboard)


    def configure_logging(self):
        self.suppress_logging(0x11db, 0x11f0, "Init RAM cleanup")
        pass

    def get_screen_size(self):
        return (DISPLAY_WIDTH * SCALE, DISPLAY_HEIGHT * SCALE)


    def update(self, screen):
        self._display.update(screen)


    def handle_event(self, event):
        self._keyboard.handle_event(event)


    def setup_special_breakpoints(self):
        self._emulator.add_breakpoint(0x129c, lambda: dump(self._emulator._machine))


def main():
    parser = argparse.ArgumentParser(
                    prog='UT-88 Emulator',
                    description='ZX SpectrumUT-88 DIY i8080-based computer emulator')
    
    #parser.add_argument('configuration', choices=["48k"])
    parser.add_argument('configuration', choices=["48k"], nargs='?', default="48k")
    parser.add_argument('-d', '--debug', help="enable CPU instructions logging", action='store_true')
    args = parser.parse_args()

    pygame.init()

    
    if args.configuration == "48k":
        configuration = Spectrum48K()
    
    configuration.enable_logging(args.debug)

    configuration.run()


if __name__ == '__main__':
    main()
