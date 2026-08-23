import logging
import time
import tkinter as tk

import ttkbootstrap as ttk

from artrefsync.config import get_config
from artrefsync.constants import BINDING, NAMES
from artrefsync.db.post_db import PostDb
from artrefsync.stores.store_models import PostFile
from artrefsync.ui.widgets.GifAdvancedScrolling import CanvasImage
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.IntegerVar import IntegerVar
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)


class ViewerTab(ttk.Frame):
    def __init__(self, root):
        logger.info("Initializing Viewer Tab")
        super().__init__(root, name=NAMES.VIEWER_TAB)
        event_binder[BINDING.VIEWER_WIDGET] = self

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.pid = None
        self.cancel_key = "ViewerTab"
        self.last_scale = time.time()

        self.file = ""
        self.height = self.winfo_height()
        self.width = self.winfo_width()
        self.index_var = IntegerVar(value=0)
        self.canvas_image = CanvasImage(self, self.index_var)
        self.init_widgets()
        self.init_bindings()
        self.gif_top = False
        self.curr_focus = None
        self.after_add_binding_id = None

    def init_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas_image.grid(row=0, column=0)
        self.clear_button = RoundedIcon(self, text="✕", size=(25, 25))
        self.clear_button.place(relx=1.0, rely=0.0, anchor=tk.NE)
        self.gif_controls = ttk.Frame(self)
        self.init_gif_control()

    def init_bindings(self):
        self.clear_button.bind("<Button-1>", self.close_image_viewer)
        self.canvas_image.canvas.bind("<FocusIn>", self.on_focus_in)
        self.canvas_image.canvas.bind("<FocusOut>", self.unbind_canvas_escape)
        event_binder.bind(BINDING.ON_IMAGE_DOUBLE_CLICK, self.open_image_viewer, self)
        event_binder.bind(BINDING.ON_POST_SELECT, self.update_viewer_image, self)
        event_binder.bind(BINDING.ON_FILTER_UPDATE, self.close_image_viewer, self)
        event_binder.bind(BINDING.ON_TEXT_ESCAPE, self.close_image_viewer, self)
        event_binder.bind(BINDING.ON_CLOSE_VIEWER, self.close_image_viewer, self)
        event_binder.bind(BINDING.ON_TEXT_Z, self.prev_frame, self)
        event_binder.bind(BINDING.ON_TEXT_X, self.toggle_play, self)
        event_binder.bind(BINDING.ON_TEXT_C, self.next_frame, self)

    def on_scale(self, e=None):
        if time.time() - self.last_scale < 0.2:
            return
        else:
            self.last_scale = time.time()
        self.scaling = True
        if self.index_var.get() == self.canvas_image.frames.curr:
            return
        if self.grid_info() and self.canvas_image:
            self.canvas_image.toggle_pause(toggle_on=False)

    def on_scale_release(self, e=None):
        logger.info("On Scale Release")
        self.scaling = False
        if self.playing:
            self.canvas_image.toggle_play(toggle_play=False)

    def init_gif_control(self):
        self.count_button = RoundedIcon(
            self.gif_controls, text_variable=self.index_var, command=self.toggle_play, size=30
        )
        self.scale = ttk.Scale(
            self.gif_controls,
            from_=0,
            to=100,
            variable=self.index_var.dummy_var,
            length=400,
            command=lambda e: self.after_idle(self.on_scale),
        )

        self.left_button = RoundedIcon(self.gif_controls, "<", command=self.prev_frame, size = 30)
        self.pause_play_button = RoundedIcon(
            self.gif_controls, "⏸", command=self.toggle_play, size=30
 
        )
        self.right_button = RoundedIcon(self.gif_controls, "˃", command=self.next_frame, size=30)
        self.rightright_button = RoundedIcon(
            self.gif_controls,
            "˃˃",
            command=lambda x: event_binder.event_generate(
                BINDING.ON_NEXT_GALLERY_IMAGE
            ),
            size=30
        )

        self.pause_play_button.grid(row=0, column=0, padx=0, pady=0)
        self.left_button.grid(row=0, column=1, padx=0, pady=0)
        self.right_button.grid(row=0, column=2, padx=0, pady=0)
        self.scale.grid(row=0, column=3, padx=0, pady=0)
        self.count_button.grid(row=0, column=4, padx=0, pady=0)
        self.canvas_image.playing.trace_add("write", self.on_playing_change)

    def on_playing_change(self, *args):
        text = "⏸" if self.canvas_image.playing.get() else "▶"
        self.pause_play_button.config(text = text)
    

    def toggle_gif_control(self, toggle_on=True):
        if toggle_on:
            self.gif_controls.place(relx=0.5, rely=1.0, anchor=tk.S)
        else:
            self.gif_controls.place_forget()

    def on_focus_in(self, e):
        if self.after_add_binding_id:
            self.after_cancel(self.after_add_binding_id)
        self.after_add_binding_id = self.after(100, self.add_escape_binding)

    def open_image_viewer(self, pid):
        logger.info("Opening Image Viewer")
        if self.grid_info():
            return

        event_binder.event_generate(BINDING.ON_TOGGLE_UI, toggle_on=False)

        if pid is None:
            return
        self.canvas_image.canvas.focus_set()

        self.grid(column=0, row=0, sticky=tk.NSEW)
        self.lift()
        self.update_viewer_image(pid)

    def close_image_viewer(self, _=None):
        logger.info("Closing Image Viewer")
        if self.after_add_binding_id:
            self.after_cancel(self.after_add_binding_id)
        self.canvas_image.cancel_next_frame()
        event_binder[BINDING.GALLERY_WIDGET].text.focus_set()
        if self.grid_info():
            logger.info("Closing Image Viewer")
            event_binder[BINDING.GALLERY_WIDGET].lift()
            self.grid_forget()
            event_binder.event_generate(BINDING.ON_TOGGLE_UI, toggle_on=True)

    def unbind_canvas_escape(self, *_):
        if self.after_add_binding_id:
            self.after_cancel(self.after_add_binding_id)
        self.canvas_image.canvas.unbind("<KeyRelease-space>")
        self.canvas_image.canvas.unbind("<Escape>")

    def add_escape_binding(self, *_):
        logger.info("Adding space binding")
        self.canvas_image.canvas.bind("<KeyRelease-space>", self.close_image_viewer)
        self.canvas_image.canvas.bind("<Escape>", self.close_image_viewer)

    def update_viewer_image(self, pid):
        if not self.grid_info():
            return
        self.last_open_time = time.time()
        thread_caller.cancel(__name__)
        self.canvas_image.cancel_next_frame()
        self.update_idletasks()

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
            thread_caller.cancel(self.cancel_key)
            self.curr_focus = self.canvas_image.canvas.focus_get()
            self.canvas_image.canvas.focus_set()
            self.cancel_key = thread_caller.add(
                self.canvas_image.load_media,
                self.on_canvas_set_image,
                self.cancel_key,
                filename,
            )
            self.pid = pid

    def on_canvas_set_image(self, *args):
        self.clear_button.lift()
        frame_count = len(self.canvas_image.frames)
        state = "normal" if frame_count > 1 else "disabled"
        self.scale.configure(to=frame_count, state=state)
        self.toggle_gif_control(toggle_on=frame_count > 1)
        # event_binder.event_generate(BINDING.ON_TOGGLE_UI, False)

    def prev_frame(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.move_left()

    def next_frame(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.move_right()

    def toggle_play(self, e=None):
        if self.grid_info() and self.canvas_image:
            playing = self.canvas_image.toggle_pause()

    def resize_gif(self, e=None):
        if self.grid_info() and self.canvas_image:
            self.canvas_image.update_frame_size()
            self.canvas_image.__show_image()
