import logging
import time
import tkinter as tk

import ttkbootstrap as ttk

# import sv_ttk
from tkinterdnd2 import TkinterDnD

from artrefsync.config import Config
from artrefsync.constants import BINDING
from artrefsync.stores.link_cache import LinkCache
from artrefsync.ui.tabs.ActiveTags import ActiveTagsTab
from artrefsync.ui.tabs.ArtistTab import ArtistTab
from artrefsync.ui.tabs.ConfigTab import ConfigTab
from artrefsync.ui.tabs.SortByTab import SortByTab
from artrefsync.ui.tabs.TagTab import TagTab
from artrefsync.ui.tabs.ViewerTab import ViewerTab
from artrefsync.ui.widgets.LoadingBar import LoadingBars
from artrefsync.ui.widgets.ModernTopBar import ModernTopBar
from artrefsync.ui.widgets.PhotoGallery import PhotoImageGallery
from artrefsync.ui.widgets.PostInfo import PostInfo
from artrefsync.utils.EventManager import ebinder
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger(__name__)


def main():
    app = App()
    app.mainloop()


class App(ttk.Window):
    def __init__(self, config_path="config", config_file_name="config"):
        """
        Parameters:

            config_path (str):
                The title that appears on the application titlebar.

            config_file_name (str):
                The name of the ttkbootstrap theme to apply to the
                application.
        """
        global config
        config = Config(config_path=config_path, config_file_name=config_file_name)
        self.load_config()

    def load_config(self):
        logger.setLevel(config.log_level)
        logger.info("Starting App")
        self.init_scaffolding()
        self.init_top_bar_vars()
        self.init_tabs()
        self.init_views()
        self.after_idle(ebinder.event_generate, BINDING.ON_FILTER_UPDATE)
        self.gallery.text.focus_set()
        self.init_bindings()
        logger.info("App Init Complete")

    def start(self):
        with LinkCache(), TkThreadCaller(self):
            try:
                self.mainloop()
            except Exception:
                logger.exception("Exception Raised")

    def init_scaffolding(self):
        logger.info("Init Scafolding")
        super().__init__(
            themename="darkly",
            size=(1080, 1080),
            hdpi=True,
            scaling=2,
            title="Art Ref Sync App",
        )
        TkinterDnD._require(self)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bar = ModernTopBar(self, False)
        self.stime = time.time()
        self.thread_caller = TkThreadCaller(self)

        self.bar.mid_mid.columnconfigure(0, weight=0)
        self.bar.mid_mid.columnconfigure(1, weight=4)
        self.bar.mid_mid.rowconfigure(0, weight=1)

        self.bar.mid_left.rowconfigure(0, weight=1)
        self.bar.mid_left.columnconfigure(0, weight=1, minsize=250)

        self.bar.mid_right.rowconfigure(0, weight=1)
        self.bar.mid_right.columnconfigure(0, weight=1, minsize=250)

        self.right = ttk.Frame(self.bar.mid_mid)
        self.right.grid(row=0, column=1, sticky=tk.NSEW)
        self.right.rowconfigure(0, weight=1)
        self.right.columnconfigure(0, weight=1)

        self.left_tabs = ttk.Frame(self.bar.mid_left)
        self.left_tabs.grid(row=0, column=0, sticky=tk.NSEW)
        self.left_tabs.rowconfigure(3, weight=1)
        self.left_tabs.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.left_tabs)
        self.notebook.grid(column=0, row=3, padx=5, sticky=tk.NSEW)

    def swap_to_notebook_entry(self, *e):
        tab = self.notebook.nametowidget(self.notebook.select())
        tab.entry.focus_set()
        return "break"

    def swap_to_notebook_tree(self, *e):
        tab = self.notebook.nametowidget(self.notebook.select())
        tab.tree.focus_set()
        return "break"

    def init_tabs(self):
        logger.info("Init tabs")
        self.artist_tab = ArtistTab(self.notebook)
        self.notebook.add(self.artist_tab, text="Artists")
        self.tag_tab = TagTab(self.notebook)
        self.notebook.add(self.tag_tab, text="Tags")
        self.tag_tab.grid_forget()
        self.active_tab = ActiveTagsTab(self.left_tabs)
        self.sort_by_tab = SortByTab(self.bar.top_right)
        self.sort_by_tab.pack(side="right", padx=5)
        self.post_info = PostInfo(self.bar.mid_right, self.thread_caller)
        self.loading_bar = LoadingBars(self.bar._bot)

    def init_top_bar_vars(self):
        self.top_artist_text = ttk.StringVar()
        self.top_artist_count_text = ttk.StringVar()
        self.top_post_text = ttk.StringVar()
        ebinder.bind(BINDING.ON_ARTIST_SELECT, self.on_artist_select, self.bar)
        ebinder.bind(
            BINDING.ON_POST_COUNT,
            lambda x: self.top_artist_count_text.set(f"({x})"),
            self.bar,
        )
        ttk.Label(self.bar.top_mid, textvariable=self.top_artist_text).pack(
            side=tk.LEFT
        )
        ttk.Label(self.bar.top_mid, textvariable=self.top_artist_count_text).pack(
            side=tk.LEFT
        )

    def on_artist_select(self, artist, *nargs):
        self.top_artist_text.set(artist)

    def init_views(self):
        logger.info("Init Views")
        self.config_tab = ConfigTab(self.right)
        self.image_viewer = ViewerTab(self.right)
        self.image_viewer.grid(column=0, row=0, sticky=tk.NSEW)
        self.image_viewer.grid_forget()
        self.gallery = PhotoImageGallery(self.right, self.thread_caller)
        self.gallery.grid(column=0, row=0, sticky=tk.NSEW)

    def init_bindings(self):
        logger.info("Init Bindings")
        self.bind(self.bar.menu_event_name, self.toggle_config)
        self.config_tab.clear_button.bind("<Button-1>", self.toggle_config)
        self.bind_all("<Control-Key-1>", lambda e: self.notebook.select(0))
        self.bind_all("<Control-Key-2>", lambda e: self.notebook.select(1))
        self.bind_all("<Control-Key-3>", self.toggle_config)
        self.bind_all("<Control-comma>", self.toggle_config)
        self.gallery.scrolled_text.text.bind("<Tab>", self.swap_to_notebook_entry)
        self.gallery.scrolled_text.text.bind("<Shift-Tab>", self.swap_to_notebook_tree)
        self.artist_tab.entry.bind("<Shift-Tab>", self.focus_galery)
        self.tag_tab.entry.bind("<Shift-Tab>", self.focus_galery)

    def focus_galery(self, e):
        self.gallery.scrolled_text.text.focus_set()
        return "break"

    def toggle_config(self, event=None):
        if self.config_tab.grid_info():
            self.gallery.grid(column=0, row=0, sticky=tk.NSEW)
            self.config_tab.grid_forget()
        else:
            self.config_tab.grid(column=0, row=0, sticky=tk.NSEW)
            self.gallery.grid_forget()

    def toggle_side_bar(self, event):
        logger.info("Toggling Sidebar")
        left_info = self.bar.mid_left.grid_info()
        logger.info("Toggling side bar. Pack Info = %s", str(left_info))

        if len(left_info) != 0:
            logger.info("Forgetting = %s", str(left_info))
            self.bar.mid_right.grid_forget()
            self.bar.mid_left.grid_forget()
        else:
            logger.info("Reattaching = %s", str(left_info))
            self.right.grid(column=2, row=2, sticky="nse")
            self.bar.mid_left.grid(row=2, column=0, sticky="nws")


if __name__ == "__main__":
    main()
