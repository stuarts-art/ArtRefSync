import platform

import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip
import tkinter as tk
from tkinter.font import nametofont
import os
from tkinterdnd2 import COPY, DND_FILES

from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.constants import BINDING
from artrefsync.db.post_db import PostDb
from artrefsync.ui.widgets.ModernTopBar import RoundedIcon
from artrefsync.utils.TkThreadCaller import TkThreadCaller
from artrefsync.utils.EventManager import ebinder
from artrefsync.config import config

import logging

from artrefsync.utils.image_utils import ImageUtils

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class PostInfo(ttk.Frame):
    def __init__(self, root, thread_caller: TkThreadCaller, **kwargs):
        logger.info("Creating Post Info Tab")
        super().__init__(root, *kwargs, width=4)
        self.grid(column=0, row=0, sticky=tk.NSEW)
        self.thread_caller = TkThreadCaller
        text_width = 25
        self.font = nametofont("TkDefaultFont")
        self.colors = ttk.Style().colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, minsize=200)
        self.grid_rowconfigure(5, weight=1)

        self.thumbnail = tk.Label(self)
        self.thumbnail.grid(column=0, row=0, sticky=tk.NSEW)
        self.name = ttk.Label(
            self, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        )
        self.name.grid(column=0, row=1, sticky=tk.EW)
        self.artist_frame = ttk.Labelframe(self, text="Artist")
        self.artist_frame.grid(column=0, row=2, sticky=tk.EW, ipady=0)
        self.artist = RoundedIcon.from_text(self.artist_frame, "", self.colors.primary)
        self.artist.pack(side=tk.LEFT)

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
        self.ext_label = ttk.Label(
            ext_frame, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        )
        self.dim_label = ttk.Label(
            dim_frame, cursor="arrow", justify=tk.LEFT, wraplength=240, border=1
        )
        self.score_label.pack()
        self.ext_label.pack()
        self.dim_label.pack()

        self.file = ttk.Label(self, cursor="arrow", justify=tk.LEFT, border=1)
        self.file.grid(column=0, row=4, sticky=tk.NSEW)
        self.file_tooltip = ToolTip(self.file)
        self.tags_frame = ttk.Frame(self)
        self.tags_frame.grid(column=0, row=5, sticky=tk.NSEW)

        self.tags = ttk.Text(
            self.tags_frame, wrap=tk.WORD, width=text_width
        )
        self.tags.pack(fill="both", expand=True)
        self.grid_propagate(False)

        self.add_bindings()

    def add_bindings(self):
        ebinder.bind(BINDING.ON_POST_SELECT, self.on_post_select, self)
        self.file.drag_source_register(DND_FILES)
        self.file.dnd_bind("<<DragInitCmd>>", self.drag_init)
        self.file.bind("<Double-1>", self.start_file)
        self.file.bind("<Button-2>", self.start_file_dir)
        self.tags.bind("<Double-Button-1>", self.tags_double)

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
        logger.info("On Post Select, post id: %s", post_id)
        with PostDb() as postdb:
            post = postdb.posts[post_id]
            post_file = postdb.files[post_id]

        if post_file and post:
            post.file_link = post_file.file
            post.sample_link = post_file.preview
            self.name.configure(text=post.name)
            self.artist.update_text(post_file.artist_name)
            self.score_label.configure(text=post.score)
            self.ext_label.configure(text=f"{post.ext.upper()}")
            self.dim_label.configure(text=f"{post.width}x{post.height}")
            self.file.configure(text=post.file_link)
            self.file_tooltip.text = f"{post.file_link}\n-Double Click: Open\n-Middle Click: Open file location"
            self.tags.config(state=tk.NORMAL)
            self.tags.delete("1.0", tk.END)
            for tag in post.tags:
                self.tags.insert(tk.END, f"{tag}  ")
            self.tags.config(state=tk.DISABLED)
            self.after(0, self.after_on_post_select, post, post_file)

    def after_on_post_select(self, post: Post, post_file: PostFile):
        if post_file:
            if post_file.preview:
                file_name = post_file.preview
            elif post_file.sample:
                file_name = post_file.sample
            else:
                file_name = post_file.file if post.ext not in ("webm", "mp4") else ""

        if file_name:
            if not os.path.exists(file_name):
                return
            thumbnail = ImageUtils.get_tk_thumb(file_name, (190, 190))
            self.thumbnail.config(image=thumbnail)
            self.thumbnail.image = thumbnail


    def tags_double(self, event):
        widget: tk.Text = event.widget
        try:
            index = widget.index(f"@{event.x},{event.y}")
            word = self.get_word(widget, index).strip()
            if word:
                self.query_by_tag(word)
        except Exception:
            pass

    def get_word(self, widget, index):
        try:
            start = widget.search(" ", index, "1.0", backwards=True)
            end = widget.search(" ", index, tk.END)
            return widget.get(start, end)
        except Exception:
            return ""

    def query_by_tag(self, tag):
        if tag in ebinder[BINDING.ARTIST_SET]:
            ebinder.event_generate(BINDING.ON_ARTIST_SELECT, tag)
        else:
            ebinder.event_generate(BINDING.ON_TAG_SELECT, tag)

    def drag_init(self, event):
        file = self.file.cget("text")
        if file:
            return (COPY, DND_FILES, file)
