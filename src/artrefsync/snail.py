import sys
import time
import math
import random
from enum import StrEnum

class CURS(StrEnum):
    U = "\033[1A"
    D = "\033[1B"
    R = "\033[1C"
    L = "\033[1D"
    HIDE = "\033[?25l"
    CLEAR = '\x1b[2K'

def loading(percent, prefix = "Loading", width = 20, snail = "🐌", trail = "_"):
    sys.stdout.write(f"\r{prefix}: {str(int(percent*100)).rjust(3)}%[{str(trail*int(percent * width - 1) + snail).ljust(width)}]")
    sys.stdout.flush() # Ensure the output is immediately displayed

def double_loading(percent, prefix = "Loading", width = 20, snail = "🐌", trail = "_", movement = 0):
    snail_str =  "{0}\r{1}: {2}%[{3}]{4}".format(
        "" if movement < 1 else CURS.U * movement,
        prefix,
        str(int(percent*100)).rjust(3),
        {str(trail*int(percent * width - 1) + snail).ljust(width)},
        "" if movement < 1 else CURS.D * movement,
    )
    sys.stdout.write(snail_str)

def done(prefix = "Loading"):
    sys.stdout.write(f"\r{prefix}: Done\n") # Overwrite and add a newline at the end


def double_snail():
    sys.stdout.write(f"\n\n\n\n\n{CURS.HIDE}")

    a = 0
    b = 0
    c = 0
    d = 0
    i = 0
    while a < 100 and b < 100 and c < 100 and d < 100:
        a+=random.randint(0,1)
        b+=random.randint(0,1)
        c+=random.randint(0,1)
        d+=random.randint(0,1)
        sys.stdout.write(f"{CURS.U * 6}\r{"#" * 50}{CURS.D*6}")
        sys.stdout.write(f"{CURS.U * 5}\rSNAIL RACE{CURS.D*5}")
        double_loading(a/100, prefix= "SNAIL A",movement=4-0)
        double_loading(b/100, prefix= "SNAIL B",movement=4-1)
        double_loading(c/100, prefix= "SNAIL C",movement=4-2)
        double_loading(d/100, prefix= "SNAIL D",movement=4-3)
        sys.stdout.write(f"\rTurn {i}")
        sys.stdout.flush() # Ensure the output is immediately displayed
        i +=1
        time.sleep(.2)
    done(f"{CURS.D*4}      ")

if __name__ == "__main__":
    double_snail()
    # for i in range(101):
    #     loading(i/100)
    #     sys.stdout.flush() # Ensure the output is immediately displayed
    #     time.sleep(.1)
    # done()
    





    

    
    