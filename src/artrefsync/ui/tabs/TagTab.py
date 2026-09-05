import logging
import tkinter as tk

import ttkbootstrap as ttk
from dataclassdb import QueryBuilder

from artrefsync.config import get_config
from artrefsync.constants import APP, BINDING, EVENT, HOTKEY, TABLE, TTKColor
from artrefsync.db.db_models import TagType
from artrefsync.db.post_db import PostDb
from artrefsync.ui.tabs.RoundedDropDown import RoundedDropDown
from artrefsync.ui.widgets.ImagePreview import update_preview_with_tags
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
        self.last_hover_row = None
        self.previewing = ""
        self.is_focus = False


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
            root=self.ui_frame,
            options=self.tag_types,
            on_select=self.on_board_menu_select,
            variable=self.tag_type_var,
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

        self.ui_frame.pack(side=tk.TOP, fill="x")
        self.entry.pack(side="left", fill="x")

        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=80, stretch=0, anchor="e")

        self.after(100, self.on_entry_update)
        config.subscribe_reload(self.on_entry_update)
        self.init_bindings()
        logger.info("Tag Tab Initialized.")


    def update_preview(self, tag):
        if not tag:
            self.previewing = ""
            self.last_hover_row = ""
            return update_preview_with_tags("")
        elif event_binder[BINDING.APP_WIDGET].last_widget != self:
            return
        if artist := event_binder[BINDING.ACTIVE_WIDGET].artist:
            tags = [artist, tag]
        else:
            tags = [tag]

        if tags == self.previewing:
            return
        self.previewing = tags

        app = event_binder[BINDING.APP_WIDGET]
        rootx = self.tree.winfo_rootx() - app.winfo_rootx()
        rooty = self.tree.winfo_rooty() - app.winfo_rooty()

        x, y, w, h = self.tree.bbox(tag)
        x_offset = rootx + x + w + 14
        y_offset = rooty + y + h // 2
        update_preview_with_tags(tags=tags, x = x_offset, y = y_offset, anchor = tk.W)


    def on_board_menu_select(self):
        selected_board = self.tag_type_menu.get()
        if selected_board == "Tags":
            selected_board = ""
        logger.info('Selected "%s"', selected_board)

    def init_bindings(self):
        self.entry.bind(
            "<Tab>", event_binder.closure(BINDING.ON_ICON_ARTIST), add=False
        )
        self.entry.bind("<Return>", lambda e: self.tree.focus_set())
        self.entry.bind("<KeyRelease>", self.on_entry_update)
        self.tag_type_var.trace_add("write", self.on_entry_update)


        self.tree.bind("<Motion>", self.on_tree_hover)
        self.tree.bind("<Enter>", self.on_tree_enter)
        self.tree.bind("<Leave>", self.on_tree_leave)
        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<FocusOut>", self.on_tree_focusout)
        self.tree.bind("<Key>", self.__keystroke)
        self.tree.bind("<ButtonRelease-1>", self.query_by_tag)
        self.tree.bind("<Button-2>", self.on_middle_tag)

        event_binder.bind(BINDING.ON_ARTIST_UPDATE, self.update_artist, self)
        event_binder.bind(BINDING.ON_DB_UPDATE, self.on_entry_update, self)


    def on_tree_enter(self, e):
        # if tag := self.previewing:
        #     self.tree.focus(tag)
        #     self.tree.selection_set(tag)
        #     self.tree.see(tag)
        #     self.tree.focus_set()
        pass

    def on_tree_leave(self, e):
        if self.is_focused:
            tag = self.tree.focus()
            self.update_preview(tag)
        else:
            self.update_preview("")

    def on_tree_hover(self, e):
        if row := self.tree.identify_row(e.y):
            if row == self.last_hover_row:
                return
            else:
                self.last_hover_row = row
                self.update_preview(row)

    def __keystroke(self, event: tk.Event):
        keysym = event.keysym
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        shift_pressed = (event.state & 0x1) != 0

        target = ""
        tag = self.tree.focus()
        if not tag and (children := self.tree.get_children()):
            target = children[0]

        if keysym in config[HOTKEY.ZOOM_IN_LIST]:
            event_binder.after_idle(BINDING.ON_ICON_INFO, focus_entry=False)

        elif keysym in config[HOTKEY.ZOOM_OUT_LIST] + config[HOTKEY.SWAP_LIST]:
            event_binder.after_idle(BINDING.ON_ICON_ARTIST, focus_entry=False)
        elif keysym in config[HOTKEY.SEARCH_LIST]:
            self.entry.focus_set()
        elif keysym in config[HOTKEY.DELETE_LIST]:
            event_binder.after_idle(BINDING.RUN_TAG_REMOVE_LAST)
        elif keysym in config[HOTKEY.UP_LIST]:
            if prev := self.tree.prev(tag):
                target = prev
        elif keysym in config[HOTKEY.LEFT_LIST]:
            event_binder.after_idle(BINDING.REMOVE_IF_ACTIVE, tag)

        elif keysym in config[HOTKEY.DOWN_LIST]:
            if next_ := self.tree.next(tag):
                target = next_
        elif keysym in config[HOTKEY.RIGHT_LIST] + config[HOTKEY.OPEN_LIST]:
            if tag in event_binder[BINDING.ARTIST_SET]:
                event_binder.after_idle(BINDING.ON_ARTIST_SELECT, tag, ctrl_pressed or shift_pressed)
            else:
                event_binder.after_idle(BINDING.ON_TAG_SELECT, tag, ctrl_pressed or shift_pressed)
            return "break"

        if target:
            self.tree.focus(target)
            self.tree.selection_set(target)
            self.tree.see(target)
            self.update_preview(target)
            return "break"
        return "break"

    def on_tree_focusin(self, *_):
        self.is_focused = True
        self.after(50, self.delayed_focusin)

    def delayed_focusin(self):
        if tag := self.tree.focus():
            self.tree.focus(tag)
            self.tree.selection_set(tag)
            self.tree.see(tag)
            self.update_preview(tag)
        elif children := self.tree.get_children():
            child = children[0]
            tag = child
            self.tree.focus(tag)
            self.tree.selection_set(tag)
            self.tree.see(tag)
            self.update_preview(tag)
        else:
            tag = ""
            self.update_preview(tag)

        self.previewing = tag

    def on_tree_focusout(self, e):
        self.is_focused = False
        self.update_preview("")

    def update_artist(self, artist, middle=False):
        if artist != self.curr_artist:
            if not artist:
                self.curr_artist = ""
            elif self.is_artist(artist):
                self.curr_artist = artist
        self.on_entry_update()

    def is_artist(self, artist):
        return (
            artist in event_binder[BINDING.ARTIST_SET]
            or artist in event_binder[BINDING.BOARD_SET]
        )

    def on_entry_update(self, *_):
        artist = self.curr_artist
        text = self.entry.get()
        type_ = self.tag_type_menu.get()
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
            tags = post_db.get_tag_counts(artist=artist, search=text, type_=type_, limit=100)
        return tags

    def update_tree_with_tags(self, tags):

        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, (tag, count) in enumerate(tags):
            if self.is_artist(tag):
                continue
            tag_text: str = tag
            if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
                tag_text = censor_text(tag_text)
            if self.tree.exists(tag):
                self.tree.move(tag, "", i)
            else:
                self.tree.insert("", i, iid=tag, text=tag_text, values=(count,))
        if children := self.tree.get_children():
            self.update_preview(children[0])
        else:
            self.update_preview("")
        

    def query_by_tag(self, event: tk.Event):
        state = event.state
        ctrl_pressed = (state & 0x4) != 0

        if event.type == EVENT.TYPE.BUTTON:
            tag = self.tree.identify_row(event.y)
        else:
            tag = self.tree.selection()[0]

        if tag in event_binder[BINDING.ARTIST_SET]:
            event_binder.after_idle(BINDING.ON_ARTIST_SELECT, tag, ctrl_pressed)
        else:
            event_binder.after_idle(BINDING.ON_TAG_SELECT, tag, ctrl_pressed)
        return "break"

    def on_middle_tag(self, e=None):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click received for %s", tag)
        event_binder.after_idle(BINDING.ON_TAG_SELECT, tag, True)
