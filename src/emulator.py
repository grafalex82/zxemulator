import logging
from machine import Machine, TICKS_PER_FRAME, CPU_FREQ
from cpu import CPU

logger = logging.getLogger('emulator')

class Emulator:
    """
        Z80-based machine emulator.

        This class is responsible to driving emulation process with the given machine and CPU. The Emulator
        provides possibility to run emulated CPU for a a single instruction, as well as for a number of cycles.
        The Emulator also provides possibility to hook to the emulated code execution by setting up breakpoints.
        Breakpoints allow running emulator side code when the emulated CPU reaches a certain instruction address.

        In order to speed up data loading into the computer, this emulator class provides a feature to load
        a tape data from disk directly to the emulater computer memory.
    """
    def __init__(self, machine):
        self._machine = machine
        self._cpu = CPU(self._machine)
        self._breakpoints = {}
        self._startaddr = 0x0000

    def set_start_addr(self, addr):
        self._startaddr = addr

    def add_breakpoint(self, addr, fn):
        if addr not in self._breakpoints:
            self._breakpoints[addr] = []    
        self._breakpoints[addr].append(fn)

    def _handle_breakpoints(self):
        # Run the breakpoint function if condition is met
        br_list = self._breakpoints.get(self._cpu._pc, [])
        for br in br_list:  
            br()

    def step(self):
        self._handle_breakpoints()
        self._cpu.step()

    def run(self, num_cycles=0):
        stop_at = self._cpu._cycles + num_cycles
        logger.debug(f"Running for {num_cycles} cycles. Current cycles: {self._cpu._cycles} (Time: {self._cpu._cycles / CPU_FREQ:.3}), stop at: {stop_at}")
        while num_cycles == 0 or self._cpu._cycles <= stop_at:
            self.step()

    def run1frame(self):
        # TODO: scheduling an interrupt each 50ms shall be a Machine's responsibility, not Emulator
        self._machine.schedule_interrupt()
        self.run(TICKS_PER_FRAME)

    def reset(self):
        self._machine.reset()
        self._cpu._pc = self._startaddr

        


