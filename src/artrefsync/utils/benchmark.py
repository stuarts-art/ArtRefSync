import shutil
import sys
import time
import humanize
import inspect
from pympler import asizeof


def main():
    with Bm("Test"):
        test = "Hello World"
        test2 = "I don't know?"

    with Bm("Test 2"):
        test3 = "Hello World"
        test4 = "I don't know?"


def obj_size(obj) -> str:
    return humanize.naturalsize(asizeof.asizeof(obj))


def wrap_line(lines, line_size, border_char="│"):
    wrapped_lines = ""
    for line in lines.split("\n"):
        inner_line = line_size - 4
        c_line = ""
        for s in line.split(" "):
            if len(c_line) == 0:
                pass
            elif len(c_line) > inner_line or len(c_line) + len(s) + 1 > inner_line:
                wrapped_lines += f"│ {c_line.ljust(inner_line)} │\n"
                c_line = ""
            c_line += " " if len(c_line) > 0 else ""
            c_line += s
        if c_line != "":
            wrapped_lines += f"│ {c_line.ljust(inner_line)} │\n"
    return wrapped_lines

class Bm(object):
    def __init__(self, name = "Benchmark", pretty=True, logger=None):
        self.name = name
        self.pretty = pretty
        self.logger = logger

    def __enter__(self):
        self.time_start = time.perf_counter()
        self.old_locals = sys._getframe(1).f_locals.copy()
        self.caller_frame = inspect.stack()[1]
        self.class_name = None

        if 'self' in self.old_locals:
            self.class_name = self.old_locals['self'].__class__.__name__

        return self

    def __exit__(self, exc_time, exc_value, traceback):
        time_line = f"{f"{self.class_name} - " if self.class_name else ""} {self.name} - {time.perf_counter() - self.time_start:.3f} seconds."
        size_lines = ""
        new_locals = sys._getframe(1).f_locals
        for local in new_locals.keys() - self.old_locals.keys():
            size_lines += f"\n- {local}: {obj_size(new_locals[local])}"

        if self.pretty:
            line_size = int(min(80, shutil.get_terminal_size((80, 50)).columns))
            pretty_lines = (
                f"╭{'─' * (line_size - 2)}╮\n"
                + wrap_line(time_line, line_size)
                + f"├{'─' * (line_size - 2)}┤\n"
                + wrap_line(size_lines, line_size)
                + f"╰{'─' * (line_size - 2)}╯"
            )
            if self.logger:
                self.logger.info("\n%s", pretty_lines)
            else:
                print(pretty_lines)

        else:
            if self.logger:
                self.logger.info(time_line + size_lines)
            else:
                print(time_line + size_lines)
        return False


if __name__ == "__main__":
    main()
