import logging
import tkinter
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


@dataclass
class _EventBinding:
    func: callable
    root: tkinter.Widget


class EventBinder:
    """
    Standard tkinter bindings can't easily pass data in events.
    This class provides a simplified solution leveraging the builtin "after" method.
    [2016 Python PR for virtual event data](https://github.com/python/cpython/pull/7142).
    It looks like this will be part of Python 3.15.
    """

    def __init__(self):
        self.sequence_bindings: dict[str, list[_EventBinding]] = {}
        self.map = {}

    def __setitem__(self, key: str | StrEnum, value):
        key = str(key)
        self.map[key] = value

    def __contains__(self, key: str | StrEnum):
        key = str(key)
        return key in self.map

    def __getitem__(self, key: str | StrEnum):
        key = str(key)
        return self.map[key]

    def get(self, key: StrEnum | str, default = None):
        key = str(key)
        self.map.get(key, default)

    def bind(self, sequence: str, func: callable, root: tkinter.Widget):
        sequence = str(sequence)
        logger.info("Adding Binding %s for func %s", sequence, callable.__name__)
        if sequence not in self.sequence_bindings:
            self.sequence_bindings[sequence] = []
        self.sequence_bindings[sequence].append(_EventBinding(func, root))

    def event_generate(self, sequence: str, *args, **kwargs):
        sequence = str(sequence)
        logger.debug("Generating event for sequence: %s", sequence)
        if args:
            if len(args) == 1:
                self[sequence] = args[0]
            else:
                self[sequence] = args
        if sequence in self.sequence_bindings:
            for binding in self.sequence_bindings[sequence]:
                binding.root.after(0, binding.func, *args)
        elif sequence.startswith("on_"):
            logger.debug(
                "Sequence %s not bound. Currently bound keys: %s.",
                sequence,
                self.sequence_bindings.keys(),
            )


    def get_or_default(self, key, default):
        if str(key) in self.map:
            return self.map[str(key)]
        else:
            return default


event_binder = EventBinder()
