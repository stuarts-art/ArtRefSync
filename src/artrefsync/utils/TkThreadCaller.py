from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
import ttkbootstrap as ttk
from threading import Event, Thread
import time
from artrefsync.config import config

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class TkThreadCaller:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            return object.__new__(cls)
        else:
            return TkThreadCaller._instance

    @staticmethod
    def get_thread_caller() -> "TkThreadCaller":
        return TkThreadCaller._instance


    def __init__(self, root: ttk.Frame, event_name=None):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.root = root
        self.on_finish_map = {}
        self.cancel_map = defaultdict(set)
        self.cancel_key_map = {}

    class _GUICallData:
        def __init__(self, fn, response):
            self.fn = fn
            self.response = response
            self.reply = None
            self.reply_event = Event()

    def add(
        self, task: callable, on_finish: callable, cancel_key="key", *args, **kwargs
    ) -> None:
        new_kwargs = {"task": task, "on_finish": on_finish, "old_kwargs": kwargs}
        future = self.executor.submit(task, *args, **kwargs)
        self.on_finish_map[future] = on_finish
        future.add_done_callback(self.call_on_finish)
        if cancel_key:
            self.cancel_map[cancel_key].add(future)
            self.cancel_key_map[future] = cancel_key
            logger.info("%i active threads for cancel key %s", len(self.cancel_map[cancel_key]), cancel_key)

        return future

    def cancel(self, cancel_key):
        logger.info(
            "Cancel called for key: %s, Current thread count: %s",
            cancel_key,
            0
            if cancel_key not in self.cancel_map
            else len(self.cancel_map[cancel_key]),
        )

        if cancel_key in self.cancel_map:
            for future in self.cancel_map.pop(cancel_key):
                future.cancel()
                if future in self.cancel_key_map:
                    self.cancel_key_map.pop(future)
        return

    def call_on_finish(self, future):
        try:
            if future in self.cancel_key_map:
                self.root.after(0, self.on_finish_map.pop(future), future.result())
                cancel_key = self.cancel_key_map.pop(future)
                if cancel_key in self.cancel_map:
                    self.cancel_map[cancel_key].remove(future)
        except Exception as e:
            logger.error(e)

    def stop(self):
        logger.info("Stopping active threads...")
        return self.executor.shutdown(cancel_futures=True, wait=True)
