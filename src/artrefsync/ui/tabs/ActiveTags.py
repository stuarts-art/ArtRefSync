import logging
import tkinter as tk
from tkinter.font import nametofont

import ttkbootstrap as ttk

from artrefsync.constants import BINDING
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.EventManager import e_binder

logger = logging.getLogger(__name__)


class ActiveTagsTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        logger.info("Init Active Tags Tab.")
        super().__init__(root, *args, **kwargs)
        self.font = nametofont("TkDefaultFont")
        self.artist = None
        self.tags = []
        self.last_filter = None
        self.stored_grid_info = None
        self.active_tags: dict[str, ttk.Frame] = {}
        self.style = ttk.Style()
        self.colors = self.style.colors

        self.place_self()

        self.tags_frame = ttk.Frame(self).grid(row=0, column=1, sticky=tk.W)
        self.artist_button = RoundedIcon.from_text(
            self,
            text="",
            normal_color=self.colors.secondary,
            command=self.remove_tag_cmd,
        )
        self.clear_button = RoundedIcon.from_text(self, text="✕")
        ttk.Frame(self.tags_frame).pack(side=tk.LEFT)
        self.add_bindings()

    def add_bindings(self):
        self.clear_button.bind("<Button-1>", self.clear_active)
        e_binder.bind(BINDING.ON_ARTIST_CLEAR, self.clear_active, self)
        e_binder.bind(BINDING.ON_ARTIST_SELECT, self.on_artist, self)
        e_binder.bind(BINDING.ON_TAG_SELECT, self.on_tag, self)

    def remove_tag_cmd(self, e):
        widget = e.widget
        if self.remove_tag(widget.text):
            self.columnconfigure(1)
            self.update_filter()

    def grid_artist_button(self, forget=False):
        try:
            if forget:
                self.artist_button.grid_forget()
            else:
                self.artist_button.grid(row=0, column=0, sticky=tk.W)
        except tk.TclError:
            pass

    def grid_clear_frame(self, forget=False):
        try:
            if forget:
                self.clear_button.grid_forget()
            else:
                self.clear_button.grid(row=0, column=2, sticky=tk.W)
        except tk.TclError:
            pass

    def place_self(self):
        self.pack(side=tk.LEFT, expand=tk.TRUE, fill=tk.X)

    def is_artist(self, artist):
        return artist in e_binder[BINDING.ARTIST_SET] | e_binder[BINDING.BOARD_SET]

    def on_artist(self, artist, middle_click=False):
        logger.debug("Artist Recieved: %s, Middle Clicked: %d", artist, middle_click)

        if not self.is_artist(artist):
            return self.on_tag(artist, middle_clicked=middle_click)

        if artist in self.active_tags:
            logger.info("Artist %s already selected.", artist)
            return

        self.add_artist(artist)
        self.update_idletasks()
        self.update_filter()

    def on_tag(self, tag, middle_clicked=False):
        logger.info("Tag Recieved: %s. Middle click = %s", tag, middle_clicked)
        if tag in self.active_tags:
            logger.info("Tag %s already selected")
            return
        elif tag == self.artist:
            logger.info("Artist %s already selected")
            return
        elif self.is_artist(tag):
            return self.on_artist(tag)

        if not middle_clicked:
            if len(self.active_tags) == 1:
                t, widget = self.active_tags.popitem()
                widget.update_text(tag)
                self.active_tags[tag] = widget
                self.update_filter()
                self.update_idletasks()
                return
            else:
                while self.active_tags:
                    _, widget = self.active_tags.popitem()
                    widget.destroy()

        self.add_tag(tag)
        self.update_filter()
        self.update_idletasks()

        if middle_clicked:
            if tag in self.active_tags:
                return
            if self.is_artist(tag):
                return self.on_artist(tag)
            self.add_tag(tag)
            self.update_filter()
            return

        if self.active_tags:
            tags = [tag for tag in self.active_tags]

            for curr_tag in tags:
                if not self.is_artist(curr_tag):
                    removed = self.remove_tag(curr_tag)
                    if not removed:
                        logger.warning("Failed to remove %s from active tags", curr_tag)
        self.add_tag(tag)
        self.update_filter()

    def on_remove_tag(self, event=None):
        if event.widget and event.widget.text:
            tag = event.widget.text
            if self.remove_tag(tag):
                self.update_filter()
            if self.is_artist(tag):
                e_binder.event_generate(BINDING.ON_ARTIST_SELECT, None, False)
        if not self.active_tags:
            self.forget_self()
            self.clear_button.pack_forget()

    def remove_tag(self, tag) -> bool:
        removed = False
        if tag == self.artist:
            removed = True
            self.artist = None
            self.grid_artist_button(forget=True)
            self.artist_button.update_text("")
        elif tag in self.active_tags:
            removed = True
            widget = self.active_tags.pop(tag)
            widget.pack_forget()
            widget.destroy()
        if not self.active_tags:
            forget = not self.artist
            self.grid_clear_frame(forget=forget)

        self.update_idletasks()
        return removed

    def add_artist(self, artist=""):
        if artist == self.artist:
            logger.info("Artist %s already selected", artist)
            return False

        if not artist and self.artist:
            self.artist = ""
            self.artist_button.update_text("")
            self.grid_artist_button(forget=True)
            if not self.active_tags:
                self.grid_clear_frame(forget=True)
            return False
        else:
            self.artist = artist
            self.artist_button.update_text(artist)
            self.grid_artist_button(forget=False)
            self.grid_clear_frame(forget=False)

    def add_tag(self, tag="", color=None):
        if not tag or tag in self.active_tags:
            return
        if not color:
            color = self.colors.secondary
        if self.is_artist(tag):
            return self.add_artist(tag)

        tag_icon = RoundedIcon.from_text(
            self.tags_frame, tag, color, command=self.remove_tag_cmd
        )
        tag_icon.pack(side=tk.LEFT)
        self.active_tags[tag] = tag_icon

        self.grid_clear_frame(forget=False)

    def clear_active(self, event=None, update=True):
        while self.active_tags:
            _, widget = self.active_tags.popitem()
            widget.destroy()
        self.artist = ""
        self.artist_button.update_text("")
        self.grid_clear_frame(forget=True)
        self.grid_artist_button(forget=True)
        self.update_filter()

    def update_filter(self):
        tags = [tag for tag in list(self.active_tags.keys()) + [self.artist] if tag]
        if tags == self.last_filter:
            return
        self.update_idletasks()
        logger.info("Updating filter to be: %s", tags)
        self.last_filter = tags
        e_binder.event_generate(BINDING.ON_FILTER_UPDATE, tags)

    def forget_self(self):
        logger.info("Forgetting Active Tags from Grid")
        self.grid_forget()
