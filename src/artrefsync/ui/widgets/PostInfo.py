import logging
import os
import platform
import tkinter as tk
from tkinter.font import nametofont

import ttkbootstrap as ttk
from PIL import ImageTk
from tkinterdnd2 import COPY, DND_FILES

from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.config import get_config
config = get_config()
from artrefsync.constants import APP, BINDING, TABLE
from artrefsync.db.post_db import PostDb
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.EventManager import e_binder
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.TkThreadCaller import thread_caller

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class PostInfoTab(ttk.Frame):
    def __init__(self, root, **kwargs):
        logger.info("Creating Post Info Tab")
        super().__init__(root, *kwargs, width=4)
        self.color = ttk.Style().colors
        self.grid(column=0, row=0, sticky=tk.NSEW)
        text_width = 25
        self.font = nametofont("TkDefaultFont")
        self.colors = ttk.Style().colors
        self.cancel_key = "post_info"
        self.blur_map = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, minsize=200)
        self.grid_rowconfigure(5, weight=1)

        self.thumbnail = ttk.Label(self)
        self.thumbnail.grid(column=0, row=0, sticky=tk.NSEW)
        self.name = ttk.Label(
            self, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        )
        self.name.grid(column=0, row=1, sticky=tk.EW)
        self.artist_frame = ttk.Labelframe(self, text="Artist")
        self.artist_frame.grid(column=0, row=2, sticky=tk.EW, ipady=0)
        self.board_button = RoundedIcon.from_text(
            self.artist_frame, "", self.colors.primary, command=self.on_artist_click
        )
        self.board_button.pack(side=tk.LEFT)
        self.artist_button = RoundedIcon.from_text(
            self.artist_frame, "", self.colors.primary, command=self.on_artist_click
        )
        self.artist_button.pack(side=tk.LEFT)

        self.small_details_frame = ttk.Frame(self)
        self.small_details_frame.grid(column=0, row=3, sticky=tk.EW)
        score_frame = ttk.Labelframe(self.small_details_frame, text="Score")
        ext_frame = ttk.Labelframe(self.small_details_frame, text="Ext")

        dim_frame = ttk.Labelframe(self.small_details_frame, text="Size")
        score_frame.pack(side=tk.LEFT, expand=True, fill="x")
        ext_frame.pack(side=tk.LEFT, expand=True, fill="x")
        dim_frame.pack(side=tk.LEFT, expand=True, fill="x")
        self.score_label = ttk.Label(
            score_frame, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        )
        self.ext_button = RoundedIcon.from_text(
            ext_frame, "", self.colors.primary, command=self.on_artist_click
        )
        # self.ext_label = ttk.Label(
        #     ext_frame, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        # )
        self.dim_label = ttk.Label(
            dim_frame, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        )
        self.score_label.pack()
        # self.ext_label.pack()
        self.ext_button.pack()
        self.dim_label.pack()

        self.file = ttk.Label(self, cursor="arrow", justify=tk.LEFT, border=1)
        self.file.grid(column=0, row=4, sticky=tk.NSEW)
        self.file_tooltip = ttk.ToolTip(self.file)
        self.tags_frame = ttk.Frame(self)
        self.tags_frame.grid(column=0, row=5, sticky=tk.NSEW)

        self.tags = ttk.ScrolledText(
            self.tags_frame, wrap=tk.WORD, width=text_width, cursor="arrow"
        )
        self.tags.text.tag_configure(
            "sel",
            background=self.color.warning,
            foreground=self.color.warning,
            underline=1,
        )
        self.tags.pack(fill="both", expand=True)
        self.grid_propagate(False)

        self.add_bindings()

    def on_artist_click(self, event: tk.Event):
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        widget_text = event.widget.text
        e_binder.event_generate(BINDING.ON_ARTIST_SELECT, widget_text, ctrl_pressed)

    def on_tag_click(self, event: tk.Event):
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        widget_text = event.widget.text
        e_binder.event_generate(BINDING.ON_TAG_SELECT, widget_text, ctrl_pressed)

    def add_bindings(self):
        e_binder.bind(BINDING.ON_POST_SELECT, self.on_post_select, self)
        self.file.drag_source_register(DND_FILES)
        self.file.dnd_bind("<<DragInitCmd>>", self.drag_init)
        self.file.bind("<Double-1>", self.start_file)
        self.file.bind("<Button-2>", self.start_file_dir)
        self.tags.text.bind("<Button-1>", self.on_text_tag_click)

    def start_file(self, event):
        file = self.file.cget("text")
        if file and platform.system() == "Windows":
            os.startfile(file)

    def start_file_dir(self, event):
        file = self.file.cget("text")
        if file and platform.system() == "Windows":
            dir = os.path.dirname(file)
            if dir and os.path.isdir(dir):
                os.startfile(dir)

    def on_post_select(self, post_id):
        blur_tags = config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]

        logger.info("On Post Select, post id: %s", post_id)
        with PostDb() as post_db:
            post: Post = post_db.posts.get(id=post_id)
            post_file: PostFile = post_db.files.get(id=post_id)

        if post_file and post:
            post.file_link = post_file.file
            post.sample_link = post_file.preview
            self.name.configure(text=post.name)
            self.name.configure(text=post.name)
            self.board_button.update_text(post_file.board)
            self.artist_button.update_text(post_file.artist_name)
            self.score_label.configure(text=post.score)
            self.ext_button.update_text(post.ext)
            self.dim_label.configure(text=f"{post.width}x{post.height}")
            self.file.configure(text=post.file_link)
            self.file_tooltip.text = f"{post.file_link}\n-Double Click: Open\n-Middle Click: Open file location"
            self.tags.config(state=tk.NORMAL)
            self.tags.delete("1.0", tk.END)
            for tag in post.tags:
                tag_text = tag
                if blur_tags:
                    blur_text = config.censor_text(tag)
                    self.blur_map[blur_text] = tag
                    tag_text = blur_text
                self.tags.insert(tk.END, f"{tag_text}  ")

            self.tags.config(state=tk.DISABLED)
            self.after_idle(self.after_on_post_select, post, post_file)

    def after_on_post_select(self, post: Post, post_file: PostFile):
        if not post_file:
            return
        if post_file.preview:
            file_name = post_file.preview
        elif post_file.sample:
            file_name = post_file.sample
        else:
            file_name = post_file.file if post.ext not in ("webm", "mp4") else ""

        blur = False
        if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
            blur = "rating_s" not in post.tags

        thread_caller.add(
            ImageUtils.get_cv2_pil_image,
            self.set_image,
            self.cancel_key,
            file=file_name,
            size=(190, 190),
            blur=blur,
        )

    def set_image(self, image):
        photo = ImageTk.PhotoImage(image)
        self.thumbnail.config(image=photo)
        self.thumbnail.image = photo

    def on_text_tag_click(self, event: tk.Event):
        state = event.state
        ctrl_pressed = (state & 0x4) != 0
        blur_tags = config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]
        widget: tk.Text = self.tags.text
        print(event)

        index = widget.index(f"@{event.x},{event.y}")
        start, end = self.get_word_box(widget, index)
        if not start or not end:
            return
        if word := widget.get(start, end).strip():
            self.tags.config(state=tk.NORMAL)
            ranges = self.tags.tag_ranges("sel")
            if ranges:
                widget.tag_remove("sel", 1.0, tk.END)
            widget.tag_add("sel", start, end)
            self.tags.config(state=tk.DISABLED)
            tag_text = word
            if blur_tags:
                tag_text = self.blur_map[word]
            e_binder.event_generate(BINDING.ON_TAG_SELECT, tag_text, ctrl_pressed)
        return "break"

    def get_word_box(self, widget, index):
        try:
            start = widget.search(" ", index, "1.0", backwards=True)
            end = widget.search(" ", index, tk.END)
            return start, end

        except Exception:
            return ""

    def drag_init(self, event):
        file = self.file.cget("text")
        if file:
            return (COPY, DND_FILES, file)
