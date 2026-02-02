import logging
import tkinter as tk
from ctypes import windll

import ttkbootstrap as ttk
import win32api
from PIL import ImageTk

from artrefsync.config import config
from artrefsync.utils.image_utils import ImageUtils
from artrefsync.utils.TkThreadCaller import TkThreadCaller
import pywinstyles

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class RoundedIcon(ttk.Label):
    def __init__(
        self,
        root,
        text,
        normal_color="#FFFFFF00",
        hover_color="#595253",
        size=40,
        radius=5,
        style=None,
        **kwargs,
    ):
        if isinstance(size, int):
            width = size
            height = size
        else:
            width = size[0]
            height = size[1]

        self.text = text
        self.normal_icon = ImageTk.PhotoImage(
            ImageUtils.get_round_colored_rect(width, height, radius, normal_color)
        )
        if hover_color:
            self.hover_icon = ImageTk.PhotoImage(
                ImageUtils.get_round_colored_rect(width, height, radius, hover_color)
            )
            self.image = (self.normal_icon, "hover", self.hover_icon)
        else:
            self.image = self.normal_icon

        if not style:
            style = "TLabel"
            if isinstance(root, ttk.Text):
                style = "primary.TLabel"

        super().__init__(
            root, image=self.image, text=text, compound=tk.CENTER, style=style, **kwargs
        )


