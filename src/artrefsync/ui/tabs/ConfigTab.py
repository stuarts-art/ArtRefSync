from asyncio import Event
import os
import tkinter as tk
from PIL import Image, ImageTk
import ttkbootstrap as ttk
# from ttkbootstrap.widgets.scrolled import 
from artrefsync.config import config
from artrefsync.constants import E621, TABLE, get_table_mapping
from artrefsync.sync import sync_config
from artrefsync.ui.TagApp import AppTab, ImagViewerApp
from artrefsync.ui.TkThreadCaller import TkThreadCaller

import logging

from artrefsync.ui.widgets.InputTreeView import InputTreeviewFrame
logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)




class  TabWrapper(AppTab):
    def init_ui(self, root):
        return ConfigTab(root)


class ConfigTab(ttk.Frame):
    def __init__(self, root: ImagViewerApp):
        self.tab = root.config_tab
        self.root = root

        self.sync_running = False
        self.start_event = None

        self.configure_style(self.root)
        self.init_config_tab()


    def init_config_tab(self):
        self.config_notebook = ttk.Notebook(self.tab)
        self.config_notebook.pack(expand=True, fill="both", padx=5, pady=5)
        # self.config_notebook.pack(expand=True, fill="both", padx=10, pady=10)
        self.config_table_tabs = {}
        self.widget_dict = {}
        self.var_dict = {}
        for table in TABLE:
            tab_frame = ttk.Frame(self.config_notebook)
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

            for i, table_field in enumerate(get_table_mapping()[table], 3 if table == TABLE.APP else 0):
                # lspacer = ttk.Label(tab_frame, text="", width=5)
                # lspacer.grid(row=i, column=0, sticky="w", pady=10, padx=5)
                # lspacer.grid(row=i, column=0, sticky="w", pady=10, padx=5)
                label = ttk.Label(
                    # tab_frame, text=f"{table_field.capitalize()}:", width=2
                    tab_frame, text=f"{table_field.capitalize()}:"
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
                    elif "api" in table_field or "name" in table_field:
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

            self.config_notebook.add(
                tab_frame,
                text=table.capitalize().ljust(6),
            )

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
            # self.start_sync_button["text"] = "Cancel Run"
            # self.start_sync_button.state(["active"])
            self.start_sync_button.configure(state="active", text = "Cancel Sync")
            self.root.thread_caller.add(sync_config, self.finish_sync, self.start_event)
        else:
            self.start_sync_button.configure(state="disabled")
            self.start_event.set()
            # self.start_sync_button.state(["disabled"])

    def finish_sync(self, *nargs, **kwargs):
        logger.info("Sync Finished. Reseting button.")
        self.sync_running = False
        # self.start_sync_button["text"] = "Start Sync"
        # self.start_sync_button.state(["normal"])
        self.start_sync_button.configure(state="normal", text = "Start Sync")

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
