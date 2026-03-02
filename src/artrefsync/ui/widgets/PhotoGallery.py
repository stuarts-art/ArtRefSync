import os
import threading
import time
import tkinter as tk
from sortedcontainers import SortedSet
import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledText
from threading import Event

from tkinterdnd2 import COPY, DND_FILES
from PIL import ImageTk

from artrefsync.boards.board_handler import PostFile
from artrefsync.db.post_db import PostDb
from artrefsync.utils.TkThreadCaller import TkThreadCaller
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.config import config

from artrefsync.constants import BINDING

# from artrefsync.ui.tag_post_manager import TagPostManager
from artrefsync.utils.EventManager import ebinder

import logging

logger = logging.getLogger()
logger.setLevel(config.log_level)

thread_caller: TkThreadCaller = None


class SimpleFrames:
    frames:list["SimplePhotoLabel"] = []
    frame_map:map = {}

    # @staticmethod
    def __class_getitem__(cls, index):
        if index is not None and index >= 0 and index < len(SimpleFrames.frames):
            return SimpleFrames.frames[index]

    def __init__(self, text: ttk.Text, width_var, height_var):
        self.text = text
        self.width_var = width_var
        self.height_var = height_var
        self.post_ids = []
        self.focused = None
        self.focused_idx = None
        self.reloading=False
        self.last_selected = None
        self.zooming = False

        self.last_focus_prev = time.time()
        self.focussing_prev = False

        

        self.increase_frames()

        ebinder.bind(BINDING.ON_PREV_GALLERY_IMAGE, self.focus_prev, self.text)
        ebinder.bind(BINDING.ON_NEXT_GALLERY_IMAGE, self.focus_next, self.text)
        # ebinder.bind(BINDING.ON_POST_FOCUS_CHANGE, self.update_focus, self.text)
        self.text.bind("q", lambda _: self.change_zoom(-100))
        self.text.bind("e", lambda _: self.change_zoom(+100))
        self.text.bind("w", self.focus_prev_row)
        self.text.bind("a", self.throttled_focus_prev)
        self.text.bind("s", self.focus_next_row)
        self.text.bind("d", self.focus_next)
        self.color=ttk.Style().colors
        SimplePhotoLabel.text = text

    def create_frame(self):

        idx = len(self.frames) if self.frames else 0
        label = SimplePhotoLabel(
            self.text, idx, self.height_var, self.width_var
        )
        self.frames.append(label)
        self.frame_map[f"1.{idx}"] = label

        label.bind("<Visibility>", self.on_visibility)
        label.bind("<MouseWheel>", self.bind_scroll)
        # label.bind("<ButtonRelease-1>", self.add_select_tag)
        label.bind("<Button-1>", self.add_select_tag)
        # label.bind("<FocusIn>", self.on_focus_in)
        # label.bind("<FocusOut>", self.on_focus_out)
        label.bind("<Double-Button-1>",
            lambda e: ebinder.event_generate(BINDING.ON_IMAGE_DOUBLE_CLICK, self.post_ids[e.widget.idx]),
        )
        # label.bind("s", lambda _: ImageUtils.getPhotoThumbnail.cache_clear())
        label.drag_source_register(DND_FILES)
        label.dnd_bind("<<DragInitCmd>>", self.drag_binding)
        # label.config(text=label.idx)
        # self.text.window_create(tk.END, window=label, padx=5, pady=5, align=tk.TOP)
        self.text.window_create(tk.END, window=label, padx=5, pady=5)
        self.scrolling = Event()


    def change_zoom(self, delta):
        if self.zooming:
            return 
        self.zooming = True
        # print(f"Change zoom {delta}")
        old_height = self.height_var.get()
        new_height = old_height + delta
        if new_height < 200:
            new_height = 200
        if new_height > 800:
            new_height = 800
        
        if new_height != old_height:
            self.height_var.set(new_height)
            self.update()
        self.text.after(300, self.clear_zoom)
    
    def clear_zoom(self):
        self.zooming = False




    def change_posts(self, posts):
        if posts == self.post_ids:
            return

        self.text.focus_set()
        logger.info("Changing %s posts.  %s", len(posts), posts[0:5])
        SimplePhotoLabel.posts = posts
        self.post_ids = posts
        self.text.see(self.frames[0])
        self.update()
        # self.add_select_tag()
        # self.focus_on_idx(0)
        self.text.after(100, lambda: self.frames[0].event_generate("<Button-1>"))
    
    def update(self):
        logger.info("Updating Image Gallery")
        ImageUtils.get_tk_thumb.cache_clear()
        ImageUtils.getPilImageThumb.cache_clear()
        thread_caller.cancel(SimplePhotoLabel.get_image_cancel_key)
        for frame in self.frames:
            if frame.bbox:
                frame.get_image()
            else:
                if frame.photo == None:
                    break
                frame.reset()


    # def on_text_selection(self, event):

    #     print(f"ON TEXT SELECTION {event}")
    #     w = event.widget
    #     if isinstance(w, ttk.Label):
    #         self.text.tag_add("sel", w)
    #     try:
    #         pass
    #     except tk.TclError:
    #         pass # No selection or selection cleared

    def add_select_tag(self, e):
        self.text.focus_set()
        logger.info("Add Select Tag %s", e)
        s = e.state
        ctrl_pressed = (s & 0x4) != 0
        shift_pressed = (s & 0x1) != 0
        # print(ctrl_pressed)
        # print(shift_pressed)
        ranges = self.text.tag_ranges('sel')
        if not ranges or (not ctrl_pressed and not shift_pressed):
            if ranges:
                self.text.tag_remove("sel", 1.0, tk.END)
            self.text.tag_add("sel", e.widget)
        elif ctrl_pressed:
            if 'sel' in self.text.tag_names(e.widget):
                logger.info("Removing sel tag from %s", e.widget.pid)
                self.text.tag_remove("sel", e.widget)
            else:
                self.text.tag_add("sel", e.widget)
                index = self.text.index(e.widget)
        elif shift_pressed:
            if 'sel' in self.text.tag_names(e.widget):
                return
            index = self.text.index(e.widget)
            start = min(self.text.index(ranges[0]), index)
            end = max(self.text.index(ranges[0]), index + '+1c')
            self.text.tag_add('sel', start, end)
            # self.set_focus(e)


            # ebinder.event_generate(BINDING.ON_POST_SELECT, self.selected.pid)
            # ebinder.event_generate(BINDING.ON_POST_SELECT, self.selected.pid)
        self.updated_selected_post(self.selected.pid)
        
    def updated_selected_post(self, pid):
        # print(f"Updating Selected Post {pid}")
        if self.last_selected != pid:
            self.last_selected = pid
            ebinder.event_generate(BINDING.ON_POST_SELECT, self.selected.pid)
        

    

    @property
    def selected(self) -> "SimplePhotoLabel":

        ranges = self.text.tag_ranges("sel")
        # print(self.text)
        # print(ranges)
            # first:SimplePhotoLabel = self.text.nametowidget(ranges[0])
        # print(f"Selected Result {start}")
        if ranges:
            first = self.text.index("sel.first")
            return self.frame_map[first]

            # first:SimplePhotoLabel = self.text.nametowidget(ranges[0])
            # name =  self.text.window_cget(ranges[0], "window")
            # widget =  self.text.nametowidget(name)

            # print(f"Selected Result {widget}")
            # print(selected)
            # return first
        return None



        

    def drag_binding(self, event):
        # print("EVENT printselected")
        # print(event)
        try:
            files = []
            ranges = self.text.tag_ranges('sel')
            # print(ranges)
            # if ranges:
            #     for i in range(0, len(ranges), 2):
            #         first:SimplePhotoLabel = self.text.window_cget()
            #         # first:SimplePhotoLabel = self.text.nametowidget(ranges[i])
            #         second = self.text.nametowidget(ranges[i+1])

            #         while(first and first != second):
            #             files.append(first.file.file)
            #             first = first.nextL
            first = self.text.index("sel.first")
            last = self.text.index("sel.last")
            for text_char in self.text.dump(first, last, window=True):
                name = text_char[1]
                photo: SimplePhotoLabel = self.text.nametowidget(name)
                if 'sel' in self.text.tag_names(photo):
                    if photo.file:
                        if photo.file.ext in ["webm", "mp4"]:
                            files.append(photo.file.preview)
                        else:
                            files.append(photo.file.file)
                # print(frame.post.file)
            # print(files)
            if files:
                data = tuple(file for file in files)
                dnd_packet = (COPY, DND_FILES, data)
                # dnd_packet = (DND_FILES, data)
                # print(dnd_packet)
                return dnd_packet
            # else:
            #     frame:SimplePhotoLabel = self.text.nametowidget(event.widget)
            #     if not frame:
            #         return
            #     file = frame.file.file
            #     if not file:
            #         return
            #     dnd_packet = (COPY, DND_FILES, file)
            #     return dnd_packet
 

        except tk.TclError:
            frame:SimplePhotoLabel = self.text.nametowidget(event.widget)
            if not frame:
                return
            file = frame.file.file
            if not file:
                return
            dnd_packet = (COPY, DND_FILES, file)
            # print(dnd_packet)
            return dnd_packet

    def update_focus(self, pid):
        # self.focused = pid
        if pid in self.post_ids:
            focused_idx = self.post_ids.index(pid)
            self.focus_on_idx(focused_idx)

    def increase_frames(self, target = None):
        logger.info("CREATING MORE FRAMES")
        if not target:
            for i in range(50):
                self.create_frame()
        else:
            while len(self.frames) < target:
                self.create_frame()
    
    def focus_on_idx(self, idx):
        if idx < 0:
            return
        elif idx >= len(self.frames):
            return
        frame = self.frames[idx]
        # frame.label.focus_set()
        # frame.focus_set()
        self.text.see(frame)
        self.scrolling.clear()

    def bind_scroll(self, event):
        self.text.event_generate("<MouseWheel>", delta=event.delta)


    def scroll_delta(self, delta):
        self.text.event_generate("<MouseWheel>", delta=delta)

    def scroll_easing(self, delta, ms:list[int]):
        for m in ms:
            self.text.after(m, self.scroll_delta, delta)

    def throttled_focus_prev(self, e=None):
        if self.focussing_prev:
            return
        self.focussing_prev = True
        time_since_last_prev = time.time() - self.last_focus_prev

        wait_time_ms = min(max(0, int((.3 - time_since_last_prev) * 1000)),300)
        self.text.after(wait_time_ms, self.focus_prev)




    def focus_prev(self, e = None):
        self.focussing_prev=False
        self.last_focus_prev = time.time()
        if self.selected:
            if self.selected.prev:
                widget = self.selected.prev
                self.text.tag_remove("sel", 1.0, tk.END)
                self.text.tag_add("sel", widget)
                if not self.selected.same_row(widget):
                    self.text.event_generate("<MouseWheel>", delta=120)
                self.updated_selected_post(widget.pid)
                self.text.after(0, self.text.see, widget)
        else:
            for frame in self.frames:
                if frame.bbox:
                    frame.event_generate("<Button-1>")

        # # if self.scrolling.is_set():
        # #     return
        # self.scrolling.is_set()
        # frame = e.widget
        # # print(self.text.bbox(frame))
        # next = self.frames[frame.idx + 1]
        # # print(self.text.bbox(next))

    
    def focus_next(self, e = None):
        if self.selected:
            if self.selected.next:
                widget = self.selected.next
                self.text.tag_add("sel", widget)
                self.text.tag_remove("sel", 1.0, self.text.index(widget))
                self.text.tag_remove("sel", f"{self.text.index(widget)}+1c", tk.END)
                if not self.selected.same_row(widget):
                    self.text.event_generate("<MouseWheel>", delta=-120)
                self.updated_selected_post(widget.pid)
                self.text.after(0, self.text.see, widget)
            return
        else:
            for frame in self.frames:
                if frame.bbox:
                    frame.event_generate("<Button-1>")
        

        # if self.scrolling.is_set():
        #     return
        # self.scrolling.is_set()

        # frame:SimplePhotoLabel = e.widget

        # next = self.frames[frame.idx + 1]
        # # print(self.text.bbox(frame))
        # # print(self.text.bbox(next))
        # if not frame.same_row(next):
        #     self.text.event_generate("<MouseWheel>", delta=-120)
        # # self.scroll_easing(-120, [8,14,18,20,26,])
        # frame = e.widget
        # self.text.after(16, self.focus_on_idx, frame.idx + 1)

    def focus_prev_row(self, e = None):

        label:SimplePhotoLabel = self.selected
        prev = label.prev_row
        if prev:
            self.update_focus(prev.pid)
            # self.focus_on_idx(next.idx)

    def focus_next_row(self, e = None):
        label:SimplePhotoLabel = self.selected
        next = label.next_row
        if next:
            self.update_focus(next.pid)
            # self.focus_on_idx(next.idx)
    
    def set_focus(self, e = None):
        logger.info("Set Focus on %s", e.widget.pid)
        self.focus_on_idx(e.widget.idx)

    def on_visibility(self, e):
        widget: SimplePhotoLabel = e.widget
        if widget.bbox:
            logger.info("Visibility TRUE for %s", widget.pid)
            idx = widget.idx
            widget.get_image()
            if widget.next:
                widget.next.get_image()
                if widget.next.next:
                    widget.next.get_image()
                

            if len(self.frames) - idx  < 10 and len(self.frames) < len(self.post_ids):
                self.increase_frames(idx + 10)
        else:
            logger.info("Visibility: FALSE for %s. Resetting.", widget.pid)
            widget.reset()
            # logger.info("On visibility NO for %s", widget.pid)
            # self.text.after(1000, widget.reset, True)
        return


