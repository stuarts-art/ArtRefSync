import logging
import os
import tkinter as tk
from asyncio import Event
from threading import Lock
from tkinter.filedialog import askdirectory

import ttkbootstrap as ttk
from tenacity import retry, stop_after_attempt

from artrefsync.config import get_config
from artrefsync.constants import BINDING, TABLE, get_table_mapping
from artrefsync.sync_coordinator import sync_artist, sync_config, sync_from_store
from artrefsync.ui.widgets.InputTreeView import InputTreeviewFrame
from artrefsync.ui.widgets.RoundedIcon import RoundedIcon
from artrefsync.utils.event_binder import event_binder
from artrefsync.utils.TkThreadCaller import thread_caller

config = get_config()
logger = logging.getLogger(__name__)


class ConfigTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        logger.info("Init Config Tab")
        super().__init__(root, *args, **kwargs)
        self.configure_style(root)
        style = ttk.Style()
        self.sync_lock = Lock()
        self.lock_owner = ""
        style.configure(
            "custom.TNotebook", tabposition="nw", borderwidth=0, tabmargins=0
        )
        style.configure(
            "custom.TNotebook.Tab",
            width=8,
            font=(None, 8),
            borderwidth=0,
            focuscolor=style.lookup("custom.TNotebook.Tab", "background"),
            bordercolor="black",
        )

        style.configure(
            "sub.TNotebook", tabposition="wn", borderwidth=0, tabmargins=0, padding=5
        )
        style.configure("sub.TNotebook.Tab", width=10, borderwidth=0)
        self.config_notebook = ttk.Notebook(self, style="custom.TNotebook")
        self.config_notebook.pack(expand=True, fill="both")
        self.init_control_tab()
        event_binder.bind(BINDING.ON_ARTIST_SYNC, self.start_artist_sync, self)
        event_binder[BINDING.SYNC_LOCK] = self.sync_lock

        self.load()

    @retry(stop=stop_after_attempt(3))
    def load(self):
        self.config_table_tabs = {}
        self.widget_dict = {}
        self.var_dict = {}
        self.sync_event = Event()
        self.store_sync_running = False
        self.frames = {}

        self.tab_groups = ["App", "Boards", "Stores"]
        self.tab_groups = {
            "App": [TABLE.APP],
            "Boards": [TABLE.E621, TABLE.R34, TABLE.DANBOORU],
            "Stores": [TABLE.EAGLE, TABLE.LOCAL],
        }
        self.group_widgets = {}

        for tab_group, tables in self.tab_groups.items():
            if len(tables) == 1:
                table = tables[0]
                group_widget = ttk.ScrolledFrame(self.config_notebook, padding=10)
                self.group_widgets[tab_group] = group_widget
                self.init_config_tabs(table, group_widget)
                self.frames[table] = group_widget
                group_widget = group_widget.container

            else:
                group_widget = ttk.Notebook(self.config_notebook, style="sub.TNotebook")
                self.group_widgets[tab_group] = group_widget
                for table in tables:
                    sub_frame = ttk.Frame(group_widget)
                    sub_frame.grid_columnconfigure(0, minsize=15)
                    self.init_config_tabs(table, sub_frame)
                    group_widget.add(
                        sub_frame,
                        text=table.capitalize(),
                    )
                    self.frames[table] = sub_frame

            self.config_notebook.add(group_widget, text=tab_group.capitalize())

        self.clear_button = RoundedIcon(
            self, text="✕", size=(25, 25), command=self.toggle_console_window
        )
        self.clear_button.place(relx=1.0, rely=0.0, anchor=tk.NE)

    @retry(stop=stop_after_attempt(3))
    def reload(self):
        config.reload_config()
        for table, frame in self.frames.items():
            logger.info("Destroying config table: %s", table)
            frame.destroy()

        self.load()

    def init_control_tab(self):
        tab_frame = ttk.Frame(self.config_notebook, padding=10)
        self.config_notebook.add(tab_frame, text="Controls")
        pack_args = {"side": tk.TOP, "pady": 10, "padx": 10, "anchor": tk.NW}

        def create_control_button(text, command):
            return ttk.Button(tab_frame, text=text, command=command).pack(**pack_args)

        create_control_button("Save config", self.save_config)
        create_control_button("Reset config", self.reload)
        self.start_sync_button = create_control_button("Start Sync", self.start_sync)
        self.start_store_sync_button = create_control_button(
            "Sync from store", self.start_store_sync
        )

    def init_config_tabs(self, table, tab_frame: ttk.Frame):
        self.config_table_tabs[table] = tab_frame
        self.widget_dict[table] = {}
        self.var_dict[table] = {}

        tab_frame.columnconfigure(0, weight=0, minsize=150)
        tab_frame.columnconfigure(1, weight=1)

        grid_args = {"pady": 10, "padx": 10}

        for i, table_field in enumerate(get_table_mapping()[table]):
            lines = []
            line = ""
            for word in table_field.capitalize().split("_"):
                if len(word) + len(line) > 12:
                    if line:
                        lines.append(line)
                    line = word
                else:
                    if line:
                        line += " "
                    line += word
            lines.append(line)

            label = ttk.Label(tab_frame, text="\n".join(lines))
            label.grid(row=i, column=0, sticky="w", **grid_args)

            if "list" in table_field or "artists" == table_field:
                list_frame = InputTreeviewFrame(tab_frame, config[table][table_field])
                widget = list_frame
                list_frame.grid(row=i, column=1, sticky=("w", "E"), **grid_args)
            else:
                if "enabled" in table_field:
                    check_var = tk.IntVar()
                    check_var.set(1 if config[table][table_field] else 0)
                    self.var_dict[table][table_field] = check_var
                    entry = ttk.Checkbutton(
                        tab_frame,
                        text="",
                        variable=check_var,
                        bootstyle="round toggle",
                    )

                elif "dir" in table_field:
                    entry = ttk.Entry(tab_frame)
                    entry.insert(0, config[table][table_field])
                    entry.bind("<Double-Button-1>", self.select_dir)

                elif "key" in table_field or "username" in table_field:
                    entry = ttk.Entry(tab_frame, show="*")
                    entry.insert(0, config[table][table_field])
                else:
                    entry = ttk.Entry(
                        tab_frame
                        # width=30,
                    )
                    entry.insert(0, config[table][table_field])
                entry.grid(row=i, column=1, sticky=("w", "e"), **grid_args)
                widget = entry
            self.widget_dict[table][table_field] = widget

    def toggle_console_window(self):
        self.console_var.set(not self.console_var.get())
        toggle = self.console_var.get()
        logger.info("Toggling to %s", toggle)

    def select_dir(self, e):
        dir = askdirectory()
        if dir:
            e.widget.delete(0, tk.END)
            e.widget.insert(0, dir)

    def save_config(self):
        for table in TABLE:
            for table_field in get_table_mapping()[table]:
                widget = self.widget_dict[table][table_field]
                if isinstance(widget, ttk.Checkbutton):
                    val = self.var_dict[table][table_field].get() == 1
                else:
                    val = widget.get()
                config[table][table_field] = val
        config.reload_config()

    def configure_style(self, root):
        self.style = ttk.Style()

    def start_sync(self):
        func_name = "start_sync"
        if not self.sync_lock.acquire(blocking=False):
            if self.lock_owner == func_name:
                logger.warning("Canceling %s.", func_name)
                thread_caller.cancel(func_name)
                self.sync_lock.release()
                self.start_sync_button.configure(state="normal", text="Start Sync")
                self.start_store_sync_button.configure(state="normal")
                self.sync_lock.release()
            else:
                logger.warning(
                    "Could not acquire sync for %s because %s is running.",
                    func_name,
                    self.lock_owner,
                )
                thread_caller.cancel()
            return
        try:
            self.start_sync_button.configure(state="active", text="Cancel Sync")
            self.start_store_sync_button.configure(state="disabled")
            if config.log_level == "DEBUG":
                sync_config(self.sync_event)
                self.finish_sync()
            else:
                thread_caller.add(
                    sync_config, self.finish_sync, func_name, self.sync_event
                )
        except Exception:
            thread_caller.cancel(func_name)
            logger.exception("Exception recieved while syncing. Resetting buttons.")
            self.after_idle(self.finish_sync)

    def finish_sync(self, *nargs, **kwargs):
        logger.info("Sync Finished. Resetting button.")
        self.start_sync_button.configure(state="normal", text="Start Sync")
        self.start_store_sync_button.configure(state="normal")
        config.reload_config()
        self.lock_owner = ""
        self.sync_event.clear()
        self.sync_lock.release()

    def start_artist_sync(self, artist="", board="", only_recent=False):
        logger.info("START ARTIST SYNC %s, %s, %s", artist, board, only_recent)
        func_name = "artist_sync"
        if not self.sync_lock.acquire(blocking=False):
            logger.warning("Failed to acquire lock.")
            if self.lock_owner == func_name:
                logger.warning("Canceling %s.", func_name)
                thread_caller.cancel(func_name)
                self.sync_lock.release()
                self.start_sync_button.configure(state="normal", text="Start Sync")
                self.start_store_sync_button.configure(state="normal")
                return
            else:
                logger.warning(
                    "Could not acquire sync for %s because %s is running.",
                    func_name,
                    self.lock_owner,
                )
        thread_caller.add(
            sync_artist,
            self.finish_artist_sync,
            func_name,
            artist_name=artist,
            board_name=board,
            stop_event=self.sync_event,
            only_recent=only_recent,
        )

    def finish_artist_sync(self, *args, **kwargs):
        self.sync_lock.release()
        self.lock_owner = ""
        logger.info("FINISH ARTIST SYNC")
        event_binder.event_generate(BINDING.ON_LOADING_DONE)

    def config_menu(self):
        self.root.filemenu.add_command(
            label="Edit Config", command=lambda: os.startfile(config.path)
        )

    def start_store_sync(self):
        func_name = "start_store_sync"
        if not self.sync_lock.acquire(blocking=False):
            if func_name == self.lock_owner:
                logger.warning("Canceling %s.", func_name)
                thread_caller.cancel(func_name)
                self.finish_sync()
            else:
                logger.warning("Start sync called but could not acquire lock.")
            return

        try:
            self.lock_owner = func_name
            self.store_sync_running = True
            self.start_store_sync_button.configure(
                state="active", text="Cancel Sync", bootstyle="warning"
            )
            self.start_sync_button.configure(state="disabled")
            if config.log_level == "DEBUG":
                sync_from_store(self.sync_event)
                self.finish_store_sync()
            else:
                thread_caller.add(
                    sync_from_store,
                    self.finish_store_sync,
                    func_name,
                    self.sync_event,
                )
        except Exception:
            thread_caller.cancel(func_name)
            logger.exception("Exception recieved while syncing. Resetting buttons.")
            self.after_idle(self.finish_sync)

    def finish_store_sync(self, *nargs, **kwargs):
        logger.info("Store sync Finished. Reseting button.")
        self.sync_event.clear()
        self.start_store_sync_button.configure(
            state="normal", text="Start Store Sync", bootstyle="default"
        )
        self.start_sync_button.configure(state="normal")
        config.reload_config()
        self.sync_lock.release()
