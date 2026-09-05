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

    def after_idle(self, sequence: str, *args, **kwargs):
        sequence = str(sequence)
        logger.debug("Generating event for sequence: %s", sequence)
        if args:
            if len(args) == 1:
                self[sequence] = args[0]
            else:
                self[sequence] = args
        if sequence in self.sequence_bindings:
            for binding in self.sequence_bindings[sequence]:
                binding.root.after_idle(binding.func, *args, **kwargs)
        elif sequence.startswith("on_"):
            logger.debug(
                "Sequence %s not bound. Currently bound keys: %s.",
                sequence,
                self.sequence_bindings.keys(),
            )

    def after(self, ms, sequence: str, *args, **kwargs):
        sequence = str(sequence)
        logger.debug("Generating event for sequence: %s", sequence)
        if args:
            if len(args) == 1:
                self[sequence] = args[0]
            else:
                self[sequence] = args
        if sequence in self.sequence_bindings:
            for binding in self.sequence_bindings[sequence]:
                binding.root.after(ms, binding.func, *args, **kwargs)
        elif sequence.startswith("on_"):
            logger.debug(
                "Sequence %s not bound. Currently bound keys: %s.",
                sequence,
                self.sequence_bindings.keys(),
            )

    def run(self, sequence: str, *args, **kwargs):
        sequence = str(sequence)
        logger.info("Generating event for sequence: %s", sequence)
        if args:
            if len(args) == 1:
                self[sequence] = args[0]
            else:
                self[sequence] = args
        if sequence in self.sequence_bindings:
            for binding in self.sequence_bindings[sequence]:
                binding.func(*args, **kwargs)
        elif sequence.startswith("on_"):
            logger.debug(
                "Sequence %s not bound. Currently bound keys: %s.",
                sequence,
                self.sequence_bindings.keys(),
            )
        
    def closure(self, sequence, use_event = False, returns_break = True):
        """Returns a closure method method that can be passed to normal bind calls"""
        if use_event:
            def gen_event(event):
                self.after_idle(sequence, event)
                if returns_break:
                    return "break"
        else:
            def gen_event(*args, **kwargs):
                self.after_idle(sequence, *args, **kwargs)
                if returns_break:
                    return "break"
        return gen_event

    def get_or_default(self, key, default):
        if str(key) in self.map:
            return self.map[str(key)]
        else:
            return default


event_binder = EventBinder()
