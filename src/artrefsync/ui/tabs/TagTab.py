import logging
import tkinter as tk

import ttkbootstrap as ttk
from dataclassdb import QueryBuilder

from artrefsync.config import get_config
from artrefsync.constants import APP, BINDING, TABLE
from artrefsync.db.post_db import PostDb
from artrefsync.db.TagType import TagType
from artrefsync.utils.EventManager import e_binder
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)

class TagTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        self.root = root
        logger.info("Init Tag Tab")
        super().__init__(root, *args, **kwargs)

        self.curr_artist = ""
        self.artist_tag_count_map = {}
        self.artist_tags = []
        self.tag_type_var = ttk.StringVar()

        self.ui_frame = ttk.Frame(self)
        self.entry = ttk.Entry(self.ui_frame)
        self.tag_type_button = ttk.Menubutton(
            self.ui_frame, image=None, compound="left"
        )
        self.tree = ttk.Treeview(
            self, columns=("Count"), show="tree", takefocus=True, *kwargs
        )

        self.tag_type_menu = ttk.Menu(self.tag_type_button)
        self.tag_type_button["menu"] = self.tag_type_menu

        self.ui_frame.pack(side=tk.TOP, fill="x")
        self.entry.pack(side="left", fill="x")
        self.tag_type_button.pack(side="left")

        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=80, stretch=0, anchor="e")
        self.type_tags = set()

        with PostDb() as post_db:
            query = (
                QueryBuilder(post_db.connection).SELECT.DISTINCT("type").FROM(TagType)
            )
            rows = query.execute(as_dict=False)
        self.tag_types = [""] + [row[0] for row in rows]

        for tag in self.tag_types:
            label = str(tag)
            self.tag_type_menu.add_radiobutton(
                label=label,
                value=label,
                variable=self.tag_type_var,
                compound="left",
                command=self.on_board_menu_select,
            )

        self.after(100, self.on_key_release)
        config.subscribe_reload(self.on_key_release)

        self.init_bindings()

    def on_board_menu_select(self):
        selected_board = self.tag_type_var.get()
        logger.info('Selected "%s"', selected_board)

    def init_bindings(self):
        e_binder.bind(BINDING.ON_ARTIST_SELECT, self.update_artist, self)
        self.entry.bind("<KeyRelease>", self.on_key_release)
        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<Button-1>", self.query_by_tag)
        self.tree.bind("<Button-2>", self.on_middle_tag)
        self.tree.bind("<Key>", self.__keystroke)

        self.tag_type_var.trace_add("write", self.__on_tag_type_update)

    def __on_tag_type_update(self, *args):
        self.on_key_release()

    def __keystroke(self, event: tk.Event):
        keycode = event.keycode  # noqa: F841
        keysym = event.keysym
        state = event.state
        ctrl_pressed = (state & 0x4) != 0  # noqa: F841
        shift_pressed = (state & 0x1) != 0  # noqa: F841

        if keysym in ["Return", "grave"]:
            self.query_by_tag(event)
        elif keysym == "w":
            self.tree.event_generate("<Up>")
        elif keysym == "a":
            self.tree.event_generate("<Shift-Tab>")
        elif keysym == "s":
            self.tree.event_generate("<Down>")
        elif keysym == "d":
            self.tree.event_generate("<Tab>")
        else:
            return ""

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
                self.curr_artist = ""
        self.on_key_release()

    def is_artist(self, artist):
        if (
            artist in e_binder[BINDING.ARTIST_SET]
            or artist in e_binder[BINDING.BOARD_SET]
        ):
            return True
        else:
            return False

    def on_key_release(self, e=None):
        artist = self.curr_artist
        text = self.entry.get()
        type_ = self.tag_type_var.get()
        logger.debug("On Key Release for text = %s", text)
        cancel_key = "tag_tab_on_key_release"

        thread_caller.add(
            self.get_tag_counts,
            self.update_tree_with_tags,
            cancel_key=cancel_key,
            artist=artist,
            text=text,
            type_=type_,
        )

    def get_tag_counts(self, artist, text, type_):
        with PostDb() as post_db:
            tags = post_db.get_tag_counts(artist, text, type_)
        return tags

    def update_tree_with_tags(self, tags):
        for item in self.tree.get_children():
            if item not in tags:
                self.tree.delete(item)

        for i, (tag, count) in enumerate(tags):
            if not self.is_artist(tag):
                tag_text: str = tag
                if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
                    tag_text = config.censor_text(tag_text)
                if self.tree.exists(tag):
                    self.tree.move(tag, "", i)
                else:
                    self.tree.insert("", i, iid=tag, text=tag_text, values=(count,))

    def get_tag_counts(self, artist, text, type_):
        with PostDb() as post_db:
            tags = post_db.get_tag_counts(artist, text, type_, limit=50)
        return tags

    def query_by_tag(self, event: tk.Event = None):
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        tag = self.tree.identify_row(event.y)

        if self.tree.selection():
            if tag in e_binder[BINDING.ARTIST_SET]:
                e_binder.event_generate(BINDING.ON_ARTIST_SELECT, tag, ctrl_pressed)
            else:
                e_binder.event_generate(BINDING.ON_TAG_SELECT, tag, ctrl_pressed)
        else:
            children = self.tree.children
            if children:
                self.tree.selection_set(children[0])

    def on_middle_tag(self, e=None):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click received for %s", tag)
        e_binder.event_generate(BINDING.ON_TAG_SELECT, tag, True)
