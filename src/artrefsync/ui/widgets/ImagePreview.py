import logging
import tkinter as tk

import ttkbootstrap as ttk
from PIL import Image, ImageTk

from artrefsync.config import get_config
from artrefsync.constants import APP, BINDING
from artrefsync.db.post_db import PostDb, get_sorted_posts
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)


def cancel_preview_jobs():
    widget: ImagePreview = event_binder[BINDING.PREVIEW_WIDGET]
    if widget:
        widget.cancel_preview_jobs()


def update_preview_with_tags(tags: str | tuple[str] | list[str] = "", x=10, y=10, anchor=tk.NW):
    widget: ImagePreview = event_binder[BINDING.PREVIEW_WIDGET]
    if widget:
        if not tags:
            tags = []
        elif isinstance(tags, str) | isinstance(tags, tuple):
            tags = [tags]
        widget.update_preview(tags=tags, x=x, y=y, anchor=anchor)


class ImagePreview:
    def __init__(self, root, count=1):
        logger.debug("Initializing Image Preview")
        self.root: ttk.Window = root
        self.update_preview_cancel_key = "update_preview"
        self.after_jobs = []
        self.labels = [ttk.Label(root) for x in range(count)]
        event_binder[BINDING.PREVIEW_WIDGET] = self
        self.last_update = None
        logger.debug("Image Preview Initialized.")

    def cancel_preview_jobs(self):
        thread_caller.cancel(self.update_preview_cancel_key)
        while self.after_jobs:
            job = self.after_jobs.pop()
            self.root.after_cancel(job)


    def clear(self):
        logger.info("Clearing preview")
        self.cancel_preview_jobs()
        for label in self.labels:
            label.config(image=None)
            label.photo = None
            label.place_forget()
        self.last_update = None
        self.root.update_idletasks()

    def update_preview(self, tags, x=10, y=10, anchor=tk.NW):
        args = (tags, x, y, anchor)
        logger.info("updating with tags %s", args)
        if args == self.last_update:
            return
        self.last_update = args
        if not config[APP.PREVIEW_ENABLED]:
            return
        logger.debug("Updating preview for tags %s", tags)
        self.cancel_preview_jobs()
        if not tags:
            return self.clear()

        thread_caller.add(
            self._get_image,
            on_finish=None,
            cancel_key=self.update_preview_cancel_key,
            after=0,
            tags=tags,
            x=x,
            y=y,
            anchor=anchor,
        )

    def _get_image(self, tags:list[str], x, y, anchor):
        logger.info("Getting images for tags %s", tags)
        sort_by = event_binder.get_or_default(BINDING.SORT_BY, "id")
        sort_dir = event_binder.get_or_default(BINDING.SORT_DIR, "DESC")
        
        rows = get_sorted_posts(*tags, order_by=sort_by, order_dir=sort_dir, limit=len(self.labels))
        if not rows:
            return self.clear()

        image_info = []
        with PostDb() as post_db:
            for row in rows:
                pid = row
                thumbnail_name = post_db.get_thumbnail(pid)
                is_rating_s = post_db.is_rating_s(pid)
                image_info.append((thumbnail_name, is_rating_s))

        if not image_info:
            return self.clear()

        small_images = []
        large_images = []
        for thumbnail_name, is_rating_s in image_info:
            blur = config[APP.BLUR_UNSAFE_ENABLED] and not is_rating_s
            image = ImageUtils.get_cv2_pil_image(
                thumbnail_name, (400, 200), as_photoimage=False, blur=blur
            )
            larger = ImageUtils.get_cv2_pil_image(
                thumbnail_name, (410, 205), as_photoimage=False, blur=blur
            )
            if image and larger:
                small_images.append(image)
                large_images.append(larger)

        if small_images and large_images:
            self.after_jobs.append(
                self.root.after(
                    0, self._set_image, small_images, x=x, y=y, anchor=anchor
                )
            )

            self.after_jobs.append(
                self.root.after(
                    25, self._set_image, large_images, x=x - 5, y=y, anchor=anchor
                )
            )
            self.after_jobs.append(
                self.root.after(
                    125, self._set_image, small_images, x=x, y=y, anchor=anchor
                )
            )
        else:
            self.clear()

    def _set_image(self, images: list[Image.Image], x, y, anchor, index=0):
        logger.debug("Setting images for tags %s, %d", len(images), index)
        if not images:
            self.clear()

        image = images[0]

        photo = ImageTk.PhotoImage(image)
        buffer = 5

        image_w, image_h = image.size
        half_w = image_w // 2
        half_h = image_h // 2
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        x_offset = 0 if tk.W in anchor else image_w if tk.E in anchor else half_w
        y_offset = 0 if tk.N in anchor else image_h if tk.S in anchor else half_h

        x_start = x - x_offset
        x_end = x + image_w

        if x_start < buffer:
            x_start = buffer
        elif x_end > root_w - buffer:
            x_start = root_w - buffer - image_w

        y_start = y - y_offset
        y_end = y + image_h

        if y_start < buffer:
            y_start = buffer
        elif y_end > root_h - buffer:
            y_start = root_h - buffer - image_h

        label = self.labels[index]
        label.place(x=x_start, y=y_start, anchor=tk.NW)
        label.config(image=photo)
        label.photo = photo
        if len(images) > 1:
            img = images[1]
            x_offset = x_end - img.width // 2
            y_offset = y_start + 10
            self._set_image(
                images[1:], x=x_offset, y=y_offset, anchor=tk.NW, index=index + 1
            )
        else:
            self.root.update_idletasks()
        label.lift()
