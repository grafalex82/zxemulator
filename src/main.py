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

resources_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
tapes_dir = os.path.join(os.path.dirname(__file__), "..", "tapes")


def breakpoint():
    logging.disable(logging.NOTSET)


class Configuration:
    def __init__(self):
        # self._screen = pygame.display.set_mode(self.get_screen_size())
        # self._clock = pygame.time.Clock()

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
            # for event in pygame.event.get():
            #     if event.type == pygame.QUIT:
            #         exit()

            #     self.handle_event(event)
            
            self._emulator.run(20000)

            # if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            #     self._emulator.reset()

            self._machine.update()

            # surface = pygame.display.get_surface()
            # surface.fill(pygame.Color('black'))
            # self.update(surface)

            # pygame.display.flip()
            # self._clock.tick(60)
            # pygame.display.set_caption(f"UT-88 Emulator (FPS={self._clock.get_fps()})")


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
        self._machine.add_memory(MemoryDevice(RAM(), 0x8000, 0xffff))
        self._machine.add_memory(MemoryDevice(ROM(f"{resources_dir}/spectrum48.rom"), 0x0000))


    def create_peripherals(self):
        # TODO
        pass


    def configure_logging(self):
        # TODO
        pass

    def get_screen_size(self):
        # TODO
        return (450, 294)


    def update(self, screen):
        # TODO
        pass


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
