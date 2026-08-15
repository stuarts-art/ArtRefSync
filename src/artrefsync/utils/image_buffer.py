import logging
import time
import tkinter as tk
from collections import OrderedDict, deque
from threading import Lock

import cv2
import ttkbootstrap as ttk
from PIL import ImageTk
from tkinterdnd2 import DND_FILES

from artrefsync.config import get_config
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.IntegerVar import IntegerVar
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)


class ImageCache:  # WIP Video/Gif Viewer
    def __init__(self, max_size=50):
        self.cache = OrderedDict()
        self.deque = deque()
        self.max_size = 50
        self.pop_count = 0

    def __contains__(self, key):
        return self.cache.__contains__(key)

    def __len__(self):
        return self.cache.__len__()

    def __getitem__(self, key):
        if key in self.cache:
            if key in self.deque:
                self.deque.remove(key)
            self.deque.append(key)
        return self.cache.get(key, None)

    def __setitem__(self, key, value):
        if key in self:
            self.cache.move_to_end(key, last=False)
        self.cache[key] = value
        while len(self.deque) > self.max_size:
            r_key = self.deque.pop()
            self.pop_count += 1

            self.cache.pop(r_key)
            if self.pop_count % 20 == 0:
                logger.info("Popped id: %s, total popped: %s", r_key, self.pop_count)

    def clear(self):
        self.deque.clear()
        while self.cache:
            self.cache.popitem()


