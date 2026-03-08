import logging
import time
import tkinter as tk
from threading import Event

import ttkbootstrap as ttk
from PIL import ImageTk
from tkinterdnd2 import COPY, DND_FILES
from ttkbootstrap.widgets.scrolled import ScrolledText

from artrefsync.boards.board_handler import PostFile
from artrefsync.config import config
from artrefsync.constants import BINDING
from artrefsync.db.post_db import PostDb
from artrefsync.utils.EventManager import ebinder
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger()
logger.setLevel(config.log_level)

thread_caller: TkThreadCaller = None


class PhotoImageGallery(ttk.Frame):
    def __init__(self, root: ttk.Frame, thread_caller_arg=None):
        logger.info("Creating Photo Image Gallery.")
        global thread_caller
        super().__init__(root)
        self.tags = None
        self.scrolled_text = ScrolledText(self)
        self.text = self.scrolled_text.text
        self.colors = ttk.Style().colors

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.scrolled_text.grid(row=1, column=0, sticky=tk.NSEW)

        self.tag_sets: dict[str, set] = {}
        self.root = root
        thread_caller = thread_caller_arg

        color = ttk.Style().colors
        self.text.tag_configure(
            "sel", background=color.warning, foreground=color.warning, underline=1
        )

        self.frame_height = ttk.IntVar(self, value=500)
        self.frame_width = ttk.IntVar(self, value=500)

        self.simple_frames = SimpleFrames(
            self.text, self.frame_width, self.frame_height, self.scrolled_text
        )
        self.text.config(state="disabled")
        self.bind("<Configure>", self.update_width)
        ebinder.bind(BINDING.ON_FILTER_UPDATE, self.change_tags, self)
        ebinder.bind(BINDING.ON_SORT_BY_UPDATE, self.update_posts, self)

    def update_sort_var(self, e: tk.Event):
        self.sort_menu.post(
            e.widget.winfo_rootx() + 5, e.widget.winfo_rooty() + e.widget.winfo_height()
        )

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
                if last_bboxed and i - last_bboxed > 3:
                    break

    def change_tags(self, tags):
        if self.tags == tags:
            return
        self.tags = tags
        self.update_posts()

    def update_posts(self, *args, **kwargs):
        sort_by = ebinder.get_or_default(BINDING.SORT_BY, "id")
        sort_dir = ebinder.get_or_default(BINDING.SORT_DIR, "DESC")
        print(sort_by)
        print(sort_dir)

        with PostDb() as post_db:
            order_query = f" ORDER BY {sort_by} {sort_dir}"
            if self.tags:
                posts = post_db.get_tag_intersection(self.tags)
                sorted = post_db.posts.get_all(
                    posts, ["id"], as_scalar=True, suffix=order_query
                )
                self.simple_frames.change_posts(sorted)
            else:
                posts = post_db.posts.select_id_list(
                    conditions=None, suffix=f"{order_query} LIMIT 1000"
                )
                self.simple_frames.change_posts(posts)


