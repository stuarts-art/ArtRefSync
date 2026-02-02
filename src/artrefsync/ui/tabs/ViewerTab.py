from itertools import count, cycle
from PIL import Image, ImageTk, ImageSequence
import tkinter as tk
import ttkbootstrap as ttk
from artrefsync.boards.board_handler import PostFile
from artrefsync.config import config
from artrefsync.constants import BINDING, NAMES
from artrefsync.db.post_db import PostDb
import logging
from artrefsync.ui.AdvancedScrolling  import CanvasImage
from artrefsync.ui.widgets.ModernTopBar import RoundedIcon
from artrefsync.utils.EventManager import ebinder

from artrefsync.utils.TkThreadCaller import TkThreadCaller
from artrefsync.utils.benchmark import Bm
from artrefsync.utils.image_utils import ImageUtils



logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ViewerTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        logger.info("Init Viewer Tab")
        super().__init__(root, name=NAMES.VIEWER_TAB, *args, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.file = ""
        self.post_file:PostFile = None
        self.thread_caller = TkThreadCaller(self)
        self.height = self.winfo_height()
        self.width = self.winfo_width()
        self.canvas_image = None

        self.init_widgets()
        self.init_bindings()
        self.gif_top = False

    def init_widgets(self):
        self.image_label = ttk.Label(self, justify=tk.CENTER)
        self.image_label.grid(row=0, column=0, sticky= tk.NSEW)

        self.clear_button = RoundedIcon(self, text="✕", size=(25, 25))
        self.clear_button.place(relx=1.0, rely= 0.0, anchor=tk.NE)
        self.gif_viewer:GifViewer = GifViewer(self.image_label)

    def init_bindings(self):
        self.bind("<Configure>", self.resize)
        self.image_label.bind("<Button-2>", self.close_image_viewer)
        self.clear_button.bind("<Button-1>", self.close_image_viewer)
        self.clear_button.bind("<Button-2>", self.toggle_gif)
        ebinder.bind(BINDING.ON_IMAGE_DOUBLE_CLICK, self.open_image_viewer, self)
        ebinder.bind(BINDING.ON_POST_SELECT, self.update_viewer_image, self)
        ebinder.bind(BINDING.ON_FILTER_UPDATE, self.close_image_viewer, self)

    def open_image_viewer(self, pid):
        self.grid(column=0, row=0, sticky=tk.NSEW)
        self.lift()
        self.after(50, self.update_viewer_image, pid)

    def toggle_gif(self, _=None):
        logger.info("Toggling Gif from %s",  self.gif_top)
        if self.gif_top:
            self.image_label.lower()
            self.gif_top = False
        else:
            self.canvas_image.canvas.master.lower()
            self.gif_top = True



    def close_image_viewer(self, _=None):
        if self.grid_info():
            logger.info("Closing Image Viewer")
            self.grid_forget()

    def resize(self, e):
        if not self.post_file:
            return
        if e.widget == self:

            height = self.winfo_height()
            width = self.winfo_width()
            if height != self.height or width != self.width:
                self.height = height
                self.width = width
                self.async_update_image()

    def async_update_image(self):
        post_file = self.post_file
        self.file = post_file.thumbnail if post_file.ext in ("webm", "mp4") else post_file.file
        self.thread_caller.cancel(__name__)
        # self.thread_caller.add(
        #     ImageUtils.getPilImage,
        #     self.setImage,
        #     __name__,
        #     self.file,
        # )
        self.setImage()



    def update_viewer_image(self, pid):
        if not pid:
            logger.error("Missing PID in viewer")
            return
        if self.grid_info():
            logger.info("Opening Image Viewer for %s", pid)
            with PostDb() as postdb:
                # self.post_file:PostFile = postdb.files[pid]
                post_file:PostFile = postdb.files[pid]
            # self.post_file = post_file
            # file_name = post_file.thumbnail if post_file.ext in ("webm", "mp4") else post_file.file
            # self.file = file_name

            self.file = post_file.thumbnail if post_file.ext in ("webm", "mp4") else post_file.file
            # if post_file.ext != "gif":
            if not self.canvas_image:
                self.canvas_image = CanvasImage(self, self.file)
                self.canvas_image.grid(row=0, column=0)
            else: 
                self.canvas_image.set_image(self.file)
            # self.canvas_image.canvas.master.lift()
            # self.image_label.lower()
            self.clear_button.lift()


            if post_file.ext == "gif":

                # photoimage = ImageUtils.get_tk_thumb(post_file.thumbnail, (self.winfo_width(), self.winfo_height()))
                # self.image_label.config(image=photoimage)
                # self.image_label.image=photoimage

                self.gif_viewer.load( post_file.file, (self.winfo_width(), self.winfo_height()))
                # self.image_label.lift()
                # self.clear_button.lift()
                # self.async_update_image()








            # size = (self.winfo_width(), self.winfo_height())
            # self.thread_caller.add(self.tasked_GetImage, self.setImage, file_name, size)

    # def tasked_GetImage(self, file_name, size):
    #     try:
    #         image = ImageUtils.getPilImage(file_name, None, None)
    #         # image = Image.open(file_name)
    #         # image.thumbnail(size)
    #         return image
    #     except:
    #         return None

    def setImage(self):
        width = self.winfo_width()
        height = self.winfo_height()
        self.gif_viewer.unload()
        if self.post_file.ext != 'gif':
            with Bm():
                self.image_label = ttk.Label(self, justify=tk.CENTER)
                photoimage = ImageUtils.get_tk_thumb(self.file, (width, height))
                self.image_label.config(image=photoimage)
                self.image_label.image = photoimage
        else:
            # photoimage = ImageUtils.get_tk_thumb(self.file)
            # self.image_label.config(image=photoimage)
            # self.image_label.image = photoimage
            # self.after(0, self.gif_viewer.load, self.post_file.file, (self.winfo_width(), self.winfo_height()))
            with Bm():
                photoimage = ImageUtils.get_tk_thumb(self.post_file.thumbnail, (width, height))
                self.image_label.config(image=photoimage)
                self.image_label.image=photoimage

            with Bm():
                self.gif_viewer.load( self.post_file.file, (self.winfo_width(), self.winfo_height()))

class GifViewer:
    def __init__(self, label):
        self.image_label:ttk.Label = label
        self.frames:cycle  = None # image frames
        self.delay=None
        self.image = None
        self.file = None
        self.raw_frames = []
        self.job_id = None
        # self.delay_map = {} #Only call duration once per file.
        self.thread_caller = TkThreadCaller(label)
        self.task_name = "load_frames"

    def load(self, file:str, size:tuple):
        self.file = file
        self.size = size
        logger.info("Gif Viewer with %s", file)
        self.thread_caller.cancel(self.task_name)
        self.thread_caller.add(ImageUtils.getPilFrames, self.set_frames, self.task_name, file)
        # self.image_label.after(0, self.set_frames, self.file)

    def set_frames(self, result):

        frames, duration = ImageUtils.getTkFrames(self.file, self.size)
        self.frames=cycle(frames)
        self.delay=duration

        logger.info("Gif Viewer with %d frames and %d delay", len(frames), self.delay)
        if len(frames) == 1:
            self.image_label.config(image=next(self.frames))
        else:
            # self.next_frame()
            # self.frames=None
            self.job_id = self.image_label.after(0, self.next_frame, self.file)


        
        
        
        

    def oldload(self, file:str, size:tuple):
        logger.info("Gif Viewer with %s", file)

        # width, height = size
        thumb = ImageUtils.get_tk_thumb(file, size=size)
        self.image_label.config(image=thumb)


        if self.job_id:
            self.image_label.after_cancel(self.job_id)
        # Reload Raw Frames
        if file != self.file:
        # Get delay between frames
            self.image = ImageUtils.getPilImage(file, None, None)
            # self.image = ImageUtils.getPilImage(file, None, None)
            self.raw_frames = []
            try:
                self.delay = self.image.info['duration']
            except:
                self.delay = 100

            try:
                for frame in ImageSequence.Iterator(self.image):
                    frame = self.image.copy()
                    self.raw_frames.append(frame)
                    # self.image.seek(i)
            except EOFError:
                pass
        
        frames = []
        for raw_frame in self.raw_frames:
            frame = raw_frame.copy()
            frame.thumbnail(size=size)
            frames.append(ImageTk.PhotoImage(image=frame))

        self.frames = cycle(frames)

        logger.info("Gif Viewer with %d frames and %d delay", len(frames), self.delay)
        # If single image, display frame and don't animate.
        if len(frames) == 1:
            self.image_label.config(image=next(self.frames))
        else:
            # self.next_frame()
            # self.frames=None
            self.job_id = self.image_label.after(0, self.next_frame)
    

    # def load_raw_map(self, file, size):

        
    # def load_thumb_frames(self, file, size):

    

    def next_frame(self, filename):
        if filename != self.file:
            return
        elif self.frames:
            self.image_label.config(image=next(self.frames))
            self.job_id = self.image_label.after(self.delay, self.next_frame, filename)

    def unload(self):
        self.image_label.config(image=None)
        self.frames = None

        if self.job_id:
            self.image_label.after_cancel(self.job_id)