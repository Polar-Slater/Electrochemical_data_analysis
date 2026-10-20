"""Shared, non-destructive figure formatting and text annotations for Tk plotters."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib import rcParams
from matplotlib.colors import is_color_like
from matplotlib.ticker import AutoLocator, AutoMinorLocator, MultipleLocator


DEFAULT_FONT = "Times New Roman"
rcParams.update({
    "font.family": DEFAULT_FONT,
    "mathtext.fontset": "custom",
    "mathtext.rm": DEFAULT_FONT,
    "mathtext.it": f"{DEFAULT_FONT}:italic",
    "mathtext.bf": f"{DEFAULT_FONT}:bold",
})


def number(value, name, positive=False):
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{name} must be a finite {'positive ' if positive else ''}number.")
    return value


def validate_axis(settings, ax=None):
    """Validate a complete edit before changing any artists."""
    for axis in ("x", "y"):
        if settings.get(axis + "scale") not in ("linear", "log"):
            raise ValueError("Axis scale must be linear or log.")
        lo, hi = settings.get(axis + "min", ""), settings.get(axis + "max", "")
        if bool(str(lo)) != bool(str(hi)):
            raise ValueError(f"Enter both {axis.upper()} limits, or leave both blank for automatic limits.")
        if str(lo):
            lo, hi = number(lo, "Minimum"), number(hi, "Maximum")
            if lo >= hi:
                raise ValueError("Minimum must be smaller than maximum; use Reverse to invert an axis.")
            if settings.get(axis + "scale") == "log" and lo <= 0:
                raise ValueError("Logarithmic limits must be positive.")
        spacing = settings.get(axis + "step", "")
        if str(spacing):
            spacing = number(spacing, "Tick spacing", True)
            limits = (lo, hi) if str(lo) else (getattr(ax, "get_" + axis + "lim")() if ax else None)
            if limits and settings[axis + "scale"] == "linear" and abs(limits[1] - limits[0]) / spacing > 2000:
                raise ValueError("Tick spacing is too small; choose fewer than 2,000 major ticks.")
    number(settings.get("fontsize", 11), "Font size", True)
    number(settings.get("legend_size", 9), "Legend font size", True)
    columns = number(settings.get("legend_columns", 1), "Legend columns", True)
    if not columns.is_integer():
        raise ValueError("Legend columns must be an integer.")
    if settings["tick_direction"] not in ("in", "out", "inout"):
        raise ValueError("Invalid tick direction.")
    if settings["legend_location"] not in ("best", "upper right", "upper left", "lower right",
                                          "lower left", "center", "center left", "center right",
                                          "upper center", "lower center"):
        raise ValueError("Invalid legend position.")
    from matplotlib.mathtext import MathTextParser
    for key in ("title", "xlabel", "ylabel"):
        if "$" in settings.get(key, ""):
            MathTextParser("path").parse(settings[key])


def validate_curve(settings):
    if settings.get("color") and not is_color_like(settings["color"]):
        raise ValueError("Use a color name or hex code such as #0072B2.")
    number(settings.get("linewidth", 1.5), "Line width", True)
    number(settings.get("markersize", 5), "Marker size", True)
    if not 0 <= number(settings.get("alpha", 1), "Opacity") <= 1:
        raise ValueError("Opacity must be between 0 and 1.")
    from matplotlib.lines import Line2D
    Line2D([], [], linestyle=settings["linestyle"], marker=settings["marker"])


def apply_axis(ax, settings, curves):
    if settings:
        for name in ("title", "xlabel", "ylabel"):
            getattr(ax, "set_" + name)(settings[name])
        for dim in ("x", "y"):
            scale = settings[dim + "scale"]
            getattr(ax, "set_" + dim + "scale")(scale)
            lo, hi = settings[dim + "min"], settings[dim + "max"]
            if str(lo):
                limits = (float(lo), float(hi))
            else:
                getattr(ax, "set_autoscale" + dim + "_on")(True)
                ax.autoscale_view()
                limits = sorted(getattr(ax, "get_" + dim + "lim")())
            if settings[dim + "reverse"]:
                limits = limits[::-1]
            getattr(ax, "set_" + dim + "lim")(limits)
            axis = getattr(ax, dim + "axis")
            if scale == "linear":
                if settings[dim + "step"]:
                    axis.set_major_locator(MultipleLocator(float(settings[dim + "step"])))
                else:
                    axis.set_major_locator(AutoLocator())
                if settings["minor"]:
                    axis.set_minor_locator(AutoMinorLocator())
        if not settings["minor"]:
            ax.minorticks_off()
        ax.tick_params(which="both", direction=settings["tick_direction"],
                       labelsize=float(settings["fontsize"]))
        ax.grid(settings["grid"], alpha=0.3)
        for text in [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()]:
            text.set_fontfamily(settings["font"])
            text.set_fontsize(float(settings["fontsize"]))
            text.set_fontweight("bold" if settings["bold"] else "normal")
            text.set_fontstyle("italic" if settings["italic"] else "normal")
    for index, line in enumerate(ax.lines):
        style = curves.get(str(index))
        if style:
            line.set_label(style["label"])
            if style["color"]:
                line.set_color(style["color"])
            line.set_linewidth(float(style["linewidth"]))
            line.set_linestyle(style["linestyle"])
            line.set_marker(style["marker"])
            line.set_markersize(float(style["markersize"]))
            line.set_markerfacecolor("none" if style["hollow"] else line.get_color())
            line.set_alpha(float(style["alpha"]))
    if settings:
        old = ax.get_legend()
        if old:
            old.remove()
        handles, labels = ax.get_legend_handles_labels()
        if settings["legend"] and handles:
            legend = ax.legend(handles, labels, loc=settings["legend_location"],
                               fontsize=float(settings["legend_size"]),
                               ncols=int(float(settings["legend_columns"])),
                               frameon=settings["legend_frame"])
            for text in legend.get_texts():
                text.set_fontfamily(settings["font"])
            legend.set_draggable(True)


def apply_legend(ax, settings):
    """Edit legend entries without changing curve data, labels, or drawing order."""
    if not settings:
        return
    handles, labels = ax.get_legend_handles_labels()
    entries = settings["entries"]
    known = {entry["index"] for entry in entries}
    entries = entries + [dict(index=i, label=label, visible=True)
                         for i, label in enumerate(labels) if i not in known]
    selected = [entry for entry in entries
                if entry["visible"] and 0 <= entry["index"] < len(handles)]
    old = ax.get_legend()
    if old:
        old.remove()
    if not settings["show"] or not selected:
        return
    legend = ax.legend([handles[entry["index"]] for entry in selected],
                       [entry["label"] for entry in selected],
                       title=settings["title"], loc=settings["location"],
                       ncols=int(float(settings["columns"])), frameon=settings["frame"],
                       prop={"family": settings["font"], "size": float(settings["size"])})
    legend.get_title().set_fontfamily(settings["font"])
    legend.get_title().set_fontsize(float(settings["size"]))
    legend.set_draggable(True)


class PlotEditor:
    def __init__(self, owner, toolbar, redraw):
        self.owner, self.figure, self.canvas = owner, owner.figure, owner.canvas
        self.redraw = redraw
        self.contexts = {}
        self.context = ""
        self.artists = []
        self.drag = None
        self.placing = False
        self.window = None
        self.legend_window = None
        self.export = {"width": 17.8, "height": 12.7, "dpi": 300, "transparent": False}
        self.default_export = dict(self.export)
        ttk.Button(toolbar, text="Plot Settings", command=self.open).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Add Text", command=self.add_text).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Edit Legend", command=self.edit_legend).pack(side=tk.LEFT, padx=4)
        for event, handler in (("button_press_event", self.press),
                               ("motion_notify_event", self.motion),
                               ("button_release_event", self.release)):
            self.canvas.mpl_connect(event, handler)

    @property
    def state(self):
        return self.contexts.setdefault(self.context, {"axes": {}, "curves": {}, "texts": []})

    def refresh(self):
        # Called after the host has rebuilt its artists, before drawing.
        self.context = json.dumps([(ax.get_title(), ax.get_xlabel(), ax.get_ylabel())
                                   for ax in self.figure.axes])
        self.apply()
        legend_window = getattr(self, "legend_window", None)
        if legend_window and legend_window.winfo_exists():
            legend_window.destroy()
            self.legend_window = None
        if self.window and self.window.winfo_exists():
            self.window.destroy()
            self.window = None
        self.canvas.draw_idle()

    def apply(self):
        for index, ax in enumerate(self.figure.axes):
            apply_axis(ax, self.state["axes"].get(str(index), {}),
                       self.state["curves"].get(str(index), {}))
            apply_legend(ax, self.state.get("legends", {}).get(str(index), {}))
        self.render_texts()

    def edit_legend(self):
        if self.legend_window and self.legend_window.winfo_exists():
            self.legend_window.lift()
            return
        if not self.context:
            self.refresh()
        win = self.legend_window = tk.Toplevel(self.owner)
        win.title("Edit Legend")
        win.transient(self.owner.winfo_toplevel())
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)
        selector = ttk.Combobox(win, state="readonly", width=55,
                               values=[f"{i+1}: {ax.get_title() or 'Untitled'}"
                                       for i, ax in enumerate(self.figure.axes)])
        selector.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=8)
        selector.current(0)
        tree = ttk.Treeview(win, columns=("label", "visible"), show="headings",
                            selectmode="browse", height=7)
        tree.heading("label", text="Legend entry")
        tree.heading("visible", text="Show")
        tree.column("label", width=330)
        tree.column("visible", width=60, stretch=False)
        tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0))
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10))
        tree.configure(yscrollcommand=scrollbar.set)
        edit = ttk.Frame(win, padding=10)
        edit.grid(row=2, column=0, columnspan=2, sticky="ew")
        label = tk.StringVar(win)
        visible = tk.BooleanVar(win, value=True)
        ttk.Label(edit, text="Entry text").grid(row=0, column=0, sticky="w")
        entry_widget = ttk.Entry(edit, textvariable=label, width=45)
        entry_widget.grid(row=0, column=1, columnspan=3, sticky="ew")
        ttk.Checkbutton(edit, text="Show entry", variable=visible).grid(row=1, column=0)
        fields = {}
        appearance = ttk.Frame(win)
        appearance.grid(row=3, column=0, columnspan=2, sticky="ew")
        for key, caption, default, options in (
            ("title", "Legend title", "", None), ("font", "Font family", DEFAULT_FONT, None),
            ("size", "Font size", 9, None), ("columns", "Columns", 1, None),
            ("location", "Position", "best", ["best", "upper right", "upper left",
             "lower right", "lower left", "center", "center left", "center right",
             "upper center", "lower center"]),
            ("frame", "Frame", True, True), ("show", "Show legend", True, True),
        ):
            self.field(appearance, fields, key, caption, default, options)
        rows = []
        selected = None

        def store_entry():
            if selected is not None:
                rows[selected]["label"] = label.get()
                rows[selected]["visible"] = visible.get()

        def fill_tree():
            tree.delete(*tree.get_children())
            for i, row in enumerate(rows):
                tree.insert("", "end", iid=str(i), values=(row["label"], "Yes" if row["visible"] else "No"))

        def select(event=None):
            nonlocal selected
            store_entry()
            selection = tree.selection()
            selected = int(selection[0]) if selection else None
            if selected is not None:
                label.set(rows[selected]["label"])
                visible.set(rows[selected]["visible"])
            for i, row in enumerate(rows):
                tree.item(str(i), values=(row["label"], "Yes" if row["visible"] else "No"))

        def load_panel(event=None):
            nonlocal rows, selected
            selected = None
            ax = self.figure.axes[selector.current()]
            handles, labels = ax.get_legend_handles_labels()
            saved = self.state.get("legends", {}).get(str(selector.current()), {})
            rows = copy.deepcopy(saved.get("entries", []))
            rows = [row for row in rows if row["index"] < len(handles)]
            known = {row["index"] for row in rows}
            rows.extend(dict(index=i, label=value, visible=True)
                        for i, value in enumerate(labels) if i not in known)
            axis_settings = self.state["axes"].get(str(selector.current()), {})
            legend = ax.get_legend()
            defaults = dict(title=legend.get_title().get_text() if legend else "",
                            font=axis_settings.get("font", DEFAULT_FONT),
                            size=axis_settings.get("legend_size", 9),
                            columns=axis_settings.get("legend_columns", 1),
                            location=axis_settings.get("legend_location", "best"),
                            frame=legend.get_frame_on() if legend else True,
                            show=legend is not None)
            for key, var in fields.items():
                var.set(saved.get(key, defaults[key]))
            label.set("")
            fill_tree()
            if rows:
                tree.selection_set("0")
                select()

        def move(delta):
            nonlocal selected
            store_entry()
            if selected is None or not 0 <= selected + delta < len(rows):
                return
            target = selected + delta
            rows[selected], rows[target] = rows[target], rows[selected]
            selected = None
            fill_tree()
            tree.selection_set(str(target))
            select()

        def apply():
            store_entry()
            try:
                values = {key: var.get() for key, var in fields.items()}
                values["size"] = number(values["size"], "Legend font size", True)
                columns = number(values["columns"], "Legend columns", True)
                if not columns.is_integer():
                    raise ValueError("Legend columns must be an integer.")
                values["columns"] = int(columns)
                from matplotlib.mathtext import MathTextParser
                for text in [values["title"], *[row["label"] for row in rows]]:
                    if "$" in text:
                        MathTextParser("path").parse(text)
                values["entries"] = copy.deepcopy(rows)
                index = str(selector.current())
                self.state.setdefault("legends", {})[index] = values
                axis_settings = self.state["axes"].get(index)
                if axis_settings:
                    for source, target in (("show", "legend"), ("size", "legend_size"),
                                           ("columns", "legend_columns"), ("location", "legend_location"),
                                           ("frame", "legend_frame")):
                        axis_settings[target] = values[source]
                apply_legend(self.figure.axes[int(index)], values)
                self.canvas.draw_idle()
                # Avoid an already-open settings window overwriting these edits.
                if self.window and self.window.winfo_exists():
                    self.window.destroy()
                    self.window = None
                fill_tree()
                if selected is not None:
                    tree.selection_set(str(selected))
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Invalid legend", str(exc), parent=win)

        ttk.Button(edit, text="Move up", command=lambda: move(-1)).grid(row=1, column=1)
        ttk.Button(edit, text="Move down", command=lambda: move(1)).grid(row=1, column=2)
        tree.bind("<<TreeviewSelect>>", select)
        tree.bind("<Double-1>", lambda event: entry_widget.focus_set())
        selector.bind("<<ComboboxSelected>>", load_panel)
        buttons = ttk.Frame(win, padding=10)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Apply / Preview", command=apply).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=win.destroy).pack(side=tk.RIGHT)
        ttk.Label(win, text="Apply before switching panels. Hidden entries keep their curves visible.",
                  padding=8).grid(row=5, column=0, columnspan=2)
        load_panel()

    def render_texts(self):
        for artist, _ in self.artists:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass
        self.artists = []
        for spec in self.state["texts"]:
            if spec["axis"] >= len(self.figure.axes):
                continue
            ax = self.figure.axes[spec["axis"]]
            artist = ax.text(spec["x"], spec["y"], spec["text"],
                             transform=ax.transAxes if spec["coordinates"] == "Plot area" else ax.transData,
                             fontsize=spec["size"], color=spec["color"], family=spec["font"],
                             weight="bold" if spec["bold"] else "normal",
                             style="italic" if spec["italic"] else "normal",
                             rotation=spec["rotation"], picker=True, zorder=20)
            self.artists.append((artist, spec))

    def add_text(self):
        self.placing = True
        messagebox.showinfo("Add text", "Click inside the plot to place text.\n"
                            "Drag text to move it; double-click to edit or delete it.",
                            parent=self.owner)

    def press(self, event):
        if event.button != 1 or not event.inaxes:
            return
        if getattr(self.canvas.toolbar, "mode", ""):
            return
        for artist, spec in reversed(self.artists):
            if artist.contains(event)[0]:
                if event.dblclick:
                    self.edit_text(spec)
                else:
                    position = artist.get_transform().inverted().transform((event.x, event.y))
                    self.drag = (artist, spec, position[0] - spec["x"], position[1] - spec["y"])
                return
        if self.placing:
            self.placing = False
            xy = event.inaxes.transAxes.inverted().transform((event.x, event.y))
            self.edit_text({"axis": self.figure.axes.index(event.inaxes), "x": float(xy[0]),
                            "y": float(xy[1]), "text": "", "size": 12, "color": "black",
                            "font": DEFAULT_FONT, "bold": False, "italic": False,
                            "rotation": 0, "coordinates": "Plot area"}, new=True)

    def motion(self, event):
        if self.drag and event.x is not None and event.y is not None:
            artist, spec, dx, dy = self.drag
            xy = artist.get_transform().inverted().transform((event.x, event.y))
            spec["x"], spec["y"] = float(xy[0] - dx), float(xy[1] - dy)
            artist.set_position((spec["x"], spec["y"]))
            self.canvas.draw_idle()

    def release(self, event):
        self.drag = None

    def edit_text(self, spec, new=False):
        win = tk.Toplevel(self.owner)
        win.title("Text annotation")
        win.transient(self.owner.winfo_toplevel())
        fields = {}
        for key, label, options in (
            ("text", "Text (Greek supported; equations: $R_{ct}$)", None),
            ("font", "Font family", None), ("size", "Font size", None),
            ("color", "Color name / hex", None), ("rotation", "Rotation (degrees)", None),
            ("coordinates", "Anchor", ["Plot area", "Data"]),
            ("bold", "Bold", True), ("italic", "Italic", True),
        ):
            self.field(win, fields, key, label, spec[key], options)

        def save():
            try:
                values = {key: var.get() for key, var in fields.items()}
                if not values["text"].strip():
                    raise ValueError("Enter some text.")
                if not is_color_like(values["color"]):
                    raise ValueError("Invalid text color.")
                values["size"] = number(values["size"], "Font size", True)
                values["rotation"] = number(values["rotation"], "Rotation")
                # Validate math syntax before storing it.
                from matplotlib.mathtext import MathTextParser
                if "$" in values["text"]:
                    MathTextParser("path").parse(values["text"])
                if values["coordinates"] != spec["coordinates"]:
                    ax = self.figure.axes[spec["axis"]]
                    old = ax.transAxes if spec["coordinates"] == "Plot area" else ax.transData
                    target = ax.transAxes if values["coordinates"] == "Plot area" else ax.transData
                    xy = target.inverted().transform(old.transform((spec["x"], spec["y"])))
                    spec["x"], spec["y"] = float(xy[0]), float(xy[1])
                spec.update(values)
                if new:
                    self.state["texts"].append(spec)
                self.render_texts()
                self.canvas.draw_idle()
                win.destroy()
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Invalid text", str(exc), parent=win)

        buttons = ttk.Frame(win)
        buttons.grid(columnspan=2, sticky="ew", padx=10, pady=10)
        ttk.Button(buttons, text="Save", command=save).pack(side=tk.LEFT)
        if not new:
            def delete():
                self.state["texts"].remove(spec)
                self.render_texts()
                self.canvas.draw_idle()
                win.destroy()
            ttk.Button(buttons, text="Delete", command=delete).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side=tk.LEFT)

    @staticmethod
    def field(parent, variables, key, label, value, options=None):
        row = len(variables)
        variable = tk.BooleanVar(parent, value=bool(value)) if options is True else tk.StringVar(parent, value=value)
        variables[key] = variable
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=3)
        if options is True:
            widget = ttk.Checkbutton(parent, variable=variable)
        elif options:
            widget = ttk.Combobox(parent, textvariable=variable, values=options, state="readonly", width=25)
        else:
            widget = ttk.Entry(parent, textvariable=variable, width=30)
        widget.grid(row=row, column=1, sticky="ew", padx=10, pady=3)

    def open(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
        if not self.context:
            self.refresh()
        win = self.window = tk.Toplevel(self.owner)
        win.title("Plot Settings")
        win.transient(self.owner.winfo_toplevel())
        top = ttk.Frame(win, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Panel").pack(side=tk.LEFT)
        selector = ttk.Combobox(top, state="readonly", width=48,
                               values=[f"{i + 1}: {ax.get_title() or 'Untitled'}"
                                       for i, ax in enumerate(self.figure.axes)])
        selector.pack(side=tk.LEFT, padx=8)
        selector.current(0)
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8)
        tabs = {}
        for name in ("Axes", "Labels & Legend", "Curves", "Export"):
            tabs[name] = ttk.Frame(notebook, padding=6)
            notebook.add(tabs[name], text=name)
        axis_vars, label_vars, curve_vars, export_vars = {}, {}, {}, {}
        curve_selector = None

        def load_panel(event=None):
            nonlocal curve_selector
            for name in ("Axes", "Labels & Legend", "Curves"):
                for child in tabs[name].winfo_children():
                    child.destroy()
            axis_vars.clear()
            label_vars.clear()
            curve_vars.clear()
            index = selector.current()
            ax = self.figure.axes[index]
            saved = self.state["axes"].get(str(index), {})
            for dim in ("x", "y"):
                for suffix, label, value, options in (
                    ("scale", "scale", getattr(ax, "get_" + dim + "scale")(), ["linear", "log"]),
                    ("min", "minimum (blank = auto)", "", None),
                    ("max", "maximum (blank = auto)", "", None),
                    ("step", "major tick spacing (linear)", "", None),
                    ("reverse", "reverse", getattr(ax, dim + "axis_inverted")(), True),
                ):
                    key = dim + suffix
                    self.field(tabs["Axes"], axis_vars, key, f"{dim.upper()} {label}", saved.get(key, value), options)
            for key, label, value, options in (
                ("minor", "Minor ticks", False, True),
                ("tick_direction", "Tick direction", "in", ["in", "out", "inout"]),
                ("grid", "Grid", any(line.get_visible() for line in ax.get_xgridlines()), True),
            ):
                self.field(tabs["Axes"], axis_vars, key, label, saved.get(key, value), options)
            for key, label, value, options in (
                ("title", "Title", ax.get_title(), None),
                ("xlabel", "X label", ax.get_xlabel(), None),
                ("ylabel", "Y label", ax.get_ylabel(), None),
                ("font", "Font family", DEFAULT_FONT, None),
                ("fontsize", "Font size", 11, None),
                ("bold", "Bold", False, True), ("italic", "Italic", False, True),
                ("legend", "Show legend", ax.get_legend() is not None, True),
                ("legend_location", "Legend position", "best",
                 ["best", "upper right", "upper left", "lower right", "lower left", "center", "center left", "center right", "upper center", "lower center"]),
                ("legend_size", "Legend font size", 9, None),
                ("legend_columns", "Legend columns", 1, None),
                ("legend_frame", "Legend frame", True, True),
            ):
                self.field(tabs["Labels & Legend"], label_vars, key, label, saved.get(key, value), options)
            panel = tabs["Curves"]
            curve_selector = ttk.Combobox(panel, state="readonly", width=40,
                                         values=[f"{i + 1}: {line.get_label()}" for i, line in enumerate(ax.lines)])
            curve_selector.pack(fill=tk.X)
            body = ttk.Frame(panel)
            body.pack(fill=tk.BOTH, expand=True)

            def load_curve(event=None):
                for child in body.winfo_children():
                    child.destroy()
                curve_vars.clear()
                if curve_selector.current() < 0:
                    return
                line = ax.lines[curve_selector.current()]
                defaults = {"label": line.get_label(), "color": line.get_color(),
                            "linewidth": line.get_linewidth(), "linestyle": line.get_linestyle(),
                            "marker": line.get_marker(), "markersize": line.get_markersize(),
                            "alpha": line.get_alpha() if line.get_alpha() is not None else 1,
                            "hollow": str(line.get_markerfacecolor()).lower() == "none"}
                # Matplotlib may use an RGB tuple for a color.
                from matplotlib.colors import to_hex
                defaults["color"] = to_hex(defaults["color"])
                for key, label, options in (
                    ("label", "Legend text", None), ("color", "Color name / hex", None),
                    ("linewidth", "Line width", None),
                    ("linestyle", "Line style", ["-", "--", "-.", ":", "None"]),
                    ("marker", "Marker", ["None", "o", "s", "^", "v", "D", "+", "x", ".", "*"]),
                    ("markersize", "Marker size", None), ("alpha", "Opacity (0–1)", None),
                    ("hollow", "Hollow markers", True),
                ):
                    self.field(body, curve_vars, key, label, defaults[key], options)
                self.field(body, curve_vars, "all", "Apply style to all curves (keep names)", False, True)
            curve_selector.bind("<<ComboboxSelected>>", load_curve)
            if ax.lines:
                curve_selector.current(0)
                load_curve()
        load_panel()
        selector.bind("<<ComboboxSelected>>", load_panel)
        for key, label, options in (
            ("width", "Export width (cm)", None), ("height", "Export height (cm)", None),
            ("dpi", "Export DPI", None), ("transparent", "Transparent background", True),
        ):
            self.field(tabs["Export"], export_vars, key, label, self.export[key], options)
        ttk.Label(tabs["Export"], text="Exact export size; preview follows the window size.\n"
                  "Export includes text annotations.").grid(row=5, columnspan=2, padx=10, pady=12)

        def apply():
            try:
                settings = {key: var.get() for key, var in {**axis_vars, **label_vars}.items()}
                validate_axis(settings, self.figure.axes[selector.current()])
                export = {key: var.get() for key, var in export_vars.items()}
                for key in ("width", "height", "dpi"):
                    export[key] = number(export[key], key, True)
                if export["width"] * export["dpi"] / 2.54 > 20000 or export["height"] * export["dpi"] / 2.54 > 20000:
                    raise ValueError("Reduce size or DPI to keep each image dimension below 20,000 pixels.")
                curve = {key: var.get() for key, var in curve_vars.items()}
                if curve:
                    validate_curve(curve)
                index = str(selector.current())
                self.state["axes"][index] = settings
                legend_settings = self.state.get("legends", {}).get(index)
                if legend_settings:
                    for source, target in (("legend", "show"), ("legend_size", "size"),
                                           ("legend_columns", "columns"), ("legend_location", "location"),
                                           ("legend_frame", "frame")):
                        legend_settings[target] = settings[source]
                    legend_settings["font"] = settings["font"]
                self.export = export
                if curve:
                    all_curves = curve.pop("all")
                    target = self.state["curves"].setdefault(index, {})
                    indices = range(len(self.figure.axes[int(index)].lines)) if all_curves else [curve_selector.current()]
                    for i in indices:
                        style = dict(curve)
                        if all_curves:
                            style["label"] = self.figure.axes[int(index)].lines[i].get_label()
                        target[str(i)] = style
                self.apply()
                self.figure.tight_layout()
                self.canvas.draw_idle()
                return True
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Invalid plot setting", str(exc), parent=win)
                return False

        buttons = ttk.Frame(win, padding=10)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Apply / Preview", command=apply).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Reset view", command=self.reset).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Save preset", command=lambda: self.save_preset() if apply() else None).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Load preset", command=self.load_preset).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Export figure", command=lambda: self.export_dialog() if apply() else None).pack(side=tk.LEFT)
        ttk.Label(win, text="Apply before switching panels or curves. Add Text is on the plot toolbar.",
                  padding=8).pack()

    def reset(self):
        self.contexts.pop(self.context, None)
        self.export = dict(self.default_export)
        self.redraw()

    def save_preset(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension=".json",
                                          filetypes=[("Plot style", "*.json")])
        if path:
            # Text positions and data-specific limits/labels are intentionally not style presets.
            axes = copy.deepcopy(self.state["axes"])
            for settings in axes.values():
                for key in ("title", "xlabel", "ylabel", "xmin", "xmax", "ymin", "ymax"):
                    settings.pop(key, None)
            curves = copy.deepcopy(self.state["curves"])
            for group in curves.values():
                for settings in group.values():
                    settings.pop("label", None)
            try:
                Path(path).write_text(json.dumps({"version": 1, "axes": axes, "curves": curves,
                                                  "export": self.export}, indent=2), encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("Could not save preset", str(exc), parent=self.window)

    def load_preset(self):
        path = filedialog.askopenfilename(parent=self.window, filetypes=[("Plot style", "*.json")])
        if not path:
            return
        previous = copy.deepcopy(self.state)
        previous_export = dict(self.export)
        try:
            preset = json.loads(Path(path).read_text(encoding="utf-8"))
            if preset["version"] != 1:
                raise ValueError("Unsupported preset version.")
            for index, settings in preset["axes"].items():
                if int(index) >= len(self.figure.axes) or int(index) < 0:
                    continue
                ax = self.figure.axes[int(index)]
                settings.update(title=ax.get_title(), xlabel=ax.get_xlabel(), ylabel=ax.get_ylabel(),
                                xmin="", xmax="", ymin="", ymax="")
                validate_axis(settings, ax)
                self.state["axes"][index] = settings
            for index, group in preset["curves"].items():
                if not 0 <= int(index) < len(self.figure.axes):
                    continue
                lines = self.figure.axes[int(index)].lines
                for i, settings in group.items():
                    if not 0 <= int(i) < len(lines):
                        continue
                    settings["label"] = lines[int(i)].get_label()
                    validate_curve(settings)
                    self.state["curves"].setdefault(index, {})[i] = settings
            for key in ("width", "height", "dpi"):
                number(preset["export"][key], key, True)
            self.export = preset["export"]
            if any(self.export[dim] * self.export["dpi"] / 2.54 > 20000 for dim in ("width", "height")):
                raise ValueError("Preset image dimensions exceed 20,000 pixels.")
            self.apply()
            self.canvas.draw_idle()
            self.window.destroy()
            self.window = None
            self.open()
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.contexts[self.context] = previous
            self.export = previous_export
            # Rebuild native artists so a partially applied invalid preset cannot linger.
            self.redraw()
            messagebox.showerror("Could not load preset", str(exc), parent=self.owner)

    def save_figure(self, path, figure=None, source_axis=None):
        figure = figure or self.figure
        if source_axis is not None:
            apply_axis(figure.axes[0], self.state["axes"].get(str(source_axis), {}),
                       self.state["curves"].get(str(source_axis), {}))
            apply_legend(figure.axes[0], self.state.get("legends", {}).get(str(source_axis), {}))
            for spec in self.state["texts"]:
                if spec["axis"] == source_axis:
                    ax = figure.axes[0]
                    ax.text(spec["x"], spec["y"], spec["text"],
                            transform=ax.transAxes if spec["coordinates"] == "Plot area" else ax.transData,
                            fontsize=spec["size"], color=spec["color"], family=spec["font"],
                            weight="bold" if spec["bold"] else "normal",
                            style="italic" if spec["italic"] else "normal", rotation=spec["rotation"])
        size = figure.get_size_inches().copy()
        positions = [ax.get_position().frozen() for ax in figure.axes]
        try:
            figure.set_size_inches(self.export["width"] / 2.54, self.export["height"] / 2.54, forward=False)
            figure.tight_layout()
            figure.savefig(path, dpi=self.export["dpi"], transparent=self.export["transparent"])
        finally:
            figure.set_size_inches(size, forward=False)
            for ax, position in zip(figure.axes, positions):
                ax.set_position(position)
            self.canvas.draw_idle()

    def export_dialog(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension=".png",
                                          filetypes=[("PNG", "*.png"), ("TIFF", "*.tiff"),
                                                     ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if path:
            try:
                self.save_figure(path)
            except (OSError, ValueError, RuntimeError) as exc:
                messagebox.showerror("Export failed", str(exc), parent=self.window)
