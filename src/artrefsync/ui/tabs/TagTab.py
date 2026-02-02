import fnmatch
import ttkbootstrap as ttk
import tkinter as tk

from artrefsync.constants import BINDING
from artrefsync.db.post_db import PostDb
from artrefsync.utils.EventManager import ebinder
from artrefsync.config import config
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class TagTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, *args, **kwargs)
        self.entry = ttk.Entry(self)
        self.tree = ttk.Treeview(self, columns=("Count"), show="tree", *kwargs)
        self.curr_artist = ""
        self.artist_tag_count_map = {}
        self.artist_tags = []
        self.tree.config(selectmode=tk.NONE)
        self.entry.pack(side=tk.TOP, fill="x")
        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        # self.tree.pack(side=tk.BOTTOM, fill="x")
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=80, stretch=0, anchor="e")
        self.entry.bind("<KeyRelease>", self.on_key_release)
        self.tree.bind("<<TreeviewSelect>>", self.query_by_tag)
        self.tree.bind("<Button-2>", self.on_middle_tag)
        self.tree.config(selectmode=tk.BROWSE)
        ebinder.bind(BINDING.ON_ARTIST_SELECT, self.update_artist, self)
        self.after(100, self.on_key_release)
        config.subscribe_reload(self.on_key_release)

    # def get_artist(self):
    #     if BINDING.SELECTED_ARTIST in ebinder:
    #         return ebinder[BINDING.SELECTED_ARTIST]
    #     return None
    
    def update_artist(self, artist, middle=False):
        # artist = self.get_artist()
        if artist != self.curr_artist:
            self.curr_artist = artist
            if not artist:
                self.artist_tag_count_map = {}
            else:
                with PostDb() as post_db:
                    self.artist_tag_count_map = post_db.artist_tags[artist]
                self.artist_tags = [str(k) for k in self.artist_tag_count_map.keys()]
                self.artist_tags.sort(key=lambda tag: self.artist_tag_count_map[tag], reverse=True)

                # keylist = [str(k) for k in self.artist_tag_count_map.keys()]
                # filtered = fnmatch.filter(keylist, f"*{text}*")
                # tags:list = [item for item in self.artist_tag_count_map.items() if item[0] in filtered]

            self.entry.delete(0, tk.END)
            self.entry.insert(0, "")
            self.after(100, self.on_key_release)



    def is_artist(self, artist):
        if (
            artist in ebinder[BINDING.ARTIST_SET] or
            artist in ebinder[BINDING.BOARD_SET]
            ):
            return True
        else:
            return False

    def on_key_release(self, e=None):
        text = self.entry.get()
        logger.info("On Key Release for text = %s", text)

        if self.artist_tag_count_map:
            filtered = fnmatch.filter(self.artist_tags, f"*{text}*")
            # keylist = [str(k) for k in self.artist_tag_count_map.keys()]
            # tags:list = [item for item in self.artist_tag_count_map.items() if item[0] in filtered]
            tags = [(tag, self.artist_tag_count_map[tag]) for tag in filtered]
            # tags.sort(reverse=True, key=lambda x: x[1])

        else:
            with PostDb() as post_db:
                tags = post_db.tag_posts.count_list(text, 10000)
                # if self.artist_tags:
                #     tags = [tag for tag in tags if tag in self.artist_tags]
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, (tag, count) in enumerate(tags):
            if not self.is_artist(tag):
                self.tree.insert("", "end", iid=tag, text=tag, values=(count,))

    def query_by_tag(self, e=None):
        # self.filter_set = set()
        if self.tree.selection():
            tag = self.tree.selection()[0]
            if tag in ebinder[BINDING.ARTIST_SET]:
                ebinder.event_generate(BINDING.ON_ARTIST_SELECT, tag)
            else:
                ebinder.event_generate(BINDING.ON_TAG_SELECT, tag)

    def on_middle_tag(self, e=None):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click recieved for %s", tag)
        ebinder.event_generate(BINDING.ON_TAG_MIDDLE, tag)
