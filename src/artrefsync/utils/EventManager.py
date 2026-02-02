from dataclasses import dataclass
from enum import StrEnum, auto
import tkinter
import logging

logger = logging.getLogger(__name__)


@dataclass
class _EventBinding:
    func: callable
    root: tkinter.Widget


class EventManager:
    """
    Standard tkinter bindings can't easily pass data in events.
    This class provides a simplified solution leveraging the builtin "after" method.
    [2016 Python PR for virtual event data](https://github.com/python/cpython/pull/7142)

    """

    def __init__(self):
        self.sequence_bindings: dict[str, list[_EventBinding]] = {}
        self.map = {}
        # self.__setitem__ = self.map.__setitem__
        # self.__contains__ = self.map.__contains__
        # self.__getitem__ = self.map.__getitem__


    def bind(self, sequence: str, func: callable, root: tkinter.Widget):
        sequence = str(sequence)
        logger.info("Adding Binding %s for func %s", sequence, callable.__name__)
        if sequence not in self.sequence_bindings:
            self.sequence_bindings[sequence] = []
        self.sequence_bindings[sequence].append(_EventBinding(func, root))

    def event_generate(self, sequence: str, *args):
        sequence = str(sequence)
        logger.info("Generating event for sequence: %s", sequence)
        if args:
            if len(args) == 1:
                self[sequence] = args[0]
            else:
                self[sequence] = args
        if sequence in self.sequence_bindings:
            for binding in self.sequence_bindings[sequence]:
                binding.root.after(0, binding.func, *args)
        elif sequence.startswith("on_"):
            logger.warning(
                "Sequence %s not bound. Currently bound keys: %s.",
                sequence,
                self.sequence_bindings.keys(),
            )

    def __setitem__(self, key, value):

        self.map[str(key)] = value

    def __contains__(self, key):
        return str(key) in self.map

    def __getitem__(self, key):
        return self.map[str(key)]


ebinder = EventManager()

if __name__ == "__main__":
    import ttkbootstrap as ttk
    root = ttk.Window(themename="darkly", size=(1080, 1080))
    def hello(data):
        print(f"Hello {data}")

    ebinder.bind("Test", hello, root)
    ebinder.event_generate("Test", "World")

    root.mainloop()
