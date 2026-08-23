import logging
import platform
import subprocess
import time
import tkinter as tk
from collections import deque
from typing import ClassVar

import ttkbootstrap as ttk
from PIL import ImageTk
from tkinterdnd2 import COPY, DND_FILES

from artrefsync.boards.board_models import Post
from artrefsync.config import get_config
from artrefsync.constants import APP, BINDING, HOTKEY, TABLE
from artrefsync.db.post_db import PostDb
from artrefsync.stores.store_models import PostFile
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger()


class PhotoImageGallery(ttk.Frame):
    def __init__(self, root: ttk.Frame, thread_caller_arg=None):
        logger.info("Init Photo Image Gallery.")
        self.root = root
        super().__init__(root)

        self.init_vars()
        self.init_widgets()
        self.init_scaffolding()
        self.init_bindings()
        logger.info("Init Photo Image Complete.")
        event_binder[BINDING.GALLERY_WIDGET] = self

    def init_vars(self):
        logger.info("Init vars")
        self.colors = ttk.Style().colors
        self.tags = ["Initial Value"]
        self.tag_sets: dict[str, set] = {}
        self.frame_height = ttk.IntVar(self, value=500)
        self.frame_width = ttk.IntVar(self, value=500)
        self.color = ttk.Style().colors

    def init_widgets(self):
        logger.info("Init widgets")
        self.scrolled_text = ttk.ScrolledText(self, autohide=False)
        self.text = self.scrolled_text.text
        self.simple_frames = SimpleFrames(
            self.scrolled_text, self.frame_width, self.frame_height
        )
        self.text.tag_configure(
            "sel",
            background=self.color.warning,
            foreground=self.color.warning,
            underline=1,
        )
        self.text.tag_configure("center", justify="center")
        self.text.config(state="disabled")

    def init_scaffolding(self):
        logger.info("Init scaffolding")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.scrolled_text.grid(row=1, column=0, sticky=tk.NSEW)

    def init_bindings(self):
        logger.info("Init bindings")
        self.bind("<Configure>", self.update_width)
        self.bind("<FocusIn>", self.simple_frames.on_swap)
        event_binder.bind(BINDING.ON_FILTER_UPDATE, self.change_tags, self)
        event_binder.bind(BINDING.ON_SORT_BY_UPDATE, self.update_posts, self)
        event_binder.bind(BINDING.ON_DB_UPDATE, self.update_posts, self)

    def update_sort_var(self, e: tk.Event):
        self.sort_menu.post(
            e.widget.winfo_rootx() + 5, e.widget.winfo_rooty() + e.widget.winfo_height()
        )

    def update_width(self, e):
        if e.widget == self:
            width = self.winfo_width()
            self.frame_width.set(width - 50)

    def change_tags(self, tags=None):
        logger.info("Updating tags to be %s", self.tags)
        if self.tags == tags:
            return
        if tags is None:
            tags = []
        self.tags = tags
        self.text.see("1.0")
        self.update_posts()

    def update_posts(self, *args, **kwargs):
        cancel_key = "get_sorted_posts"
        sort_by = event_binder.get_or_default(BINDING.SORT_BY, "id")
        sort_dir = event_binder.get_or_default(BINDING.SORT_DIR, "DESC")
        logger.info(
            "Displaying image gallery, sorted by: %s %s, with tags: %s",
            sort_by,
            sort_dir,
            self.tags,
        )
        thread_caller.add(
            self.get_sorted_posts,
            self.simple_frames.change_posts,
            cancel_key,
            tags=self.tags,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        thread_caller.add(
            self.get_sorted_posts,
            self.update_count,
            "get_sorted_count",
            tags=self.tags,
            as_count=True,
        )

    def update_count(self, row):
        if row:
            event_binder.event_generate(BINDING.ON_SET_TOP_RIGHT_TEXT, row)
        else:
            event_binder.event_generate(BINDING.ON_SET_TOP_RIGHT_TEXT, 0)

    def get_sorted_posts(
        self, tags, sort_by="", sort_dir="", limit=200, offset=0, as_count=False
    ):
        with PostDb() as post_db:
            sorted_posts = post_db.posts_in_intersection(
                tags, sort_by, sort_dir, limit=limit, offset=offset, as_count=as_count
            )
        return sorted_posts


class SimpleFrames:
    frames: ClassVar[list[SimplePhotoLabel]] = []
    frame_map: ClassVar[dict] = {}

    def __init__(self, scrolled_text: ttk.ScrolledText, width_var, height_var):
        self.scrolled_text = scrolled_text
        self.text = scrolled_text.text
        SimplePhotoLabel.text = scrolled_text.text
        self.width_var = width_var
        self.height_var = height_var

        self.post_ids = []
        self.focused = None
        self.focused_idx = None
        self.last_selected = None
        self.zooming = False
        self.min_focus_delay = 100
        self.last_focus_prev = time.time() - self.min_focus_delay
        self.last_focus_next = time.time() - self.min_focus_delay
        self.focussing_prev = False
        self.focussing_next = False
        self.color = ttk.Style().colors
        self.init_bindings()
        self.increase_frames()
        self.last_event = ()
        if self.frames:
            self.add_select_tag(self.frames[0], False, False)

    def __class_getitem__(cls, index) -> SimpleFrames:
        if index is not None and index >= 0 and index < len(SimpleFrames.frames):
            return SimpleFrames.frames[index]

    def init_bindings(self):
        event_binder.bind(BINDING.ON_PREV_GALLERY_IMAGE, self.focus_prev, self.text)
        event_binder.bind(BINDING.ON_NEXT_GALLERY_IMAGE, self.focus_next, self.text)
        event_binder.bind(BINDING.ON_ZOOM_DELTA, self.change_zoom, self.text)
        self.text.bind("<FocusOut>", self.unbind_canvas_escape)
        self.text.bind("<KeyRelease-space>", self.on_space)
        self.text.bind("<Key>", lambda e: self.text.after_idle(self.__keystroke, e))
        self.text.bind(
            "<FocusIn>", lambda e: self.text.after(100, self.add_escape_binding)
        )

    def __keystroke(self, event: tk.Event):
        keysym = event.keysym
        state = event.state

        ctrl_pressed = (state & 0x4) != 0

        if keysym == "q":
            event_binder.event_generate(BINDING.ON_ZOOM_DELTA, -100)
        elif keysym == "e":
            event_binder.event_generate(BINDING.ON_ZOOM_DELTA, +100)
        elif keysym in config[HOTKEY.UP_LIST]:
            self.throttled_focus_prev()
        elif keysym in config[HOTKEY.LEFT_LIST]:
            event_binder.event_generate(BINDING.ON_GALLERY_SHIFT_TAB)
        elif keysym in config[HOTKEY.DOWN_LIST]:
            self.throttled_focus_next()
        elif keysym == "Return":
            event_binder.event_generate(BINDING.ON_GALLERY_SHIFT_TAB, True)
        elif keysym == "z":
            event_binder.event_generate(BINDING.ON_TEXT_Z)
        elif keysym == "x":
            event_binder.event_generate(BINDING.ON_TEXT_X)
        elif keysym == "c":
            if ctrl_pressed:
                self.on_ctrl_c()
            else:
                event_binder.event_generate(BINDING.ON_TEXT_C)
        elif keysym == "grave":
            event_binder.event_generate(BINDING.ON_TEXT_ESCAPE)
        elif keysym == "Tab":
            event_binder.event_generate(BINDING.ON_GALLERY_SHIFT_TAB)
        elif keysym == "BackSpace":
            event_binder.event_generate(BINDING.RUN_TAG_REMOVE_LAST)

        else:
            return ""

        logger.debug(
            "KeyCode: %s, KeySym: %s, State: %s",
            event.keycode,
            event.keysym,
            event.state,
        )
        return "break"  # Prevents old bindings from triggering.

    def on_swap(self, *e):
        self.text.focus_set()

        if self.selected and self.selected.bbox:
            self.text.see(self.selected)
        else:
            for frame in self.frames:
                if frame.bbox:
                    self.text.see(frame)
                    self.add_select_tag(frame, False, False)

    def on_space(self, *e):
        logger.info("ON SPACE")
        if self.selected and self.selected.bbox:
            event_binder.event_generate(
                BINDING.ON_IMAGE_DOUBLE_CLICK, self.selected.pid
            )
        else:
            for frame in self.frames:
                if frame.bbox:
                    self.text.see(frame)
                    self.add_select_tag(frame, False, False)
                    event_binder.event_generate(
                        BINDING.ON_IMAGE_DOUBLE_CLICK, frame.pid
                    )
                    break

    def unbind_canvas_escape(self, *_):
        pass

    def add_escape_binding(self, *_):
        if self.selected:
            self.text.see(self.selected)
        else:
            self.text.after_idle(
                lambda: self.frames[0].event_generate("<ButtonRelease-1>")
            )

    def create_frame(self):
        idx = len(self.frames) if self.frames else 0
        label = SimplePhotoLabel(
            self.text, idx, self.height_var, self.width_var, bg=self.color.inputbg
        )
        self.frames.append(label)
        self.frame_map[f"1.{idx}"] = label
        label.bind("<Visibility>", self.on_visibility)
        label.bind("<MouseWheel>", self.bind_scroll)
        label.bind("<ButtonRelease-1>", self.add_select_tag_handler)
        label.bind("<Double-1>", self.on_double_button_1)
        label.drag_source_register(DND_FILES)
        label.dnd_bind("<<DragInitCmd>>", self.drag_binding)
        self.text.window_create(tk.END, window=label, padx=3, pady=3)
        self.text.tag_add("center", label)

    def on_double_button_1(self, e):
        self.text.focus_set()
        event_binder.event_generate(
            BINDING.ON_IMAGE_DOUBLE_CLICK, self.post_ids[e.widget.idx]
        )

    def bind_b2(self, e: tk.Event):
        edict = {k: v for k, v in e.__dict__.items() if k not in ["num"]}
        self.text.event_generate("<ButtonPress-2>", **edict)

    def bind_b2_motion(self, e: tk.Event):
        edict = {k: v for k, v in e.__dict__.items() if k not in ["num"]}
        self.text.event_generate("<B2-Motion>", **edict)

    def bind_scroll(self, event):
        self.text.event_generate("<MouseWheel>", delta=event.delta)

    def change_zoom(self, delta):
        logger.info("Changing zoom by %s", delta)
        if self.zooming:
            return
        self.zooming = True
        old_height = self.height_var.get()
        new_height = old_height + delta
        new_height = max(new_height, 250)
        new_height = min(new_height, self.text.winfo_height())
        if new_height != old_height:
            self.height_var.set(new_height)
            self.update()
        self.text.after_idle(self.clear_zoom)

    def clear_zoom(self):
        self.zooming = False

    def change_posts(self, posts):
        if posts is None:
            posts = []
        if posts == SimplePhotoLabel.post_ids:
            return
        logger.info("%s posts recieved for change_post", len(posts))
        self.post_ids = posts
        SimplePhotoLabel.post_ids = posts
        self.update()
        self.text.update_idletasks()
        # self.text.after(100, lambda: self.frames[0].event_generate("<ButtonRelease-1>"))
        if self.frames:
            event_binder.event_generate(BINDING.ON_POST_SELECT, self.frames[0].pid)

    def update(self, reset=True):
        logger.info("Updating Image Gallery")
        # self.text.yview_moveto(0.0)
        # self.update_focus()
        # self.text.update_idletasks()
        # self.focus_on_idx(0)
        # self.text.mark_set("insert", "1.0")
        self.text.yview_moveto(0)
        self.focus_on_idx(0)
        # self.text.see("1.0")

        thread_caller.cancel(SimplePhotoLabel.get_image_cancel_key)
        self.text.yview_moveto(0)
        for i, frame in enumerate(self.frames):
            if frame.bbox:
                frame.get_image(True)
            elif reset:
                frame.reset()
        self.text.after(100, self.text.yview_moveto, 0)

    def add_select_tag_handler(self, e: tk.Event):
        self.text.focus_set()
        logger.debug("Add Select Tag %s", e)
        s = e.state
        ctrl_pressed = (s & 0x4) != 0
        shift_pressed = (s & 0x1) != 0
        self.add_select_tag(e.widget, ctrl_pressed, shift_pressed)

    def add_select_tag(self, widget, ctrl_pressed=False, shift_pressed=False):
        ranges = self.text.tag_ranges("sel")
        if not ranges or (not ctrl_pressed and not shift_pressed):
            if ranges:
                self.text.tag_remove("sel", 1.0, tk.END)
            self.text.tag_add("sel", widget)
        elif ctrl_pressed:
            if "sel" in self.text.tag_names(widget):
                logger.debug("Removing sel tag from %s", widget.pid)
                self.text.tag_remove("sel", widget)
            else:
                self.text.tag_add("sel", widget)
                index = self.text.index(widget)
        elif shift_pressed:
            if "sel" in self.text.tag_names(widget):
                return
            index = self.text.index(widget)
            start = min(self.text.index(ranges[0]), index)
            end = max(self.text.index(ranges[0]), index + "+1c")
            self.text.tag_add("sel", start, end)

        if self.selected is not None:
            self.updated_selected_post(self.selected.pid)

    def updated_selected_post(self, pid):
        if self.last_selected != pid:
            self.last_selected = pid
            event_binder.event_generate(BINDING.ON_POST_SELECT, self.selected.pid)

    @property
    def selected(self) -> SimplePhotoLabel:
        ranges = self.text.tag_ranges("sel")
        if ranges:
            first = self.text.index("sel.first")
            return self.frame_map[first]
        return None

    def get_selected_files(self):
        files = []
        first = self.text.index("sel.first")
        last = self.text.index("sel.last")
        for text_char in self.text.dump(first, last, window=True):
            name = text_char[1]
            photo: SimplePhotoLabel = self.text.nametowidget(name)
            if "sel" in self.text.tag_names(photo) and photo.file:
                files.append(photo.file.file)
        return files

    def copy_files_to_clipboard(self, file_paths):
        if platform.system() == "Windows":
            files = ",".join([f"'{path}'" for path in file_paths])
            command = f'powershell -command "Set-Clipboard -Path {files}"'
            subprocess.run(command, shell=True)  # noqa: PLW1510
        else:
            logger.warning("Copy not implemented for OS %s", platform.system())

    def on_ctrl_c(self, *e):
        files = self.get_selected_files()
        self.copy_files_to_clipboard(files)

    def drag_binding(self, event):
        try:
            files = self.get_selected_files()
            if files:
                data = tuple(file for file in files)
                dnd_packet = (COPY, DND_FILES, data)
                return dnd_packet
        except tk.TclError:
            frame: SimplePhotoLabel = self.text.nametowidget(event.widget)
            if not frame:
                return
            file = frame.file.file
            if not file:
                return
            dnd_packet = (COPY, DND_FILES, file)
            return dnd_packet

    def update_focus(self, pid):
        if pid in self.post_ids:
            focused_idx = self.post_ids.index(pid)
            self.focus_on_idx(focused_idx)

    def increase_frames(self, target=None):
        logger.debug("CREATING MORE FRAMES")
        if not target:
            for i in range(50):
                self.create_frame()
        else:
            while len(self.frames) < target:
                self.create_frame()

    def focus_on_idx(self, idx):
        if idx < 0 or idx >= len(self.frames):
            return
        frame = self.frames[idx]
        self.text.see(frame)

    def scroll_delta(self, delta):
        self.text.event_generate("<MouseWheel>", delta=delta)

    def scroll_easing(self, delta, ms: list[int]):
        for m in ms:
            self.text.after(m, self.scroll_delta, delta)

    def throttled_focus_prev(self, e=None):
        if self.focussing_prev:
            return
        self.focussing_prev = True
        time_since_last_prev = time.time() - self.last_focus_prev
        wait_time_ms = min(
            max(0, int((0.3 - time_since_last_prev) * 1000)), self.min_focus_delay
        )
        self.text.after(wait_time_ms, self.focus_prev)
        return "break"

    def focus_prev(self, e=None):
        self.focussing_prev = False
        self.last_focus_prev = time.time()
        if self.selected:
            if widget := self.selected.prev:
                self.text.tag_remove("sel", 1.0, tk.END)
                self.text.tag_add("sel", widget)
                self.updated_selected_post(widget.pid)
                if not self.selected.same_row(widget) and widget.bbox:
                    self.text.event_generate("<MouseWheel>", delta=+120)
                self.text.after_idle(self.text.see, widget)
        else:
            for frame in self.frames:
                if frame.bbox:
                    frame.event_generate("<Button-1>")

    def throttled_focus_next(self, e=None):
        if self.focussing_next:
            return
        self.focussing_next = True
        time_since_last_next = time.time() - self.last_focus_next

        wait_time_ms = min(
            max(0, int((0.3 - time_since_last_next) * 1000)), self.min_focus_delay
        )
        self.text.after(wait_time_ms, self.focus_next)
        return "break"

    def focus_next(self, e=None):
        self.focussing_next = False
        self.last_focus_next = time.time()
        if self.selected:
            if widget := self.selected.next:
                self.text.tag_add("sel", widget)
                self.text.tag_remove("sel", 1.0, self.text.index(widget))
                self.text.tag_remove("sel", f"{self.text.index(widget)}+1c", tk.END)
                self.updated_selected_post(widget.pid)
                if not self.selected.same_row(widget) and widget.bbox:
                    self.text.event_generate("<MouseWheel>", delta=-120)
                self.text.see(widget)
            return
        else:
            for frame in self.frames:
                if frame.bbox:
                    frame.event_generate("<Button-1>")
                    # break

    def focus_prev_row(self, e=None):
        label: SimplePhotoLabel = self.selected
        prev = label.prev_row
        if prev:
            self.text.event_generate("<MouseWheel>", delta=+120)
            self.update_focus(prev.pid)
            widget = prev
            self.text.tag_remove("sel", 1.0, self.text.index(widget))
            self.text.tag_remove("sel", f"{self.text.index(widget)}+1c", tk.END)
            self.updated_selected_post(widget.pid)
            self.text.after_idle(self.text.see, widget)

    def focus_next_row(self, e=None):
        label: SimplePhotoLabel = self.selected
        next = label.next_row
        if next:
            if self.selected:
                if self.selected.next:
                    widget = next
                    self.text.event_generate("<MouseWheel>", delta=-120)
                    self.text.tag_add("sel", widget)
                    self.text.tag_remove("sel", 1.0, self.text.index(widget))
                    self.text.tag_remove("sel", f"{self.text.index(widget)}+1c", tk.END)
                    self.updated_selected_post(widget.pid)
                    self.text.see(widget)
                return
            else:
                for frame in self.frames:
                    if frame.bbox:
                        frame.event_generate("<Button-1>")
                        break

    def set_focus(self, e=None):
        logger.debug("Set Focus on %s", e.widget.pid)
        self.focus_on_idx(e.widget.idx)

    def on_visibility(self, e):
        widget: SimplePhotoLabel = e.widget
        if widget.bbox:
            logger.debug("Visibility TRUE for %s", widget.pid)
            idx = widget.idx
            if len(self.frames) - idx < 10 and len(self.frames) < len(self.post_ids):
                self.increase_frames(idx + 10)
            for i in range(idx, idx + 8):
                try:
                    SimpleFrames.frames[i].get_image()
                except Exception:  # noqa: BLE001
                    break
        else:
            logger.debug("Visibility: FALSE for %s. Resetting.", widget.pid)
            widget.reset(True)


class ImageCache:
    def __init__(self, max_size=200):
        self.cache = {}
        self.deque = deque()
        self.max_size = max_size

    def __contains__(self, item):
        return item in self.cache

    def __len__(self):
        return len(self.cache)

    def __getitem__(self, key):
        if key in self.cache:
            self.deque.remove(key)
            self.deque.append(key)
        return self.cache.get(key, None)

    def __setitem__(self, key, value):
        if key in self.deque:
            self.deque.remove(key)
        self.deque.append(key)
        self.cache[key] = value
        while len(self.deque) > self.max_size - 1:
            r_key = self.deque.popleft()
            self.cache.pop(r_key)

    def remove(self, key):
        if key in self.cache:
            self.cache.pop(key)
            if key in self.deque:
                self.deque.remove(key)


class SimplePhotoLabel(tk.Label):
    post_ids = []  # noqa: RUF012
    post_files: dict[str, PostFile] = {}  # noqa: RUF012
    photo_cache = ImageCache()
    text: ttk.Text = None
    default_height = 40
    default_width = 14
    get_image_cancel_key = "photo_label_get_image"

    @staticmethod
    def get_post(pid) -> Post:
        with PostDb() as post_db:
            post = post_db.posts.get(id=pid)
        return post

    @staticmethod
    def get_post_file(pid) -> PostFile:
        if pid not in SimplePhotoLabel.post_files:
            with PostDb() as post_db:
                file = post_db.files.get(pid)
            if not file:
                return None
            SimplePhotoLabel.post_files[pid] = file
        return SimplePhotoLabel.post_files[pid]

    def __init__(
        self, root, idx, height_var: ttk.IntVar, width_var: ttk.IntVar, **kwargs
    ):
        self.root: tk.Text = root
        self.idx = idx
        self.width_var = width_var
        self.height_var = height_var
        super().__init__(
            root,
            height=self.default_height,
            width=self.default_width,
            padx=5,
            pady=5,
            takefocus=False,
            **kwargs,
        )
        self.image_h = None
        self.post = None

    @property
    def pid(self):
        if SimplePhotoLabel.post_ids is None or self.idx >= len(
            SimplePhotoLabel.post_ids
        ):
            return None
        else:
            return SimplePhotoLabel.post_ids[self.idx]

    @property
    def post_file(self):
        if not self.pid:
            return None
        return self.get_post_file(self.pid)

    @property
    def bbox(self):
        return SimplePhotoLabel.text.bbox(self)

    @property
    def prev(self) -> SimplePhotoLabel:
        return SimpleFrames[self.idx - 1] if self.idx > 0 else None

    @property
    def next(self) -> SimplePhotoLabel:
        if self.idx < len(SimpleFrames.frames):
            return SimpleFrames[self.idx + 1]
        else:
            return None

    def same_row(self, next):
        is_same_row = False
        if self and self.bbox:
            x = self.bbox[1]
            y = self.bbox[3]
            x0 = next.bbox[1]
            y0 = next.bbox[3]
            is_same_row = max(x, x0) < min(y, y0)
        return is_same_row

    @property
    def prev_row(self):
        if not self:
            return None
        prev = self.prev
        while prev and prev.bbox:
            if not self.same_row(prev):
                break
            if not prev.prev:
                return prev
            prev = prev.prev
        return prev

    @property
    def next_row(self):
        if not self:
            return None
        next = self.next
        while next:
            if not self.same_row(next):
                break
            next = next.next
        return next

    def reset(self, check_viewable=False):
        if check_viewable and not self.bbox:
            logger.debug("Reset Skipped for %s. It is currently in View.", self.pid)
            return
        if self.pid:
            logger.debug("Resetting %s", self.pid)
            self.photo_cache.remove(self.pid)
        self.file = None
        self.loading = False

    def update_size(self):
        try:
            thumb_size = ImageUtils.get_cv_thumb_size(
                (self.post_file.width, self.post_file.height),
                (self.width_var.get(), self.height_var.get()),
            )
            return thumb_size
        except Exception:  # noqa: BLE001
            return (self.width_var.get(), self.height_var.get())

    def get_image(self, force_update=False):
        if self.pid is None or not self.post_file:
            self.config(image=None)
            return
        if not force_update and self.pid in SimplePhotoLabel.photo_cache:
            photo = SimplePhotoLabel.photo_cache[self.pid]
            self.config(image=photo, height=photo.height(), width=photo.width())
            return

        self.file: PostFile = self.post_file
        if self.file:
            self.image_h = self.height_var.get()
            if self.file.thumbnail:
                self.file_name = self.file.thumbnail
            elif self.file.sample:
                self.file_name = self.file.sample
            elif self.file.preview:
                self.file_name = self.file.preview
            else:
                self.file_name = self.file.file

            self.config(image=None)

            text_width = self.root.winfo_width()
            self.thumb_size = (text_width, self.height_var.get())
            if self.file.ext not in ["webm", "mp4"] and self.image_h > 400:
                logger.debug("Upscaling file %s to the full file", self.file_name)
                self.file_name = self.file.file

            if not self.post or self.post.id != self.file.id:
                self.post = self.get_post(self.file.id)

            blur = False
            if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
                blur = "rating_s" not in self.post.tags

            thread_caller.add(
                ImageUtils.get_cv2_pil_image,
                self.set_image,
                self.get_image_cancel_key,
                self.file_name,
                self.thumb_size,
                False,
                blur,
            )

    def set_image(self, image):
        if not image:
            return
        photo = ImageTk.PhotoImage(image)
        if not photo:
            return
        SimplePhotoLabel.photo_cache[self.pid] = photo
        self.config(image=photo, height=photo.height(), width=photo.width())
        self.loading = False
        logger.debug("Setting Image")
        self.update_idletasks()
