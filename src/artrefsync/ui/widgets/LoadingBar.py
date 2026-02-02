import ttkbootstrap as ttk
import tkinter as tk

from artrefsync.config import config
from artrefsync.constants import BINDING
from artrefsync.utils.EventManager import ebinder
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class LoadingBar(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, *args, **kwargs)
        # self.columnconfigure(1, weight=1)

        self.bar_val = ttk.IntVar(self, value=0)
        self.bar_max_val = ttk.IntVar(self, value=100)
        self.bar = ttk.Progressbar(
            self,
            orient=tk.HORIZONTAL,
            maximum=self.bar_max_val.get(),
            length=200,
            mode="determinate",
            variable=self.bar_val
        )
        self.bar_left_text = ttk.StringVar(self)
        self.label_left = ttk.Label(self, textvariable=self.bar_left_text)
        self.bar_right_text = ttk.StringVar(self)
        self.label_right = ttk.Label(self, textvariable=self.bar_right_text)

        self.label_right.pack(side="left")
        self.bar.pack(side="left", fill="x", expand=True)
        self.label_left.pack(side="left", fill="none")
        
    def increment(self, left_text = None, amount = 1, right_text = None ):
        self.bar_val.set(self.bar_val.get() + amount)
        if left_text is not None:
            self.bar_left_text.set(left_text)
        if right_text is not None:
            self.bar_right_text.set(right_text)
        else:
            count = self.bar_val.get()
            max = str(self.bar_max_val.get())
            max_len = len(max)
            self.bar_right_text.set(f"{count:0{max_len}d}/{max}")

    def set(self, max = 100, left_text = "", value = 0, right_text = None ):
        self.bar_max_val.set(max)
        self.bar['maximum'] = max

        self.bar_val.set(value)
        self.bar_left_text.set(left_text)
        if right_text is not None:
            self.bar_right_text.set(right_text)
        else:
            count = self.bar_val.get()
            max_str = str(self.bar_max_val.get())
            max_len = len(max_str)
            self.bar_right_text.set(f"{count:0{max_len}d}/{max_str}")

class LoadingBars(ttk.Frame):
    def __init__(self, root:ttk.Frame, *args, **kwargs):

        super().__init__(root, *args, **kwargs)
        self.root = root
        self.pack(side="left", fill="both", expand=True)
        self.root.grid_forget()
        self.is_packed = False
        self.right_is_packed = False
        self.columnconfigure(0, weight=0, minsize=400)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0, minsize=400)
        
        self.left_bar = LoadingBar(self)
        self.right_bar = LoadingBar(self)
        self.sep = ttk.Label(self)

        self.left_bar.grid(column=0,row=0, sticky=tk.W)
        self.sep.grid(column=1,row=0, sticky=tk.NSEW)
        # self.right_bar.grid(column=2,row=0, sticky=tk.W)

        ebinder.bind(BINDING.ON_LOAD_LEFT_SET, self.reset_right, self)
        ebinder.bind(BINDING.ON_LOAD_RIGHT_SET, self.set_right, self)
        ebinder.bind(BINDING.ON_LOADING_DONE, self.reset_bar, self)

        ebinder.bind(BINDING.ON_LOAD_LEFT_SET, self.left_bar.set, self)
        ebinder.bind(BINDING.ON_LOAD_LEFT_INCR, self.left_bar.increment, self)
        ebinder.bind(BINDING.ON_LOAD_RIGHT_SET, self.right_bar.set, self)
        ebinder.bind(BINDING.ON_LOAD_RIGHT_INCR, self.right_bar.increment, self)

    def reset_bar(self):
        self.is_packed = False
        self.root.grid_forget()
        
    def set_bar(self, *args, **kwargs):
        if not self.is_packed:
            self.root.grid(column=0, row=3, sticky="we")
            self.is_packed = True

    def reset_right(self, *args, **kwargs):
        self.set_bar()
        if self.right_is_packed:
            self.right_bar.grid_forget()
            self.right_is_packed = False

    def set_right(self, *args, **kwargs):
        self.set_bar()
        if not self.right_is_packed:
            self.right_bar.grid(column=2,row=0, sticky=tk.W)
            self.right_is_packed = True

