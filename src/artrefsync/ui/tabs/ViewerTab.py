import logging
import tkinter as tk
import ttkbootstrap as ttk

from artrefsync.boards.board_handler import PostFile
from artrefsync.config import config
from artrefsync.constants import BINDING, NAMES
from artrefsync.db.post_db import PostDb
from artrefsync.ui.widgets.AdvancedScrolling import CanvasImage
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.EventManager import ebinder
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ViewerTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        logger.info("Init Viewer Tab")
        super().__init__(root, name=NAMES.VIEWER_TAB, *args, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.pid = None
        self.cancle_key = "ViewerTab"

        self.file = ""
        self.thread_caller = TkThreadCaller(self)
        self.height = self.winfo_height()
        self.width = self.winfo_width()
        self.index_var = ttk.IntVar(value=0)
        self.canvas_image = CanvasImage(self)
        self.init_widgets()
        self.init_bindings()
        self.gif_top = False

    def init_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas_image.grid(row=0, column=0)
        # self.init_gif_control()
        self.clear_button = RoundedIcon(self, text="✕", size=(25, 25))
        self.clear_button.place(relx=1.0, rely=0.0, anchor=tk.NE)

    # TODO: Fix gif/video support.
    def init_gif_control(self):
        self.gif_controls = ttk.Frame(self)
        self.gif_controls.grid(row=1, column=0)
        self.count_button = RoundedIcon(
            self.gif_controls, text_variable=self.index_var, command=self.toggle_play
        )
        self.left_button = RoundedIcon(self.gif_controls, "˂", command=self.prev_frame)
        self.leftleft_button = RoundedIcon(
            self.gif_controls,
            "˂˂",
            command=lambda x: ebinder.event_generate(BINDING.ON_PREV_GALLERY_IMAGE),
        )
        self.right_button = RoundedIcon(self.gif_controls, "˃", command=self.next_frame)
        self.rightright_button = RoundedIcon(
            self.gif_controls,
            "˃˃",
            command=lambda x: ebinder.event_generate(BINDING.ON_NEXT_GALLERY_IMAGE),
        )
        self.leftleft_button.pack(side=tk.LEFT)
        self.left_button.pack(side=tk.LEFT)
        self.count_button.pack(side=tk.LEFT)
        self.right_button.pack(side=tk.LEFT)
        self.rightright_button.pack(side=tk.RIGHT)

        ebinder.bind(BINDING.ON_TEXT_Z, self.prev_frame, self)
        ebinder.bind(BINDING.ON_TEXT_X, self.toggle_play, self)
        ebinder.bind(BINDING.ON_TEXT_C, self.next_frame, self)

    def init_bindings(self):
        self.clear_button.bind("<Button-1>", self.close_image_viewer)
        ebinder.bind(BINDING.ON_IMAGE_DOUBLE_CLICK, self.open_image_viewer, self)
        ebinder.bind(BINDING.ON_POST_SELECT, self.update_viewer_image, self)
        ebinder.bind(BINDING.ON_FILTER_UPDATE, self.close_image_viewer, self)
        ebinder.bind(BINDING.ON_TEXT_ESCAPE, self.close_image_viewer, self)

    def open_image_viewer(self, pid):
        if pid is None:
            return
        self.grid(column=0, row=0, sticky=tk.NSEW)
        self.lift()
        self.after(50, self.update_viewer_image, pid)

    def close_image_viewer(self, _=None):
        if self.gif_top:
            # self.gif_viewer.unload()
            self.gif_top = False
        if self.grid_info():
            logger.info("Closing Image Viewer")
            self.grid_forget()

    def update_viewer_image(self, pid):
        self.thread_caller.cancel(__name__)

        if self.pid == pid:
            self.close_image_viewer()
            self.pid = None

        if not pid:
            logger.error("Missing PID in viewer")
            return
        if self.grid_info():
            logger.info("Opening Image Viewer for %s", pid)
            with PostDb() as post_db:
                if pid in post_db.files:
                    post_file: PostFile = post_db.files[pid]
                else:
                    logger.info("Failed to load postFile for %s", pid)
                    return
            filename = post_file.file
            self.thread_caller.cancel(self.cancle_key)
            self.thread_caller.add(
                self.canvas_image.set_image,
                self.clear_button.lift,
                self.cancle_key,
                filename,
            )
            self.pid = pid

    def prev_frame(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.move_left()

    def next_frame(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.move_right()

    def toggle_play(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.toggle_pause()

    def resize_gif(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.update_frame_size()
            self.canvas_image.__show_image()
