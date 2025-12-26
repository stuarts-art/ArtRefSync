from sortedcontainers import SortedSet
from artrefsync.config import config
import logging
from functools import lru_cache
from PIL import Image, ImageTk
import ttkbootstrap as ttk
from artrefsync.boards.board_handler import Post
from artrefsync.constants import E621, R34, TABLE


logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class Artist_Tree(ttk.Treeview):
    def __init__(self, root, **kwargs):
        # self.columns = ("Name", "Count",)
        self.columns = ("Name")

        super().__init__(root, columns=self.columns, show= "tree", *kwargs)

        # print(ttk.Style().theme_use())
        ttk.Style().configure("Treeview", background = "#222222")



        self.artists = {
            TABLE.E621: set(config[TABLE.E621][E621.ARTISTS]),
            TABLE.R34: set(config[TABLE.R34][R34.ARTISTS]),
        }
        self.set_icon_map(16)
        self.artist_set = SortedSet(set().union(*self.artists.values()))
        
        artists = self.artists
        aset = self.artist_set
        # self.column("#0", width = 30, stretch=0, anchor='w')
        self.column("#0", width = 150, anchor='w', stretch=False)
        for table in [TABLE.E621, TABLE.R34]:
            self.insert(
                "",
                "end",
                iid=table,
                text=table,
                image=self.icon_map[table],
                # values=(table),
                open=True,
            )
            for artist in aset:
                if artist in artists[table]:
                    self.insert(
                        table,
                        "end",
                        iid=artist,
                        text=artist,
                        # image=self.icon_map[table],
                        # values=(f"{artist}",),
                        open=True,
                    )

    # @lru_cache(maxsize=5)
    def get_photo_image(self, pid, width, height):
        logger.info("Loading %s", pid)
        post: Post = self.tag_post_manager.post_id[pid]
        file = post.file
        image = Image.open(file)
        image.thumbnail((1000, 500))
        return ImageTk.PhotoImage(image)

    def set_icon_map(self, size=24):
        self.icon_map = {}
        for table, icon in [
            (TABLE.E621, "resources/favicon-32x32.png"),
            (TABLE.R34, "resources/apple-touch-icon-precomposed.png"),
        ]:
            image = Image.open(icon)
            image.thumbnail((size, size))
            self.icon_map[table] = ImageTk.PhotoImage(image)
