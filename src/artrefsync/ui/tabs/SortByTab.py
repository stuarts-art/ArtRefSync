import os
import threading
import time
import tkinter as tk
from sortedcontainers import SortedSet
import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledText
from threading import Event

from tkinterdnd2 import COPY, DND_FILES
from PIL import ImageTk

from artrefsync.ui.widgets.ModernTopBar import RoundedIcon
from artrefsync.boards.board_handler import PostFile
from artrefsync.db.post_db import PostDb
from artrefsync.utils.TkThreadCaller import TkThreadCaller
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.config import config

from artrefsync.constants import BINDING

from artrefsync.utils.EventManager import ebinder
from itertools import cycle

import logging

logger = logging.getLogger()
logger.setLevel(config.log_level)

thread_caller: TkThreadCaller = None


class RoundedDropDown(ttk.Label):
    def __init__(
        self,
        root,
        options,
        on_select,
        variable=None,
        use_image=True,
        radius=10,
        **kwargs,
    ):
        logger.info("Init Rounded DropDown.")
        self.colors = ttk.Style().colors
        self.menu = ttk.Menu(root)
        self.variable = variable if variable else ttk.StringVar
        self.image = None
        if use_image:
            width = RoundedIcon.text_width(max(options, key=len))
            self.image = ImageUtils.get_round_colored_rect(
                width + 10, 30, radius=radius, as_photoimage=True
            )
        super().__init__(
            root, textvariable=self.variable, compound="center", image=self.image
        )
        for option in options:
            self.menu.add_radiobutton(
                label=f" {option} ",
                value=option,
                variable=self.variable,
                command=on_select,
            )
        self.bind("<Button-1>", self.on_label_click)

    def get(self):
        return self.variable.get()

    def on_label_click(self, e: tk.Event):
        self.menu.post(
            e.widget.winfo_rootx() + 5,
            e.widget.winfo_rooty() + e.widget.winfo_height() + 5,
        )


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


class SortByTab(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.sort_var = ttk.StringVar(value="id")
        self.sort_dir_var = ttk.StringVar(value="DESC")
        Toggle(
            self, {"DESC": "▾", "ASC": "▴"}, self.update_posts, self.sort_dir_var
        ).pack(side=tk.RIGHT)
        RoundedDropDown(
            self,
            ["id", "board_update_str", "artist_name", "board", "score"],
            self.update_posts,
            self.sort_var,
            radius=10,
            use_image=False,
        ).pack(side=tk.RIGHT)
        self.update_dict()

    def update_dict(self):
        ebinder.map[BINDING.SORT_BY] = self.sort_var.get()
        ebinder.map[BINDING.SORT_DIR] = self.sort_dir_var.get()

    def update_posts(self, *args, **kwargs):
        self.update_dict()
        ebinder.event_generate(BINDING.ON_SORT_BY_UPDATE)
