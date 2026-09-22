"""Scrollable control panel with wheel bindings confined to its own widgets."""

import tkinter as tk
from tkinter import ttk


class ScrollableSidebar(ttk.Frame):
    def __init__(self, master, *, padding=18):
        super().__init__(master, style="Panel.TFrame")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, background="#ffffff", highlightthickness=0,
                                borderwidth=0, width=420, height=1, yscrollincrement=24)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content = ttk.Frame(self.canvas, style="Panel.TFrame", padding=padding)
        self._window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._content_changed)
        self.canvas.bind("<Configure>", self._viewport_changed)

    def _content_changed(self, _event=None):
        self.canvas.configure(width=self.content.winfo_reqwidth(),
                              scrollregion=self.canvas.bbox("all"))

    def _viewport_changed(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def enable_mousewheel(self):
        """Call once after building controls; bindings die with the panel."""
        def bind_tree(widget):
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                widget.bind(sequence, self._scroll)
            for child in widget.winfo_children():
                bind_tree(child)
        bind_tree(self)

    def _scroll(self, event):
        if self.canvas.yview() == (0.0, 1.0):
            return "break"
        if event.num == 4:
            units = -3
        elif event.num == 5:
            units = 3
        elif event.delta:
            units = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
        else:
            return "break"
        self.canvas.yview_scroll(units, "units")
        return "break"
