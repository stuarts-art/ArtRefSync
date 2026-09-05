import logging
import tkinter as tk

import ttkbootstrap as ttk

from artrefsync.config import get_config
from artrefsync.constants import BINDING
from artrefsync.ui.tabs.RoundedDropDown import RoundedDropDown
from artrefsync.ui.tabs.Toggle import Toggle
from artrefsync.utils.event_binder import event_binder

config = get_config()
logger = logging.getLogger(__name__)


class SortByTab(ttk.Frame):
    def __init__(self, root):
        logger.info("Initializing Sort By Widgets.")
        super().__init__(root)
        self.sort_var = ttk.StringVar(value="id")
        self.sort_dir_var = ttk.StringVar(value="DESC")
        Toggle(
            self, {"DESC": "▾", "ASC": "▴"}, self.update_posts, self.sort_dir_var
        ).pack(side=tk.RIGHT)
        RoundedDropDown(
            self,
            [
                "id",
                "artist_name",
                "board",
                "score",
                "update_timestamp",
                "create_timestamp",
            ],
            self.update_posts,
            self.sort_var,
            radius=10,
            use_image=False,
        ).pack(side=tk.RIGHT)
        self.update_dict()

    def update_dict(self):
        event_binder.map[BINDING.SORT_BY] = self.sort_var.get()
        event_binder.map[BINDING.SORT_DIR] = self.sort_dir_var.get()

    def update_posts(self, *args, **kwargs):
        self.update_dict()
        event_binder.after_idle(BINDING.ON_SORT_BY_UPDATE)
