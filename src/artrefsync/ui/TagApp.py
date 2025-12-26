# import pywinstyles
import abc
import ttkbootstrap as ttk
import ttkbootstrap.style as style
import time

# import sv_ttk
from PIL import Image, ImageTk
import logging
from artrefsync.boards.board_handler import Post
from artrefsync.config import config
from artrefsync.ui.TkThreadCaller import TkThreadCaller
from ttkbootstrap import utility

from artrefsync.ui.tabs.ArtistTab import Artist_Tree
from artrefsync.ui.tabs.PostTab import Post_Tree
from artrefsync.ui.tag_post_manager import TagPostManager
from artrefsync.ui.widgets.ModernTopBar import ModernTopBar, RoundedIcon
from artrefsync.ui.widgets.PhotoLabel import PhotoImageGallery

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class AppTab(abc.ABC):
    @abc.abstractmethod
    def init_ui(self, root):
        pass


def main():
    app = ImagViewerApp()


class ImagViewerApp(ttk.Window):
    def __init__(self):
        logger.info("Starting App")
        self.tag_post_manager:TagPostManager = None

        super().__init__(themename="darkly", size=(1080, 1080))
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.bar = ModernTopBar(self)

        self.stime = time.time()
        # Init Window
        self.thread_caller = TkThreadCaller(self)
        ico = Image.open("resources/small_cat.png")
        photo = ImageTk.PhotoImage(ico)
        self.wm_iconphoto(False, photo)
        # self.menu = self.menus(self)

        self.bar.mid.columnconfigure(0, weight=0)
        self.bar.mid.columnconfigure(1, weight=4)
        self.bar.mid.rowconfigure(0, weight=1)


        self.side_bar_icons = ttk.Frame(self.bar.mid)
        self.right = ttk.Frame(self.bar.mid)

        self.side_bar_icons.grid(row=0, column=0, sticky="wns")
        self.right.grid(row=0, column=1, sticky="nsew")

        self.side_bar_icons.rowconfigure(3, weight=1)

        self.config_button = RoundedIcon(self.side_bar_icons, text="Config", size=(100,30))
        self.artists_button = RoundedIcon(self.side_bar_icons, text="Artists", size=(100,30))
        self.posts_button = RoundedIcon(self.side_bar_icons, text="Posts", size=(100,30))

        self.config_tab = ttk.Frame(self.side_bar_icons)
        self.artists_tree = Artist_Tree(self.side_bar_icons)
        self.post_tree = Post_Tree(self.side_bar_icons)
        
        self.config_button.grid(column=0, row=0, sticky='ew')
        self.artists_button.grid(column=0, row=1, sticky='ew')
        self.posts_button.grid(column=0, row=2, sticky='ew')

        self.config_tab.grid(column=0, row=3, sticky="nsew")
        self.artists_tree.grid(column=0, row=3, sticky="nsew")
        self.post_tree.grid(column=0, row=3, sticky="nsew")

        self.gallery = PhotoImageGallery(self.right)
        self.gallery.pack(fill="both", expand=True)
        self.filter_set = set()


        # self.thread_caller.add(self.import_viewer_tab, self.init_tab_ui)

        self.config_button.bind("<Button-1>", self.toggle_config)
        self.artists_button.bind("<Button-1>",self.toggle_artists)
        self.posts_button.bind("<Button-1>", self.toggle_posts)
        self.bar.side_bar_label_button.bind("<Button-1>", self.toggle_side_bar)
        self.artists_tree.bind("<<TreeviewSelect>>", self.query_by_artist)
        self.post_tree.bind("<<TreeviewSelect>>", self.add_image_to_gallery)

        self.thread_caller.add(self.import_config_tab, self.init_tab_ui)
        self.thread_caller.add(self.init_tag_post_manager, self.after_tag_post_manager)
        self.after(20,self.toggle_config)
        self.mainloop()

    def query_by_artist(self, e=None):

        self.filter_set = set()
        artist = self.artists_tree.selection()[0]
        if artist not in self.filter_set:
            self.filter_set.add(artist)
            print(f"Current FilterSet {self.filter_set}")
            self.post_tree.refresh(self.filter_set)
        
            self.reset_toggle()
            self.toggle_posts()
            
        

    def init_tag_post_manager(self):
        self.tag_post_manager = TagPostManager()
        logger.info("Tag Post Manager Initiated.")

    def after_tag_post_manager(self, event=None):
        self.post_tree.populate_tree(self.tag_post_manager)
    
    
    def reset_toggle(self, event=None):
        if len(self.config_button.grid_info()) == 0:
            self.config_button.grid(column=0, row=0, sticky='ew')

        if len(self.artists_button.grid_info()) == 0:
            self.artists_button.grid(column=0, row=1, sticky='ew')

        if len(self.posts_button.grid_info()) == 0:
            self.posts_button.grid(column=0, row=2, sticky='ew')

    def toggle_config(self, event=None):
        if len(self.artists_button.grid_info()) == 0:
            self.artists_button.grid(column=0, row=1, sticky='ew')
            self.posts_button.grid(column=0, row=2, sticky='ew')
        else:
            self.artists_button.grid_forget()
            self.posts_button.grid_forget()
            self.config_tab.lift()

    def toggle_artists(self, event=None):
        if len(self.config_button.grid_info()) == 0:
            self.config_button.grid(column=0, row=0, sticky='ew')
            self.posts_button.grid(column=0, row=2, sticky='ew')
        else:
            self.config_button.grid_forget()
            self.posts_button.grid_forget()
            self.artists_tree.lift()

    def toggle_posts(self, event= None):
        if len(self.config_button.grid_info()) == 0:
            self.artists_button.grid(column=0, row=1, sticky='ew')
            self.config_button.grid(column=0, row=0, sticky='ew')
        else:
            self.config_button.grid_forget()
            self.artists_button.grid_forget()
            self.post_tree.lift()

    def toggle_side_bar(self, event):

        # mid_info = self.side_bar_icons.pack_info()
        mid_info = self.side_bar_icons.grid_info()
        logger.info("Toggling side bar. Pack Info = %s", str(mid_info))

        if len(mid_info) != 0:
            logger.info("Forgetting = %s", str(mid_info))

            # self.paned_window.forget(self.side_bar_icons)
            # self.side_bar_icons.pack_forget()
            self.side_bar_icons.grid_remove()
            # self.sep.grid_remove()
            # self.left_side_bar.grid_remove()
        else:
            logger.info("Reattaching = %s", str(mid_info))
            # self.paned_window.insert(0, self.side_bar_icons)
            # self.side_bar_icons.pack_forget()
            # self.side_bar_icons.pack(side="left", fill="y")
            self.side_bar_icons.grid(row=0, column=0, sticky="ns")
            # self.sep.grid(row=0, column=1, sticky="ns")
            # self.left_side_bar.grid(row=0, column=2, sticky="nsw")
    
    def add_image_to_gallery(self, event):
        if not self.tag_post_manager:
            logger.warning("Warning, Tag Post Manager not initialized.")
            return

        selection = self.post_tree.selection()[0]
        index = self.post_tree.image_set.bisect_left(selection)
        print(index)
        start = min(len(self.post_tree.image_set)-1, index + 10)
        end = max(index - 10, 0)
        print(f"start: {start}, end: {end}")
        # for pid in islice:
        for i in range(start, end, -1):
            print(i)
            pid = self.post_tree.image_set[i]
            print(pid)
            post: Post = self.tag_post_manager.post_id[pid]
            self.gallery.add_image(post)
        # frame_w = self.post_tree.winfo_width()
        # frame_h = self.post_tree.winfo_height()
        # image = self.get_photo_image(selection, frame_w, frame_h)


        # self.gallery_tree.item("top", image=image)

    def menus(self, root):
        self.menu = ttk.Menu(root)
        self.filemenu = ttk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=self.filemenu)
        root.config(menu=self.menu)
        self.menu.add

    def import_config_tab(self):
        import artrefsync.ui.tabs.ConfigTab as configTab

        config_wrapper = configTab.TabWrapper()
        return config_wrapper

    def import_viewer_tab(self):
        import artrefsync.ui.tabs.ViewerTab as viewerTab

        return viewerTab.TabWrapper()

    def init_tab_ui(self, tab: AppTab):
        logger.info("Init Tab UI %s", tab.__module__.split(".")[-1])
        tab.init_ui(self)


if __name__ == "__main__":
    main()
