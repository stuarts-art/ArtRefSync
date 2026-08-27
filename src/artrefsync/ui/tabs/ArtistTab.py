import fnmatch
import logging
import tkinter as tk

import ttkbootstrap as ttk
from sortedcontainers import SortedSet

from artrefsync.config import get_config
from artrefsync.constants import (
    BINDING,
    BOARD,
    EVENT,
    HOTKEY,
    ICON,
    TTKColor,
)
from artrefsync.db.post_db import PostDb
from artrefsync.ui.tabs.RoundedDropDown import RoundedDropDown
from artrefsync.utils.event_binder import event_binder

config = get_config()
logger = logging.getLogger(__name__)


class ArtistTab(ttk.Frame):
    def __init__(self, root):
        logger.info("Initializing Artist Tab.")
        super().__init__(
            root,
        )
        self.colors = ttk.Style().colors
        self.last_parent = ""
        self.reload_count = 0
        self.init_structure()
        self.init_bindings()
        self.load_config()
        config.subscribe_reload(self.load_config)

    def init_structure(self):
        self.board_var = ttk.StringVar(value="Artists")
        self.tab_label = ttk.Label(self, text="Artists", anchor="center")
        self.tab_label.pack(side=tk.TOP, fill="x")
        self.ui_frame = ttk.Frame(self)
        RoundedDropDown(
            self.ui_frame,
            ["Board", BOARD.DANBOORU, BOARD.R34, BOARD.E621],
            self.on_board_filter_select,
            # self.update_posts,
            self.board_var,
            radius=10,
            use_image=True,
            fill=self.colors.get(TTKColor.DARK),
        ).pack(side=tk.RIGHT)
        self.ui_frame.pack(side=tk.TOP, fill="x")

        self.entry = ttk.Entry(self.ui_frame)
        self.entry.pack(side=tk.RIGHT, fill="x")
        self.artist_right_menu = ttk.Menu(self, tearoff=False)
        self.tree = ttk.Treeview(self, columns=("Icon", "Name", "Count"), show="")

        self.ui_frame.pack(side=tk.TOP, fill="x")
        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, minwidth=0, stretch=False)
        self.tree.column("#1", width=40, stretch=0, anchor="w")
        self.tree.column("#2", width=0, stretch=1, anchor="w")
        self.tree.column("#3", width=80, stretch=0, anchor="e")
        self.tree["displaycolumns"] = ("Icon", "Name", "Count")

    def init_bindings(self):

        self.entry.bind("<Tab>", event_binder.closure(BINDING.ON_ICON_TAG), add=False)
        self.entry.bind("<Down>", lambda e: self.tree.focus_set())
        self.entry.bind("<Return>", lambda e: self.tree.focus_set())
        self.tree.bind("<Return>", lambda e: self.entry.focus_set())

        self.entry.bind("<KeyRelease>", self.on_entry_key_release)

        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<Key>", self.__keystroke)
        self.tree.bind("<Double-Button-1>", lambda _: None, add=True)
        self.tree.bind("<Button>", self.__button, add=True)
        self.tree.bind(
            "<<TreeviewOpen>>",
            lambda e: self.after(20, self.set_open_icon, e),
            add=True,
        )
        self.tree.bind(
            "<<TreeviewClose>>",
            lambda e: self.after(20, self.set_open_icon, e),
            add=True,
        )

        event_binder.bind(BINDING.ON_DB_UPDATE, self.load_config, self)

    def load_config(self):
        if self.tree.get_children():
            self.tree.delete(*self.tree.get_children())
        self.reload_count += 1
        if self.reload_count > 1:
            entries = self.tree.get_children()
            if entries:
                logger.info("Reloading Artist Tree. Removing %i entries", len(entries))
                self.tree.delete(*entries)

        with PostDb() as post_db:
            self.board_artists_map = post_db.get_board_artists()

        self.board_set = SortedSet()
        self.artist_set = SortedSet()
        self.board_counts = {}

        for board, artist_count in self.board_artists_map.items():
            self.board_set.add(board)
            board_count = 0
            for artist, count in artist_count.items():
                self.artist_set.add(artist)
                board_count += count
            self.board_counts[board] = board_count

        event_binder[BINDING.ARTIST_SET] = self.artist_set
        event_binder[BINDING.BOARD_SET] = self.board_set
        event_binder[BINDING.BOARD_ARTIST_MAP] = self.board_artists_map

        self.update_tree()

    def update_tree(self):
        logger.info("Updating Tree")

        for board, artist_count_map in self.board_artists_map.items():
            board_str = str(board)
            board_count = self.board_counts[board]
            if not self.tree.exists(board_str):
                self.tree.insert(
                    "",
                    "end",
                    iid=board_str,
                    text=board_str,
                    values=(ICON.FOLDER_OPEN, board_str, board_count),
                    open=True,
                )
            for artist, artist_count in artist_count_map.items():
                if not self.tree.exists(artist):
                    # count = self.count_map.get(artist, 0)
                    self.tree.insert(
                        board_str,
                        "end",
                        iid=artist,
                        text=artist,
                        values=("", artist, artist_count),
                        open=True,
                    )
        event_binder[BINDING.ARTIST_SET] = self.artist_set
        event_binder[BINDING.BOARD_SET] = self.board_set

    def __keystroke(self, event: tk.Event):

        keysym = event.keysym
        ctrl_pressed = (event.state & 0x4) != 0
        shift_pressed = (event.state & 0x1) != 0  # noqa: F841

        if keysym in config[HOTKEY.ZOOM_IN_LIST] + ["Tab"]:
            event_binder.event_generate(BINDING.ON_ICON_TAG, focus_entry=False)

        elif keysym in config[HOTKEY.ZOOM_OUT_LIST]:
            event_binder.event_generate(BINDING.ON_ICON_INFO, focus_entry=False)

        elif keysym in config[HOTKEY.UP_LIST]:
            tag = self.tree.focus()
            target = ""

            if parent := self.tree.parent(tag):
                if prev := self.tree.prev(tag):
                    target = prev
                else:
                    target = parent
            elif prev := self.tree.prev(tag):
                target = prev
                if row := self.tree.item(prev):
                    is_open = row["open"] in (True, 1, "true")
                    children = self.tree.get_children(prev)
                    if is_open and children:
                        target = children[-1]

            if target:
                self.tree.focus(target)
                self.tree.selection_set(target)
                self.tree.see(target)

            # self.tree.event_generate("<Up>", event)
        elif keysym in config[HOTKEY.LEFT_LIST]:
            # elif keysym in ["a", "h", "Left"]:
            tag = self.tree.focus()
            if parent := self.tree.parent(tag):
                self.tree.focus(parent)
                self.tree.selection_set(parent)
                self.tree.see(parent)

                # self.on_artist_left(parent)
            else:
                row = self.tree.item(tag)
                if row["open"] in (True, 1, "true"):
                    self.tree.item(tag, open=False)
                else:
                    self.tree.item(tag, open=True)
                    # self.entry.focus_set()

        elif keysym in config[HOTKEY.DOWN_LIST]:
            tag = self.tree.focus()
            target = ""

            if (children := self.tree.get_children(tag)) and self.tree.item(
                tag, "open"
            ):
                target = children[0]
            elif next_ := self.tree.next(tag):
                target = next_
            elif parent := self.tree.parent(tag):  # noqa: SIM102
                if parent_next := self.tree.next(parent):
                    target = parent_next

            if target:
                self.tree.focus(target)
                self.tree.selection_set(target)
                self.tree.see(target)

        elif keysym in config[HOTKEY.RIGHT_LIST]:
            # elif keysym in ["d", "l", "Right"]:
            tag = self.tree.focus()
            self.on_artist_left(tag)
            if parent := self.tree.parent(self.tree.focus()):
                event_binder.event_generate(BINDING.RUN_FOCUS_GALLERY)
                self.last_parent = parent
            elif row := self.tree.item(tag):
                is_open = row["open"]
                if is_open:
                    event_binder.event_generate(BINDING.RUN_FOCUS_GALLERY)
                else:
                    self.tree.item(tag, open=True)

                if is_open := row["open"] in (True, 1, "true"):
                    event_binder.event_generate(BINDING.RUN_FOCUS_GALLERY)
                else:
                    self.tree.item(tag, open=not is_open)

        elif keysym == "space":
            pass
        elif keysym == "BackSpace":
            tag = self.focus()
            event_binder.event_generate(BINDING.RUN_TAG_REMOVE_LAST, tag)

        else:
            return ""
        return "break"

    def __button(self, event: tk.Event):
        num = event.num
        y = event.y
        x = event.x
        tag = self.tree.identify_row(y)
        col = self.tree.identify_column(x)
        parent = self.tree.parent(tag)

        if num == EVENT.NUM.LEFT.value:
            self.on_artist_left(tag)
            return "break"
        elif num == EVENT.NUM.LEFT.value:
            pass
        elif num == EVENT.NUM.RIGHT.value:
            self.on_artist_left(tag)
            self.on_menu(tag, parent, col, x, y)

    def on_tree_focusin(self, e):
        tag = self.tree.focus()

        if tag:
            if not self.tree.parent(tag) and not self.tree.get_children(tag):
                tag = self.last_parent

            self.tree.selection_set(tag)
            self.tree.focus(tag)
            self.tree.see(tag)

        elif children := self.tree.get_children():
            self.tree.focus(children[0])
            self.tree.selection_set(children[0])
            self.tree.see(children[0])

    def on_artist_middle(self, e: tk.Event):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click recieved for %s", tag)
        event_binder.event_generate(BINDING.ON_ARTIST_SELECT, tag, True)

    def on_menu(self, tag, parent, col, x, y):
        if col != "#2":
            return
        if self.tree.identify_element(x, y) == "Treeitem.indicator":
            return

        if parent:
            menu = self.get_artist_menu(tag, parent)
        else:
            menu = self.get_board_menu(tag)
        try:
            x, y, _, height = self.tree.bbox(tag)
            menu_x = self.tree.winfo_rootx() + x
            menu_y = self.tree.winfo_rooty() + y + height
            menu.tk_popup(menu_x, menu_y)
        finally:
            menu.grab_release()

    def copy_to_clipboard(self, artist):
        self.clipboard_clear()
        self.clipboard_append(artist)
        self.update_idletasks()

    def get_board_menu(self, board: BOARD):
        # TODO: Implement commands
        logger.info("Updating artist right click menu for board %s", board)
        menu = self.artist_right_menu
        menu.delete(0, tk.END)
        menu.add_command(
            label="Copy to clipboard",
            command=lambda: self.copy_to_clipboard(str(board)),
        )
        menu.add_separator()
        menu.add_command(label="Open config.", compound="left", state="disabled")
        menu.add_command(label="Add artist", compound="left", state="disabled")
        menu.add_command(
            label="Sync All",
            compound="left",
            command=lambda: event_binder.event_generate(
                BINDING.RUN_SYNC, only_recent=False, board_override=board
            ),
        )
        menu.add_command(
            label="Sync Recent",
            compound="left",
            command=lambda: event_binder.event_generate(
                BINDING.RUN_SYNC, only_recent=True, board_override=board
            ),
        )
        menu.add_command(
            label="Update app from local files",
            compound="left",
            command=lambda: event_binder.event_generate(
                BINDING.RUN_STORE_SYNC, board_override=board
            ),
        )
        return menu

    def get_artist_menu(self, artist, board):
        # TODO: Implement delete
        menu = self.artist_right_menu
        menu.delete(0, tk.END)
        prefix = "   "
        menu.add_command(
            label=prefix + "Sync All",
            command=lambda: event_binder.event_generate(
                BINDING.RUN_SYNC,
                only_recent=False,
                board_override=board,
                artist_override=artist,
            ),
        )
        menu.add_command(
            label=prefix + "Sync New",
            command=lambda: event_binder.event_generate(
                BINDING.RUN_SYNC,
                only_recent=True,
                board_override=board,
                artist_override=artist,
            ),
        )
        menu.add_command(
            label=prefix + "Copy to clipboard",
            command=lambda: self.copy_to_clipboard(artist),
        )
        menu.add_separator()
        menu.add_command(label=prefix + "Delete artist", state="disabled")
        return menu

    def on_board_filter_select(self, new_value=None):
        if new_value is not None:
            self.board_var.set(new_value)
        selected_board = self.board_var.get().strip()
        if selected_board == "Board":
            selected_board = ""
        logger.info('Selected "%s"', selected_board)
        if selected_board != "":
            event_binder.event_generate(BINDING.ON_ARTIST_SELECT, selected_board)
            selected_found = False
            for c in self.tree.get_children(""):
                if c == selected_board:
                    selected_found = True
                else:
                    self.tree.detach(c)

            if not selected_found:
                self.tree.move(selected_board, "", "end")
            self.tree.selection_set((selected_board,))
            self.tree.item(selected_board, open=True)
            self.tree.set(selected_board, "#1", ICON.FOLDER_OPEN)
        else:
            for i, b in enumerate(self.board_artists_map.keys()):
                self.tree.move(b, "", i)
            self.tree.selection_set((selected_board,))
            event_binder.event_generate(BINDING.ON_ARTIST_CLEAR, "")

    def on_entry_key_release(self, e=None):
        text = self.entry.get()
        logger.debug("On Key Release for text = %s", text)
        artist_index = 0
        for board in self.tree.get_children():
            self.tree.item(board, open=True)
            artists = sorted(self.board_artists_map[board])
            filtered = fnmatch.filter(self.board_artists_map[board], f"*{text}*")
            active_children = self.tree.get_children(board)
            for artist in artists:
                if artist in active_children and artist not in filtered:
                    self.tree.detach(artist)
                elif artist not in active_children and artist in filtered:
                    self.tree.move(artist, board, artist_index)
                artist_index += 1

    def on_artist_left(self, artist):
        if artist:
            self.tree.focus(artist)
            self.tree.selection_set((artist,))
            logger.info("Querying by artist: %s", artist)
            event_binder.event_generate(BINDING.ON_ARTIST_SELECT, artist)

    def set_open_icon(self, event):
        for b in [BOARD.E621, BOARD.R34, BOARD.DANBOORU]:
            row = self.tree.item(b)
            open = row["open"] not in (True, 1, "true")
            icon = ICON.FOLDER_CLOSED if open else ICON.FOLDER_OPEN
            self.tree.set(b, "#1", icon)
