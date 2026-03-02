# import ttkbootstrap.
import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.scrolled import ScrolledText
from PIL import Image, ImageTk, ImageDraw
import functools
from ctypes import windll
import win32api
from screeninfo import get_monitors
from artrefsync.config import config
import logging
from artrefsync.ui.widgets.ModernTopBar import RoundedIcon

from artrefsync.boards.board_handler import Post
from artrefsync.constants import BOARD, E621, TABLE
from artrefsync.stores.eagle_storage import EagleHandler

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


@functools.lru_cache
def getPhotoThumbnail(file: str, height=540, width=1080) -> ImageTk.PhotoImage:
    logger.info("Cache-Miss, Getting Thumbnail")
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
    logger.info("Cache-Miss, Getting Thumbnail")
    # return Image.open(file).convert("rgb")
    image = Image.open(file)
    image.thumbnail((720, 720))
    return image


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


class PhotoFrame(ttk.Frame):
    def __init__(
        self, root, file, height: int | None = 540, width: int | None = 1080, **kwargs
    ):
        super().__init__(root, style="dark.TFrame")
        self.file = file
        self.photo = getPhotoThumbnail(file, height, width)
        self.label = ttk.Label(
            self,
            image=self.photo,
            padding=0,
            style="custom.TLabel",
            takefocus=True,
            **kwargs,
        )
        self.last_height = height
        self.winfo_name()

        self.label.pack(expand=True, fill="both")
        # self.label = ttk.Label(self, image=self.photo, **kwargs)
        # self.label.pack()
        self.is_toggled_on = True

        self.label.bind("<FocusIn>", self.on_focus_in)
        self.label.bind("<FocusOut>", self.on_focus_out)
        self.label.bind("<Button-1>", self.set_focus)
        self.bind("<Button-2>", lambda e: self.toggle_state())
        self.label.bind("<Double-Button-1>", lambda _: self.show())

    def update_image(self, file):
        photo = getPhotoThumbnail(file, self.last_height, self.last_width)
        self.configure(image=photo)
        self.photo = photo

    def toggle_state(self, on=None):
        # print(f"{self.winfo_width()}")
        # print(f"{self.winfo_height()}")
        # print(f"on = {on}\nself on = {self.is_toggled_on}")
        if on is None:
            on = not self.is_toggled_on
        # print(f"on = {on}\nself on = {self.is_toggled_on}")

        if on and not self.is_toggled_on:
            # print("Toggling on")
            self.label.configure(image=self.photo)
            self.label.pack()
            # self.pack_propagate=True
            # self.grid_propagate=True
            self.is_toggled_on = True

        elif not on and self.is_toggled_on:
            print("Toggling off")
            print(self.__dict__)
            print(f"{self.winfo_width()}")
            print(f"{self.winfo_height()}")
            # self.pack_propagate=False
            # self.grid_propagate=False
            # self.label.pack_propagate=False
            # self.label.grid_propagate=False
            self.label.configure(
                image="",
                text=" ",
            )
            # self.label.place(height=200, width=200)
            self.label.place(height=1, width=1)
            # self.configure(width = 200, height=200)
            self.update()
            print(f"{self.winfo_width()}")
            print(f"{self.winfo_height()}")
            self.is_toggled_on = False

    def on_focus_in(self, event):
        widget: ttk.Label = event.widget
        event.widget.configure(bootstyle="inverse-warning")
        self.move_to_widget(widget)

    def move_to_widget(self, widget: ttk.Label):
        if not isinstance(widget, ttk.Label):
            return
        name = widget.master.winfo_name()
        scrolledtext = widget.master.master
        text = scrolledtext.text
        indexes = text.dump("1.0", "end", window=True)
        index_map = {}
        for index in indexes:
            logger.info(index)
            index_map[index[1].split(".")[-1]] = index[2]
        logger.info(index_map)
        text.see(index_map[name])

    def on_focus_out(self, event):
        event.widget.configure(bootstyle="primary")

    def set_focus(self, event):
        event.widget.focus_set()

    def resize(self, height=None):
        height = (height // 100) * 100

        if height != self.last_height:
            self.last_height = height
            logger.info("Resize Received")
            photo = getPhotoThumbnail(self.file, height)
            logger.info(f"New Thumbnail Size: {photo.height()} {photo.width()}")
            self.label.configure(image=photo)
            self.photo = photo

    def show(self):
        logger.info(f"Binding call for {self.file}")
        top_level = self.winfo_toplevel()
        width = top_level.winfo_width()
        height = top_level.winfo_height()

        # top_level = ttk.Toplevel(self.root.root)
        top_level_label = PhotoLabel(self.winfo_toplevel(), self.file, width, height)

        # top_level_label.grid(row=0, column=0, sticky="nswe")
        top_level_label.pack(fill="both")
        # close_label.grid(row=0, column=1)
        top_level_label.bind("<Button-3>", lambda e: e.widget.destroy())
        # top_level.overrideredirect(True)

    @property
    def width(self):
        return self.photo.width()

    @property
    def height(self):
        return self.photo.width()


class PhotoLabel(ttk.Label):
    def __init__(
        self, root, file, height: int | None = 540, width: int | None = 1080, **kwargs
    ):
        self.root = root
        if file:
            photo = getPhotoThumbnail(file, height, width)
        else:
            photo = None
        self.file = file
        super().__init__(
            root, image=photo, padding=0, takefocus=True, bootstyle="primary", **kwargs
        )
        self.photo: ImageTk.PhotoImage = photo
        self.last_height = height
        self.last_width = height
        # self.config(image=photo, height=photo.height, width=photo.height)
        self.pack_propagate(False)
        self.grid_propagate(False)
        # self.bind("<FocusIn>", self.on_focus_in)
        # self.bind("<FocusOut>", self.on_focus_out)
        # self.bind("<Button-1>", self.set_focus)
        # self.bind("<Button-2>", lambda e: self.toggle_state())
        # self.bind("<Double-Button-1>", lambda _:self.show())
        self.is_toggled_on = True

    def update_image(self, file):
        photo = getPhotoThumbnail(file, self.last_height, self.last_width)
        self.configure(image=photo)
        self.photo = photo

    def on_focus_in(self, event):
        widget: ttk.Label = event.widget
        event.widget.configure(bootstyle="inverse-warning")
        self.move_to_widget(widget)

    def move_to_widget(self, widget: ttk.Label):
        if not isinstance(widget, ttk.Label):
            return
        name = widget.winfo_name()
        scrolledtext = widget.master
        text = scrolledtext.text
        indexes = text.dump("1.0", "end", window=True)
        index_map = {}
        for index in indexes:
            logger.debug(index)
            index_map[index[1].split(".")[-1]] = index[2]
        logger.debug(index_map)
        text.see(index_map[name])

    def on_focus_out(self, event):
        event.widget.configure(bootstyle="primary")

    def set_focus(self, event):
        event.widget.focus_set()

    def resize(self, height=None):
        height = (height // 100) * 100

        if height != self.last_height:
            self.last_height = height
            logger.info("Resize Received")
            photo = getPhotoThumbnail(self.file, height)
            logger.info(f"New Thumbnail Size: {photo.height()} {photo.width()}")
            self.configure(image=photo)
            self.photo = photo

    def show(self):
        logger.info(f"Binding call for {self.file}")
        top_level = self.winfo_toplevel()
        width = top_level.winfo_width()
        height = top_level.winfo_height()

        # top_level = ttk.Toplevel(self.root.root)
        top_level_label = PhotoLabel(self.winfo_toplevel(), self.file, width, height)

        # top_level_label.grid(row=0, column=0, sticky="nswe")
        top_level_label.pack(fill="both")
        # close_label.grid(row=0, column=1)
        top_level_label.bind("<Button-3>", lambda e: e.widget.destroy())
        # top_level.overrideredirect(True)

    @property
    def width(self):
        return self.photo.width()

    @property
    def height(self):
        return self.photo.width()


class PhotoImageRow(ttk.Frame):
    def __init__(self, root, max_row_width, max_height):
        self.root = root
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
        photo.pack(side=side, padx=5, pady=5, anchor="center")
        return photo

    def add_photo(self, file: str, side: str = "left"):
        photo = PhotoLabel(self, file, self.curr_height)
        self.photos.append(photo)
        self.curr_width += photo.width
        if self.curr_width > self.max_row_width:
            new_height = self.curr_height / self.curr_width * self.max_row_width
            self.curr_width = 0
            for p in self.photos:
                p.resize(new_height)
                self.curr_width += p.width
            self.curr_height = new_height
        photo.pack(side=side, padx=5, pady=5)
        return photo

    def destroy(self):
        for photo in self.photos:
            photo.destroy()

    def row_full(self) -> bool:
        return self.max_row_width <= self.curr_width

    def open_if_image(self, event) -> bool:
        w = event.widget()
        if isinstance(w, PhotoLabel):
            w.show()


# class PhotoImageGallery(ScrolledFrame):
class PhotoImageGallery(ttk.Frame):
    def __init__(self, root):
        self.root = root
        # super().__init__(root, bootstyle=("round"), autohide=True)
        super().__init__(root)
        colors = ttk.Style().colors
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.frame_height = 540
        self.text_widget = ScrolledText(self)
        self.text_widget.text.config(background=colors.dark)
        self.text_widget.grid(column=0, row=0, sticky="nsew")
        self.text_widget.text.config(state="disabled")

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

    def add_images(self, post_ids):
        self.post_ids = post_ids
        self.curr_index = 0
        self.target_index = 10
        self.after(10, self.load_next_image)

    def load_next_image(self):
        if self.curr_index >= self.target_index:
            logger.info("Stopping Loading Images")

        self.add_image()
        ttk.Text()

    def bind_scroll(self, event):
        delta = 0
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-1 * (event.delta / 120))

        first, _ = self.text_widget.vbar.get()
        fraction = (delta / 100) + first
        self.text_widget.yview_moveto(fraction)
        # self.text_widget.yview_scroll(delta, "units")

    def add_image(self, post: Post, at_end=True):
        file_name = post.file_link
        if file_name.endswith("webm"):
            return False

        photoframe = PhotoFrame(self.text_widget, file_name, self.frame_height)
        l = photoframe
        # l = PhotoLabel(self.text_widget, file_name, self.frame_height)
        bindtags = list(l.bindtags())
        bindtags.insert(1, self.text_widget)
        l.bindtags(bindtags)

        # # photo_image = l.image
        # # l.image

        l.label.bind("<MouseWheel>", self.bind_scroll)

        side = tk.END if at_end else "1.0"
        window_create_output = self.text_widget.window_create(
            side, window=l, padx=10, pady=10
        )
        print(f"Window create output: {window_create_output}")
        print(self.text_widget.text.window_names())

        if not at_end:
            side.lower()
        return l

    def set_tags(self, tags: set[str]):
        self.tags = tags