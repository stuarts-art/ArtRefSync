import logging
import tkinter as tk

import ttkbootstrap as ttk

from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.image_utils import ImageUtils

logger = logging.getLogger(__name__)


class RoundedDropDown(ttk.Label):
    def __init__(
        self,
        root,
        options,
        on_select,
        variable=None,
        use_image=True,
        radius=10,
        fill=None,
        **kwargs,
    ):

        self.option_map = {}
        for option in options:
            if isinstance(option, tuple):
                k, v = option
            else:
                k = option
                v = option
            self.option_map[k] = v

        logger.info("Init Rounded DropDown.")
        self.colors = ttk.Style().colors
        self.menu = ttk.Menu(root)
        self.variable = variable if variable else ttk.StringVar()
        self.image = None
        fill = fill if fill else self.colors.bg
        if use_image:
            width = RoundedIcon.text_width(max(self.option_map.keys(), key=len))
            self.image = ImageUtils.get_round_colored_rect(
                width + 10, 30, radius=radius, as_photoimage=True, fill=fill
            )
        super().__init__(
            root, textvariable=self.variable, compound="center", image=self.image
        )
        for key, option in self.option_map.items():
            self.menu.add_radiobutton(
                label=f" {key} ",
                value=option,
                variable=self.variable,
                command=on_select,
            )
        self.bind("<Button-1>", self.on_label_click)

    def get(self):
        return self.option_map.get(self.variable.get())

    def on_label_click(self, e: tk.Event):
        self.menu.post(
            e.widget.winfo_rootx() + 5,
            e.widget.winfo_rooty() + e.widget.winfo_height() + 5,
        )
