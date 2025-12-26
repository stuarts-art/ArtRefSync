import sys
import time
import math
import random
from enum import StrEnum
import builtins

class CURS(StrEnum):
    U = "\033[1A"
    D = "\033[1B"
    R = "\033[1C"
    L = "\033[1D"
    SCROLLD = "\033[1S"
    HIDE = "\033[?25l"
    SHOW = "\033[?25h"
    STARTD = "\033[1E"
    STARTU = "\033[1F"
    CLEAR = '\033[K'
    SAVE = "\033[s"
    RESTORE = "\033[u"

def curs_print(input, line = 0):
    cursor = CURS.STARTD * line if line >= 0 else CURS.STARTU * (-line)
    rcursor = CURS.STARTU * line if line >= 0 else CURS.STARTD * (-line)
    return f"\r{cursor}\r{CURS.CLEAR}{input}{rcursor}"


class Snail():
    def __init__(self, total_count = 100, bar_preffix = "Loading"):
        self._oldprint = builtins.print
        self.bar_preffix = bar_preffix
        self.total_count = total_count
        builtins.print = self.snail_print
        self.last = ""

    def __enter__(self):
        sys.stdout.write(f"{'\n' * 2}{CURS.STARTU*2}")
        return self

    def load(self, current_count):
        self.loading(current_count/ self.total_count, self.bar_preffix)
        
    def __exit__(self, type, value, traceback):
        builtins.print = self._oldprint
        print("\n")

    def loading(self, percent, prefix = "Loading", width = 20, snail = "🐌", trail = "_", line = 1, suffix = "", boxed = False):
        percent_str = str(int(percent*100)).rjust(3)
        snail_str = str(trail*int(percent * width - 1) + snail).ljust(width)
        bar_str = f"{prefix}: {percent_str}%[{snail_str}]{suffix}"
        output = curs_print(bar_str, line)
        self.last = output
        sys.stdout.write(output)
        sys.stdout.flush()

    def snail_print(self, input):
        if self.last == "":
            sys.stdout.write(f"{input}\n\r")
            sys.stdout.flush()
        else:
            output = f"\n\r{CURS.CLEAR}{input}\r\n"
            output += self.last
            sys.stdout.write(output)
            sys.stdout.flush()



if __name__ == "__main__":

    print("print before snail")
    with Snail(100) as snail:
        print("print in snail before loading")
        print("more print in snail before loading")

        for i in range(1,101):
            snail.load(i)
            time.sleep(.1)
            print(i)

    print("print after snail")