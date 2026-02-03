# import pywinstyles
import ttkbootstrap as ttk
import tkinter as tk
import time

# import sv_ttk
from PIL import Image, ImageTk
import logging
from artrefsync.config import config
from artrefsync.ui.tabs.ActiveTags import ActiveTagsTab
from artrefsync.ui.tabs.ConfigTab import ConfigTab
from artrefsync.ui.widgets.LoadingBar import LoadingBars
from artrefsync.ui.tabs.ViewerTab import ViewerTab
from artrefsync.ui.tabs.TagTab import TagTab
from artrefsync.utils.TkThreadCaller import TkThreadCaller

from artrefsync.ui.tabs.ArtistTab import ArtistTab
from artrefsync.ui.widgets.PostInfo import PostInfo
from artrefsync.ui.widgets.ModernTopBar import ModernTopBar, RoundedIcon
from artrefsync.ui.widgets.PhotoGallery import PhotoImageGallery
from tkinterdnd2 import TkinterDnD

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    app = ImagViewerApp()
    app.mainloop()


class ImagViewerApp(ttk.Window):
    def __init__(self):
        logger.info("Starting App")
        self.init_scaffolding()
        self.init_tabs()
        self.init_views()
        self.init_bindings()

    def init_scaffolding(self):
        logger.info("Init Scafolding")
        super().__init__(themename="darkly", size=(1080, 1080), hdpi=True, scaling=2, title="Art Ref Sync App")
        TkinterDnD._require(self)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bar = ModernTopBar(self, False)
        self.stime = time.time()
        self.thread_caller = TkThreadCaller(self)

        self.bar.mid.columnconfigure(0, weight=0)
        self.bar.mid.columnconfigure(1, weight=4)
        self.bar.mid.rowconfigure(0, weight=1)

        self.bar.left.rowconfigure(0, weight=1)
        self.bar.left.columnconfigure(0, weight=1, minsize=250)
        self.bar.right.rowconfigure(0, weight=1)
        self.bar.right.columnconfigure(0, weight=1, minsize=250)
        self.left_tabs = ttk.Frame(self.bar.left)
        self.right = ttk.Frame(self.bar.mid)

        self.left_tabs.grid(row=0, column=0, sticky=tk.NSEW)
        self.right.grid(row=0, column=1, sticky=tk.NSEW)
        self.right.rowconfigure(0, weight=1)
        self.right.columnconfigure(0, weight=1)

        self.left_tabs.rowconfigure(3, weight=1)
        self.left_tabs.columnconfigure(0, weight=1)

        self.button_frame = ttk.Frame(self.left_tabs)
        self.button_frame.grid(column=0, row=1, padx=5)

        self.artists_button = RoundedIcon(
            self.button_frame, text="Artists", size=(100, 30)
        )
        self.artists_button.grid(column=0, row=0, sticky=tk.EW, padx=5)
        self.tags_button = RoundedIcon(self.button_frame, text="Tags", size=(100, 30))
        self.tags_button.grid(column=1, row=0, sticky=tk.EW, padx=5)

    def init_tabs(self):
        logger.info("Init tabs")

        self.artist_tab = ArtistTab(self.left_tabs)
        self.artist_tab.grid(column=0, row=3, sticky=tk.NSEW)

        self.tag_tab = TagTab(self.left_tabs)
        self.tag_tab.grid(column=0, row=3, sticky=tk.NSEW)
        self.tag_tab.grid_forget()

        self.active_tab = ActiveTagsTab(self.left_tabs)

        self.post_info = PostInfo(self.bar.right, self.thread_caller)
        self.loading_bar = LoadingBars(self.bar.bot)

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

        self.artists_button.bind("<Button-1>", self.toggle_artists)
        self.tags_button.bind("<Button-1>", self.toggle_tags)

    def taskedGetImage(self, file_name, size):
        image = Image.open(file_name)
        image.thumbnail(size)
        return ImageTk.PhotoImage(image)

    def setImage(self, photoimage):
        self.image_label.config(image=photoimage)

    def toggle_config(self, event=None):
        if self.config_tab.grid_info():
            self.gallery.grid(column=0, row=0, sticky=tk.NSEW)
            self.config_tab.grid_forget()
        else:
            self.config_tab.grid(column=0, row=0, sticky=tk.NSEW)
            self.gallery.grid_forget()

    def toggle_artists(self, event=None):
        logger.info("Toggling Artist")
        if len(self.artist_tab.grid_info()) == 0:
            self.artist_tab.grid(column=0, row=3, sticky=tk.NSEW)
            self.artists_button.configure(bootstyle="secondary-inverse")
            self.tags_button.configure(bootstyle="normal")
            self.tag_tab.grid_forget()

    def toggle_tags(self, event=None):
        logger.info("Toggling Tags")
        if len(self.tag_tab.grid_info()) == 0:
            self.artists_button.configure(bootstyle="normal")
            self.tags_button.configure(bootstyle="secondary-inverse")
            self.tag_tab.grid(column=0, row=3, sticky=tk.NSEW)
            self.artist_tab.grid_forget()

    def toggle_side_bar(self, event):
        logger.info("Toggling Sidebar")
        left_info = self.bar.left.grid_info()
        logger.info("Toggling side bar. Pack Info = %s", str(left_info))

        if len(left_info) != 0:
            logger.info("Forgetting = %s", str(left_info))
            self.bar.right.grid_forget()
            self.bar.left.grid_forget()
        else:
            logger.info("Reattaching = %s", str(left_info))
            self.right.grid(column=2, row=2, sticky="nse")
            self.bar.left.grid(row=2, column=0, sticky="nws")

if __name__ == "__main__":
    main()