class ModernTopBar(ttk.Frame):
    def __init__(self, root: ttk.Window, override_default_top_bar=False):
        self.root = root
        self.init_style()
        self.init_scafolding()
        if override_default_top_bar:
            self.root.overrideredirect(True)
            self.minimized = False
            self.lastmonitor = None
            self.pre_snap = self.root.winfo_geometry()
            self.snapped = False
            self.init_modern_bar()
        else:
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
            self.top_bar_right,
            text="◨",
            hover_color=self.colors.dark,
            font=("Helvetica", 12),
            style=self.button_style,
            size=30
        )
        self.menu_button = RoundedIcon(
            self.top_bar_left,
            text="≡",
            hover_color=self.colors.dark,
            font=("Helvetica", 12),
            style=self.button_style,
            size=30
        )
        self.sidebar_left_toggle = RoundedIcon(
            self.top_bar_left,
            text="◧",
            hover_color=self.colors.dark,
            font=("Helvetica", 12),
            style=self.button_style,
            size=30
        )
        
        self.sidebar_right_toggle.pack(side="right", padx=5)
        self.menu_button.pack(side="left", padx=5)  # ,   pady=12)
        self.sidebar_left_toggle.pack(side="left", padx=5)  # ,   pady=12)

        self.menu_button.bind("<ButtonPress-1>", self.create_menu_settings_event)
        self.sidebar_left_toggle.bind("<ButtonPress-1>", self.toggle_left_sidebar)
        self.sidebar_right_toggle.bind("<ButtonPress-1>", self.toggle_right_sidebar)
        
    def init_scafolding(self):
        super().__init__(self.root, padding=5, style=self.top_style)
        self.grid(row=0, column=0, sticky="nswe")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.top = ttk.Frame(self, style=self.top_style, height=34)
        self.top_sep = ttk.Separator(self)
        self._mid = ttk.Frame(self)
        self.bot = ttk.Frame(self)

        self.left = ttk.Frame(self._mid, padding=5, style=self.side_style)
        self.left_sep = ttk.Separator(self._mid, orient="vertical")
        self.mid = ttk.Frame(self._mid)
        self.right_sep = ttk.Separator(self._mid, orient="vertical")
        self.right = ttk.Frame(self._mid, padding=5, style=self.side_style)

        self.top.grid(column=0, row=0, sticky="new", columnspan=3)


        self.top_sep.grid(column=0, row=1, sticky="we", columnspan=3)
        self._mid.grid(column=0, row=2, sticky="nswe")
        self.bot.grid(column=0, row=3, sticky="we")

        self._mid.rowconfigure(0, weight=2)
        self._mid.columnconfigure(2, weight=1, minsize=300)

        self.left.grid(column=0, row=0, sticky="nws")
        self.left_sep.grid(column=1, row=0, sticky="ns")
        self.mid.grid(column=2, row=0, sticky="nswe")
        self.right_sep.grid(column=3, row=0, sticky="ns")
        self.right.grid(column=4, row=0, sticky="nes")

        # Top Grid: L,M,R rows
        self.top.rowconfigure(0, weight=1, pad=2)
        self.top.columnconfigure(0, weight=1)
        self.top.columnconfigure(1, weight=1)
        self.top.columnconfigure(2, weight=1)
        self.top_bar_left = ttk.Frame(self.top, style=self.top_style)
        self.top_bar_mid = ttk.Frame(self.top, style=self.top_style)
        self.top_bar_right = ttk.Frame(self.top, style=self.top_style)
        self.top_bar_left.grid(row=0, column=0, sticky="w")
        self.top_bar_mid.grid(row=0, column=1)
        self.top_bar_right.grid(row=0, column=2, sticky="e")
        self.top.grid_propagate(False)

    def init_modern_bar(self):
        button_style = "TLabel"
        close_label = RoundedIcon(
            self.top_bar_right,
            text="✕",
            hover_color=self.colors.danger,
            style=button_style,
        )
        box_label = RoundedIcon(
            self.top_bar_right,
            text="☐",
            hover_color=self.colors.dark,
            style=button_style,
        )
        dash_label = RoundedIcon(
            self.top_bar_right,
            text="🗕",
            hover_color=self.colors.dark,
            style=button_style,
        )
        self.sidebar_right_toggle = RoundedIcon(
            self.top_bar_right,
            text="◨",
            hover_color=self.colors.dark,
            font=("Helvetica", 14),
            style=button_style,
        )
        self.menu_button = RoundedIcon(
            self.top_bar_left,
            text="≡",
            hover_color=self.colors.dark,
            font=("Helvetica", 14),
            style=button_style,
        )
        self.sidebar_left_toggle = RoundedIcon(
            self.top_bar_left,
            text="◧",
            hover_color=self.colors.dark,
            font=("Helvetica", 14),
            style=button_style,
        )

        close_label.pack(side="right", padx=5)  # , pady=12)
        box_label.pack(side="right", padx=5)  # ,   pady=12)
        dash_label.pack(side="right", padx=5)  # ,  pady=12)
        self.sidebar_right_toggle.pack(side="right", padx=5)
        self.menu_button.pack(side="left", padx=5)  # ,   pady=12)
        self.sidebar_left_toggle.pack(side="left", padx=5)  # ,   pady=12)

        self.bind("<Enter>", self.outer_frame_enter)
        self.bind("<Leave>", self.outer_frame_leave)
        self.bind("<ButtonPress-1>", self.start_drag)
        self.bind("<ButtonRelease-1>", self.end_drag)

        self.menu_button.bind("<ButtonPress-1>", self.create_menu_settings_event)
        self.sidebar_left_toggle.bind("<ButtonPress-1>", self.toggle_left_sidebar)
        self.sidebar_right_toggle.bind("<ButtonPress-1>", self.toggle_right_sidebar)
        self.top.bind("<ButtonPress-1>", self.start_move)
        self.top.bind("<ButtonRelease-1>", self.end_move)
        self.top.bind("<Double-1>", lambda e: self.on_zoom())
        dash_label.bind("<ButtonRelease-1>", lambda e: self.minimize_window())
        box_label.bind("<ButtonRelease-1>", lambda e: self.on_zoom())
        # close_label.bind("<ButtonRelease-1>", lambda e: self.root.destroy())
        close_label.bind("<ButtonRelease-1>", self.on_close)
        close_label.bind("<Map>", lambda e: self.restore_window())
        self.root.after(10, lambda: self.set_appwindow())

    def on_close(self, event=None):
        thread_caller = TkThreadCaller(self)
        thread_caller.stop()
        self.root.destroy()
        # raise Exception()

    def toggle_left_sidebar(self, event=None):
        left_info = self.left.grid_info()
        if left_info:
            self.left.grid_forget()
            self.left_sep.grid_forget()
        else:
            self.left.grid(column=0, row=0, sticky="nws")
            self.left_sep.grid(column=1, row=0, sticky="ns")

    def toggle_right_sidebar(self, event=None):
        right_info = self.right.grid_info()
        if right_info:
            self.right.grid_forget()
            self.right_sep.grid_forget()
        else:
            self.right_sep.grid(column=3, row=0, sticky="ns")
            self.right.grid(column=4, row=0, sticky="nes")

    def start_drag(self, event):
        g = [int(g) for g in self.root.winfo_geometry().replace("x", "+").split("+")]
        x = event.x_root - g[2]
        y = event.y_root - g[3]

        self.drag_i = 0 if x <= 7 else (1 if x < g[0] - 7 else 2)
        self.drag_j = 0 if y <= 7 else (1 if y < g[1] - 7 else 2)

        event.widget.unbind("<Enter>")  # Remove change cursor binding
        event.widget.unbind("<Leave>")  # Remove change cursor binding
        event.widget.bind("<B1-Motion>", self.drag)
        self.dragx = event.x_root
        self.dragy = event.y_root

    def drag(self, event):
        g = [int(g) for g in self.root.winfo_geometry().replace("x", "+").split("+")]
        out_g = g
        deltax = event.x_root - self.dragx
        deltay = event.y_root - self.dragy
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
        self.dragx = event.x_root
        self.dragy = event.y_root
        if self.drag_i == 0:
            out_g[0] -= deltax
            out_g[2] += deltax
        elif self.drag_i == 2:
            out_g[0] += deltax

        if self.drag_j == 0:
            out_g[1] -= deltay
            out_g[3] += deltay
        elif self.drag_j == 2:
            out_g[1] += deltay
        self.root.geometry(f"{out_g[0]}x{out_g[1]}+{out_g[2]}+{out_g[3]}")

    def end_drag(self, event):
        self.pre_snap = self.root.winfo_geometry()
        self.unbind("<B1-Motion>")
        self.bind("<Enter>", self.outer_frame_enter)
        self.bind("<Leave>", self.outer_frame_leave)
        self.outer_frame_leave(None)

    def outer_frame_enter(self, event):
        cursor_rows = [
            ["size_nw_se", "sb_v_double_arrow", "size_ne_sw"],
            ["sb_h_double_arrow", "arrow", "sb_h_double_arrow"],
            ["size_ne_sw", "sb_v_double_arrow", "size_nw_se"],
        ]
        g = [int(g) for g in self.root.winfo_geometry().replace("x", "+").split("+")]
        x = event.x_root - g[2]
        y = event.y_root - g[3]

        i = 0 if x <= 20 else (1 if x < g[0] - 20 else 2)
        j = 0 if y <= 20 else (1 if y < g[1] - 20 else 2)

        # print(f"({i}, {j}), {cursor_rows[j][i]}")
        self.root.config(cursor=cursor_rows[j][i])

    def outer_frame_leave(self, event):
        self.root.config(cursor="arrow")

    def set_appwindow(self):
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        hwnd = windll.user32.GetParent(self.root.winfo_id())
        style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        self.root.wm_withdraw()
        self.root.after(10, lambda: self.root.wm_deiconify())

    def on_zoom(self, _=None):
        self.root.state()
        if self.root.state() == "zoomed":
            self.root.state("normal")
        else:
            self.root.state("zoomed")

    # TODO: Do more testing on iconify and window management. Maybe find a less "magical" solution.
    def minimize_window(self, _=None):
        self.minimized = True
        self.root.overrideredirect(False)
        self.root.iconify()

    def restore_window(self, _=None):
        if self.minimized:
            self.root.overrideredirect(True)
            self.set_appwindow()
        self.minimized = False

    def start_move(self, event):
        self.outer_frame_enter(event)
        x = event.x_root
        y = event.y_root

        if not self.snapped:
            self.pre_snap = self.root.winfo_geometry()
        else:
            geometry = [
                int(g) for g in self.root.winfo_geometry().replace("x", "+").split("+")
            ]
            x_ratio = (x - geometry[2]) / geometry[0]
            y_offset = y - geometry[3]
            pre_geometry = [int(g) for g in self.pre_snap.replace("x", "+").split("+")]
            new_x = x - int(x_ratio * pre_geometry[0])
            new_y = y - y_offset
            self.root.geometry(f"{pre_geometry[0]}x{pre_geometry[1]}+{new_x}+{new_y}")
        self.lastx = event.x_root
        self.lasty = event.y_root
        event.widget.bind("<B1-Motion>", self.move_window)

    def move_window(self, event):
        deltax = event.x_root - self.lastx
        deltay = event.y_root - self.lasty
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
        self.lastx = event.x_root
        self.lasty = event.y_root
        monitor = win32api.MonitorFromPoint((x, y))
        if monitor:
            self.lastmonitor = monitor

    def end_move(self, event):
        self.root.update()
        x = event.x_root
        y = event.y_root
        monitor = win32api.MonitorFromPoint((x, y))
        if monitor:
            self.lastmonitor = monitor

        monitor_info = win32api.GetMonitorInfo(self.lastmonitor)

        work = monitor_info["Work"]
        monitor = monitor_info["Monitor"]

        north = y - monitor[1] < 20
        south = monitor[3] - y < 20
        west = x - monitor[0] < 20
        east = monitor[2] - x < 20

        if north or south or east or west:
            height = work[3] - work[1]
            width = work[2] - work[0]
            x = work[0]
            y = work[1]

            if south:
                height = height // 2
            if west or east:
                width = width // 2
                if north:
                    height = height // 2
            if east:
                x = work[0] + width
            if south:
                y = work[1] + height

            dir = f"{'N' if north else ''}{'S' if south else ''}{'W' if west else ''}{'E' if east else ''}"
            logger.info(f"Snap to {dir}")

            if not self.snapped:
                self.pre_snap = self.root.wm_geometry()
            self.snapped = True
            self.root.wm_geometry(f"{width}x{height}+{x}+{y}")
        else:
            if self.snapped:
                self.snapped = False
        event.widget.unbind("<B1-Motion>")

    def start(self):
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error("Error: %s", e)
            logger.error("Attempting to close existing threads")
            self.on_close()


if __name__ == "__main__":
    # window = ttk.Window(themename="superhero", size=(1080,1080))
    window = ttk.Window(themename="darkly", size=(1080, 1080))
    bar = ModernTopBar(window)
    bar.pack(fill="both", expand=True)
    ttk.Label(bar.left, text="Left", style="danger.TLabel").pack()
    ttk.Label(
        bar.mid,
        text="Test",
    ).pack()
    ttk.Label(bar.right, text="Right", style="danger.TLabel").pack()
    style = ttk.Style()


    window.mainloop()
