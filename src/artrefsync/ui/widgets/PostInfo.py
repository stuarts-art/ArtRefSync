import ttkbootstrap as ttk
import tkinter as tk
from tkinter.font import nametofont
import os
from tkinterdnd2 import COPY, DND_FILES

from artrefsync.boards.board_handler import Post
from artrefsync.constants import BINDING
from artrefsync.db.post_db import PostDb
from artrefsync.ui.widgets import InputTreeView
from artrefsync.ui.widgets.PhotoLabel import PhotoLabel
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
        # self.width = 100
        super().__init__(root, *kwargs, width=4)
        self.grid(column=0, row=0, sticky=tk.NSEW)
        print(self.winfo_width())
        self.thread_caller = TkThreadCaller
        text_width = 25
        self.font = nametofont("TkDefaultFont")
        self.colors = ttk.Style().colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, minsize=200)
        self.grid_rowconfigure(5, weight=1)

        self.thumbnail = tk.Label(self)
        # self.thumbnail = PhotoLabel(self, None, 190, 190)
        self.thumbnail.grid(column=0, row=0, sticky=tk.NSEW)
        self.name = ttk.Text(self, height=1, width=text_width)
        self.name.grid(column=0, row=1, sticky=tk.EW)
        self.artist = tk.Text(self, height=1, width=text_width)
        self.artist.grid(column=0, row=2, sticky=tk.EW)
        self.score = ttk.Text(self, height=1, width=text_width)
        self.score.grid(column=0, row=3, sticky=tk.EW)
        self.file = ttk.Label(self, cursor="arrow", justify=tk.LEFT, wraplength=240)
        self.file.grid(column=0, row=4, sticky=tk.NSEW)

        self.tags_frame = ttk.Frame(self)
        self.tags_frame.grid(column=0, row=5, sticky=tk.NSEW)
        # self.tags= 


        self.tags = ttk.Text(
            self.tags_frame, wrap=tk.WORD, width=text_width
        )  # , bg=self.colors.get('primary'))
        self.tags.pack(fill="both", expand=True)

        self.add_bindings()

    def add_bindings(self):
        ebinder.bind(BINDING.ON_POST_SELECT, self.on_post_select, self)
        self.file.drag_source_register(DND_FILES)
        self.file.dnd_bind("<<DragInitCmd>>", self.drag_init)
        self.file.bind("<Double-1>", self.start_file)
        self.tags.bind("<Double-Button-1>", self.tags_double)

    def start_file(self, event):
        file = self.file.cget("text")
        # file = self.file.get(1.0, 'end-1c')
        if file:
            os.startfile(file)

    def on_post_select(self, post_id):
        logger.info("On Post Select, post id: %s", post_id)
        with PostDb() as postdb:
            post = postdb.posts[post_id]
            post_file = postdb.files[post_id]
            # print(post_file)

        if post_file and post:
            post.file_link = post_file.file
            post.sample_link = post_file.preview
            self.winfo_toplevel
            self.name.delete("1.0", tk.END)
            self.name.insert(tk.END, post.name)
            self.artist.delete("1.0", tk.END)
            self.artist.insert(tk.END, post.artist_name)
            self.score.delete("1.0", tk.END)
            self.score.insert(tk.END, post.score)
            self.file.configure(text=post.file_link)
            self.tags.config(state=tk.NORMAL)
            self.tags.delete("1.0", tk.END)
            self.tags.config(state=tk.DISABLED)

            self.after(0, self.after_on_post_select(post))

    def after_on_post_select(self, post: Post):
        if self.thumbnail:
            file_name = post.sample_link if post.ext in ("webm", "mp4") else post.file_link
            if not os.path.exists(post.sample_link):
                file_name = post.file_link

            thumbnail = ImageUtils.get_tk_thumb(file_name, (190, 190))
            self.thumbnail.config(image=thumbnail)
            self.thumbnail.image=thumbnail

        self.tags.config(state=tk.NORMAL)
        for tag in post.tags:
            width = self.font.measure(tag)
            ticon = ttk.Label(self.tags, text=tag, padding= 1)
            # ticon = RoundedIcon(
            #     self.tags, tag, size=(width + 10, 22)
            #     # , normal_color=self.colors.primary
            #     # , bootstyle="primary.inverted"
            # )
            self.tags.insert(tk.END, f"{tag}  ")
        self.tags.config(state=tk.DISABLED)

    def tags_double(self, event):
        widget:tk.Text = event.widget
        try:
            index = widget.index(f"@{event.x},{event.y}")
            word = self.get_word(widget, index).strip()
            if word:
                self.query_by_tag(word)

        except:
            pass
        
    def get_word(self, widget, index):
        try:
            start = widget.search(" ", index, "1.0", backwards=True)
            end = widget.search(" ", index, tk.END)
            return widget.get(start, end)
        except:
            return ""

 

    def query_by_tag(self, tag):
        if tag in ebinder[BINDING.ARTIST_SET]:
            ebinder.event_generate(BINDING.ON_ARTIST_SELECT, tag)
        else:
            ebinder.event_generate(BINDING.ON_TAG_SELECT, tag)

    def drag_init(self, event):
        file = self.file.cget("text")
        if file:
            # os.startfile(file)
            return (COPY, DND_FILES, file)

