from typing import Iterable
from operator import neg
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from artrefsync.config import config
from artrefsync.constants import BOARD, E621, EAGLE, R34, STORE, TABLE
from sortedcontainers import SortedDict, SortedSet
from artrefsync.stores.eagle_storage import EagleHandler

import logging
logger = logging.getLogger(__name__)


run = True


def main():
    root = ttk.Window(themename="darkly", size=(1080, 1080))
    # config = __Config()
    frame_left = ttk.Frame(root)
    frame_left.pack(side="left", padx=10, pady=10, anchor="n")
    artists = config[TABLE.E621][E621.ARTISTS]
    artists2 = config[TABLE.R34][R34.ARTISTS]

    artist_tree = InputTreeviewFrame(frame_left, artists)
    name_tree = InputTreeviewFrame(frame_left, artists2)

    artist_tree.pack(fill="y", expand=False, anchor="w", side="bottom", padx=5, pady=10)
    name_tree.pack(fill="y", expand=False, anchor="w", side="bottom")
    root.mainloop()


class ReadTreeView(ttk.Frame):
    def __init__(self, root, input_list: Iterable, ascending=True):
        super().__init__(root)
        self.setup_entry()
        self.setup_tree(input_list, ascending=ascending)
        self.detached_list = []
        self.setup_bindings()

    def setup_bindings(self):
        self.entry.bind("<Return>", self.on_return)
        self.entry.bind("<KeyRelease>", lambda e: self.tree.focus_on_text(self.entry.get()))
        self.tree.bind("<Double-1>", self.on_tree_lclick)
        # self.tree.bind("<BackSpace>", self.tree.delete_selected)
        # self.tree.bind("<KeyRelease-a>", self.tree.delete_selected)
        # self.tree.bind("<Control-z>", self.tree.undo_delete)

    def get(self):
        return list(self.tree.sorted)

    def setup_entry(self):
        entry_frame = ttk.Frame(self)
        entry_frame.pack(side="top", fill="x")
        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side="left", fill="x", expand=True)
        # self.button = ttk.Button(entry_frame)
        # self.button.pack(side="right")

    def setup_tree(self, input_list: Iterable, ascending=True):
        self.tree_frame = ttk.Frame(self, takefocus=True)
        # self.tree = ttk.Treeview(tree_frame, columns=("Artists","Close"), show="")
        self.tree = InputTreeview(
            self.tree_frame, input_list, columns=("Input", "Delete"), show=""
        )
        self.scroll = ttk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview
        )

        self.tree.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=self.scroll.set)

        self.detached = SortedSet()
        self.deleted = []
        input_list = sorted(input_list)
        self.tree_frame.pack(side="top", fill="both", pady=10, expand=True)

    def on_return(self, event):
        if self.focus_get() == self.entry:
            self.tree.add(self.entry.get())
        print(event)

    def on_tree_lclick(self, event):
        # rid = self.tree.selection()[0]
        column_id = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        print(f"{column_id} {row_id}")

        if column_id == "#2":
            self.tree.delete(row_id)



    def on_tree_rclick(self, event):

        selection = self.tree.selection()
        self.tree.detach()


class InputTreeview(ttk.Treeview):
    def __init__(self, parent, starting_list, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.sorted = SortedSet(starting_list)
        self.detached = set()
        self.created = []
        self.deleted = []  # Deleted Stack

        # Enforce alphabetical order for ease.
        self.column("Input", anchor="w")
        self.column("Delete", anchor="e", width=30)
        for val in self.sorted:
            self.insert("", "end", iid=val, values=(val, "❌"))

    def delete_selected(self, event=None):
        for item in self.selection():
            self.delete(item)

    def delete(self, *items):
        for item in items:
            self.sorted.discard(item)
            self.detached.discard(item)
            self.deleted.append(item)
        return super().delete(*items)

    def add(self, item):
        print(f"Adding {item}")
        if item not in self.sorted:
            self.sorted.add(item)
            index = self.sorted.index(item)
            self.insert("", index, iid=item, values=(item, "❌"))

    def undo_delete(self, event):
        print("Undo Recieved")
        if len(self.deleted) > 0:
            item = self.deleted.pop()
            self.add(item)
            print("Item {item} added back")

    def focus_on_text(self, text):
        for item in self.selection():
            self.selection_remove(item)
        # self.selection_clear()
        if not text:
            self.focus(self.sorted[0])

        else:
            idx = min(len(self.sorted) - 1, self.sorted.bisect_left(text))
            focusidx = min(len(self.sorted) - 1, idx + 5)
            match = self.sorted[idx]
            focus_match = self.sorted[focusidx]

            print(match)
            self.focus(match)
            self.see(match)
            self.selection_add(match)
            self.see(focus_match)

    def focus_on_next(self):
        # for item in self.selection():
        #     self.selection_remove(item)
        next = self.next(self.selection()[0])
        print(next)
        # self.focus(next)
        # self.see(next)

    def focus_on_prev(self):
        prev = self.prev(self.selection()[0])
        print(prev)
        # self.focus(prev)
        # self.see(prev)


if __name__ == "__main__":
    if run:
        main()
