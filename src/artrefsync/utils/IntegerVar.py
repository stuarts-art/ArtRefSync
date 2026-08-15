import tkinter as tk


class IntegerVar(tk.IntVar):
    """Extension of the Intvar class which ensures that the output is an integer.
    This is useful in conjunction with the ttk scale widget, which does not enforce full ints on assignment.
    """

    def __init__(self, value: int = 0, on_update: callable | None = None):
        """
        Args:
            value (int, optional): _description_. Defaults to 0.
            on_update (callable, optional): _description_. Defaults to None.
        """
        self.on_update = on_update
        super().__init__(value=value)
        self.dummy_var = tk.IntVar(value=value)
        self.prev = None
        self.dummy_var.trace_add("write", self.on_dummy_write)

    def on_dummy_write(self, *args):
        int_val = int(self.dummy_var.get())
        if int_val != self.prev:
            self.prev = int_val
            super().set(int_val)
            if self.on_update:
                self.on_update(int_val)

    def set(self, value):
        self.dummy_var.set(value)

    def __eq__(self, other):
        return self.get() == other

    def __add__(self, val):
        return self.get() + val

    def __mod__(self, val):
        return self.get() % val

    def __iadd__(self, val):
        self.set(self + val)
        return self

    def __imod__(self, val):
        self.set(self % val)
        return self
