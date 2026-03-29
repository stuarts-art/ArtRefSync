import functools
import logging
import os
import threading

import ttkbootstrap as ttk
from PIL import Image, ImageDraw, ImageSequence, ImageTk
from tenacity import retry

from artrefsync.config import config

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ImageUtils:
    cache = {}

    _lock = threading.Lock()
    _photolock = threading.Lock()
    _thumblock = threading.Lock()
    photo_failed_set = set()

    @property
    @functools.lru_cache()
    def blank():
        return ttk.PhotoImage()

    @classmethod
    @retry
    @functools.lru_cache(maxsize=100)
    def getPilImage(cls, file: str, height=None, width=None):
        logger.debug("Cache-Miss, Getting Image")
        if not os.path.exists(file):
            logger.error("Cannot open path: %s", file)
            return None

        with cls._lock:
            image = Image.open(file)
        if height and width:
            with cls._lock:
                image.thumbnail((height, width))
        return image

    @staticmethod
    @functools.lru_cache(maxsize=100)
    @retry
    def getPilImageThumb(file: str, size: tuple, upscale=False):

        try:
            image = ImageUtils.getPilImage(file)
            with ImageUtils._thumblock:
                if not upscale or image.height > size[1]:
                    thumbnail = image.copy()
                    thumbnail.thumbnail(size=size)
                else:
                    resize = (int((size[1] / image.height) * image.width), size[1])
                    thumbnail = image.resize(
                        size=resize, resample=Image.Resampling.LANCZOS
                    )
            return thumbnail
        except Exception as e:
            print(e)

    @staticmethod
    @functools.lru_cache(maxsize=3)
    @retry
    def getPilFrames(file, size=(1440, 1440)):
        image = ImageUtils.getPilImage(file)
        frames = []
        try:
            duration = image.info["duration"]
        except Exception:
            duration = 100
        try:
            for frame in ImageSequence.Iterator(image):
                compressed_frame = frame.copy()
                if size:
                    compressed_frame.thumbnail(size=size)
                frames.append(compressed_frame)
        except EOFError:
            return (None, None)
        return (frames, duration)

    @retry
    def getTkFrames(file, size=(1440, 1440)):
        frames, duration = ImageUtils.getPilFrames(file)
        if not frames:
            return (None, None)
        tkFrames = []
        for frame in frames:
            frame_copy = frame.copy()
            frame_copy.thumbnail(size=size)
            photoFrame = ImageTk.PhotoImage(image=frame_copy)
            tkFrames.append(photoFrame)

        return (tkFrames, duration)

    @staticmethod
    @retry
    @functools.lru_cache(maxsize=50)
    def get_tk_thumb(file: str, size=(1080, 720), radius=0):
        image = ImageUtils.getPilImageThumb(file, size=size)
        if radius:
            size = (image.width, image.height)
            image.putalpha(ImageUtils.getrounded_rect(size=size, radius=radius))
        with ImageUtils._photolock:
            return ImageTk.PhotoImage(image=image)

    @staticmethod
    @retry
    @functools.lru_cache
    def getrounded_rect(size, radius) -> Image.Image:
        """
        Produces a rounded grey-scale rectagle, useful for layer masking with putalpha.
        """
        width, height = size
        scale = 4
        image = Image.new(mode="L", size=(width * scale, height * scale))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (0, 0, width * scale, height * scale),
            fill="white",
            radius=radius * scale,
            width=4,
            outline="grey",
        )
        image.thumbnail((width, height))
        return image

    @staticmethod
    @retry
    @functools.lru_cache(maxsize=20)
    def get_round_colored_rect(
        width, height, radius, fill="white", as_photoimage=False
    ) -> Image.Image:
        scale = 4
        image = Image.new(mode="RGBA", size=(width * scale, height * scale))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (0, 0, width * scale, height * scale), fill=fill, radius=radius * scale
        )
        image.thumbnail((width, height), Image.Resampling.LANCZOS)

        return ImageTk.PhotoImage(image) if as_photoimage else image
