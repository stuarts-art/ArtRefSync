from functools import lru_cache
from sortedcontainers import SortedSet
import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from PIL import Image, ImageTk

from artrefsync.boards.board_handler import Post
from artrefsync.constants import E621, R34, TABLE
from artrefsync.config import config
import logging
from artrefsync.ui.TagApp import AppTab, ImagViewerApp
from artrefsync.ui.tag_post_manager import TagPostManager

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class TabWrapper(AppTab):
    def init_ui(self, root):
        return ViewerTab(root)


# Prettier Tab
# Click once, Open, twice, close
class Side_bar(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.l_frame = ttk.Frame(self, padding= 5)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(0, weight=1)
        self.sep = ttk.Separator(self, orient="vertical")
        self.widgets: ttk.Frame = []
        self.buttons: list[ttk.Button] = []
        self.widget_index = {}

    def pack_widgets(self):
        self.l_frame.grid(column=0, row=0, sticky="ns")
        self.l_frame.grid_columnconfigure(0, minsize=75, weight=1)

        for i, button in enumerate(self.buttons):
            self.l_frame.grid_rowconfigure(i, minsize=85)
            button.grid(column=0, row=i, stick="nwes", pady=5)
            # button.config(height)
        self.sep.grid(column=1, row=0, sticky="ns")
        if len(self.widgets) > 0:
            self.widgets[0].grid(row=0, column=2, stick="ns")

    def add_widget(self, name, widget, image=None):
        if name not in self.widget_index:

            self.widget_index[name] = len(self.widget_index)
            button = ttk.Button(self.l_frame, text=name, bootstyle="dark", padding=5)
            button.bind("<Button-1>", self.toggle_widget)
            # self.button.bind()
            self.buttons.append(button)
            self.widgets.append(widget)

    def toggle_widget(self, event):
        name = event.widget["text"]
        index = self.widget_index[name]
        widget: ttk.Frame = self.widgets[index]
        if widget.grid_info():
            widget.grid_forget()
        else:
            for w in self.widgets:
                if w.grid_info():
                    w.grid_forget()
            widget.grid(row=0, column=2, sticky="ns")


class ViewerTab:
    def __init__(self, root: ImagViewerApp):
        self.packed = False
        self.root = root
        self.tab = root.viewer_tab
        self.tag_post_manager: TagPostManager = None
        self.current_frame = 0

        self.artists = {
            TABLE.E621: set(config[TABLE.E621][E621.ARTISTS]),
            TABLE.R34: set(config[TABLE.R34][R34.ARTISTS]),
        }
        self.init_widgets()
        self.set_icon_map(16)
        self.artist_set = SortedSet(set().union(*self.artists.values()))
        self.init_artists_tree()
        self.root.thread_caller.add(self.init_tag_post_manager, self.init_image_frame)
        self.filter_set = set()

    def init_widgets(self):
        logger.info("Initializing widgets")

        self.frame_top = ttk.Frame(self.tab)
        self.frame_bot = ttk.Frame(self.tab)
        self.combo = ttk.Combobox(self.frame_top)

        self.side_bar = Side_bar(self.frame_bot)

        # self.style = ttk.Style()
        # self.style.configure('Custom.Treeview', rowheight=15)

        self.artist_tree = ttk.Treeview(self.side_bar, columns=("Name",))
        self.image_tree = ttk.Treeview(self.side_bar, columns=("Name",),)
        self.gallery_tree = ttk.Treeview(self.frame_bot, columns=("Name",))

        self.side_bar.add_widget("Artists", self.artist_tree)
        self.side_bar.add_widget("Posts", self.image_tree)

        self.artist_tree.column("#0", width = 30, stretch=0, anchor='w')
        self.image_tree.column("#0", width = 30, stretch=0, anchor='w')
        self.gallery_tree.column("#0", stretch=True, anchor="center")

        self.on_tab_changed()
        # self.root.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def pack_frames(self):
        print("Packing")
        self.tab.rowconfigure(0, weight=0)
        self.tab.rowconfigure(1, weight=1)
        self.tab.columnconfigure(0, weight=1)
        self.frame_top.grid(row=0, column=0, sticky="we")
        self.frame_bot.grid(row=1, column=0, sticky="nswe")

        # 2nd level top -> (combobox),
        self.combo.grid(row=0, column=0)

        # 2nd level bot -> (left, mid, right)
        self.frame_bot.columnconfigure(0, weight=0)
        self.frame_bot.columnconfigure(1, weight=1)
        # self.frame_bot.columnconfigure(2, weight=1)
        self.frame_bot.rowconfigure(0, weight=1)
        self.side_bar.grid(row=0, column=0, sticky="ns")
        self.side_bar.pack_widgets()
        # # self.frame_left.grid(row=0, column=0, sticky='ns')
        # # self.frame_mid.grid(row=0, column=1, sticky='ns')
        # # self.frame_right.grid(row=0, column=2, sticky='nwse')
        self.gallery_tree.grid(row=0, column=1, sticky="nwse")

        # 3rd level, trees left->artists_tree, mid->image_tree, right -> image_label
        #self.artist_tree.pack(fill="both", expand=1)
        #self.image_tree.pack(side="left", fill="y")
        # self.image_tree_scroll.pack(side="right", fill="y")
        # self.image_label.pack(fill="both", expand=1)
        # self.image_label.pack(fill="both", expand=1)

    def tab_oppened(self):
        tab_id = self.root.notebook.select()
        tab_index = self.root.notebook.index(tab_id)
        print(f"Tab Index {tab_index} {type(tab_index)}")
        return tab_index == 1

    def on_tab_changed(self, event=None):
        # print(f"On Tab Changed {self.tab_oppened()} {self.root.notebook.select()}")
        # if self.tab_oppened():
        #     if not self.packed:
        self.pack_frames()

    # Note that init happens beffore
    def init_artists_tree(self):
        # self.image_tree.configure(yscrollcommand=self.image_tree_scroll.set)
        artists = self.artists
        atree = self.artist_tree
        aset = self.artist_set
        for table in [TABLE.E621, TABLE.R34]:
            atree.insert(
                "",
                "end",
                iid=table,
                image=self.icon_map[table],
                values=(table),
                open=True,
            )
            for artist in aset:
                if artist in artists[table]:
                    atree.insert(
                        table,
                        "end",
                        iid=artist,
                        values=(f"  │ {artist}",),
                        image=self.icon_map[table],
                    )
                        # values=(f"  {artist}",),

    def init_tag_post_manager(self):
        self.tag_post_manager = TagPostManager()

    def init_image_frame(self, _):
        self.image_set = SortedSet(self.tag_post_manager.post_set)
        for i in reversed(range(len(self.image_set))):
            val = self.image_set[i]
            self.image_tree.insert("", "end", iid=val, values=(val,))
        self.image_tree.bind("<<TreeviewSelect>>", self.update_label_image)
        self.artist_tree.bind("<<TreeviewSelect>>", self.update_label_image)
        self.gallery_tree.insert("", "end", iid="top", values=("top"))

    def update_filter(self, event):
        selection = self.artist_tree.selection()[0]
        if selection not in self.filter_set:
            self.filter_set.add(selection)

    def print_winfo_stats(self, widget: ttk.Frame):
        print(
            f"\n{'-' * 10}\nPrinting winget vars for {widget.__class__.__name__}  {widget=}"
        )
        funcs = [
            widget.winfo_geometry,
            widget.winfo_width,
            widget.winfo_height,
            widget.winfo_x,
            widget.winfo_y,
            widget.winfo_height,
            widget.winfo_rootx,
            widget.winfo_rooty,
            widget.winfo_vrootheight,
            widget.winfo_vrootwidth,
        ]
        for f in funcs:
            print(f"{f.__name__} {f()}")

    def update_label_image(self, event):
        selection = self.image_tree.selection()[0]
        frame_w = self.gallery_tree.winfo_width()
        frame_h = self.gallery_tree.winfo_height()
        image = self.get_photo_image(selection, frame_w, frame_h)

        self.gallery_tree.item("top", image=image)
        # self.gallery_tree.item("top", imageanchor='center')
        # self.gallery_tree.insert("", 0, iid=selection, image=image)

        # self.image_label.image = image
        # self.image_label.config(image=image)

    @lru_cache(maxsize=5)
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