class ImageBuffer:
    def __init__(self, size=1080, index: ttk.IntVar = None):
        self.lock = Lock()
        self.frame_count = 1
        self.count = 0
        self.duration = 0
        self.index = index
        self.frames = ImageCache()
        self.thread_caller = thread_caller
        self.gif: cv2.VideoCapture = cv2.VideoCapture()
        self.path = ""
        self.prev = -1

    def current_frame(self, frame=None):
        try:
            if self.frame_count == 1:
                return 1
            if frame is None:
                return int(self.gif.get(cv2.CAP_PROP_POS_FRAMES))
            else:
                self.gif.set(cv2.CAP_PROP_POS_FRAMES, frame)
        except Exception:  # noqa: BLE001
            return 0

    def __contains__(self, index):
        if not self.gif:
            return None
        index %= self.frame_count
        key = self.get_key(index)
        return self.frames.__contains__(key)

    def __len__(self):
        if self.frame_count:
            return self.frame_count
        else:
            return 1

    def size(self):
        return self.__len__()

    def __getitem__(self, index):

        if not self.gif:
            return None
        index %= self.frame_count
        key = self.get_key(index)
        if key not in self.frames:
            image, _ = self.get_frame(key)
            self.frames[key] = image
        return self.frames[key]

    def __setitem__(self, key, value):
        key = self.get_key(key)
        self.frames[key] = value

    def get_key(self, index):
        return index

    def update_file(self, path, size=(720, 720)):
        logger.info("Updating file to be %s", path)
        if path == self.path:
            return
        self.path = path
        self.frames.clear()
        self.size = size
        self.prev = -1

        if ImageUtils.is_multiple_frames(path):
            if self.gif and self.gif.isOpened():
                self.gif.release()
            self.gif = cv2.VideoCapture(path)
            try:
                with self.lock:
                    self.frame_count = int(
                        max(int(self.gif.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
                    )
                    self.fps = int(self.gif.get(cv2.CAP_PROP_FPS))
                    self.delay = int(1000 / self.fps)
            except Exception:
                logger.exception("Failed to read video")
                self.frame_count = 1
                self.fps = 1
                self.delay = 1
        else:
            self.frames[0] = [ImageUtils.get_cv2_pil_image(path)]
            self.frame_count = 1
            self.fps = 1
            self.delay = 1
            self.delay = None

    def get_frame(self, index):
        index = int(index)
        index %= self.frame_count
        if index == self.prev:
            return

        key = self.get_key(index)
        if key in self.frames:
            return self.frames[key], index

        with self.lock:
            if self.current_frame() != index:
                self.current_frame(index)
            ret, frame = self.gif.read()

        if not ret:
            if self.frame_count > 1:
                with self.lock:
                    self.current_frame(0)
                return self.get_frame(index)
            else:
                return None, index
        if self.size:
            h, w = frame.shape[:2]
            thumb_size = ImageUtils.get_cv_thumb_size((w, h), self.size)
            frame = cv2.resize(frame, thumb_size, interpolation=cv2.INTER_AREA)
        frame = ImageUtils.cv_array_to_image(frame)
        self.frames[key] = frame
        self.prev = index
        return frame, index

    def _read_frame(self, path):
        return None

    def get(self, index):
        if index < 0:
            return
        if index < len(self.frames):
            return


class ImagePlayer:
    def __init__(self, parent, size: int, index: IntegerVar):
        self.parent = parent
        self.size = size
        self.index: IntegerVar = index
        self.__init_vars()
        self.__init_widgets()
        self.__init_bindings()

    def __init_vars(self):
        logger.info("Image Buffer Init Vars")
        self.scaling = False
        self.last_scale = time.time()
        self.path = ""
        self.after_id = None
        self.set_future = None
        self.playing = True
        self.play_lock = Lock()
        self.after_map = {}
        self.start = time.time()
        self.displayed_index = -1

    def __init_widgets(self):
        logger.info("Image Buffer Init Widgets")

        self.root = ttk.Frame(self.parent)
        self.root.pack(expand=True, fill="both")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.label: ttk.Label = ttk.Label(self.root)
        self.buffer = ImageBuffer(self.size, self.index)
        self.ui_frame = ttk.Frame(self.root)
        self.ui_frame.rowconfigure(0, weight=1)

        self.scale = ttk.Scale(
            self.ui_frame,
            from_=0,
            to=100,
            variable=self.index.dummy_var,
            length=400,
            command=self.on_scale,
        )
        self.index_label = ttk.Label(self.ui_frame, textvariable=self.index)
        self.label.grid(row=0, column=0, sticky="nsew")
        self.ui_frame.grid(row=1, column=0, sticky="s")
        self.scale.grid(row=0, column=0, sticky="ew")
        self.index_label.grid(row=0, column=1, sticky="e")
        self.prev_index = -1

    def __init_bindings(self):
        logger.info("Image Buffer Init Bindings")
        self.label.drop_target_register(DND_FILES)
        self.label.dnd_bind("<<Drop>>", self.handle_drop)
        self.label.bind("<space>", self.on_space)
        self.scale.bind("<ButtonRelease-1>", self.on_scale_release)

    def on_space(self, e=None):
        if self.playing:
            logger.info("Toggle play on")
            self.playing = False
            self.cancel_after_map()
        else:
            logger.info("Toggle play off")
            self.playing = True
            self.index += 1
            self.schedule_play()

    def on_scale(self, e=None):
        if time.time() - self.last_scale < 0.2:
            return
        else:
            self.last_scale = time.time()
        self.scaling = True
        if self.index.get() == int(self.buffer.prev):
            return
        self.schedule_play()

    def on_scale_release(self, e=None):
        logger.info("On Scale Release")
        self.scaling = False
        if self.playing:
            self.schedule_play()

    def handle_drop(self, e: tk.Event):
        file = e.data
        if file == self.path:
            return
        self.playing = False
        self.index.set(0)
        self.label.focus()
        self.cancel_after_map()

        self.buffer.update_file(file)
        self.count = self.buffer.frame_count
        self.scale.config(to=self.count)

        self.playing = True
        self.schedule_play()

    def cancel_after_map(self):
        while self.after_map:
            index, after_id = self.after_map.popitem()
            self.label.after_cancel(after_id)
            logger.info("index %s cancelled.", index)

    def play(self, _=None):
        index = self.index.get() % len(self.buffer)
        if index in self.after_map:
            return

        image = self.buffer[index]
        if image is None:
            return
        if len(self.buffer) > 1:
            delay = int(self.buffer.delay - 100 * (time.time() - self.start))
            delay = max(10, delay)
            after_id = self.label.after(delay, self.set_image, index)
            self.after_map[index] = after_id

    def set_image(self, index):
        if index not in self.after_map:
            return
        if index in self.after_map:
            self.after_map.pop(index)
        if self.displayed_index == index:
            pass

        else:
            pil_image = self.buffer[index]
            if pil_image is None:
                logger.warning("index %s not in buffer", index)
                return
            photo = ImageTk.PhotoImage(pil_image)

            self.label.config(image=photo)
            self.label.image = photo
            self.displayed_index = index

            self.start = time.time()
            if len(self.buffer) > 1 and self.playing and not self.scaling:
                self.index += 1
                self.index %= len(self.buffer)
        self.schedule_play()

    def schedule_play(self):
        self.set_future = thread_caller.add(self.play, None, "play")
