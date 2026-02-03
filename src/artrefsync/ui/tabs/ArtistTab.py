from artrefsync.config import config
import logging
from PIL import Image, ImageTk, ImageDraw
import ttkbootstrap as ttk
import tkinter as tk
from artrefsync.constants import BINDING, BOARD, DANBOORU, E621, R34, TABLE
from artrefsync.db.post_db import PostDb
from artrefsync.utils.PyInstallerUtils import resource_path
from artrefsync.utils.EventManager import ebinder


logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ArtistTab(ttk.Frame):
    def __init__(self, root, **kwargs):
        super().__init__(
            root,
        )
        self.entry = ttk.Entry(self)
        self.tree = ttk.Treeview(self, columns=("Name", "Count"), show="tree", *kwargs)
        # self.tree = ttk.Treeview(self, columns=("Count"), show="tree", *kwargs)
        self.board_var = ttk.StringVar()
        self.board_menu_button = ttk.Menubutton(
            self, textvariable=self.board_var, image=None, compound="left"
        )
        self.board_menu_button.pack(side=tk.TOP, fill="x")
        self.board_menu = ttk.Menu(self.board_menu_button)
        self.board_menu_button["menu"] = self.board_menu

        # self.entry.pack(side=tk.TOP, fill="x")
        self.tree.pack(side=tk.TOP, fill="both", expand=True)
        # self.set_icon_map(16)
        # self.tree.column("#0", width=0, anchor="w", stretch=False, minwidth=0)
        self.tree.column("#0", width=0, anchor="w", stretch=True)
        self.tree.column("#1", width=0, stretch=0, anchor="w")
        self.tree.column("#2", width=80, stretch=0, anchor="e")
        self.tree.bind("<<TreeviewSelect>>", self.query_by_artist)
        self.tree.bind("<Button-2>", self.on_middle_tag)
        # self.tree.bind("<<TreeviewSelect>>", self.query_by_artist)
        self.tree.bind("<Double-Button-1>", self.change_folder_text, add=True)
        self.tree["displaycolumns"] = ("Name", "Count")
        # self.set()
        self.reload_count = 0
        self.load_config()
        config.subscribe_reload(self.load_config)

    def on_middle_tag(self, e=None):
        tag = self.tree.identify_row(e.y)
        logger.info("Middle click recieved for %s", tag)
        ebinder.event_generate(BINDING.ON_ARTIST_SELECT, tag, True)

    def load_config(self):
        self.reload_count += 1
        if self.reload_count > 1:
            entries = self.tree.get_children()
            if entries:
                logger.info("Reloading Artist Tree. Removing %i entries", len(entries))
                self.tree.delete(*entries)
        # TODO: Set boards progamatically.
        self.board_artists_map = {
            TABLE.E621: set(config[TABLE.E621][E621.ARTISTS]),
            TABLE.R34: set(config[TABLE.R34][R34.ARTISTS]),
            TABLE.DANBOORU: set(config[TABLE.DANBOORU][DANBOORU.ARTISTS]),
        }
        self.artist_set = set(
            [str(artist) for artist in set().union(*self.board_artists_map.values())]
        )
        print(self.artist_set)
        self.board_set = set([str(board) for board in BOARD if board != BOARD.OTHER])

        ebinder.event_generate(BINDING.ARTIST_SET, self.artist_set)
        ebinder.event_generate(BINDING.BOARD_SET, self.board_set)
        self.set_artist_counts()

        # menu_options = [""].update(self)
        for board in [""] + list(self.board_artists_map.keys()):
            b = str(board)
            self.board_menu.add_radiobutton(
                label=b,
                value=b,
                variable=self.board_var,
                # image=self.icon_map[b],
                compound="left",
                command=self.on_board_menu_select,
            )

    def on_board_menu_select(self):
        selected_board = self.board_var.get()
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

    def query_by_artist(self, e=None):
        artist = self.tree.selection()[0]
        ebinder.event_generate(BINDING.ON_ARTIST_SELECT, artist)

    def change_folder_text(self, e=None):
        board = self.tree.selection()[0]
        if board in self.board_set:
            row = self.tree.item(board)
            open = row["open"] not in (True, 1, "true")

            # icon = "🗁" if open else "🗀"
            icon = "⯆ 🗁" if open else "⯈ 🗀"
            self.tree.set(board, "#1", f" {icon} {board}")

    def set_artist_counts(self):
        with PostDb() as postdb:
            for table, artists in postdb.board_artists.items():
                count = postdb.tag_posts.count(str(table))
                count = count if count else 0
                self.tree.insert(
                    "",
                    "end",
                    iid=table,
                    text=table,
                    # image=self.icon_map[table],
                    values=(
                        f" 🗁 {table}",
                        count,
                    ),
                    open=True if count else False,
                )
                for artist in artists:
                    try:
                        count = postdb.tag_posts.count(str(artist))
                        count = count if count else 0
                        self.tree.insert(
                            table,
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
                            "Failed to set count for board %s, artist %s", table, artist
                        )
                        logger.warning("Exception %s", e)
                        pass

    # def set_icon_map(self, size=24):
    #     self.icon_map = {}
    #     for table, icon in [
    #         (TABLE.E621, resource_path("resources/favicon-32x32.png")),
    #         (TABLE.R34, resource_path("resources/apple-touch-icon-precomposed.png")),
    #         (
    #             TABLE.DANBOORU,
    #             resource_path("resources/apple-touch-icon-precomposed.png"),
    #         ),
    #     ]:
    #         image = Image.open(icon)
    #         image.thumbnail((size, size))
    #         self.icon_map[table] = ImageTk.PhotoImage(image)
    #     self.icon_map[""] = None
