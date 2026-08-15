import fnmatch
import logging
import tkinter as tk

import ttkbootstrap as ttk
from sortedcontainers import SortedSet

from artrefsync.config import get_config
from artrefsync.constants import BINDING, BOARD, DANBOORU, E621, R34, TABLE, ICON
from artrefsync.db.post_db import PostDb
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)


class ArtistTab(ttk.Frame):
    def __init__(self, root):
        logger.info("Initializing Artist Tab.")
        super().__init__(
            root,
        )
        self.last_artist_right_clicked = ""
        self.reload_count = 0
        self.init_structure()
        self.init_bindings()
        self.load_config()
        config.subscribe_reload(self.load_config)

    def init_structure(self):
        self.board_var = ttk.StringVar()

        self.tab_label = ttk.Label(self, text="Artists", anchor="center")
        self.ui_frame = ttk.Frame(self)
        self.entry = ttk.Entry(self.ui_frame)
        self.board_menu_button = ttk.Menubutton(self.ui_frame, image=None, compound="left")
        self.artist_right_menu = ttk.Menu(self, tearoff=False)
        self.tree = ttk.Treeview(self, columns=("Icon", "Name", "Count"), show="")

        self.tab_label.pack(side=tk.TOP, fill="x", expand=False)
        self.ui_frame.pack(side=tk.TOP, fill="x", expand=False)
        self.entry.pack(side=tk.LEFT, fill="x")
        self.board_menu_button.pack(side=tk.LEFT)
        self.board_filter_menu = ttk.Menu(self.board_menu_button)
        self.board_menu_button["menu"] = self.board_filter_menu

        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        # self.tree.column("#0", width=0, anchor="w", stretch=False)
        self.tree.column("#0", width=0, minwidth=0, stretch=False)
        self.tree.column("#1", width=30, stretch=0, anchor="w")
        self.tree.column("#2", width=0, stretch=1, anchor="w")
        self.tree.column("#3", width=80, stretch=0, anchor="e")
        self.tree["displaycolumns"] = ("Icon", "Name", "Count")

    def init_bindings(self):
        self.entry.bind("<KeyRelease>", self.on_key_release)

        self.tree.bind("<Button-1>", self.on_artist_left, add=True)
        self.tree.bind("<Button-2>", self.on_artist_middle, add=True)
        self.tree.bind("<Button-3>", self.on_artist_right, add=True)
        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<Key>", self.__keystroke)
        self.board_menu_button.bind("<Return>", self.open_menu)
        self.tree.bind("<Button-1>", self.update_folder_icon, add=True)

    def load_config(self):
        if self.tree.get_children():
            self.tree.delete(*self.tree.get_children())
            self.board_filter_menu.delete(0, tk.END)
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

        for board in [
            "",
        ] + list(self.board_artists_map.keys()):
            board_str = str(board)
            self.board_filter_menu.add_radiobutton(
                label=board_str,
                value=board_str,
                variable=self.board_var,
                compound="left",
                command=self.on_board_filter_select,
            )
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

        if keysym in ["Return", "grave"]:
            self.on_artist_left(event)
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

    def open_menu(self, e):
        x = self.board_menu_button.winfo_rootx()
        y = self.board_menu_button.winfo_rooty() + self.board_menu_button.winfo_height()
        self.board_filter_menu.post(x, y)

    def on_artist_middle(self, e: tk.Event):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click recieved for %s", tag)
        event_binder.event_generate(BINDING.ON_ARTIST_SELECT, tag, True)

    def on_artist_right(self, e: tk.Event):
        if self.tree.identify_column(e.x) != "#2":
            return
        if self.tree.identify_element(e.x, e.y) == "Treeitem.indicator":
            return

        self.tree.event_generate("<Button-1>", x=e.x, y=e.y)
        tag = self.tree.identify_row(e.y)
        e.num = 1
        self.on_artist_left(e)
        e.num = 3
        if parent := self.tree.parent(tag):
            menu = self.get_artist_menu(tag, parent)
        else:
            menu = self.get_board_menu(tag)
        try:
            x, y, _, height = self.tree.bbox(tag)
            menu_x = e.widget.winfo_rootx() + x
            menu_y = e.widget.winfo_rooty() + y + height
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
        menu.add_command(label="Copy to clipboard", command= lambda: self.copy_to_clipboard(str(board)))
        menu.add_separator()
        menu.add_command(label="Open config.", compound="left", state="disabled")
        menu.add_command(label="Add artist", compound="left", state="disabled")
        menu.add_command(label="Sync All", compound="left", state="disabled")
        menu.add_command(label="Sync Recent", compound="left", state="disabled")
        return menu

    def get_artist_menu(self, artist, board):
        # TODO: Implement delete
        menu = self.artist_right_menu
        menu.delete(0, tk.END)
        prefix = "   "
        menu.add_command(
            label=prefix + "Sync All",
            command=lambda: event_binder.event_generate(
                BINDING.ON_ARTIST_SYNC, artist, board, False
            ),
        )
        menu.add_command(
            label=prefix + "Sync New",
            command=lambda: event_binder.event_generate(
                BINDING.ON_ARTIST_SYNC, artist, board, True
            ),
        )
        menu.add_command(
            label=prefix + "Copy to clipboard",
            command= lambda: self.copy_to_clipboard(artist)
        )
        menu.add_separator()
        menu.add_command(label=prefix + "Delete artist", state="disabled")
        return menu

    def on_board_filter_select(self):
        selected_board = self.board_var.get()
        logger.info('Selected "%s"', selected_board)
        if selected_board != "":
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

    def on_key_release(self, e=None):
        text = self.entry.get()
        logger.debug("On Key Release for text = %s", text)
        artist_index = 0
        for board in self.tree.get_children():
            artists = sorted(self.board_artists_map[board])
            filtered = fnmatch.filter(self.board_artists_map[board], f"*{text}*")
            active_children = self.tree.get_children(board)
            for artist in artists:
                if artist in active_children and artist not in filtered:
                    self.tree.detach(artist)
                elif artist not in active_children and artist in filtered:
                    self.tree.move(artist, board, artist_index)
                artist_index += 1

    def on_artist_left(self, event: tk.Event):
        event_type = str(event.type)
        artist = ""

        if event_type == "2" and self.tree.selection():
            artist = self.tree.selection()[0]
        elif event_type == "4":
            artist = self.tree.identify_row(event.y)

        if artist:
            logger.info("Querying by artist: %s", artist)
            event_binder.event_generate(BINDING.ON_ARTIST_SELECT, artist)

    def update_folder_icon(self, e=None):
        board = self.tree.selection()[0]
        if board in self.board_set:
            row = self.tree.item(board)
            open = row["open"] not in (True, 1, "true")

            icon = ICON.FOLDER_OPEN if open else ICON.FOLDER_CLOSED
            self.tree.set(board, "#1", icon)

