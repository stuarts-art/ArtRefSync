import logging
import time
import tkinter as tk
from collections import OrderedDict, deque
from queue import Empty
from threading import Lock

import cv2
import ttkbootstrap as ttk
from PIL import ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD

from artrefsync.config import config
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ImageCache:
    def __init__(self, max_size=50):
        self.cache = OrderedDict()
        self.deque = deque()
        self.max_size = 50

    def __contains__(self, key):
        # print(key)
        # key = hash(key)
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
            rkey = self.deque.pop()

            self.cache.pop(rkey)
            logger.info("Popping id: %s", rkey)

    def clear(self):
        self.deque.clear()
        while self.cache:
            k, v = self.cache.popitem()
            v.close()


class ImageBuffer:
    def __init__(
        self, size=1080, index: ttk.IntVar = None, thread_caller: TkThreadCaller = None
    ):
        self.lock = Lock()
        self.frame_count = 1
        self.count = 0
        self.duration = 0
        self.index = index
        self.frames = ImageCache()
        self.thread_caller = thread_caller
        self.gif: cv2.VideoCapture = cv2.VideoCapture()
        self.path = ""

    def current_frame(self, frame=None):
        try:
            if frame is None:
                return int(self.gif.get(cv2.CAP_PROP_POS_FRAMES))
            else:
                self.gif.set(cv2.CAP_PROP_POS_FRAMES, frame)
        except Exception:
            return 0

    def __len__(self):
        if self.frame_count:
            return self.frame_count
        else:
            return 0

    def __getitem__(self, index):
        if not self.gif:
            return None
        index %= self.frame_count
        self.get_curr_frame(index)
        index = self.get_key(index)
        return self.frames.cache.get(index, None)

    def __setitem__(self, key, value):
        key = self.get_key(key)
        self.frames[key] = value

    def get_key(self, index):
        return f"{self.path}.{index}"

    def set_image(self, path, size=(720, 720)):
        self.path = path
        if self.gif and self.gif.isOpened():
            self.gif.release()
        self.gif = cv2.VideoCapture(path)
        self.size = size
        self.prev = -1
        self.frame_count = int(max(int(self.gif.get(cv2.CAP_PROP_FRAME_COUNT)), 1))
        self.fps = int(self.gif.get(cv2.CAP_PROP_FPS))
        self.delay = int(1000 / self.fps)

    def get_frame(self, index=0):
        if index != 0:
            index %= self.frame_count
        logger.debug(f"Getting Frame {index}")
        key = self.get_key(index)
        # print(key)
        if key in self.frames:
            for i in range(5):
                next_index = (index + i) % self.frame_count
                next_key = self.get_key(next_index)
                if next_key not in self.queued and next_key not in self.frames:
                    logger.info(f"Adding frame {next_key}")
                    self.frame_queue.put(next_key)
                    self.queued.add(next_key)
            self.prev = index
            return self.frames[key], index

        if self.prev + 1 != index:
            self.gif.set(cv2.CAP_PROP_POS_FRAMES, index)

        with self.lock:
            ret, frame = self.gif.read()
        if not ret:
            return (self.frames[key], 0)

        image = ImageUtils.cv_array_to_image(frame)

        self.frames[key] = image
        for i in range(5):
            next_index = (index + i) % self.frame_count
            if next_index not in self.queued:
                self.queued.add(next_index)
                self.frame_queue.put(next_index)

        return image, index

    def get_curr_frame(self, index):
        key = self.get_key(index)
        if key in self.frames:
            return self.frames[key], index

        index = int(index)
        index %= self.frame_count
        if index == self.prev:
            return
        if self.lock.locked():
            return None, index

        with self.lock:
            if self.current_frame() != index:
                self.current_frame(index)
                # return self.get_curr_frame(index)
            ret, frame = self.gif.read()

        if not ret:
            if self.frame_count > 1:
                with self.lock:
                    self.current_frame(0)
                    return self.get_curr_frame(index)
            else:
                return None, index

        if self.size:
            h, w = frame.shape[:2]
            thumb_size = ImageUtils.get_cv_thumb_size((w, h), self.size)
            frame = cv2.resize(frame, thumb_size, interpolation=cv2.INTER_AREA)
        self.prev = index
        return frame, index

    def process_queue(self):
        self.process_queue_active = True
        logger.info(f"Processing Queue {self.frame_queue}")
        try:
            while index := self.frame_queue.get(timeout=0.1):
                index %= self.frame_count
                key = self.get_key(index)
                if key not in self.frames:
                    if self.prev + 1 != index:
                        self.gif.set(cv2.CAP_PROP_POS_FRAMES, index)
                    with self.lock:
                        ret, frame = self.gif.read()
                    if ret:
                        image = ImageUtils.cv_array_to_image(frame)
                        if self.size:
                            h, w = frame.shape[:2]
                            thumb_size = ImageUtils.get_cv_thumb_size((w, h), self.size)
                            frame = cv2.resize(
                                frame, thumb_size, interpolation=cv2.INTER_AREA
                            )
                            image = ImageUtils.cv_array_to_image(frame)
                        self.frames[key] = image
                self.prev = index
        except Empty:
            pass
        self.process_queue()

    def _read_frame(self, path):
        return None

    def get(self, index):
        if index < 0:
            return None
        if index < len(self.frames):
            return


