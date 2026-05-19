import fnmatch
import ttkbootstrap as ttk
import tkinter as tk

from artrefsync.constants import APP, BINDING, TABLE
from artrefsync.db.post_db import PostDb
from artrefsync.utils.EventManager import ebinder
from artrefsync.config import config
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class TagTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        logger.info("Init Tag Tab")
        super().__init__(root, *args, **kwargs)
        self.entry = ttk.Entry(self)
        self.tree = ttk.Treeview(self, columns=("Count"), show="tree", takefocus=True, *kwargs)
        self.curr_artist = ""
        self.artist_tag_count_map = {}
        self.artist_tags = []
        self.tree.config(selectmode=tk.NONE)
        self.entry.pack(side=tk.TOP, fill="x")
        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=80, stretch=0, anchor="e")
        self.entry.bind("<KeyRelease>", self.on_key_release)
        self.vowel_table = str.maketrans("aeiou", "*****")
        self.tree.config(selectmode=tk.BROWSE)
        ebinder.bind(BINDING.ON_ARTIST_SELECT, self.update_artist, self)
        self.after(100, self.on_key_release)
        config.subscribe_reload(self.on_key_release)
        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<Button-1>", self.query_by_tag)
        self.tree.bind("<Button-2>", self.on_middle_tag)
        self.tree.bind("<Key>", self.__keystroke)

    def __keystroke(self, event: tk.Event):
        keycode = event.keycode
        keysym = event.keysym
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        shift_pressed = (state & 0x1) != 0

        if keysym in ["Return", "grave"]:
            self.query_by_tag()
        elif keysym == 'w':
            self.tree.event_generate("<Up>")
        elif keysym == 'a':
            self.tree.event_generate("<Shift-Tab>")
        elif keysym == 's':
            self.tree.event_generate("<Down>")
        elif keysym == 'd':
            self.tree.event_generate("<Tab>")
        else:
            return ""
        return "break"

    def on_tree_focusin(self, e):
        self.tree.focus_get()
        if not self.tree.selection():
            children = self.tree.get_children()
            if children:
                child = children[0]
                self.tree.focus(child)
                self.tree.selection_set(child)


    def update_artist(self, artist, middle=False):
        if artist != self.curr_artist:
            self.curr_artist = artist
            if not artist:
                self.artist_tag_count_map = {}
            else:
                with PostDb() as post_db:
                    if artist in post_db.artist_tags:
                        self.artist_tag_count_map = post_db.artist_tags[artist]
                        self.artist_tags = [
                            str(k) for k in self.artist_tag_count_map.keys()
                        ]
                        self.artist_tags.sort(
                            key=lambda tag: self.artist_tag_count_map[tag], reverse=True
                        )
                    else:
                        self.artist_tag_count_map = {}

            self.entry.delete(0, tk.END)
            self.entry.insert(0, "")
            self.after(100, self.on_key_release)

    def is_artist(self, artist):
        if (
            artist in ebinder[BINDING.ARTIST_SET]
            or artist in ebinder[BINDING.BOARD_SET]
        ):
            return True
        else:
            return False

    def on_key_release(self, e=None):
        text = self.entry.get()
        logger.debug("On Key Release for text = %s", text)

        if self.artist_tag_count_map:
            filtered = fnmatch.filter(self.artist_tags, f"*{text}*")
            tags = [(tag, self.artist_tag_count_map[tag]) for tag in filtered]

        else:
            with PostDb() as post_db:
                tags = post_db.tag_posts.count_list(text, 10000)
        for item in self.tree.get_children():
            self.tree.delete(item)

        repl_text = "₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊"
        for i, (tag, count) in enumerate(tags):
            if not self.is_artist(tag):
                tag_text:str = tag
                if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
                    repl_split = "_".join([split[0] + repl_text[len(split):2*len(split)-2] + split[-1] for split in tag_text.split("_")])
                    tag_text = tag_text[0] + repl_split[1:-1] + tag_text[-1]
                self.tree.insert("", "end", iid=tag, text=tag_text, values=(count,))

    def query_by_tag(self, e=None):
        if self.tree.selection():
            tag = self.tree.selection()[0]
            if tag in ebinder[BINDING.ARTIST_SET]:
                ebinder.event_generate(BINDING.ON_ARTIST_SELECT, tag)
            else:
                ebinder.event_generate(BINDING.ON_TAG_SELECT, tag)
        else:
            children = self.tree.children
            if children:
                self.tree.selection_set(children[0])

    def on_middle_tag(self, e=None):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click recieved for %s", tag)
        ebinder.event_generate(BINDING.ON_TAG_MIDDLE, tag)
