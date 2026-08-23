# Taken from https://stackoverflow.com/a/48137257 by user foobar167.
# Only slight modification made was to change Image.ANTIALIAS to the new Image.LAZCOS
# ---
# Updated class to work on gifs
# - stuart (@stuarts-art) 2026-04-07

import logging
import math
import time
import tkinter as tk

import ttkbootstrap as ttk
from PIL import Image, ImageTk

from artrefsync.config import get_config
from artrefsync.constants import BINDING, HOTKEY
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.frame_buffer import FrameBuffer

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

    def __init__(self, placeholder, index_var):
        logger.info("Canvas Image Init")
        self.last_run = time.time()
        """Initialize the ImageFrame"""
        self.cancel_key = "GifViewerCancelKey"
        self.index_var: tk.IntVar = index_var
        self.after_next_frame_id = None
        self.path = None
        self.__pyramid = None
        self.clear_canvas = False

        self.imscale = 1.0  # scale for the canvas image zoom, public for outer classes
        self.__delta = 1.3  # zoom magnitude
        self.__filter = (
            Image.Resampling.LANCZOS
        )  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.__previous_state = 0  # previous state of the keyboard
        # Create ImageFrame in placeholder widget
        self.__imframe = ttk.Frame(placeholder)  # placeholder of the ImageFrame object
        # Vertical and horizontal scrollbars for canvas
        hbar = AutoScrollbar(self.__imframe, orient="horizontal")
        vbar = AutoScrollbar(self.__imframe, orient="vertical")
        hbar.grid(row=1, column=0, sticky="we")
        vbar.grid(row=0, column=1, sticky="ns")
        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = ttk.Canvas(
            self.__imframe,
            highlightthickness=0,
            xscrollcommand=hbar.set,
            yscrollcommand=vbar.set,
        )
        self.canvas.grid(row=0, column=0, sticky="nswe")
        # self.canvas.update_idletasks()
        hbar.configure(command=self.__scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.__scroll_y)
        # Bind events to the Canvas
        self.canvas.bind(
            "<Configure>", lambda event: self.__show_image()
        )  # canvas is resized
        self.canvas.bind(
            "<ButtonPress-1>", self.__move_from
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
        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.playing = ttk.BooleanVar(value=False)

        self.canvas.bind(
            "<Key>", lambda event: self.canvas.after_idle(self.__keystroke, event)
        )

        self.frames = FrameBuffer()
        self.__images = CopyDict(self.frames)
        self.container = None

    @property
    def index(self):
        return self.index_var.get()

    @index.setter
    def index(self, value):
        self.index_var.set(int(value))

    def load_media(self, path: str | None):
        if self.path == path:
            self.canvas.yview_moveto(0)
            self.canvas.xview_moveto(0)
            self.__show_image()
            return

        self.imscale = 1.0
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)
        if path is None:
            return
        if self.path == path:
            self.__show_image()
            self.toggle_pause(toggle_on=True)
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
        self.update_frame_size()
        self.__scale = self.imscale * self.__ratio  # image pyramide scale
        self.__reduction = 2  # reduction degree of image pyramid
        self.__pyramid = {}
        self.__curr_img = 0  # current image from the pyramid
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

        if self.index in self.__pyramid:
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
        for i in [1, 2]:
            next_index = (self.index + i) % len(self.frames)
            if next_index not in self.frames:
                self.__imframe.after_idle(self.frames.__getitem__, next_index)

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

    def update_frame_size(self):
        index = 0
        if not self.frames:
            logger.info("NO FRAME SET")
            return

        self.imwidth, self.imheight = self.frames[0].size  # public for outer classes
        frame_width = self.__imframe.master.winfo_width()
        frame_height = self.__imframe.master.winfo_height()
        self.imscale = min(frame_width / self.imwidth, frame_height / self.imheight)
        self.__min_side = min(self.imwidth, self.imheight)  # get the smaller image side
        self.__ratio = 1.0

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
        raise Exception(
            "Cannot use pack with the widget " + self.__class__.__name__
        )  # noqa: TRY002

    def place(self, **kw):
        """Exception: cannot use place with this widget"""
        raise Exception(
            "Cannot use place with the widget " + self.__class__.__name__
        )  # noqa: TRY002

    # noinspection PyUnusedLocal
    def __scroll_x(self, *args, **kwargs):
        """Scroll canvas horizontally and redraw the image"""
        self.canvas.xview(*args)  # scroll horizontally
        self.__show_image()  # redraw the image

    # noinspection PyUnusedLocal
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
            # self.update_container_size()

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

    def __show_image(self):
        index = self.index % len(self.frames)

        self.__update_pyramid(index)
        if self.__pyramid is None:
            return

        """Show image on the Canvas. Implements correct image zoom almost like in Google Maps"""
        if self.clear_canvas:
            self.update_container_size()

        box_image = self.canvas.coords(self.container)  # get image area
        if not box_image:
            return
        box_canvas = (
            self.canvas.canvasx(0),  # get visible area of the canvas
            self.canvas.canvasy(0),
            self.canvas.canvasx(self.canvas.winfo_width()),
            self.canvas.canvasy(self.canvas.winfo_height()),
        )
        box_img_int = tuple(
            map(int, box_image)
        )  # convert to integer or it will not work properly
        # Get scroll region box
        box_scroll = [
            min(box_img_int[0], box_canvas[0]),
            min(box_img_int[1], box_canvas[1]),
            max(box_img_int[2], box_canvas[2]),
            max(box_img_int[3], box_canvas[3]),
        ]
        # Horizontal part of the image is in the visible area
        if box_scroll[0] == box_canvas[0] and box_scroll[2] == box_canvas[2]:
            box_scroll[0] = box_img_int[0]
            box_scroll[2] = box_img_int[2]
        # Vertical part of the image is in the visible area
        if box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
            box_scroll[1] = box_img_int[1]
            box_scroll[3] = box_img_int[3]
        # Convert scroll region to tuple and to integer
        self.canvas.configure(
            scrollregion=tuple(map(int, box_scroll))
        )  # set scroll region
        x1 = max(
            box_canvas[0] - box_image[0], 0
        )  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(box_canvas[1] - box_image[1], 0)
        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
        if (
            int(x2 - x1) > 0 and int(y2 - y1) > 0
        ):  # show image if it in the visible area
            image: ImageTk.PhotoImage = self.frames[index]
            image = image.crop(  # crop current img from pyramid
                (
                    int(x1 / self.__scale),
                    int(y1 / self.__scale),
                    int(x2 / self.__scale),
                    int(y2 / self.__scale),
                )
            )

            imagetk = ImageTk.PhotoImage(
                image.resize((int(x2 - x1), int(y2 - y1)), self.__filter)
            )

            imageid = self.canvas.create_image(
                max(box_canvas[0], box_img_int[0]),
                max(box_canvas[1], box_img_int[1]),
                anchor="nw",
                image=imagetk,
            )
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = (
                imagetk  # keep an extra reference to prevent garbage-collection
            )
            if self.clear_canvas:
                canvas_objs = self.canvas.find_all()
                self.canvas.delete(*canvas_objs[3:])
                self.clear_canvas = False

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
        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y = self.canvas.canvasy(event.y)
        # if self.outside(x, y): return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down, smaller
            if round(self.__min_side * self.imscale) < 30:
                return  # image is less than 30 pixels
            self.imscale /= self.__delta
            scale /= self.__delta
        if event.num == 4 or event.delta == 120:  # scroll up, bigger
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1
            if i < self.imscale:
                return  # 1 pixel is bigger than the visible area
            self.imscale *= self.__delta
            scale *= self.__delta
        # Take appropriate image from the pyramid
        k = self.imscale * self.__ratio  # temporary coefficient
        self.__curr_img = min(
            (-1) * int(math.log(k, self.__reduction)),
            len(self.__pyramid[self.index]) - 1,
        )
        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img))
        self.canvas.scale("all", x, y, scale, scale)  # rescale all objects
        # Redraw some figures before showing image on the screen
        self.redraw_figures()  # method for child classes
        self.__show_image()

    def __keystroke(self, event):
        """Scrolling with the keyboard.
        Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc."""
        ctrl_pressed = (event.state & 0x4) != 0
        keysym = event.keysym
        if keysym in config[HOTKEY.RIGHT_LIST]:
            if ctrl_pressed:
                self.move_right()
            else:
                self.__scroll_x("scroll", 1, "unit", event=event)
        elif keysym in config[HOTKEY.LEFT_LIST]:
            if ctrl_pressed:
                self.move_left()
            else:
                self.__scroll_x("scroll", -1, "unit", event=event)
        elif keysym in config[HOTKEY.UP_LIST]:
            self.__scroll_y("scroll", -1, "unit", event=event)
        elif keysym in config[HOTKEY.DOWN_LIST]:
            if ctrl_pressed:
                self.toggle_pause()
            else:
                self.__scroll_y("scroll", 1, "unit", event=event)
        elif keysym in config[HOTKEY.ZOOM_OUT_LIST]:
            self.canvas.event_generate("<MouseWheel>", delta=-120)
        elif keysym in config[HOTKEY.ZOOM_IN_LIST]:
            self.canvas.event_generate("<MouseWheel>", delta=+120)

        elif keysym in config[HOTKEY.ZOOMED_PREV_LIST]:
            event_binder.event_generate(BINDING.ON_PREV_GALLERY_IMAGE)
        elif keysym in config[HOTKEY.ZOOMED_NEXT_LIST]:
            event_binder.event_generate(BINDING.ON_NEXT_GALLERY_IMAGE)
        elif keysym in ["Tab"]:
            event_binder.event_generate(BINDING.ON_CLOSE_VIEWER)
            event_binder.event_generate(BINDING.ON_GALLERY_SHIFT_TAB)
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
        for pyramid in self.__pyramid.values():
            (i.close for i in pyramid)  # close all pyramid images
        del self.__pyramid  # delete pyramid variable
        self.canvas.destroy()
        self.__imframe.destroy()