class SimplePhotoLabel(tk.Label):
    posts = []
    post_files:dict[str,PostFile] = {}
    load_target = 0
    load_idx = 0

    text:ttk.Text = None

    default_height = 15
    default_width = 20
    reloading = False
    get_image_cancel_key = "photo_label_get_image"


    @staticmethod
    def get_post_file(pid) -> PostFile:
        if pid not in SimplePhotoLabel.post_files:
            with PostDb() as post_db:
                file = post_db.files[pid] if pid in post_db.files else None
            SimplePhotoLabel.post_files[pid] = file
        return SimplePhotoLabel.post_files[pid]

    def __init__(self, root, idx, height_var: ttk.IntVar, width_var: ttk.IntVar):
        # logger.info("CREATING FRAME %s", idx)
        self.idx = idx
        self.photo = None
        self.width_var = width_var
        self.height_var = height_var
        # super().__init__(root, text=f"TEXT {idx}",  takefocus=True, height=50, width=50)
        # super().__init__(root,  takefocus=True, height=50, width=50)
        # super().__init__(root,  takefocus=True, height=10, width=20, padx=3, pady=3)
        super().__init__(root,  height=self.default_height, width=self.default_width, padx=5, pady=5)
        self.pid = ""
        # self.loading = False
        self.image_h = None

    @property
    def bbox(self):
        return SimplePhotoLabel.text.bbox(self)

    @property
    def prev(self) -> "SimplePhotoLabel":
        # print("Prev on {self} with {self.idx} on {self.}")
        return SimpleFrames[self.idx - 1]

    @property
    def next(self) -> "SimplePhotoLabel":
        if self.idx < len(SimpleFrames.frames):
            return SimpleFrames[self.idx + 1]
        else:
            return self
    
    def same_row(self, next):

        if self and self.bbox and next and next.bbox:
            x = self.bbox[1]
            y = self.bbox[3]
            x0 = next.bbox[1]
            y0 = next.bbox[3]
            if y < x0:
                return False
            elif y0 < x:
                return False
        return True

    @property
    def prev_row(self):
        if not self:
            return None
        prev = self.prev
        # print(f"Prev is {prev}")
        while prev and prev.bbox:
            if not self.same_row(prev):
                return prev
            
            prev = prev.prev
        return prev

    @property
    def next_row(self):
        if not self:
            return None
        next = self.next
        # print(f"Next is {next}, {next.bbox}, {self.bbox}")
        while next:
            if not next.bbox or (next.bbox[1] > self.bbox[3]):
                return next
            next = next.next
        return next

    def reset(self, check_viewable = False):
        if check_viewable and not self.bbox:
            logger.info("Reset Skipped for %s. It is currently in View.", self.pid)
            return
        if self.pid:
            logger.info("Resetting %s", self.pid)
        self.image=None
        # self.pid = None
        self.photo = None
        self.file=None
        # self.config(image=None)
        self.loading = False
        if not check_viewable:
            self.config(image = None, height=self.default_height, width=self.default_width)


    def update_size(self):
        # height=self.file.height
        # width=self.file.width
        ratio = self.file.width/self.file.height

        if ratio * self.height_var.get() > self.width_var.get():
            width = self.width_var.get()
            height = width / ratio
        else:
            width = self.height_var.get() * ratio
            height = self.height_var.get()
        
        self.config(height = int(height), width= int(width))
        # self.config(height=photo.height(), width=photo.width())


    def get_image(self):
        # if self.reloading:
        #     return
        # self.reloading = True
        if self.idx >= len(SimplePhotoLabel.posts):
            self.image=None
            self.config(image=None)
            return
        
        pid = SimplePhotoLabel.posts[self.idx]
        if not self.cget("image") or self.pid != pid or self.image_h != self.height_var.get():
            self.pid = pid
            self.file:PostFile = SimplePhotoLabel.get_post_file(pid) 
            if self.file:
                self.image_h = self.height_var.get()
                # file = self.file.thumbnail

                self.file_name = self.file.preview if self.file.ext in ("webm", "mp4") else self.file.file
                if not os.path.exists(self.file.preview):
                    self.file_name = self.file.file
                # if self.file.ext in ["mp4", "webm"]:
                # else:
                #     file = self.file.thumbnail
                thread_caller.add(
                    ImageUtils.getPilImageThumb,
                    self.set_image,
                    self.get_image_cancel_key,
                    self.file_name,
                    (self.width_var.get(), self.height_var.get())
                )
            self.pid = pid

    def set_image(self, image):
        if image:
            photo = ImageUtils.get_tk_thumb(self.file_name, size = (self.width_var.get(), self.height_var.get()))
            if photo:
                self.image = photo
                self.config(image=photo, height = photo.height(), width=photo.width())
                self.loading = False
                logger.info("Setting Image")
            else:
                logger.info("ERROR Loading %s %s", self.file.id, self.file.file)
        
        self.reloading = False
    

