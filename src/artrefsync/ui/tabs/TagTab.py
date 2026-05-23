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
        self.tree.config(selectmode=tk.NONE)

        self.tag_type_menu = ttk.Menu(self.tag_type_button)
        self.tag_type_button["menu"] = self.tag_type_menu

        self.ui_frame.pack(side=tk.TOP, fill="x")
        self.entry.pack(side="left", fill="x")
        self.tag_type_button.pack(side="left")

        # self.entry.pack(side=tk.TOP, fill="x")
        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=80, stretch=0, anchor="e")
        self.tree.config(selectmode=tk.BROWSE)
        self.type_tags = set()

        with PostDb() as post_db:
            self.tag_types = post_db.tag_types.select_freeform(
                "type, COUNT(tag) as count",
                "TagType",
                suffix_str="GROUP BY type",
                as_tupple=True,
            )
        self.tag_types.append(("", 0))

        for tag, count in self.tag_types:
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
        ebinder.bind(BINDING.ON_ARTIST_SELECT, self.update_artist, self)
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
            self.query_by_tag()
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
                self.curr_artist = ""
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

    def is_artist(self, artist):
        if (
            artist in ebinder[BINDING.ARTIST_SET]
            or artist in ebinder[BINDING.BOARD_SET]
        ):
            return True
        else:
            return False

    def on_key_release(self, e=None):
        artist = self.curr_artist
        text = self.entry.get()
        type = self.tag_type_var.get()
        logger.debug("On Key Release for text = %s", text)
        with PostDb() as post_db:
            tags = post_db.get_tag_counts(artist, text, type)

        for item in self.tree.get_children():
            self.tree.delete(item)

        repl_text = "₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊"
        for i, (tag, count) in enumerate(tags):
            if not self.is_artist(tag):
                tag_text: str = tag
                if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
                    repl_split = "_".join(
                        [
                            split[0]
                            + repl_text[len(split) : 2 * len(split) - 2]
                            + split[-1]
                            for split in tag_text.split("_")
                        ]
                    )
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
