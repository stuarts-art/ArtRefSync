import logging
from pathlib import Path
from threading import Lock

import cv2
from PIL import Image, ImageTk

from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.managed_cache import ManagedCache

logger = logging.getLogger(__name__)


class FrameBuffer(list[ImageTk.PhotoImage]):
    cache = ManagedCache()

    def __init__(self, size=(1440, 1440)):
        self.cap: cv2.VideoCapture = None
        self.lock = Lock()
        self.len = 1
        self.prev = None
        self.thumb_size = size
        self.path = None
        self.fps = None
        self.duration = None
        self.get_lock = Lock()
        self.last_frame = -1

        super().__init__()

    def load_file(self, path: Path):
        with self.get_lock:
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.path: Path = Path(path)
            self.video_format = self.path.suffix in [".gif", ".mp4", ".webm", ".mov"]

            if self.video_format:
                self.cap = cv2.VideoCapture(path)
                self.len = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.duration = int(1000 / self.fps)
            else:
                self.cap = None
                self.len = 1
                self.fps = None
                self.duration = None

    def __len__(self):
        return self.len

    def __getitem__(self, s) -> Image:
        with self.get_lock:
            i = int(s) % len(self)
            key = (self.path, i)
            if key not in self.cache:
                self.update_at_index(i, key)
            return self.cache[key]

    def __contains__(self, key):
        frame_key = (self.path, key)
        return frame_key in self.cache

    def update_at_index(self, i, key):
        if key not in self.cache:
            if self.video_format:
                self.set_frame(i)
                ret, frame = self.cap.read()
                if ret:
                    # if self.thumb_size:
                    #     h, w = frame.shape[:2]
                    #     thumb_size = ImageUtils.get_cv_thumb_size(
                    #         (w, h), self.thumb_size
                    #     )
                    #     frame = cv2.resize(
                    #         frame, thumb_size, interpolation=cv2.INTER_AREA
                    #     )
                    frame = ImageUtils.cv_array_to_image(frame)
                    self.cache[key] = frame
                self.last_frame = i
            else:
                self.cache[key] = ImageUtils.get_cv2_pil_image(
                    str(self.path), size=(1080, 1080)
                )

    def set_frame(self, i):
        if i - self.last_frame != 1:
            if self.cap and self.cap.isOpened():
                logger.info("SETTING FRAME from:%s, to:%s", self.last_frame, i)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)

    @property
    def curr(self):
        if self.cap and self.cap.isOpened():
            # with self.lock:
            return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
