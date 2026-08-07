import functools
import logging
import os
from pathlib import Path
from threading import Lock
from typing import ClassVar

import cv2
import ttkbootstrap as ttk
from PIL import Image, ImageDraw, ImageTk
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.config import get_config

config = get_config()
logger = logging.getLogger(__name__)


class ImageUtils:
    _lock: ClassVar[Lock] = Lock()
    _photo_lock: ClassVar[Lock] = Lock()
    _thumb_lock: ClassVar[Lock] = Lock()

    def blank():
        return ttk.PhotoImage()

    @classmethod
    @functools.lru_cache(maxsize=100)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    def getPilImage(cls, file: str, height=None, width=None) -> Image.Image:
        logger.debug("Cache-Miss, Getting Image")
        if not os.path.exists(file):
            raise FileNotFoundError
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
            with ImageUtils._thumb_lock:
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
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    @functools.lru_cache(maxsize=50)
    def get_tk_thumb(file: str, size=(1080, 720), radius=0):
        image = ImageUtils.getPilImageThumb(file, size=size)
        if radius:
            size = (image.width, image.height)
            image.putalpha(ImageUtils.getrounded_rect(size=size, radius=radius))
        with ImageUtils._photo_lock:
            return ImageTk.PhotoImage(image=image)

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    @functools.lru_cache
    def getrounded_rect(size, radius) -> Image.Image:
        """
        Produces a rounded grey-scale rectangle, useful for layer masking with putalpha.
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
            height = h
        else:
            width = w
            height = vh
        return (width, height)

    @staticmethod
    def cv_array_to_image(cv_image):
        cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cv_image_rgb)

    @staticmethod
    def cv2_image_open(file) -> cv2.typing.MatLike | None:
        cv_image = cv2.imread(file)
        return cv_image

    k_size = 20

    @staticmethod
    @functools.lru_cache(maxsize=50)
    def get_cv2_rgb_array(file, size, blur=False) -> cv2.typing.MatLike:
        cv_image = ImageUtils.cv2_image_open(file)
        if cv_image is None:
            error_message = "Failed to open image " + file
            logger.error(error_message)
            raise AttributeError
        h, w = cv_image.shape[:2]
        if size:
            thumb_size = ImageUtils.get_cv_thumb_size((w, h), size)
            cv_image = cv2.resize(cv_image, thumb_size, interpolation=cv2.INTER_AREA)

        if blur:
            ImageUtils.cv2_image_blur(cv_image)
        cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return cv_image_rgb

    def cv2_image_blur(cv_image, offset=0, blur_intensity=55):
        h, w = cv_image.shape[:2]
        h_start = int(h * offset)
        w_start = int(w * offset)
        h_end = int(h * (1.0 - offset))
        w_end = int(w * (1.0 - offset))
        blur_region = cv_image[h_start:h_end, w_start:w_end]
        blur_region = cv2.GaussianBlur(
            blur_region, (blur_intensity, blur_intensity), ImageUtils.k_size
        )
        cv_image[h_start:h_end, w_start:w_end] = blur_region

        text = "Censored"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.75
        thickness = 2
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]

        text_x = (w - text_size[0]) // 2
        text_y = (h + text_size[1]) // 2
        cv2.putText(
            cv_image,
            text,
            (text_x, text_y),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
        )

    @staticmethod
    def get_cv2_pil_image(
        file: str, size=(1440, 1440), as_photoimage=False, blur=False
    ) -> Image.Image | ImageTk.PhotoImage:
        if not file or not os.path.exists(file):
            raise FileNotFoundError()

        if ImageUtils.is_multiple_frames(file):
            return ImageUtils.get_cv2_frame(file, size, blur)
        else:
            image_array = ImageUtils.get_cv2_rgb_array(file, size, blur)
            img = Image.fromarray(image_array)
            if as_photoimage:
                return ImageTk.PhotoImage(img)
            else:
                return img

    @staticmethod
    def get_cv2_frame(file, size=(1080, 1080), blur=False):
        gif = cv2.VideoCapture(file)
        ret, frame = gif.read()
        if not ret:
            return None
        if size:
            h, w = frame.shape[:2]
            thumb_size = ImageUtils.get_cv_thumb_size((w, h), size)
            frame = cv2.resize(frame, thumb_size, interpolation=cv2.INTER_AREA)
        if blur:
            ImageUtils.cv2_image_blur(frame)
        image_frame = ImageUtils.cv_array_to_image(frame)
        return image_frame

    @staticmethod
    def get_cv2_frames(file, size=(1080, 1080)):
        duration = 0
        frames = []
        if not ImageUtils.is_multiple_frames(file):
            frames = [
                ImageUtils.get_cv2_pil_image(file, size),
            ]
            return frames, None, file

        gif = cv2.VideoCapture(file)
        if gif.isOpened():
            fps = gif.get(cv2.CAP_PROP_FPS)
            if fps:
                duration = int(1000 // fps)
            else:
                duration = 100

        while True:
            if len(frames) >= 100:
                break
            if frame := ImageUtils.frame_from_capture(gif, size):
                frames.append(frame)
            else:
                break
        return frames, duration, file

    @staticmethod
    def frame_from_capture(capture, size):
        ret, frame = capture.read()
        if not ret:
            return None
        if size:
            h, w = frame.shape[:2]
            thumb_size = ImageUtils.get_cv_thumb_size((w, h), size)
            frame = cv2.resize(frame, thumb_size, interpolation=cv2.INTER_AREA)
        img = ImageUtils.cv_array_to_image(frame)
        return img

    @staticmethod
    def is_multiple_frames(file):
        if not os.path.exists(file):
            raise FileNotFoundError
        if isinstance(file, Path):
            return file.suffix in [".mp4", ".mov", ".webm", ".gif"]
        else:
            ext = file.rsplit(".", 1)[-1]
            return ext in ["mp4", "mov", "webm", "gif"]

    @staticmethod
    def get_frame_duration(file):
        """Returns the average framerate of a PIL Image object"""
        duration = 100
        try:
            img = Image.open(file)
            img.seek(0)
            duration = img.info["duration"]
            duration = int(duration)
        except Exception:
            return 100
        return duration