class SimpleFrames:
    frames: list["SimplePhotoLabel"] = []
    frame_map: map = {}

    # @staticmethod
    def __class_getitem__(cls, index):
        if index is not None and index >= 0 and index < len(SimpleFrames.frames):
            return SimpleFrames.frames[index]

    def __init__(
        self, text: ttk.Text, width_var, height_var, scrolled_text: ScrolledText
    ):
        self.text = text
        self.width_var = width_var
        self.height_var = height_var
        self.post_ids = []
        self.focused = None
        self.focused_idx = None
        self.reloading = False
        self.last_selected = None
        self.zooming = False
        self.scrolled_text = scrolled_text

        self.min_focus_delay = 100
        self.last_focus_prev = time.time() - self.min_focus_delay
        self.last_focus_next = time.time() - self.min_focus_delay
        self.focussing_prev = False
        self.focussing_next = False
        self.increase_frames()
        ebinder.bind(BINDING.ON_PREV_GALLERY_IMAGE, self.focus_prev, self.text)
        ebinder.bind(BINDING.ON_NEXT_GALLERY_IMAGE, self.focus_next, self.text)
        self.text.bind("q", lambda _: self.change_zoom(-100))
        self.text.bind("e", lambda _: self.change_zoom(+100))
        self.text.bind("w", self.focus_prev_row)
        self.text.bind("a", self.throttled_focus_prev)
        self.text.bind("s", self.focus_next_row)
        self.text.bind("d", self.focus_next)
        self.color = ttk.Style().colors
        SimplePhotoLabel.text = text

    def create_frame(self):
        idx = len(self.frames) if self.frames else 0
        label = SimplePhotoLabel(self.text, idx, self.height_var, self.width_var)
        self.frames.append(label)
        self.frame_map[f"1.{idx}"] = label
        bindtags = list(label.bindtags())
        label.bind("<Visibility>", self.on_visibility)
        label.bind("<MouseWheel>", self.bind_scroll)
        bindtags.insert(1, self.text)
        label.bindtags(tuple(bindtags))
        label.bind("<ButtonRelease-1>", self.add_select_tag)
        label.bind(
            "<Double-Button-1>",
            lambda e: ebinder.event_generate(
                BINDING.ON_IMAGE_DOUBLE_CLICK, self.post_ids[e.widget.idx]
            ),
        )
        label.drag_source_register(DND_FILES)
        label.dnd_bind("<<DragInitCmd>>", self.drag_binding)
        self.text.window_create(tk.END, window=label, padx=5, pady=5)
        self.scrolling = Event()

    def bind_b2(self, e: tk.Event):
        print(e)
        edict = {k: v for k, v in e.__dict__.items() if k not in ["num"]}
        self.text.event_generate("<Button-2>", **edict)

    def bind_b2_motion(self, e: tk.Event):
        edict = {k: v for k, v in e.__dict__.items() if k not in ["num"]}

        print(e)
        self.text.event_generate("<B2-Motion>", **edict)

    def bind_scroll(self, event):
        self.text.event_generate("<MouseWheel>", delta=event.delta)

    def change_zoom(self, delta):
        if self.zooming:
            return
        self.zooming = True
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

        ebinder.event_generate(BINDING.ON_POST_COUNT, len(posts) if posts else "0")

        self.text.focus_set()
        SimplePhotoLabel.posts = posts
        self.post_ids = posts
        self.text.see(self.frames[0])
        self.update()
        self.text.after(100, lambda: self.frames[0].event_generate("<ButtonRelease-1>"))

    def update(self):
        logger.info("Updating Image Gallery")
        ImageUtils.get_tk_thumb.cache_clear()
        ImageUtils.getPilImageThumb.cache_clear()
        thread_caller.cancel(SimplePhotoLabel.get_image_cancel_key)
        for frame in self.frames:
            frame.reset()
            if frame.bbox:
                frame.get_image()
            else:
                if frame.photo == None:
                    continue

    def add_select_tag(self, e):
        self.text.focus_set()
        logger.info("Add Select Tag %s", e)
        s = e.state
        ctrl_pressed = (s & 0x4) != 0
        shift_pressed = (s & 0x1) != 0
        ranges = self.text.tag_ranges("sel")
        if not ranges or (not ctrl_pressed and not shift_pressed):
            if ranges:
                self.text.tag_remove("sel", 1.0, tk.END)
            self.text.tag_add("sel", e.widget)
        elif ctrl_pressed:
            if "sel" in self.text.tag_names(e.widget):
                logger.info("Removing sel tag from %s", e.widget.pid)
                self.text.tag_remove("sel", e.widget)
            else:
                self.text.tag_add("sel", e.widget)
                index = self.text.index(e.widget)
        elif shift_pressed:
            if "sel" in self.text.tag_names(e.widget):
                return
            index = self.text.index(e.widget)
            start = min(self.text.index(ranges[0]), index)
            end = max(self.text.index(ranges[0]), index + "+1c")
            self.text.tag_add("sel", start, end)
        self.updated_selected_post(self.selected.pid)

    def updated_selected_post(self, pid):
        if self.last_selected != pid:
            self.last_selected = pid
            ebinder.event_generate(BINDING.ON_POST_SELECT, self.selected.pid)

    @property
    def selected(self) -> "SimplePhotoLabel":
        ranges = self.text.tag_ranges("sel")
        if ranges:
            first = self.text.index("sel.first")
            return self.frame_map[first]
        return None

    def drag_binding(self, event):
        try:
            files = []
            ranges = self.text.tag_ranges("sel")
            first = self.text.index("sel.first")
            last = self.text.index("sel.last")
            for text_char in self.text.dump(first, last, window=True):
                name = text_char[1]
                photo: SimplePhotoLabel = self.text.nametowidget(name)
                if "sel" in self.text.tag_names(photo):
                    if photo.file:
                        if photo.file.ext in ["webm", "mp4"]:
                            files.append(photo.file.preview)
                        else:
                            files.append(photo.file.file)
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
        self.text.see(frame)
        self.scrolling.clear()

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

    def focus_prev(self, e=None):
        self.focussing_prev = False
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

    def throttled_focus_next(self, e=None):
        if self.focussing_next:
            return
        self.focussing_next = True
        time_since_last_next = time.time() - self.last_focus_next

        wait_time_ms = min(
            max(0, int((0.3 - time_since_last_next) * 1000)), self.min_focus_delay
        )
        self.text.after(wait_time_ms, self.focus_next)

    def focus_next(self, e=None):
        self.focus_next = False
        self.last_focus_next = time.time()
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

    def focus_prev_row(self, e=None):
        label: SimplePhotoLabel = self.selected
        prev = label.prev_row
        if prev:
            self.update_focus(prev.pid)

    def focus_next_row(self, e=None):
        label: SimplePhotoLabel = self.selected
        next = label.next_row
        if next:
            self.update_focus(next.pid)

    def set_focus(self, e=None):
        logger.info("Set Focus on %s", e.widget.pid)
        self.focus_on_idx(e.widget.idx)

    def on_visibility(self, e):
        widget: SimplePhotoLabel = e.widget
        if widget.bbox:
            logger.debug("Visibility TRUE for %s", widget.pid)
            idx = widget.idx
            widget.get_image()

            if len(self.frames) - idx < 10 and len(self.frames) < len(self.post_ids):
                self.increase_frames(idx + 10)
        else:
            logger.debug("Visibility: FALSE for %s. Resetting.", widget.pid)
            widget.reset()
        return


