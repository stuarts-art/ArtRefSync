# Initial version taken from https://stackoverflow.com/a/48137257 by user foobar167.
# Majority of functionality has been modified, but i'm keeping this in here because the solution
# ---
# Updated class to work on gifs
# - stuart (@stuarts-art) 2026-04-07
# --
# Removed tiling method to improve performance on gifs and videos.
# - stuart (@stuarts-art) 2026-08-27

import logging
import time
import tkinter as tk

import ttkbootstrap as ttk
from PIL import Image, ImageTk

from artrefsync.config import get_config
from artrefsync.constants import BINDING, HOTKEY
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.frame_buffer import FrameBuffer
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)


class AutoScrollbar(ttk.Scrollbar):
    """A scrollbar that hides itself if it's not needed. Works only for grid geometry manager"""

    def set(self, first, last):
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, first, last)

    def pack(self, **kw):
        raise tk.TclError("Cannot use pack with the widget " + self.__class__.__name__)

    def place(self, **kw):
        raise tk.TclError("Cannot use place with the widget " + self.__class__.__name__)


class CopyDict(dict):
    def __init__(self, copy_from):
        self.copy_from = copy_from
        super().__init__()

    def __missing__(self, key):
        copied = self.copy_from[key].copy()
        self[key] = copied
        return copied


