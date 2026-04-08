import functools
import logging
import os
import threading

import cv2
import ttkbootstrap as ttk
from PIL import Image, ImageDraw, ImageSequence, ImageTk
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.config import config

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class ImageUtils:
    cache = {}

    _lock = threading.Lock()
    _photolock = threading.Lock()
    _thumblock = threading.Lock()
    photo_failed_set = set()

    def blank():
        return ttk.PhotoImage()

    @classmethod
    @functools.lru_cache(maxsize=100)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    def getPilImage(cls, file: str, height=None, width=None):
        logger.debug("Cache-Miss, Getting Image")
        if not os.path.exists(file):
            logger.error("Cannot open path: %s", file)
            return None

        with cls._lock:
            image = Image.open(file)
        if height and width and height < image.height:
            with cls._lock:
                image.thumbnail((height, width))
        return image

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
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
            logger.warning(e)

    @staticmethod
    @functools.lru_cache(maxsize=3)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
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
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    @functools.lru_cache(maxsize=50)
    def get_tk_thumb(file: str, size=(1080, 720), radius=0):
        image = ImageUtils.getPilImageThumb(file, size=size)
        if radius:
            size = (image.width, image.height)
            image.putalpha(ImageUtils.getrounded_rect(size=size, radius=radius))
        with ImageUtils._photolock:
            return ImageTk.PhotoImage(image=image)

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
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
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
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

    @staticmethod
    @functools.lru_cache
    def get_cv_thumb_size(img_size, size):
        img_w, img_h = img_size
        w, h = size 
        ratio = img_w / img_h
        vh = int(w / ratio)
        vw = int(h * ratio)
        if h < vh:
            width = vw
            height= h
        else:
            width = w
            height = vh
        return (width, height)

    @staticmethod
    def cv_array_to_image(cv_image):
        cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cv_image_rgb)

    @staticmethod
    @functools.lru_cache(maxsize=50)
    def cv2_image_open(file) -> cv2.typing.MatLike:
        cv_image = cv2.imread(file)
        return cv_image

    @staticmethod
    @functools.lru_cache(maxsize=50)
    def get_cv2_rgb_array(file, size) -> cv2.typing.MatLike:
        cv_image = ImageUtils.cv2_image_open(file)
        if size:
            h, w = cv_image.shape[:2]
            thumb_size = ImageUtils.get_cv_thumb_size((w,h), size)
            cv_image = cv2.resize(cv_image, thumb_size, interpolation= cv2.INTER_AREA)
        cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return cv_image_rgb

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    def get_cv2_pil_image(file: str, size=(1440,1440), as_photoimage = False):
        image_array = ImageUtils.get_cv2_rgb_array(file, size)
        img = Image.fromarray(image_array)
        if as_photoimage:
            return ImageTk.PhotoImage(img)
        else:
            return img