class PhotoImageGallery(ScrolledText):
    def __init__(self, root, thread_caller_arg=None):
        super().__init__(root)

        global thread_caller
        self.tag_sets: dict[str, set] = {}

        self.root = root
        thread_caller = thread_caller_arg
        
        color=ttk.Style().colors
        self.text.tag_configure("sel", background=color.warning, foreground=color.warning, underline=1)

        self.frame_height = ttk.IntVar(self, value=500)
        self.frame_width = ttk.IntVar(self, value=500)

        self.height_label = ttk.Label(self, textvariable=self.frame_height)
        self.height_label.place(relx=.95, rely= 0.0, anchor=tk.NE)

        self.simple_frames = SimpleFrames(
            self.text, self.frame_width, self.frame_height
        )
        self.text.config(state="disabled")
        self.bind("<Configure>", self.update_width)
        ebinder.bind(BINDING.ON_FILTER_UPDATE, self.change_tags, self)

    def update_width(self, e):
        if e.widget == self:
            width = self.winfo_width()
            self.frame_width.set(width - 50)


        last_bboxed = None
        for i, frame in enumerate(self.simple_frames.frames):
            if frame.bbox:
                frame.get_image()
                last_bboxed = i
            else:
                # if frame.photo == None:
                #     break
                # frame.reset()
                if last_bboxed and i - last_bboxed > 3:
                    break


    def get_posts_from_tags(self, tags):
        posts = []
        if isinstance(tags, str):
            tags = [
                tags,
            ]
        with PostDb() as postdb:
            tags = [tag for tag in tags if tag in postdb.tag_posts]
            for tag in tags:
                if tag not in self.tag_sets:
                    posts = postdb.tag_posts.loads_blob(tag)
                    if posts:
                        self.tag_sets[tag] = posts

        post_sets = [self.tag_sets[tag] for tag in tags if tag in self.tag_sets]
        if len(post_sets) == 0:
            posts = []
        elif len(post_sets) == 1:
            posts = post_sets[0]
        else:
            posts = post_sets[0].intersection(*post_sets[1:])
        return sorted(posts, reverse=True)

    def dumb_change_tags(self, posts):
        logger.info("Dumb Change Tags with %d posts", len(posts))
        self.simple_frames.change_posts(posts)

    def change_tags(self, tags):
        cancel_key = "change_tags"
        if tags:
            self.tags = tags
            thread_caller.cancel(cancel_key)
            thread_caller.add(self.get_posts_from_tags, self.dumb_change_tags, cancel_key, tags)
            return
    
        else:
            with PostDb() as post_db:
                posts_ids = post_db.posts.select(conditions=None, select_fields=["id"], suffix=" ORDER BY id DESC LIMIT 1000")
            # print(f"POST IDS: {posts_ids}")
            posts = [item["id"] for item in posts_ids]
            self.simple_frames.change_posts(posts)
