# Taken from https://stackoverflow.com/a/48137257 by user foobar167.
# Only slight modification made was to change Image.ANTIALIAS to the new Image.LAZCOS
# ---
# Updated class to work on gifs
# - stuart (@stuarts-art) 2026-04-07

import logging
import math
import tkinter as tk
import warnings
from tkinter import ttk

from PIL import Image, ImageTk

from artrefsync.config import config
from artrefsync.utils.image_utils import ImageUtils

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class AutoScrollbar(ttk.Scrollbar):
    """A scrollbar that hides itself if it's not needed. Works only for grid geometry manager"""

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError("Cannot use pack with the widget " + self.__class__.__name__)

    def place(self, **kw):
        raise tk.TclError("Cannot use place with the widget " + self.__class__.__name__)


class CanvasImage:
    """Display and zoom image"""

    def toggle_pause(self, toggle_on=None):
        if not self.duration:
            return
        if toggle_on is None:
            if self.next_job:
                self.__imframe.after_cancel(self.next_job)
                self.next_job = None
            else:
                self.next(self.path)
        elif toggle_on:
            if not self.next_job:
                self.next(self.path)
        else:
            if self.next_job:
                self.__imframe.after_cancel(self.next_job)
                self.next_job = None

    def move_left(self):
        if self.duration is not None and len(self.__images) > 1:
            self.toggle_pause(toggle_on=False)
            self.index -= 1
            self.index %= len(self.__images)
            self.__show_image()

    def move_right(self):
        if self.duration is not None and len(self.__images) > 1:
            self.toggle_pause(toggle_on=False)
            self.index += 1
            self.index %= len(self.__images)
            self.__show_image()

    @property
    def index(self):
        return self.index_var.get()

    @index.setter
    def index(self, value):
        self.index_var.set(value)

    def __init__(self, placeholder, index_var):
        """Initialize the ImageFrame"""
        self.index_var: tk.IntVar = index_var
        self.next_job = None
        self.path = None
        self.__pyramid = None

        self.imscale = 1.0  # scale for the canvas image zoom, public for outer classes
        self.__delta = 1.3  # zoom magnitude
        self.__filter = (
            Image.LANCZOS
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
        self.canvas = tk.Canvas(
            self.__imframe,
            highlightthickness=0,
            xscrollcommand=hbar.set,
            yscrollcommand=vbar.set,
        )
        self.canvas.grid(row=0, column=0, sticky="nswe")
        self.canvas.update()  # wait till canvas is created
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

        self.canvas.bind(
            "<Key>", lambda event: self.canvas.after_idle(self.__keystroke, event)
        )

        # Decide if this image huge or not
        self.__huge = False  # huge or not
        self.__huge_size = 14000  # define size of the huge image
        self.__band_width = 1024  # width of the tile band
        Image.MAX_IMAGE_PIXELS = (
            1000000000  # suppress DecompressionBombError for the big image
        )
        self.__image = None
        self.__images = {}
        self.container = None
        # self.set_image(path)

    def next(self, path):
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
            self.next_job = self.__imframe.after(self.duration, self.next, path)
            self.__show_image()
        else:
            try:
                self.__show_image()
            finally:
                self.next_job = self.__imframe.after(self.duration, self.next, path)

    def update_frame_size(self):
        index  = 0
        self.imwidth, self.imheight = self.__images[
            index
        ].size  # public for outer classes
        frame_width = self.__imframe.master.winfo_width()
        frame_height = self.__imframe.master.winfo_height()
        self.imscale = min(frame_width / self.imwidth, frame_height / self.imheight)
        if (
            self.imwidth * self.imheight > self.__huge_size * self.__huge_size
            and self.__images[index].tile[0][0] == "raw"
        ):  # only raw images could be tiled
            self.__huge = True  # image is huge
            self.__offset = self.__images[index].tile[0][2]  # initial tile offset
            self.__tile = [
                self.__images[index].tile[0][0],  # it have to be 'raw'
                [0, 0, self.imwidth, 0],  # tile extent (a rectangle)
                self.__offset,
                self.__images[index].tile[0][3],
            ]  # list of arguments to the decoder
        self.__min_side = min(self.imwidth, self.imheight)  # get the smaller image side
        self.__ratio = (
            max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
        )

    # Moved out of init to allow for hotswapping images
    def set_image(self, path: str):
        if self.path == path:
            self.__show_image()
            self.toggle_pause(toggle_on=True)
            return
        if self.next_job:
            self.__imframe.after_cancel(self.next_job)
            self.next_job = None
        if path.endswith(".gif"):
            self.frames, self.duration = ImageUtils.getPilFrames(path)
        else:
            # self.frames = [ImageUtils.getPilImage(path),]
            self.frames = [
                ImageUtils.get_cv2_pil_image(path)
            ]
            self.duration = None
        self.index = 0
        self.path = path  # path to the image, should be public for outer classes
        with warnings.catch_warnings():  # suppress DecompressionBombWarning
            warnings.simplefilter("ignore")
            self.__images = {i: image.copy() for i, image in enumerate(self.frames)}

        self.update_frame_size()
        self.__scale = self.imscale * self.__ratio  # image pyramide scale
        self.__reduction = 2  # reduction degree of image pyramid
        self.__pyramid = {}
        self.__curr_img = 0  # current image from the pyramid
        if self.duration:
            self.index = -1
            self.next(path)
        else:
            self.__imframe.after_idle(self.__show_image)

    def smaller(self, index):
        """Resize image proportionally and return smaller image"""
        w1, h1 = float(self.imwidth), float(self.imheight)
        w2, h2 = float(self.__huge_size), float(self.__huge_size)
        aspect_ratio1 = w1 / h1
        aspect_ratio2 = w2 / h2  # it equals to 1.0
        if aspect_ratio1 == aspect_ratio2:
            image = Image.new("RGB", (int(w2), int(h2)))
            k = h2 / h1  # compression ratio
            w = int(w2)  # band length
        elif aspect_ratio1 > aspect_ratio2:
            image = Image.new("RGB", (int(w2), int(w2 / aspect_ratio1)))
            k = h2 / w1  # compression ratio
            w = int(w2)  # band length
        else:  # aspect_ratio1 < aspect_ration2
            image = Image.new("RGB", (int(h2 * aspect_ratio1), int(h2)))
            k = h2 / h1  # compression ratio
            w = int(h2 * aspect_ratio1)  # band length
        i, j, n = 0, 1, round(0.5 + self.imheight / self.__band_width)
        while i < self.imheight:
            logger.debug("\rOpening image: {j} from {n}".format(j=j, n=n), end="")
            band = min(self.__band_width, self.imheight - i)  # width of the tile band
            self.__tile[1][3] = band  # set band width
            self.__tile[2] = (
                self.__offset + self.imwidth * i * 3
            )  # tile offset (3 bytes per pixel)
            if self.__images[i]:
                self.__images[i].close()
            # self.__images[i] = Image.open(self.path)  # reopen / reset image
            self.__images[i] = self.frames[i].copy()
            self.__images[i].size = (self.imwidth, band)  # set size of the tile band
            self.__images[i].tile = [self.__tile]  # set tile
            cropped = self.__images[index].crop(
                (0, 0, self.imwidth, band)
            )  # crop tile band
            image.paste(
                cropped.resize((w, int(band * k) + 1), self.__filter), (0, int(i * k))
            )
            i += band
            j += 1
        logger.debug("\r" + 30 * " " + "\r", end="")  # hide printed string
        return image

    def redraw_figures(self):
        """Dummy function to redraw figures in the children classes"""
        pass

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
            self.__pyramid[index] = (
                [self.smaller(index)]
                if self.__huge
                else [self.frames[index].copy()]
            )
            w, h = self.__pyramid[index][-1].size
            while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
                w /= self.__reduction  # divide on reduction degree
                h /= self.__reduction  # divide on reduction degree
                self.__pyramid[index].append(
                    self.__pyramid[index][-1].resize(
                        (int(w), int(h)), self.__filter
                    )
                )
            if not self.container:
                self.container = self.canvas.create_rectangle(
                    (
                        0,
                        0,
                        self.imwidth * self.imscale,
                        int(self.imheight * self.imscale),
                    ),
                    width=0,
                )
            else:
                self.canvas.coords(
                    self.container,
                    (
                        0,
                        0,
                        self.imwidth * self.imscale,
                        int(self.imheight * self.imscale),
                    ),
                )

    def __show_image(self):
        index = self.index
        self.__update_pyramid(index)
        if self.__pyramid is None:
            return

        """Show image on the Canvas. Implements correct image zoom almost like in Google Maps"""
        box_image = self.canvas.coords(self.container)  # get image area
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
            if self.__huge and self.__curr_img < 0:  # show huge image
                h = int((y2 - y1) / self.imscale)  # height of the tile band
                self.__tile[1][3] = h  # set the tile band height
                self.__tile[2] = (
                    self.__offset + self.imwidth * int(y1 / self.imscale) * 3
                )

                self.__images[index].close()
                # self.__images[index] = Image.open(self.path)  # reopen / reset image
                self.__images[index] = self.frames[index].copy()
                self.__images[index].size = (
                    self.imwidth,
                    h,
                )  # set size of the tile band
                self.__images[index].tile = [self.__tile]
                image = self.__images[index].crop(
                    (int(x1 / self.imscale), 0, int(x2 / self.imscale), h)
                )
            else:  # show normal image
                image = self.__pyramid[index][
                    max(0, self.__curr_img)
                ].crop(  # crop current img from pyramid
                    (
                        int(x1 / self.__scale),
                        int(y1 / self.__scale),
                        int(x2 / self.__scale),
                        int(y2 / self.__scale),
                    # ), index
                    )
                )
            #
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
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
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
        #
        self.canvas.scale("all", x, y, scale, scale)  # rescale all objects
        # Redraw some figures before showing image on the screen
        self.redraw_figures()  # method for child classes
        self.__show_image()

    def __keystroke(self, event):
        """Scrolling with the keyboard.
        Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc."""
        if (
            event.state - self.__previous_state == 4
        ):  # means that the Control key is pressed
            pass  # do nothing if Control key is pressed
        else:
            self.__previous_state = event.state  # remember the last keystroke state
            # Up, Down, Left, Right keystrokes
            if event.keycode in [
                68,
                39,
                102,
            ]:  # scroll right: keys 'D', 'Right' or 'Numpad-6'
                self.__scroll_x("scroll", 1, "unit", event=event)
            elif event.keycode in [
                65,
                37,
                100,
            ]:  # scroll left: keys 'A', 'Left' or 'Numpad-4'
                self.__scroll_x("scroll", -1, "unit", event=event)
            elif event.keycode in [
                87,
                38,
                104,
            ]:  # scroll up: keys 'W', 'Up' or 'Numpad-8'
                self.__scroll_y("scroll", -1, "unit", event=event)
            elif event.keycode in [
                83,
                40,
                98,
            ]:  # scroll down: keys 'S', 'Down' or 'Numpad-2'
                self.__scroll_y("scroll", 1, "unit", event=event)

    def crop(self, bbox, index):
        """Crop rectangle from the image and return it"""
        if self.__huge:  # image is huge and not totally in RAM
            band = bbox[3] - bbox[1]  # width of the tile band
            self.__tile[1][3] = band  # set the tile height
            self.__tile[2] = (
                self.__offset + self.imwidth * bbox[1] * 3
            )  # set offset of the band
            self.__images[index].close()
            self.__images[index] = self.frames[self.index].copy()
            self.__images[index].size = (
                self.imwidth,
                band,
            )  # set size of the tile band
            self.__images[index].tile = [self.__tile]
            return self.__images[index].crop((bbox[0], 0, bbox[2], band))
        else:  # image is totally in RAM
            return self.__pyramid[index][0].crop(bbox)

    def destroy(self):
        """ImageFrame destructor"""
        for image in self.__images:
            image.close()
            # image[self.index].close()
        map(lambda i: i.close, self.__pyramid)  # close all pyramid images
        for pyramid in self.__pyramid.values():
            map(lambda i: i.close, pyramid)  # close all pyramid images
        # del self.__pyramid[:]  # delete pyramid list
        del self.__pyramid  # delete pyramid variable
        self.canvas.destroy()
        self.__imframe.destroy()
