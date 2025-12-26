# import ttkbootstrap.
import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.scrolled import ScrolledFrame
from PIL import Image, ImageTk, ImageDraw
import functools
from artrefsync.boards.board_handler import Post
from artrefsync.constants import BOARD, E621, TABLE
from artrefsync.stores.eagle_storage import eagle_handler
from artrefsync.ui.tag_post_manager import TagPostManager
from ctypes import windll
import win32api
from screeninfo  import get_monitors
from artrefsync.config import config
import logging

from artrefsync.ui.widgets.ModernTopBar import RoundedIcon

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


@functools.lru_cache
def getPhotoThumbnail(file: str, height=540, width = 1080) -> ImageTk.PhotoImage:
    print("Cache-Miss, Getting Thumbnail")
    image = getPilImage(file).copy()

    if height or width:
        if not width:
            width = height * 2
        if not height:
            height = width // 2
        image.thumbnail((width, height))



    image.putalpha(getrounded_rect(image.width, image.height, 15))

    return ImageTk.PhotoImage(image=image)


@functools.lru_cache
def getPilImage(file: str):
    print("Cache-Miss, Getting Thumbnail")
    # return Image.open(file).convert("rgb")
    return Image.open(file)


@functools.lru_cache
def getrounded_rect(width, height, radius) -> Image.Image:
    # image = Image.new(mode='RGBA', size=(width, height), color=(0,0,0,0))
    scale = 4
    image = Image.new(mode="L", size=(width * scale, height * scale))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, width * scale, height * scale),
        fill="white",
        radius=radius * scale,
        width=4,
        outline="grey",
    )
    image.thumbnail((width, height))
    return image


def get_round_colored_rect(width, height, radius, fill="white") -> Image.Image:
    # image = Image.new(mode='RGBA', size=(width, height), color=(0,0,0,0))

    scale = 8
    image = Image.new(mode="RGBA", size=(width * scale, height * scale))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, width * scale, height * scale),
        fill=fill,
        radius=radius * scale,
        width=1,
        outline=fill,
    )
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    return image


class PhotoLabel(ttk.Label):
    def __init__(self, root, file, height:int|None=540, width:int|None = 1080):
        self.root = root
        photo = getPhotoThumbnail(file, height, width)
        self.file = file
        super().__init__(
            root, image=photo, padding=0, takefocus=True, bootstyle="primary"
        )
        self.image = photo
        # self.config(image=photo, height=photo.height, width=photo.height)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.bind("<FocusIn>", self.on_focus_in)
        self.bind("<FocusOut>", self.on_focus_out)
        self.bind("<Button-1>", self.set_focus)
        self.bind("<Double-Button-1>", lambda _:self.show())


    def on_focus_in(self, event):
        widget: ttk.Label = event.widget
        print(widget.winfo_vrooty())
        print(widget.winfo_y())
        event.widget.configure(bootstyle="inverse-warning")
        self.move_to_widget(widget)

    def move_to_widget(self, widget: ttk.Label):
        if not isinstance(widget, ttk.Label):
            return

        row = widget.master
        row_y = row.winfo_y()
        row_h = row.winfo_height()
        row_w = row.winfo_width()

        frame = row.master
        scroll = frame.vscroll.get()
        frame_height = frame.winfo_height()
        frame_width = frame.winfo_width()
        screen_height = frame.winfo_toplevel().winfo_height()

        scroll_top = scroll[0] * frame_height
        scroll_bot = scroll[1] * frame_height

        print(f"\n{'-' * 10}\n{widget.file}:")
        for v in [
            "row_y",
            "row_h",
            "row_w",
            "frame_height",
            "frame_width",
            "screen_height",
            "scroll_top",
            "scroll_bot",
        ]:
            print(f" - {v}: {locals()[v]}")

        if row_y < scroll_top or (row_y + screen_height - row_h) > scroll_bot:
            frame.yview_moveto(row_y / frame_height)

    def on_focus_out(self, event):
        event.widget.configure(bootstyle="primary")

    def set_focus(self, event):
        event.widget.focus_set()

    def resize(self, height=None):
        print("Resize Received")
        photo = getPhotoThumbnail(self.file, height)
        print(f"{photo.height()} {photo.width()}")
        self.configure(image=photo)
        self.image = photo

    # def show(self):
    #     print(f"Binding call for {self.file}")
    #     getPilImage(self.file).show()
    def show(self):
        print(f"Binding call for {self.file}")
        top_level = self.winfo_toplevel()
        width = top_level.winfo_width()
        height = top_level.winfo_height()

        # top_level = ttk.Toplevel(self.root.root)
        top_level_label = PhotoLabel(self.winfo_toplevel(), self.file, width, height)


        top_level_label.grid(row=0, column=0, sticky="nswe")
        # close_label.grid(row=0, column=1)
        top_level_label.bind("<Button-3>", lambda e: e.widget.destroy())
        # top_level.overrideredirect(True)

        




    @property
    def width(self):
        return self.image.width()

    @property
    def height(self):
        return self.image.width()


