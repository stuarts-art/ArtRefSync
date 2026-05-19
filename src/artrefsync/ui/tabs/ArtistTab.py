import fnmatch
import logging
import tkinter as tk

from sortedcontainers import SortedSet
import ttkbootstrap as ttk

from artrefsync.config import config
from artrefsync.constants import BINDING, BOARD, DANBOORU, E621, R34, TABLE
from artrefsync.db.post_db import PostDb
from artrefsync.utils.EventManager import ebinder

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ArtistTab(ttk.Frame):
    def __init__(self, root, **kwargs):
        logger.info("Init Artist Tab.")
        super().__init__(
            root,
        )
        self.ui_frame = ttk.Frame(self)
        self.entry = ttk.Entry(self.ui_frame)
        self.board_var = ttk.StringVar()
        self.board_menu_button = ttk.Menubutton(
            self.ui_frame, image=None, compound="left"
        )
        self.tree = ttk.Treeview(self, columns=("Name", "Count"), show="tree", *kwargs)
        self.reload_count = 0
        self.init_structure()
        self.init_bindings()
        self.load_config()
        config.subscribe_reload(self.load_config)

    def init_structure(self):
        self.ui_frame.pack(side=tk.TOP, fill="x", expand=False)
        self.entry.pack(side=tk.LEFT, fill="x")
        self.board_menu_button.pack(side=tk.LEFT)
        self.board_menu = ttk.Menu(self.board_menu_button)
        self.board_menu_button["menu"] = self.board_menu

        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=0, stretch=0, anchor="w")
        self.tree.column("#2", width=80, stretch=0, anchor="e")
        self.tree["displaycolumns"] = ("Name", "Count")

    def init_bindings(self):
        self.entry.bind("<KeyRelease>", self.on_key_release)

        self.tree.bind("<Button-1>", self.query_by_artist)
        self.tree.bind("<Button-2>", self.on_middle_tag)
        self.board_menu_button.bind("<Return>", self.open_menu)
        self.tree.bind("<FocusIn>", self.on_tree_focusin)
        self.tree.bind("<Key>", self.__keystroke)

    def __keystroke(self, event: tk.Event):
        keycode = event.keycode
        keysym = event.keysym
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        shift_pressed = (state & 0x1) != 0

        if keysym in ["Return", "grave"]:
            self.query_by_artist()
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
        self.board_menu.post(x, y)

    def on_middle_tag(self, e: tk.Event):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click recieved for %s", tag)
        ebinder.event_generate(BINDING.ON_ARTIST_SELECT, tag, True)

    def load_config(self):
        if self.tree.get_children():
            self.tree.delete(*self.tree.get_children())
            self.board_menu.delete(0, tk.END)

        self.reload_count += 1
        if self.reload_count > 1:
            entries = self.tree.get_children()
            if entries:
                logger.info("Reloading Artist Tree. Removing %i entries", len(entries))
                self.tree.delete(*entries)

        self.board_artists_map: dict[str, SortedSet] = {
            str(TABLE.E621): SortedSet(config[TABLE.E621][E621.ARTISTS]),
            str(TABLE.R34): SortedSet(config[TABLE.R34][R34.ARTISTS]),
            str(TABLE.DANBOORU): SortedSet(config[TABLE.DANBOORU][DANBOORU.ARTISTS]),
        }
        with PostDb() as postdb:
            for board, artists in postdb.board_artists.items():
                if board not in self.board_artists_map:
                    self.board_artists_map[board] = SortedSet(artists)
                else:
                    self.board_artists_map[board].update(artists)
        self.artist_set = SortedSet()
        for artists in self.board_artists_map.values():
            self.artist_set.update(artists)

        self.board_set = set([str(board) for board in BOARD if board != BOARD.OTHER])
        ebinder.event_generate(BINDING.ARTIST_SET, self.artist_set)
        ebinder.event_generate(BINDING.BOARD_SET, self.board_set)
        self.set_artist_counts()

        for board in [
            "",
        ] + list(self.board_artists_map.keys()):
            b = str(board)
            self.board_menu.add_radiobutton(
                label=b,
                value=b,
                variable=self.board_var,
                compound="left",
                command=self.on_board_menu_select,
            )

    def on_board_menu_select(self):
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
        else:
            for i, b in enumerate(self.board_artists_map.keys()):
                self.tree.move(b, "", i)
            self.tree.selection_set((selected_board,))
            ebinder.event_generate(BINDING.ON_ARTIST_CLEAR, "")

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

    def query_by_artist(self, e=None):
        if self.tree.selection():
            artist = self.tree.selection()[0]
            logger.info("Querying by artist: %s", artist)
            ebinder.event_generate(BINDING.ON_ARTIST_SELECT, artist)

    def change_folder_text(self, e=None):
        board = self.tree.selection()[0]
        if board in self.board_set:
            row = self.tree.item(board)
            open = row["open"] not in (True, 1, "true")

            icon = "⯆ 🗁" if open else "⯈ 🗀"
            self.tree.set(board, "#1", f" {icon} {board}")

    def set_artist_counts(self):
        logger.debug("Setting BOARD ARTISTS")
        with PostDb() as postdb:
            sorted_board_artists = []
            for board, artists in postdb.board_artists.items():
                if str(board) == "e621":
                    sorted_board_artists.insert(0, (board, artists))
                else:
                    sorted_board_artists.append((board, artists))

            for board, artists in self.board_artists_map.items():
                # self.board_set.add(board)
                board_str = str(board)
                count = postdb.tag_posts.count(str(board_str))
                count = count if count else 0
                if not self.tree.exists(board_str):
                    self.tree.insert(
                        "",
                        "end",
                        iid=board_str,
                        text=board_str,
                        values=(
                            f" 🗁 {board_str}",
                            count,
                        ),
                        open=True,
                    )
                for artist in sorted(artists):
                    # self.board_set.add(artist)
                    if self.tree.exists(artist):
                        continue
                    try:
                        count = postdb.tag_posts.count(str(artist))
                        count = count if count else 0
                        self.tree.insert(
                            board_str,
                            "end",
                            iid=artist,
                            text=artist,
                            values=(
                                f"       {artist}",
                                count,
                            ),
                            open=True,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to set count for board %s, artist %s. Exception %s.",
                            board_str,
                            artist,
                            e,
                        )
                        pass
        ebinder.event_generate(BINDING.ARTIST_SET, self.artist_set)