class ImagePlayer:
    def __init__(self):
        self.size = 740
        self.app = ttk.Window(size=(self.size, self.size))
        TkinterDnD._require(self.app)

        self.index = ttk.IntVar(value=0)
        self.threadcaller = TkThreadCaller(self.app, __name__)
        self.label: ttk.Label = ttk.Label(self.app)

        self.buffer = ImageBuffer(self.size, self.index, self.threadcaller)
        self.ui_frame = ttk.Frame(self.app)
        self.scale = ttk.Scale(
            self.ui_frame,
            from_=0,
            to=100,
            variable=self.index,
            length=400,
            command=self.on_scale,
        )
        self.index_label = ttk.Label(self.ui_frame, textvariable=self.index)

        # Packing
        self.app.rowconfigure(0, weight=1)
        self.app.columnconfigure(0, weight=1)

        self.label.grid(row=0, column=0, sticky="nsew")
        self.ui_frame.grid(row=1, column=0)

        self.scale.grid(row=0, column=0, sticky="ew")
        self.index_label.grid(row=0, column=1, sticky="")

        self.label.drop_target_register(DND_FILES)
        self.label.dnd_bind("<<Drop>>", self.handle_drop)

        self.path = ""
        self.after_id = None
        self.set_future = None
        self.playing = True

        # self.label.bind("<Space>")
        self.label.bind("<space>", self.on_space)
        # self.app.bind("<space>", self.on_space)

        with self.threadcaller:
            self.app.mainloop()

    def on_space(self, e=None):
        if self.playing:
            if self.set_future is not None:
                # self.set_future.cancel()
                self.threadcaller.cancel("play")
            if self.after_id:
                self.label.after_cancel(self.after_id)

            self.playing = False
        else:
            self.playing = True
            self.play()

    def on_scale(self, e=None):
        if self.index.get() == self.buffer.prev:
            return
        self.playing = False

        self.threadcaller.cancel("scale")
        self.set_future = self.threadcaller.add(self.play, None, "scale")

    def handle_drop(self, e: tk.Event):
        file = e.data
        if file == self.path:
            return None
        self.label.focus()
        if self.after_id:
            self.label.after_cancel(self.after_id)
        self.buffer.set_image(file)
        self.count = self.buffer.frame_count
        self.scale.config(to=self.count)

        # self.threadcaller.cancel("play")

        self.play()

    def play(self, _=None):
        self.start = time.time()
        try:
            if self.set_future is not None:
                # self.set_future.cancel()
                self.threadcaller.cancel("play")
            self.set_future = self.threadcaller.add(
                self.buffer.get_curr_frame, self.set_image, "play", self.index.get()
            )

            cframe = self.buffer.get_curr_frame(self.index.get())
            self.set_image(cframe)
            self.index.set((self.index.get() + 1) % self.count)
        except Exception as e:
            logger.error(e)

    def set_image(self, data):
        if data is None:
            return

        image, index = data
        index %= self.buffer.frame_count
        if image is None:
            return
        key = self.buffer.get_key(index)
        if key in self.buffer.frames:
            photo = self.buffer.frames[key]
        else:
            pil_image = ImageUtils.cv_array_to_image(image)
            logger.info(f"Setting image for index {index}")
            photo = ImageTk.PhotoImage(pil_image)
            self.buffer.frames[key] = photo

        self.label.config(image=photo)
        self.label.image = photo  # pyright: ignore[reportAttributeAccessIssue]

        if self.after_id:
            self.label.after_cancel(self.after_id)

        if self.playing and self.buffer.frame_count > 1:
            delay = int(self.buffer.delay - (time.time() - self.start))
            self.after_id = self.after_id = self.label.after(delay, self.play)


if __name__ == "__main__":
    ImagePlayer()
