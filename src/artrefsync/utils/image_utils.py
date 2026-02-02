import threading
import time
from PIL import Image, ImageTk, ImageDraw
import functools
from venv import logger
import ttkbootstrap as ttk
import os
from PIL import Image, ImageTk, ImageSequence
from itertools import count, cycle

from artrefsync.boards.board_handler import PostFile


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

    @staticmethod
    @functools.lru_cache(maxsize=100)
    def getPilImage(file: str, height=None, width=None):
        logger.info("Cache-Miss, Getting Image")
        if not os.path.exists(file):
            logger.error("Cannot open path: %s", file)
            return None

        for retry in range(3):
            try:
                # with ImageUtils._lock:
                with ImageUtils._lock:
                    image = Image.open(file)
                if height and width:
                    # with ImageUtils._lock:
                    with ImageUtils._lock:
                        image.thumbnail((height, width))
                return image
            except Exception as e:
                logger.error("Loading image %s failed. Retrying", file)
                time.sleep(0.1 * (retry + 1))
        logger.error("Loading image (%s). failed. Retrying", file)
        raise Exception("Failed to load PIL image %s.")

    @staticmethod
    @functools.lru_cache(maxsize=20)
    def getPilImageThumb(file: str, size: tuple):
        image = ImageUtils.getPilImage(file)
        with ImageUtils._thumblock:
            thumbnail = image.copy()
            thumbnail.thumbnail(size=size)
        return thumbnail

    @staticmethod
    @functools.lru_cache(maxsize=3)
    def getPilFrames(file, size=(1440, 1440)):
        image = ImageUtils.getPilImage(file)
        frames = []
        try:
            duration = image.info['duration']
        except:
            duration = 100
        try:
            for frame in ImageSequence .Iterator(image):
                compressed_frame = frame.copy()
                if size:
                    compressed_frame.thumbnail(size=size)
                frames.append(compressed_frame)
        except EOFError:
            return (None, None)
        return (frames, duration)

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
    @functools.lru_cache(maxsize=50)
    def get_tk_thumb(file: str, size = (1080,720), radius=0):
        image = ImageUtils.getPilImageThumb(file, size=size)
        if radius:
            size = (image.width, image.height)
            image.putalpha(ImageUtils.getrounded_rect(size=size, radius=radius))
        with ImageUtils._photolock:
            return ImageTk.PhotoImage(image=image)


    @staticmethod
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
    @functools.lru_cache(maxsize=20)
    def get_round_colored_rect(width, height, radius, fill="white") -> Image.Image:
        scale = 4
        image = Image.new(mode="RGBA", size=(width * scale, height * scale))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (0, 0, width * scale, height * scale), fill=fill, radius=radius * scale
        )
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        return image
