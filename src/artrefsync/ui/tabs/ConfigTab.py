import logging
import os
import tkinter as tk
from asyncio import Event
from tkinter.filedialog import askdirectory

import ttkbootstrap as ttk

# from PIL import Image, ImageTk
from artrefsync.config import config
from artrefsync.constants import TABLE, get_table_mapping
from artrefsync.sync import sync_config
from artrefsync.ui.widgets.InputTreeView import InputTreeviewFrame
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class ConfigTab(ttk.Frame):
    def __init__(self, root, *args, **kwargs):
        logger.info("Init Config Tab")
        super().__init__(root, *args, **kwargs)
        self.configure_style(root)
        self.thread_caller = TkThreadCaller(self)

        self.config_table_tabs = {}
        self.widget_dict = {}
        self.var_dict = {}
        self.sync_running = False
        self.start_event = None

        self.config_notebook = ttk.Notebook(self)
        self.config_notebook.pack(expand=True, fill="both", padx=5, pady=5)
        for table in TABLE:
            logger.info("Initializing %s tab.", table)
            tab_frame = ttk.Frame(self.config_notebook)
            self.init_config_tabs(table, tab_frame)
            self.config_notebook.add(
                tab_frame,
                text=table.capitalize().ljust(6),
            )
            
    def init_config_tabs(self, table, tab_frame):
        if table == TABLE.APP:
            self.save_config_button = ttk.Button(
                tab_frame, text="Save Config", command=self.save_config
            )
            self.save_config_button.grid(
                row=1, column=1, sticky=("w", "e"), pady=10, padx=5
            )
            self.start_sync_button = ttk.Button(
                tab_frame, text="Start Sync", command=self.start_sync
            )
            self.start_sync_button.grid(
                row=2, column=1, sticky=("w", "e"), pady=10, padx=5
            )

        self.config_table_tabs[table] = tab_frame
        self.widget_dict[table] = {}
        self.var_dict[table] = {}

        for i, table_field in enumerate(
            get_table_mapping()[table], 3 if table == TABLE.APP else 0
        ):
            label = ttk.Label(
                # tab_frame, text=f"{table_field.capitalize()}:", width=2
                tab_frame,
                text=f"{table_field.capitalize()}:",
            )
            label.grid(row=i, column=0, sticky="w", pady=10, padx=5)

            if "list" in table_field or "artists" == table_field:
                list_frame = InputTreeviewFrame(
                    tab_frame, config[table][table_field]
                )
                widget = list_frame
                list_frame.grid(row=i, column=1, sticky=("w", "E"), pady=10)
            else:
                if "enabled" in table_field:
                    check_var = tk.IntVar()
                    check_var.set(1 if config[table][table_field] else 0)
                    self.var_dict[table][table_field] = check_var
                    entry = ttk.Checkbutton(
                        tab_frame,
                        text="",
                        style="Roundtoggle.Toolbutton",
                        variable=check_var,
                    )

                elif "dir" in table_field:
                    # entry = ttk.Entry(tab_frame, width=30, show="*")
                    entry = ttk.Entry(tab_frame)
                    entry.insert(0, config[table][table_field])
                    entry.bind("<Double-Button-1>", self.select_dir)

                elif "key" in table_field or "username" in table_field:
                    # entry = ttk.Entry(tab_frame, width=30, show="*")
                    entry = ttk.Entry(tab_frame, show="*")
                    entry.insert(0, config[table][table_field])
                else:
                    entry = ttk.Entry(
                        tab_frame
                        # width=30,
                    )
                    entry.insert(0, config[table][table_field])
                entry.grid(row=i, column=1, sticky=("w", "e"), pady=10)
                widget = entry
            self.widget_dict[table][table_field] = widget


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

    def start_sync(self):
        if not self.sync_running:
            self.sync_running = True
            self.start_event = Event()
            self.start_sync_button.configure(state="active", text="Cancel Sync")
            self.thread_caller.add(sync_config, self.finish_sync, __name__, self.start_event )
        else:
            self.start_sync_button.configure(state="disabled")
            self.start_event.set()

    def finish_sync(self, *nargs, **kwargs):
        logger.info("Sync Finished. Reseting button.")
        self.sync_running = False
        # self.start_sync_button["text"] = "Start Sync"
        # self.start_sync_button.state(["normal"])
        self.start_sync_button.configure(state="normal", text="Start Sync")

        self.start_event = None

    def configure_style(self, root):
        self.style = ttk.Style()
        # self.style.configure("vert.TNotebook", tabposition="wn", tabmargins=(0, 30))
        # self.style.configure("vert.TNotebook.Tab", expand=(10, 0, 0, 0))

    def config_menu(self):
        self.root.filemenu.add_command(
            label="Edit Config", command=lambda: os.startfile(config.path)
        )

    def start_sync_config(self, data):
        sync_config()


if __name__ == "__main__":
    import artrefsync.ui.TagApp as TagApp

    TagApp.main()
