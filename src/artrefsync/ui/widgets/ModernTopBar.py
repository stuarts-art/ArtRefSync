import logging

import ttkbootstrap as ttk

from artrefsync.config import config
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class ModernTopBar(ttk.Frame):
    def __init__(self, root: ttk.Window, override_default_top_bar=False):
        logger.info("Init ModernTopBar")
        self.root = root
        self.init_style()
        self.init_scafolding()
        self.init_menu()

    def init_style(self):
        self.style = ttk.Style()
        self.colors = self.style.colors
        self.style.configure("primary.TLabel", background=self.colors.get("inputbg"))
        self.top_style = "TFrame"
        self.side_style = None
        self.button_style = "TLabel"

    menu_event_name = "<<Menu_Settings>>"

    def create_menu_settings_event(self, e=None):
        self.root.event_generate("<<Menu_Settings>>")

    def init_menu(self):
        self.sidebar_right_toggle = RoundedIcon(
            self.top_right,
            text="◨",
            hover_color=self.colors.dark,
            font=("Helvetica", 12),
            style=self.button_style,
            size=30,
        )
        self.menu_button = RoundedIcon(
            self.top_left,
            text="≡",
            hover_color=self.colors.dark,
            font=("Helvetica", 12),
            style=self.button_style,
            size=30,
        )
        self.sidebar_left_toggle = RoundedIcon(
            self.top_left,
            text="◧",
            hover_color=self.colors.dark,
            font=("Helvetica", 12),
            style=self.button_style,
            size=30,
        )

        self.sidebar_right_toggle.pack(side="right", padx=5)
        self.menu_button.pack(side="left", padx=5)  # ,   pady=12)
        self.sidebar_left_toggle.pack(side="left", padx=5)  # ,   pady=12)

        self.menu_button.bind("<ButtonPress-1>", self.create_menu_settings_event)
        self.sidebar_left_toggle.bind("<ButtonPress-1>", self.toggle_left_sidebar)
        self.sidebar_right_toggle.bind("<ButtonPress-1>", self.toggle_right_sidebar)

    def init_scafolding(self):
        """ UI Structure  
        - _top: top_bar_left, top_bar_mid, top_bar_right  
        - _mid: left, mid, right  
        - _bot:
        """
        super().__init__(self.root, padding=5, style=self.top_style)
        self.grid(row=0, column=0, sticky="nswe")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Top, Mid, Bot, Init and grid placement
        self._top = ttk.Frame(self, style=self.top_style, height=34)
        self._top_sep = ttk.Separator(self)
        self._mid = ttk.Frame(self)
        self._bot = ttk.Frame(self)
        self._top.grid(column=0, row=0, sticky="new", columnspan=3)
        self._top_sep.grid(column=0, row=1, sticky="we", columnspan=3)
        self._mid.grid(column=0, row=2, sticky="nswe")
        self._bot.grid(column=0, row=3, sticky="we")

        # Top, Mid row and column config
        self._top.rowconfigure(0, weight=1, pad=2)
        self._top.columnconfigure(0, weight=1)
        self._top.columnconfigure(1, weight=1)
        self._top.columnconfigure(2, weight=1)
        self._mid.rowconfigure(0, weight=2)
        self._mid.columnconfigure(2, weight=1, minsize=300)

        # Top sub_frames init and grid placement
        self.top_left = ttk.Frame(self._top, style=self.top_style)
        self.top_mid = ttk.Frame(self._top, style=self.top_style)
        self.top_right = ttk.Frame(self._top, style=self.top_style)
        self.top_left.grid(row=0, column=0, sticky="w")
        self.top_mid.grid(row=0, column=1, sticky="we")
        self.top_right.grid(row=0, column=2, sticky="e")
        self._top.grid_propagate(False)

        # Mid sub_frames init and grid placement
        self.mid_left = ttk.Frame(self._mid, padding=5, style=self.side_style)
        self.mid_left_sep = ttk.Separator(self._mid, orient="vertical")
        self.mid_mid = ttk.Frame(self._mid)
        self.mid_right_sep = ttk.Separator(self._mid, orient="vertical")
        self.mid_right = ttk.Frame(self._mid, padding=5, style=self.side_style)
        self.mid_left.grid(column=0, row=0, sticky="nws")
        self.mid_left_sep.grid(column=1, row=0, sticky="ns")
        self.mid_mid.grid(column=2, row=0, sticky="nswe")
        self.mid_right_sep.grid(column=3, row=0, sticky="ns")
        self.mid_right.grid(column=4, row=0, sticky="nes")


    def on_close(self, event=None):
        thread_caller = TkThreadCaller(self)
        thread_caller.stop()
        self.root.destroy()
        # raise Exception()

    def toggle_left_sidebar(self, event=None):
        left_info = self.mid_left.grid_info()
        if left_info:
            self.mid_left.grid_forget()
            self.mid_left_sep.grid_forget()
        else:
            self.mid_left.grid(column=0, row=0, sticky="nws")
            self.mid_left_sep.grid(column=1, row=0, sticky="ns")

    def toggle_right_sidebar(self, event=None):
        right_info = self.mid_right.grid_info()
        if right_info:
            self.mid_right.grid_forget()
            self.mid_right_sep.grid_forget()
        else:
            self.mid_right_sep.grid(column=3, row=0, sticky="ns")
            self.mid_right.grid(column=4, row=0, sticky="nes")

