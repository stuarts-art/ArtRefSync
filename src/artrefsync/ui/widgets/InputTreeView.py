import logging
from collections.abc import Iterable

import ttkbootstrap as ttk
from sortedcontainers import SortedSet

logger = logging.getLogger(__name__)


class InputTreeviewFrame(ttk.Frame):
    def __init__(self, root, input_list: Iterable, ascending=True):
        super().__init__(root)
        self.setup_entry()
        self.setup_tree(input_list, ascending=ascending)
        self.detached_list = []
        self.setup_bindings()

    def setup_bindings(self):
        self.entry.bind("<Return>", self.on_return)
        self.entry.bind(
            "<KeyRelease>", lambda e: self.tree.focus_on_text(self.entry.get())
        )
        self.tree.bind("<Double-1>", self.on_tree_lclick)
        self.tree.bind("<BackSpace>", self.tree.delete_selected)
        self.tree.bind("<KeyRelease-a>", self.tree.delete_selected)
        self.tree.bind("<Control-z>", self.tree.undo_delete)

    def get(self):
        return list(self.tree.sorted)

    def setup_entry(self):
        entry_frame = ttk.Frame(self)
        entry_frame.pack(side="top", fill="x")
        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side="left", fill="x", expand=True)

    def setup_tree(self, input_list: Iterable, ascending=True):
        self.tree_frame = ttk.Frame(self, takefocus=False)
        self.tree = InputTreeview(
            self.tree_frame, input_list, columns=("Delete"), show="tree", takefocus=True
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
            value = self.entry.get()
            value = value.strip()
            self.tree.add(value)
        logger.info(event)

    def on_tree_lclick(self, event):
        column_id = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        logger.debug(f"{column_id} {row_id}")

        if column_id == "#1":
            self.tree.delete(row_id)

    def on_tree_rclick(self, event):
        self.tree.selection()
        self.tree.detach()


class InputTreeview(ttk.Treeview):
    def __init__(self, parent, starting_list, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.sorted = SortedSet(starting_list)
        self.detached = set()
        self.created = []
        self.deleted = []  # Deleted Stack

        # Enforce alphabetical order for ease.
        self.column("Delete", anchor="e", width=30)
        for val in self.sorted:
            self.insert("", "end", iid=val, text=val, values=("❌"))

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
        logger.debug(f"Adding {item}")
        if item not in self.sorted:
            self.sorted.add(item)
            index = self.sorted.index(item)
            self.insert("", index, iid=item, text=item, values=("❌"))

    def undo_delete(self, event):
        logger.debug("Undo Recieved")
        if len(self.deleted) > 0:
            item = self.deleted.pop()
            self.add(item)
            logger.debug("Item {item} added back")

    def focus_on_text(self, text):
        for item in self.selection():
            self.selection_remove(item)
        if not text:
            self.focus(self.sorted[0])

        else:
            idx = min(len(self.sorted) - 1, self.sorted.bisect_left(text))
            focus_idx = min(len(self.sorted) - 1, idx + 5)
            match = self.sorted[idx]
            focus_match = self.sorted[focus_idx]

            logger.debug(match)
            self.focus(match)
            self.see(match)
            self.selection_add(match)
            self.see(focus_match)

    def focus_on_next(self):
        next = self.next(self.selection()[0])
        logger.debug(next)

    def focus_on_prev(self):
        prev = self.prev(self.selection()[0])
        logger.debug(prev)