class CanvasImage:
    """Display and zoom image"""

    popups = []

    def __init__(self, placeholder, index_var, is_popup=False):
        logger.info("Canvas Image Init")
        self.last_run = time.time()
        self.is_popup = is_popup
        """Initialize the ImageFrame"""
        self.cancel_key = "GifViewerCancelKey"
        self.index_var: tk.IntVar = index_var
        self.after_next_frame_id = None
        self.path = None
        self.clear_canvas = False

        self.__delta = 1.3  # zoom magnitude
        self.scale = 1.0
        self.__filter = (
            Image.Resampling.LANCZOS
        )  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.__previous_state = 0  # previous state of the keyboard
        self.__imframe = ttk.Frame(placeholder)  # placeholder of the ImageFrame object
        hbar = AutoScrollbar(self.__imframe, orient="horizontal")
        vbar = AutoScrollbar(self.__imframe, orient="vertical")
        hbar.grid(row=1, column=0, sticky="we")
        vbar.grid(row=0, column=1, sticky="ns")
        self.canvas = ttk.Canvas(
            self.__imframe,
            highlightthickness=0,
            xscrollcommand=hbar.set,
            yscrollcommand=vbar.set,
        )
        self.canvas.grid(row=0, column=0, sticky="nswe")
        img = ImageTk.PhotoImage(Image.new("RGB", (100, 100), color="grey"))
        self.image = self.canvas.create_image(0, 0, image=img, anchor=tk.NW)
        self.canvas.image_tk = img

        hbar.configure(command=self.__scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.__scroll_y)
        # Bind events to the Canvas
        self.canvas.bind(
            "<Configure>", lambda event: self.__show_image()
        )  # canvas is resized
        self.canvas.bind(
            "<ButtonPress-1>", self.__move_from
        )  # remember canvas position

        if not is_popup:
            self.canvas.bind(
                "<ButtonPress-2>", self.__show_popup
            )  # remember canvas position
        self.canvas.bind(
            "<B1-Motion>", self.__move_to
        )  # move canvas to the new position
        self.canvas.bind(
            "<MouseWheel>", self.__wheel
        )  # zoom for Windows and MacOS, but not Linux
        self.canvas.bind(
            "<Button-5>", self.__wheel
        )  # zoom for Linux, wheel scroll down
        self.canvas.bind("<Button-4>", self.__wheel)  # zoom for Linux, wheel scroll up
        self.playing = ttk.BooleanVar(value=False)

        self.canvas.bind(
            "<Key>", lambda event: self.canvas.after_idle(self.__keystroke, event)
        )

        self.frames: FrameBuffer = FrameBuffer()
        self.__images = CopyDict(self.frames)
        self.container = None

    @property
    def index(self):
        return self.index_var.get()

    @index.setter
    def index(self, value):
        self.index_var.set(int(value))

    def load_media(self, path: str | None):
        self.scale = 1.0
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)
        if self.path == path:
            self.__show_image()
            return

        size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        self.frames.thumb_size = size
        if path is None:
            return

        if self.after_next_frame_id:
            self.__imframe.after_cancel(self.after_next_frame_id)
            self.after_next_frame_id = None
        self.frames.load_file(path)
        if len(self.frames) > 1:
            self.duration = self.frames.duration
        else:
            self.duration = None
        self.__images.clear()

        self.index = 0
        self.path = path  # path to the image, should be public for outer classes

        self.clear_canvas = True

        if len(self.frames) > 1:
            self.playing.set(True)
            self.show_next_frame(self.path)
        else:
            self.playing.set(False)
            self.__show_image()

    def cancel_next_frame(self):
        if self.after_next_frame_id is not None:
            self.__imframe.after_cancel(self.after_next_frame_id)
            self.after_next_frame_id = None
        self.cancel_show_image()

    def show_next_frame(self, path):
        self.cancel_next_frame()
        if path != self.path:
            return
        if self.duration is None:
            return

        if self.index >= len(self.frames):
            self.index = 0
        else:
            self.index += 1
            self.index %= len(self.frames)

        if self.index:
            self.after_next_frame_id = self.__imframe.after(
                self.duration, self.show_next_frame, path
            )
            self.__show_image()
        else:
            try:
                self.__show_image()
            finally:
                self.after_next_frame_id = self.__imframe.after(
                    self.duration, self.show_next_frame, path
                )

    def toggle_pause(self, toggle_on=None):
        """_summary_
        # Returns True if playing. False if paused.
        """
        playing = False
        if not self.duration:
            pass
        elif toggle_on is None:
            if self.after_next_frame_id:
                self.__imframe.after_cancel(self.after_next_frame_id)
                self.after_next_frame_id = None
            else:
                self.show_next_frame(self.path)
                playing = True
        elif toggle_on:
            if not self.after_next_frame_id:
                self.show_next_frame(self.path)
                playing = True
        else:
            if self.after_next_frame_id:
                self.__imframe.after_cancel(self.after_next_frame_id)
                self.after_next_frame_id = None
        self.playing.set(playing)
        self.__show_image()
        return playing

    def move_left(self):
        if self.duration is not None and len(self.frames) > 1:
            self.toggle_pause(toggle_on=False)
            self.index -= 1
            self.index %= len(self.frames)
            self.__show_image()

    def move_right(self):
        if self.duration is not None and len(self.frames) > 1:
            self.toggle_pause(toggle_on=False)
            self.index += 1
            self.index %= len(self.frames)
            self.__show_image()

    def redraw_figures(self):
        """Dummy function to redraw figures in the children classes"""

    def grid(self, **kw):
        """Put CanvasImage widget on the parent widget"""
        self.__imframe.grid(**kw)  # place CanvasImage widget on the grid
        self.__imframe.grid(sticky="nswe")  # make frame container sticky
        self.__imframe.rowconfigure(0, weight=1)  # make canvas expandable
        self.__imframe.columnconfigure(0, weight=1)

    def pack(self, **kw):
        """Exception: cannot use pack with this widget"""
        raise Exception("Cannot use pack with the widget " + self.__class__.__name__)

    def place(self, **kw):
        """Exception: cannot use place with this widget"""
        raise Exception("Cannot use place with the widget " + self.__class__.__name__)

    # noinspection PyUnusedLocal
    def __scroll_x(self, *args, **kwargs):
        """Scroll canvas horizontally and redraw the image"""
        self.canvas.xview(*args)  # scroll horizontally
        self.__show_image()  # redraw the image

    def __scroll_y(self, *args, **kwargs):
        """Scroll canvas vertically and redraw the image"""
        self.canvas.yview(*args)  # scroll vertically
        self.__show_image()  # redraw the image

    def __update_pyramid(self, index):
        if self.__pyramid is None:
            return
        if index >= len(self.frames):
            return
        if index not in self.__pyramid:
            if frame := self.frames[index]:
                self.__pyramid[index] = [frame.copy()]
            else:
                return
            w, h = self.__pyramid[index][-1].size
            while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
                w /= self.__reduction  # divide on reduction degree
                h /= self.__reduction  # divide on reduction degree
                self.__pyramid[index].append(
                    self.__pyramid[index][-1].resize((int(w), int(h)), self.__filter)
                )

    def update_container_size(self):
        self.container = self.canvas.create_rectangle(
            (
                0,
                0,
                self.imwidth * self.imscale,
                int(self.imheight * self.imscale),
            ),
            width=0,
        )
        self.canvas.lower(self.container)  # set image into background

    def __update_image(self, image):
        if not image:
            return
        frame_size = (
            self.__imframe.winfo_width() * self.scale,
            self.__imframe.winfo_height() * self.scale,
        )
        copy: Image.Image = image.copy()
        copy.thumbnail(frame_size)
        image_tk = ImageTk.PhotoImage(copy)
        x_offset = (frame_size[0] - copy.width) // 2
        y_offset = (frame_size[1] - copy.height) // 2

        self.canvas.itemconfigure(self.image, image=image_tk)
        self.canvas.image_tk = image_tk
        self.canvas.moveto(self.image, x=x_offset, y=y_offset)

    __show_image_cancel_key = "show_image"

    def cancel_show_image(self):
        thread_caller.cancel(self.__show_image_cancel_key)

    def __show_image(self):
        cancel_key = self.__show_image_cancel_key
        thread_caller.cancel(cancel_key)

        index = self.index % len(self.frames)
        thread_caller.add(
            self.frames.__getitem__,
            self.__update_image,
            cancel_key=cancel_key,
            after=None,
            i=index,
        )

    class Popup:
        def __init__(self, root, path=""):
            self.index_var = ttk.IntVar(value=0)
            self.window = ttk.Toplevel(event_binder[BINDING.APP_WIDGET])
            self.window.columnconfigure(0, weight=1)
            self.window.rowconfigure(0, weight=1)
            self.canvas = CanvasImage(
                self.window, index_var=self.index_var, is_popup=True
            )
            self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
            if path:
                self.canvas.load_media(path)

        def load_media(self, path):
            self.canvas.load_media(path)

    def __show_popup(self, event):
        # index_var = ttk.IntVar
        popup = self.Popup(event_binder[BINDING.APP_WIDGET], self.path)
        self.popups.append(popup)

        """Remember previous coordinates for scrolling with the mouse"""
        # self.canvas.scan_mark(event.x, event.y)

    def __move_from(self, event):
        """Remember previous coordinates for scrolling with the mouse"""
        self.canvas.scan_mark(event.x, event.y)

    def __move_to(self, event):
        """Drag (move) canvas to the new position"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.__show_image()  # zoom tile and show it on the canvas

    def outside(self, x, y):
        """Checks if the point (x,y) is outside the image area"""
        bbox = self.canvas.coords(self.container)  # get image area
        if (bbox[0] < x < bbox[2]) and (bbox[1] < y < bbox[3]):  # noqa: SIM103
            return False  # point (x,y) is inside the image area
        else:
            return True  # point (x,y) is outside the image area

    def __wheel(self, event):
        """Zoom with mouse wheel"""

        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down, smaller
            self.scale /= self.__delta
        if event.num == 4 or event.delta == 120:  # scroll up, bigger
            self.scale *= self.__delta
        self.__show_image()

    def __keystroke(self, event):
        """Scrolling with the keyboard.
        Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc."""
        ctrl_pressed = (event.state & 0x4) != 0
        shift_pressed = (event.state & 0x1) != 0
        keysym = event.keysym
        if keysym in config[HOTKEY.RIGHT_LIST]:
            if ctrl_pressed or shift_pressed:
                self.move_right()
            else:
                self.__scroll_x("scroll", 1, "unit", event=event)
        elif keysym in config[HOTKEY.LEFT_LIST]:
            if ctrl_pressed or shift_pressed:
                self.move_left()
            else:
                self.__scroll_x("scroll", -1, "unit", event=event)
        elif keysym in config[HOTKEY.UP_LIST]:
            self.__scroll_y("scroll", -1, "unit", event=event)
        elif keysym in config[HOTKEY.DOWN_LIST]:
            if ctrl_pressed or shift_pressed:
                self.toggle_pause()
            else:
                self.__scroll_y("scroll", 1, "unit", event=event)
        elif keysym in config[HOTKEY.ZOOM_OUT_LIST]:
            self.canvas.event_generate("<MouseWheel>", delta=-120)
        elif keysym in config[HOTKEY.ZOOM_IN_LIST]:
            self.canvas.event_generate("<MouseWheel>", delta=+120)
        elif self.is_popup:
            logger.debug(
                "KeyCode: %s, KeySym: %s, State: %s",
                event.keycode,
                event.keysym,
                event.state,
            )
            return ""
        elif keysym in config[HOTKEY.ZOOMED_PREV_LIST]:
            event_binder.after_idle(BINDING.ON_PREV_GALLERY_IMAGE)
        elif keysym in config[HOTKEY.ZOOMED_NEXT_LIST]:
            event_binder.after_idle(BINDING.ON_NEXT_GALLERY_IMAGE)
        elif keysym in config[HOTKEY.SWAP_LIST]:
            event_binder.after_idle(BINDING.ON_CLOSE_VIEWER)
            event_binder.after_idle(BINDING.ON_GALLERY_SHIFT_TAB)
        elif keysym in config[HOTKEY.OPEN_LIST]:
            event_binder.after_idle(BINDING.ON_CLOSE_VIEWER)
        else:
            logger.debug(
                "KeyCode: %s, KeySym: %s, State: %s",
                event.keycode,
                event.keysym,
                event.state,
            )
            return ""
        return "break"

    def crop(self, bbox, index):
        """Crop rectangle from the image and return it"""
        return self.__pyramid[index][0].crop(bbox)

    def destroy(self):
        """ImageFrame destructor"""
        for image in self.__images:
            image.close()
        self.canvas.destroy()
        self.__imframe.destroy()
