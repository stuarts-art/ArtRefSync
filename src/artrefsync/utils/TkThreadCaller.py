import logging
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event

import ttkbootstrap as ttk

from artrefsync.config import config

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class TkThreadCaller:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            return object.__new__(cls)
        else:
            return TkThreadCaller._instance

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    @staticmethod
    def get_thread_caller() -> "TkThreadCaller":
        return TkThreadCaller._instance

    def __init__(self, root: ttk.Frame = None, event_name=None):
        self.executor = ThreadPoolExecutor()
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
        future = self.executor.submit(task, *args, **kwargs)
        if on_finish:
            self.on_finish_map[future] = on_finish
            future.add_done_callback(self.call_on_finish)
            if cancel_key:
                self.cancel_map[cancel_key].add(future)
                self.cancel_key_map[future] = cancel_key
                logger.debug(
                    "%i active threads for cancel key %s",
                    len(self.cancel_map[cancel_key]),
                    cancel_key,
                )

        return future

    def cancel(self, cancel_key):
        logger.debug(
            "Cancel called for key: %s, Current thread count: %s",
            cancel_key,
            (
                0
                if cancel_key not in self.cancel_map
                else len(self.cancel_map[cancel_key])
            ),
        )

        if cancel_key in self.cancel_map:
            for future in self.cancel_map.pop(cancel_key):
                future.cancel()
                if future in self.cancel_key_map:
                    self.cancel_key_map.pop(future)
        return

    def call_on_finish(self, future: Future):
        try:
            if future in self.cancel_key_map:
                on_finish = self.on_finish_map.pop(future)
                result = future.result()
                if self.root:
                    self.root.after_idle(on_finish, result)
                else:
                    on_finish(result)
                cancel_key = self.cancel_key_map.pop(future)
                if cancel_key in self.cancel_map:
                    if future in self.cancel_map[cancel_key]:
                        self.cancel_map[cancel_key].discard(future)

        except Exception as e:
            logger.debug(e)

    def stop(self):
        logger.info("Stopping active threads...")
        self.executor.shutdown(cancel_futures=True, wait=True)
        logger.info("Active Threads Stopped.")

