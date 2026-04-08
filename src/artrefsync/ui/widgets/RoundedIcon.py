import logging
import tkinter as tk
from tkinter.font import nametofont

import ttkbootstrap as ttk
from PIL import ImageTk

from artrefsync.config import config
from artrefsync.utils.image_utils import ImageUtils

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class RoundedIcon(ttk.Label):
    font = None

    @staticmethod
    def text_width(text):
        if not RoundedIcon.font:
            RoundedIcon.font = nametofont("TkDefaultFont")
        return RoundedIcon.font.measure(text)

    @staticmethod
    def from_text(root, text, normal_color="#FFFFFF00", hover_color="#595253"):
        if not RoundedIcon.font:
            RoundedIcon.font = nametofont("TkDefaultFont")
        text_width = RoundedIcon.font.measure(text)
        icon_width = ((text_width) // 20 + 1) * 20
        return RoundedIcon(
            root,
            text,
            size=(icon_width, 22),
            normal_color=normal_color,
            hover_color=hover_color,
        )

    def update_text(self, text):
        width = RoundedIcon.font.measure(text)
        self.width = (width // 20 + 1) * 20
        self.set_image()
        self.config(image=self.image, text=text)

    def __init__(
        self,
        root,
        text = "",
        normal_color="#FFFFFF00",
        hover_color="#595253",
        size=40,
        radius=5,
        style=None,
        text_variable=None,
        command = None,
        **kwargs,
    ):
        logger.info("Round Icon init for text \"%s\"", text)
        if isinstance(size, int):
            self.width = size
            self.height = size
        else:
            self.width = size[0]
            self.height = size[1]
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.radius = radius
        self.size = size

        self.text = text
        self.normal_icon = ImageTk.PhotoImage(
            ImageUtils.get_round_colored_rect(
                self.width, self.height, radius, normal_color
            )
        )
        if hover_color:
            self.hover_icon = ImageTk.PhotoImage(
                ImageUtils.get_round_colored_rect(
                    self.width, self.height, radius, hover_color
                )
            )
            self.image = (self.normal_icon, "hover", self.hover_icon)
        else:
            self.image = self.normal_icon

        self.set_image()
        if not style:
            style = "TLabel"
            if isinstance(root, ttk.Text):
                style = "primary.TLabel"

        super().__init__(
            root, image=self.image, text=text, compound=tk.CENTER, style=style, textvariable= text_variable, **kwargs
        )

        if command:
            self.bind("<Button-1>", command)

    def set_image(self):
        self.normal_icon = ImageTk.PhotoImage(
            ImageUtils.get_round_colored_rect(
                self.width, self.height, self.radius, self.normal_color
            )
        )
        if self.hover_color:
            self.hover_icon = ImageTk.PhotoImage(
                ImageUtils.get_round_colored_rect(
                    self.width, self.height, self.radius, self.hover_color
                )
            )
            self.image = (self.normal_icon, "hover", self.hover_icon)
        else:
            self.image = self.normal_icon