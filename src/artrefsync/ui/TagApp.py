import logging
import os
import time
import tkinter as tk
from pathlib import Path

import ttkbootstrap as ttk
from tkinterdnd2 import TkinterDnD

from artrefsync.config import Config, set_config
from artrefsync.constants import APP, BINDING, ICON, TABLE
from artrefsync.ui.widgets.LoadingBar import LoadingBars
from artrefsync.ui.widgets.ModernTopBar import ModernTopBar
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.event_binder import event_binder

logger = logging.getLogger(__name__)


def main():
    app = App()
    app.start()


class App(ttk.Window):
    def __init__(self, project_path="."):
        """
        Parameters:

            config_path (str):
                The title that appears on the application titlebar.

            config_file_name (str):
                The name of the ttkbootstrap theme to apply to the
                application.
        """
        self.project_path = Path(project_path).resolve()
        self.config_path = self.project_path / "config"
        self._internal_path = self.project_path / "_internal"
        global resource_path_override
        resource_path_override = self._internal_path
        os.chdir(project_path)
        os.makedirs(self.config_path, exist_ok=True)
        os.makedirs(self._internal_path, exist_ok=True)

        config = Config(
            config_path=self.config_path,
            config_file_name="config",
            internal_override=self._internal_path,
        )
        set_config(config)
        theme = config[TABLE.APP][APP.THEME]
        theme = "bootstrap-dark" if not theme else theme
        super().__init__(
            themename=theme,
            size=(1080, 1080),
            hdpi=True,
            scaling=2,
            title="Art Ref Sync",
        )

        TkinterDnD._require(self)
        self.init_scaffolding()
        self.temp_loading_var.set(10)
        self.update_idletasks()
        self.temp_loading.start()
        self.after_idle(self.initialize_db)
        self.after(100, self.load_config)

    def initialize_db(self):
        from artrefsync.db.post_db import PostDb

        with PostDb():
            logger.info("DBs initialized")

    def load_config(self):
        self.focus_set()
        logger.info("Starting App")
        self.last_widget = ""

        self.temp_loading_var.set(20)
        self.update_idletasks()

        self.init_tabs()
        self.temp_loading_var.set(50)
        self.update_idletasks()

        self.init_views()
        self.temp_loading_var.set(70)
        self.update_idletasks()
        self.init_bindings()
        self.init_top_bar_vars()
        self.gallery.text.focus_set()
        self.after_idle(event_binder.event_generate, BINDING.ON_FILTER_UPDATE)

        logger.info("App Init Complete")

    def start(self):
        from artrefsync.stores.link_cache import link_cache
        from artrefsync.utils.TkThreadCaller import thread_caller

        thread_caller.root = self
        with thread_caller, link_cache:
            try:
                self.mainloop()
            except Exception:
                logger.exception("Exception Raised")

    def init_scaffolding(self):

        logger.info("Init Scaffolding")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bar = ModernTopBar(self, False)
        self.stime = time.time()

        self.bar.mid_mid.columnconfigure(0, weight=0)
        self.bar.mid_mid.columnconfigure(1, weight=4)
        self.bar.mid_mid.rowconfigure(0, weight=1)

        self.bar.mid_left.rowconfigure(0, weight=1)
        self.bar.mid_left.columnconfigure(0, weight=0, minsize=30)
        self.bar.mid_left.columnconfigure(1, weight=1)

        self.bar.mid_right.rowconfigure(0, weight=1)
        self.bar.mid_right.columnconfigure(0, weight=1, minsize=250)

        self.right = ttk.Frame(self.bar.mid_mid)
        self.right.grid(row=0, column=1, sticky=tk.NSEW)
        self.right.rowconfigure(0, weight=1)
        self.right.columnconfigure(0, weight=1)

        self.left_bar = ttk.Frame(self.bar.mid_left)
        self.left_bar.grid(row=0, column=0, sticky=tk.NSEW)

        self.left_artist_icon = RoundedIcon(
            self.left_bar, text=ICON.ARTISTS, size=30, pack_kwargs={"side": tk.TOP}
        )
        self.left_tag_icon = RoundedIcon(
            self.left_bar, text=ICON.TAG, size=30, pack_kwargs={"side": tk.TOP}
        )
        self.left_info_icon = RoundedIcon(
            self.left_bar, text=ICON.INFO, size=30, pack_kwargs={"side": tk.TOP}
        )
        self.left_config_icon = RoundedIcon(
            self.left_bar, text=ICON.SETTINGS, size=30, pack_kwargs={"side": tk.TOP}
        )

        self.left_tabs = ttk.Frame(self.bar.mid_left)
        self.left_tabs.grid(row=0, column=1, sticky=tk.NSEW)
        self.left_tabs.rowconfigure(0, weight=1)
        self.left_tabs.columnconfigure(0, weight=1)
        self.style.configure("NoTab.TNotebook.Tab", "")

        self.temp_loading_var = ttk.IntVar(value=0)
        self.temp_loading = ttk.Progressbar(
            self.right, variable=self.temp_loading_var, maximum=100, length=200
        )
        self.temp_loading.grid(row=0, column=0)
        self.loading_bar = LoadingBars(self.bar._bot)

    def init_tabs(self):
        from artrefsync.ui.tabs.ActiveTags import ActiveTagsTab
        from artrefsync.ui.tabs.ArtistTab import ArtistTab
        from artrefsync.ui.tabs.SortByTab import SortByTab
        from artrefsync.ui.tabs.TagTab import TagTab
        from artrefsync.ui.widgets.PostInfo import PostInfoTab

        logger.info("Initializing tabs")
        self.artist_tab = ArtistTab(self.left_tabs).grid(
            row=0, column=0, sticky=tk.NSEW
        )
        self.tag_tab = TagTab(self.left_tabs).grid(row=0, column=0, stick=tk.NSEW)
        self.post_info_tab = PostInfoTab(self.left_tabs).grid(
            row=0, column=0, stick=tk.NSEW
        )
        self.active_tab = ActiveTagsTab(self.bar.top_mid)
        self.sort_by_tab = SortByTab(self.bar.top_right)
        self.sort_by_tab.pack(side="right", padx=5)
        self.artist_tab.lift()

    def tab_toggle_closure(self, widget: ttk.Frame):
        def raise_toggle_widget(event: tk.Event):
            widget_name = widget.winfo_name()

            if not self.left_tabs.grid_info():
                self.left_tabs.grid(row=0, column=1, sticky=tk.NSEW)
                widget.lift()
                self.last_widget = widget_name
            elif self.last_widget != widget_name:
                self.last_widget = widget_name
                widget.lift()
            else:
                self.left_tabs.grid_forget()

        return raise_toggle_widget

    def toggle_top_bar(self, toggle_on=None):
        if toggle_on is None:
            top_status = self.bar._top.grid_info()
            toggle_on = not top_status

        if toggle_on and self.bar._top.grid_info():
            return
        if toggle_on and self.bar.mid_left.grid_info():
            return

        self.bar.toggle_topbar(toggle_on=toggle_on)
        self.bar.toggle_left_sidebar(toggle_on=toggle_on)
        self.update_idletasks()

    def init_top_bar_vars(self):
        self.top_right_text = ttk.StringVar(value="")
        event_binder.bind(
            BINDING.ON_SET_TOP_RIGHT_TEXT,
            lambda x: self.top_right_text.set(f"{x}"),
            self.bar,
        )
        ttk.Label(self.bar.top_mid, textvariable=self.top_right_text).pack(
            side=tk.RIGHT
        )

    def init_views(self):
        from artrefsync.ui.tabs.ConfigTab import ConfigTab
        from artrefsync.ui.tabs.ViewerTab import ViewerTab
        from artrefsync.ui.widgets.PhotoGallery import PhotoImageGallery

        logger.info("Init Views")
        self.gallery = PhotoImageGallery(self.right).grid(
            column=0, row=0, sticky=tk.NSEW
        )
        self.image_viewer = ViewerTab(self.right)
        self.config_tab = ConfigTab(self.right)

    def init_bindings(self):
        logger.info("Init Bindings")
        self.config_tab.clear_button.bind("<Button-1>", self.toggle_config)
        self.bind_all("<Control-Key-1>", self.focus_galery)
        self.bind_all("<Control-Key-4>", self.toggle_config)
        self.bind_all("<Control-comma>", self.toggle_config)
        self.artist_tab.entry.bind("<Shift-Tab>", self.focus_galery)
        self.tag_tab.entry.bind("<Shift-Tab>", self.focus_galery)
        self.top_widget = None
        self.config_tab.clear_button.bind("<Button-1>", self.toggle_config)
        self.left_tag_icon.bind("<Button-1>", self.tab_toggle_closure(self.tag_tab))
        self.left_artist_icon.bind(
            "<Button-1>", self.tab_toggle_closure(self.artist_tab)
        )
        self.left_info_icon.bind(
            "<Button-1>", self.tab_toggle_closure(self.post_info_tab)
        )
        self.left_config_icon.bind("<Button-1>", self.toggle_config)
        event_binder.bind(BINDING.ON_TOGGLE_UI, self.toggle_top_bar, self.bar)

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
            if self.left_tabs.grid_info():
                self.left_tabs.grid_forget()

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