class SimplePhotoLabel(tk.Label):
    posts = []
    post_files: dict[str, PostFile] = {}
    load_target = 0
    load_idx = 0

    text: ttk.Text = None

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
        self.idx = idx
        self.photo = None
        self.width_var = width_var
        self.height_var = height_var
        super().__init__(
            root, height=self.default_height, width=self.default_width, padx=5, pady=5
        )
        self.pid = ""
        self.image_h = None

    @property
    def bbox(self):
        return SimplePhotoLabel.text.bbox(self)

    @property
    def prev(self) -> "SimplePhotoLabel":
        return SimpleFrames[self.idx - 1] if self.idx > 0 else None

    @property
    def next(self) -> "SimplePhotoLabel":
        if self.idx < len(SimpleFrames.frames):
            return SimpleFrames[self.idx + 1]
        else:
            return None

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
        while next:
            if not next.bbox or (next.bbox[1] > self.bbox[3]):
                return next
            next = next.next
        return next

    def reset(self, check_viewable=False):
        if check_viewable and not self.bbox:
            logger.debug("Reset Skipped for %s. It is currently in View.", self.pid)
            return
        if self.pid:
            logger.debug("Resetting %s", self.pid)
        self.image = None
        # self.pid = None
        self.photo = None
        self.file = None
        # self.config(image=None)
        self.loading = False
        self.config(image=None)

    def update_size(self):
        ratio = self.file.width / self.file.height

        if ratio * self.height_var.get() > self.width_var.get():
            width = self.width_var.get()
            height = width / ratio
        else:
            width = self.height_var.get() * ratio
            height = self.height_var.get()

        self.config(height=int(height), width=int(width))

    def get_image(self):
        if self.idx >= len(SimplePhotoLabel.posts):
            self.image = None
            self.config(image=None)
            return

        pid = SimplePhotoLabel.posts[self.idx]
        self.pid = pid
        self.file: PostFile = SimplePhotoLabel.get_post_file(pid)
        if self.file:
            self.image_h = self.height_var.get()
            if self.file.preview:
                self.file_name = self.file.preview
            elif self.file.sample:
                self.file_name = self.file.sample
            else:
                self.file_name = self.file.file
            self.config(image=None)

            thread_caller.add(
                ImageUtils.getPilImageThumb,
                self.set_image,
                self.get_image_cancel_key,
                self.file_name,
                (self.width_var.get(), self.height_var.get()),
            )

    def set_image(self, image):
        if image:
            photo = ImageTk.PhotoImage(image)
            if photo:
                self.image = photo
                self.config(image=photo, height=photo.height(), width=photo.width())
                self.loading = False
                logger.debug("Setting Image")
            else:
                logger.debug("ERROR Loading %s %s", self.file.id, self.file.file)
        self.reloading = False
