import logging
import tkinter as tk

import ttkbootstrap as ttk
from dataclassdb import QueryBuilder

from artrefsync.config import get_config
from artrefsync.constants import APP, BINDING, EVENT, HOTKEY, TABLE, TTKColor
from artrefsync.db.db_models import TagType
from artrefsync.db.post_db import PostDb
from artrefsync.ui.tabs.RoundedDropDown import RoundedDropDown
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.TkThreadCaller import thread_caller
from artrefsync.utils.utils import censor_text

config = get_config()
logger = logging.getLogger(__name__)


class TagTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        self.root = root
        logger.info("Initializing Tag Tab.")
        super().__init__(root, *args, **kwargs)

        self.curr_artist = ""
        self.artist_tag_count_map = {}
        self.artist_tags = []
        self.tag_type_var = ttk.StringVar()
        self.type_tags = set()
        self.ui_frame = ttk.Frame(self)
        self.entry = ttk.Entry(self.ui_frame)
        self.colors = ttk.Style().colors

        self.tab_label = ttk.Label(self, text="Tags", anchor="center")
        self.tab_label.pack(side=tk.TOP, fill="x")

        self.tag_type_button = ttk.Menubutton(
            self.ui_frame, image=None, compound="left"
        )

        with PostDb() as post_db:
            logger.info("Getting tag types")
            query = (
                QueryBuilder(post_db.connection).SELECT.DISTINCT("type").FROM(TagType)
            )
            rows = query.execute(as_dict=False)
        self.tag_types = [("Tags", "")] + [row[0] for row in rows]
        
        
        self.tag_type_menu = RoundedDropDown(
            root = self.ui_frame,
            options = self.tag_types,
            on_select= self.on_board_menu_select,
            # self.update_posts,
            variable= self.tag_type_var,
            radius=10,
            use_image=True,
            fill=self.colors.get(TTKColor.DARK),
        ).pack(side=tk.RIGHT)

        

        self.tree = ttk.Treeview(
            self,
            columns=("Count"),
            show="tree",
            takefocus=True,
        )

        # self.tag_type_menu = ttk.Menu(self.tag_type_button)
        # self.tag_type_button["menu"] = self.tag_type_menu

        self.ui_frame.pack(side=tk.TOP, fill="x")
        self.entry.pack(side="left", fill="x")
        # self.tag_type_button.pack(side="left")

        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=80, stretch=0, anchor="e")

        # with PostDb() as post_db:
        #     logger.info("Getting tag types")
        #     query = (
        #         QueryBuilder(post_db.connection).SELECT.DISTINCT("type").FROM(TagType)
        #     )
        #     rows = query.execute(as_dict=False)
        # self.tag_types = [""] + [row[0] for row in rows]
        # logger.info("tag_types =  %s", self.tag_types)

        # for tag in self.tag_types:
        #     label = str(tag)
        #     self.tag_type_menu.add_radiobutton(
        #         label=label,
        #         value=label,
        #         variable=self.tag_type_var,
        #         compound="left",
        #         command=self.on_board_menu_select,
        #     )

        self.after(100, self.on_entry_update)
        config.subscribe_reload(self.on_entry_update)
        self.init_bindings()

    def on_board_menu_select(self):
        selected_board = self.tag_type_menu.get()
        # selected_board = self.tag_type_var.get()
        if selected_board == "Tags": 
            selected_board = ""
        logger.info('Selected "%s"', selected_board)

    def init_bindings(self):
        event_binder.bind(BINDING.ON_ARTIST_SELECT, self.update_artist, self)
        event_binder.bind(BINDING.ON_ARTIST_CLEAR, self.update_artist, self)
        event_binder.bind(BINDING.ON_DB_UPDATE, self.on_entry_update, self)

        # Entry Keybinds
        self.entry.bind("<Tab>", event_binder.closure(BINDING.ON_ICON_ARTIST), add=False)
        self.entry.bind("<Return>", lambda e: self.tree.focus_set())
        self.entry.bind("<KeyRelease>", self.on_entry_update)

        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<Key>", self.__keystroke)
        self.tree.bind("<ButtonRelease-1>", self.query_by_tag)
        self.tree.bind("<Button-2>", self.on_middle_tag)

        self.tag_type_var.trace_add("write", self.__on_tag_type_update)

    def __on_tag_type_update(self, *args):
        self.on_entry_update()

    def __keystroke(self, event: tk.Event):
        keycode = event.keycode  # noqa: F841
        keysym = event.keysym
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        shift_pressed = (state & 0x1) != 0  # noqa: F841

        target = ""
        tag = self.tree.focus()
        if not tag:
            if children := self.tree.get_children():
                target = children[0]

        if keysym in config[HOTKEY.ZOOM_IN_LIST] + ["Tab"]:
            event_binder.event_generate(BINDING.ON_ICON_INFO, focus_entry = False)

        elif keysym in config[HOTKEY.ZOOM_OUT_LIST]:
            event_binder.event_generate(BINDING.ON_ICON_ARTIST, focus_entry = False)

        elif keysym == "Tab":
            event_binder.event_generate(BINDING.ON_ICON_ARTIST)
        elif keysym == "Return":
            self.entry.focus_set()
        elif keysym == "BackSpace":
            event_binder.event_generate(BINDING.RUN_TAG_REMOVE_LAST)
        elif keysym in config[HOTKEY.UP_LIST]:
            if prev := self.tree.prev(tag):
                target = prev

        elif keysym in config[HOTKEY.LEFT_LIST]:
            pass
        elif keysym in config[HOTKEY.DOWN_LIST]:
            if next_ := self.tree.next(tag):
                target = next_
        elif keysym in config[HOTKEY.RIGHT_LIST]:
            if tag in event_binder[BINDING.ARTIST_SET]:
                event_binder.event_generate(BINDING.ON_ARTIST_SELECT, tag, ctrl_pressed)
            else:
                event_binder.event_generate(BINDING.ON_TAG_SELECT, tag, ctrl_pressed)
            return "break"
        
        if target:
            self.tree.focus(target)
            self.tree.selection_set(target)
            self.tree.see(target)
            return "break"
        return "break"

    def on_tree_focusin(self, e):
        
        if tag := self.tree.focus():
            self.tree.focus(tag)
            self.tree.selection_set(tag)
            self.tree.see(tag)
        elif children:= self.tree.get_children():
            child = children[0]
            self.tree.focus(child)
            self.tree.selection_set(child)
            self.tree.see(child)


    def update_artist(self, artist, middle=False):
        if artist != self.curr_artist:
            self.curr_artist = artist
            if not artist:
                self.curr_artist = ""
        self.on_entry_update()

    def is_artist(self, artist):
        return (
            artist in event_binder[BINDING.ARTIST_SET]
            or artist in event_binder[BINDING.BOARD_SET]
        )

    def on_entry_update(self, e=None):
        artist = self.curr_artist
        text = self.entry.get()
        type_ = self.tag_type_menu.get()
        logger.info("On Key Release for text = %s", text)
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
            # tags = post_db.get_tag_counts(artist, text, type_, limit = 1000)
            tags = post_db.get_tag_counts(artist = artist, search=text, type_=type_ )
        return tags

    def update_tree_with_tags(self, tags):

        for item in self.tree.get_children():
            self.tree.delete(item)


        for i, (tag, count) in enumerate(tags):
            if self.is_artist(tag):
                continue
            if i >= 500:
                return
            tag_text: str = tag
            if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
                tag_text = censor_text(tag_text)
            if self.tree.exists(tag):
                self.tree.move(tag, "", i)
            else:
                self.tree.insert("", i, iid=tag, text=tag_text, values=(count,))
            

    def query_by_tag(self, event: tk.Event):
        state = event.state
        ctrl_pressed = (state & 0x4) != 0

        if event.type == EVENT.TYPE.BUTTON:
            tag = self.tree.identify_row(event.y)
        else:
            tag = self.tree.selection()[0]

        if tag in event_binder[BINDING.ARTIST_SET]:
            event_binder.event_generate(BINDING.ON_ARTIST_SELECT, tag, ctrl_pressed)
        else:
            event_binder.event_generate(BINDING.ON_TAG_SELECT, tag, ctrl_pressed)
        return "break"

    def on_middle_tag(self, e=None):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click received for %s", tag)
        event_binder.event_generate(BINDING.ON_TAG_SELECT, tag, True)
