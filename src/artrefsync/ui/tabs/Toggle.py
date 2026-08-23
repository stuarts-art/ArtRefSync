import logging
from itertools import cycle

import ttkbootstrap as ttk

logger = logging.getLogger(__name__)


class Toggle(ttk.Label):
    def __init__(self, root, options_map: dict, on_select=None, variable=None):
        self.cycle = cycle(options_map.items())
        text, label = next(self.cycle)
        self.variable = variable if variable else ttk.StringVar()
        self.variable.set(text)
        self.on_select = on_select
        super().__init__(root, text=label)
        self.bind("<Button-1>", self.on_click)

    def on_click(self, _):
        text, label = next(self.cycle)
        self.config(text=label)
        self.variable.set(text)
        if self.on_select:
            self.on_select(self.get())

    def get(self):
        return self.variable.get()
