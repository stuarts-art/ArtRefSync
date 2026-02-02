from tkinter.font import nametofont
import ttkbootstrap as ttk
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import logging
from artrefsync.config import config
from artrefsync.constants import BINDING, BOARD
from artrefsync.ui.widgets.ModernTopBar import RoundedIcon
from artrefsync.utils.EventManager import ebinder

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ActiveTagsTab(ttk.Frame):
    """
    ### Structure:
    ```
    ActiveTagsTab:
        - button_frame:
            - active_button: Minimizes the tags frame
            - clear_button: Clears out tags
        - tags_frame:
            - tag1
            - tag...
    ```
    """

    def __init__(self, root, *args, **kwargs):
        super().__init__(root, *args, **kwargs)
        self.font = nametofont("TkDefaultFont")
        self.artist = None
        self.last_filter = None
        self.stored_grid_info = None
        self.active_tags: dict[str,ttk.Frame] = {}
        self.style = ttk.Style()
        self.colors = self.style.colors

        self.tabs_frame = ttk.Frame(self, cursor="star")
        self.tabs_frame.pack(side = tk.TOP, fill="both", expand=True)
        self.clear_button = RoundedIcon(self, text="✕", size=(25, 25))
        self.clear_button.place(relx=1.0, rely= 0.0, anchor=tk.NE)
        self.sep = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.sep.pack(side=tk.BOTTOM, fill=tk.X, pady=15)

        self.add_bindings()


    def is_artist(self, artist):
        if (
            artist in ebinder[BINDING.ARTIST_SET] or
            artist in ebinder[BINDING.BOARD_SET]
            ):
            return True
        else:
            return False

    def add_bindings(self):
        self.clear_button.bind("<Button-1>", self.clear_active)
        ebinder.bind(BINDING.ON_ARTIST_SELECT, self.on_artist, self)
        ebinder.bind(BINDING.ON_TAG_SELECT, self.on_tag, self)
        ebinder.bind(BINDING.ON_TAG_MIDDLE, self.on_tag_middle, self)

    def on_artist(self, artist, middle_click = False):
        logger.info("Artist Recieved: %s, Middle Clicked: %d", artist, middle_click)
        if not artist:
            if self.artist:
                self.artist = None
                self.remove_tag(self.artist)
                return

        if artist in self.active_tags:
            return
        if not self.is_artist(artist):
            return self.on_tag_middle(artist)

        if not middle_click and self.active_tags:
            self.clear_active()

        if self.artist:
            self.remove_tag(self.artist)
        
        self.add_artist(artist)
        self.update_filter()

    def add_artist(self, artist):
        self.artist = artist
        self.add_tag(self.artist, self.colors.primary)
        ebinder[BINDING.SELECTED_ARTIST] = self.artist

    def on_tag(self, tag):
        # Replace any non-artist tag.
        logger.info("Tag Recieved: %s", tag)
        if tag in self.active_tags:
            return
        if self.is_artist(tag):
            return self.on_artist(tag)
        if self.active_tags:

            tags = [tag for tag in self.active_tags]
            
            for curr_tag in tags:
                # curr_tag = str(curr_tag)
                if not self.is_artist(curr_tag):
                    removed = self.remove_tag(curr_tag)
                    if not removed:
                        logger.warning("Failed to remove %s from active tags", curr_tag)
        self.add_tag(tag)
        self.update_filter()

    def on_tag_middle(self, tag):
        # Add to tags
        logger.info("Tag Recieved: %s", tag)
        if tag in self.active_tags:
            return
        if self.is_artist(tag):
            return self.on_artist(tag)
        self.add_tag(tag)
        self.update_filter()

    def on_remove_tag(self, event=None):
        if event.widget and event.widget.text:
            tag = event.widget.text
            if self.remove_tag(tag):
                self.update_filter()
            if self.is_artist(tag):
                ebinder.event_generate(BINDING.ON_ARTIST_SELECT, None, False)
        if not self.active_tags:
            self.forget_self()
    
    def remove_tag(self, tag) -> bool:
        if tag not in self.active_tags:
            return False
        widget = self.active_tags.pop(tag)
        widget.destroy()
        return True


    def add_tag(self, tag, color = None):
        if not color:
            color = self.colors.secondary
            
        # if not self.stored_grid_info:
        #     logger.info("Setting  GRID INFO %s", self.grid_info())
        #     self.stored_grid_info = self.grid_info()
        logger.info("ADDING TAG %s", tag)
        if tag in self.active_tags:
            logger.info(
                'Tag: "%s" already in active tags. Active Tags: %s',
                tag,
                self.active_tags,
            )
            return
        if not self.grid_info():
            self.place_self()
        width = self.font.measure(tag)
        # tag_icon = RoundedIcon(self.tabs_frame, tag, size=(width + 10, 22))
        tag_icon = RoundedIcon(self.tabs_frame, tag, size=(width + 10, 22), normal_color=color)
        tag_icon.pack(side=tk.TOP, anchor=tk.NW)
        self.active_tags[tag] = tag_icon
        tag_icon.bind("<Double-Button-1>", self.on_remove_tag)

    def clear_active(self, event=None):
        while self.active_tags and (item := self.active_tags.popitem()):
            logger.info("Removing %s from active tags", item[0])
            if self.is_artist(item[0]):
                self.artist = None
            item[1].destroy()
        if event != None:  # If called by normal bind interface
            self.update_filter()
            self.forget_self()

    def update_filter(self):
        logger.info("Updating filter to be: %s")
        tags = list(self.active_tags.keys())
        if tags == self.last_filter:
            return
        self.last_filter = tags
        ebinder.event_generate(BINDING.ON_FILTER_UPDATE, tags)

    def forget_self(self):
        logger.info("Forgetting Active Tags from Grid")
        self.grid_forget()

    def place_self(self):
        # logger.info("Placing Active Tags into Grid with grid info: %s", self.stored_grid_info)
        self.grid(column=0, row=0, sticky=tk.NSEW)
        # self.grid(**self.stored_grid_info)