class PhotoImageRow(ttk.Frame):
    def __init__(self, root, max_row_width, max_height):
        self.root=root
        super().__init__(root)
        self.max_row_width = max_row_width
        self.max_height = max_height
        self.photos = []
        self.curr_width = 0
        self.curr_height = max_height
        root.bind("<Configure>", self.copy_width)
    
    def copy_width(self, event):
        self.max_row_width = event.widget.winfo_width()

        
        # self.bind("<Button-2>", self.open_if_image)

    def add_fixed_photo(self, file: str, side: str = "left"):
        photo = PhotoLabel(self, file, self.max_height)
        self.photos.append(photo)
        self.curr_width += photo.width
        # if self.curr_width > self.max_row_width:

        #     new_height = self.curr_height / self.curr_width * self.max_row_width
        #     print(new_height)
        #     self.curr_width = 0
        #     for p in self.photos:
        #         p.resize(new_height)
        #         self.curr_width += p.width
        #     self.curr_height = new_height
            # self.curr_width = self.max_row_width
        # photo.pack(side=side, padx=5, pady=5, anchor="center")
        photo.pack(side=side, padx=5, pady=5, anchor="center")
        return photo

    def add_photo(self, file: str, side: str = "left"):
        photo = PhotoLabel(self, file, self.curr_height)
        self.photos.append(photo)
        self.curr_width += photo.width
        if self.curr_width > self.max_row_width:
            new_height = self.curr_height / self.curr_width * self.max_row_width
            print(new_height)
            self.curr_width = 0
            for p in self.photos:
                p.resize(new_height)
                self.curr_width += p.width
            self.curr_height = new_height
            # self.curr_width = self.max_row_width
        photo.pack(side=side, padx=5, pady=5)
        return photo
        # photo.grid()

    def row_full(self) -> bool:
        return self.max_row_width<= self.curr_width

    def open_if_image(self, event) -> bool:
        w = event.widget()
        if isinstance(w, PhotoLabel):
            w.show()

class PhotoImageGallery(ScrolledFrame):

    def __init__(self, root):
        self.root = root
        super().__init__(root, bootstyle=("round"), autohide=True)
        self.id_set = set()

        self.width = 1080
        self.height = 1080
        self.width_offset = 20
        self.frame_height = 540
        self.rows: list[PhotoImageRow] = []
        self.add_new_row()
        self.root.bind("<Configure>", self.squish)
    
    def squish(self, event):
        for row in self.rows:
            row.max_row_width = self.winfo_width()
        


        
        
    def add_new_row(self, at_end=True):
        # self.frame.pack(side="top", expand=True, fill="both")
        self.rowconfigure(len(self.rows), weight=1)
        # new_row = PhotoImageRow(self, 1080, 540)
        new_row = PhotoImageRow(self, self.width * 3 // 4, 540)
        if at_end:
            new_row.grid(row=len(self.rows), column=0, sticky="we")
            self.rows.append(new_row)
        else:
            for i in reversed(range(len(self.rows))):
                self.rows[i].max_row_width = self.width
                self.rows[i].grid(row=i + 1, column=0)
            self.rows.insert(0, new_row)
            new_row.grid(row=0, column=0)
        return new_row

    def add_image(self, post:Post, at_end=True):
        if post.id in self.id_set:
            return
        self.id_set.add(post.id)

        file_name = post.file
        if file_name.endswith("webm"):
            return False

        if at_end:
            row = self.rows[-1]
            if row.row_full():
                row = self.add_new_row(at_end)
        elif not at_end:
            row = self.rows[0]
            if row.row_full():
                row = self.add_new_row(at_end)
        # photo = row.add_fixed_photo(file_name)
        photo = row.add_photo(file_name)
        photo.move_to_widget(self.root.focus_get())
        return True


class PhotoDemo:
    def __init__(self):

        self.root = ttk.Window(themename="darkly", size=(1080, 1400))
        self.gallery = PhotoImageGallery(self.root)
        self.gallery.pack(fill="both", expand=True)
        # self.snapped = False
        self.posts = eagle_handler.get_posts(BOARD.E621, config[TABLE.E621][E621.ARTISTS][10])
        self.post_keys = sorted(self.posts.keys(), reverse=True)
        self.postidx = 0

        self.root.bind("<Button-4>", lambda e: self.add_image(True))
        self.root.bind("<Button-5>", lambda e: self.add_image(False))

    def add_image(self, at_end = False):
        image_added = False
        while(not image_added):
            post = self.posts[self.post_keys[self.postidx]]
            image_added = self.gallery.add_image(post, at_end)
            self.postidx += 1
        
if __name__ == "__main__":
    demo = PhotoDemo()
    demo.root.mainloop()

