from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plot_ocv_txt import OCVData, read_ocv_data, summarize_ocv_data


BG = "#f6f7f9"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#667085"
ACCENT = "#7c3aed"


class OCVPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.data: OCVData | None = None
        self.status = tk.StringVar(value="Open an OCV text file to plot.")
        self.summary = tk.StringVar(value="No file loaded.")
        self.show_grid = tk.BooleanVar(value=True)
        self.y_min = tk.StringVar(value="")
        self.y_max = tk.StringVar(value="")

        self._configure_styles()
        self._build_layout()
        self._draw_empty_plot()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 6))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.map("Accent.TButton", foreground=[("active", "#ffffff"), ("!disabled", "#ffffff")])
        style.map("Accent.TButton", background=[("active", "#6d28d9"), ("!disabled", ACCENT)])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=PANEL)
        style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT, font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, style="Panel.TFrame", padding=18)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(5, weight=1)

        ttk.Label(sidebar, text="Open circuit voltage", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(sidebar, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(
            sidebar,
            text="Reads time and potential from CHI OCV files.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Open OCV file", style="Accent.TButton", command=self.open_file).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(buttons, text="Save plot", command=self.save_plot).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Export data", command=self.export_data).grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Clear", command=self.clear_plot).grid(row=3, column=0, sticky="ew", pady=(8, 0))

        options = ttk.Frame(sidebar, style="Panel.TFrame")
        options.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        ttk.Checkbutton(options, text="Grid", variable=self.show_grid, command=self.redraw).grid(
            row=0, column=0, sticky="w"
        )

        y_range = ttk.LabelFrame(sidebar, text="Y axis range", padding=10)
        y_range.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        y_range.columnconfigure((1, 3), weight=1)
        ttk.Label(y_range, text="Min", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        y_min_entry = ttk.Entry(y_range, textvariable=self.y_min, width=10)
        y_min_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        y_min_entry.bind("<KeyRelease>", self.on_y_range_change)
        y_min_entry.bind("<Return>", self.on_y_range_change)
        ttk.Label(y_range, text="Max", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 6))
        y_max_entry = ttk.Entry(y_range, textvariable=self.y_max, width=10)
        y_max_entry.grid(row=0, column=3, sticky="ew")
        y_max_entry.bind("<KeyRelease>", self.on_y_range_change)
        y_max_entry.bind("<Return>", self.on_y_range_change)
        ttk.Label(y_range, text="V", style="Panel.TLabel").grid(row=0, column=4, sticky="w", padx=(8, 0))
        ttk.Button(y_range, text="Auto", command=self.clear_y_range).grid(row=1, column=0, sticky="w", pady=(8, 0))

        info = ttk.Frame(sidebar, style="Panel.TFrame")
        info.grid(row=5, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)
        ttk.Label(info, textvariable=self.summary, style="Panel.TLabel", wraplength=280, justify="left").grid(
            row=0, column=0, sticky="nw"
        )

        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=280).grid(
            row=6, column=0, sticky="ew", pady=(14, 0)
        )

        plot_area = ttk.Frame(self, padding=(14, 14, 14, 10))
        plot_area.grid(row=0, column=1, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(7.5, 5.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar = NavigationToolbar2Tk(self.canvas, plot_area, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ew", pady=(8, 0))

    def open_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Open OCV text file",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            self.data = read_ocv_data(filename)
        except Exception as exc:
            messagebox.showerror("Could not read OCV file", str(exc))
            self.status.set("Failed to load file.")
            return

        self.summary.set(summarize_ocv_data(self.data))
        self.status.set(f"Loaded {self.data.source.name}")
        self.redraw()

    def clear_plot(self) -> None:
        self.data = None
        self.summary.set("No file loaded.")
        self.status.set("Open an OCV text file to plot.")
        self._draw_empty_plot()

    def save_plot(self) -> None:
        if self.data is None:
            messagebox.showinfo("No plot to save", "Open an OCV file first.")
            return

        default_name = f"{self.data.source.stem}_ocv.png"
        filename = filedialog.asksaveasfilename(
            title="Save OCV plot",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg"), ("All files", "*.*")],
        )
        if not filename:
            return

        self.figure.savefig(filename, dpi=300, bbox_inches="tight")
        self.status.set(f"Saved plot to {Path(filename).name}")

    def export_data(self) -> None:
        if self.data is None:
            messagebox.showinfo("No data to export", "Open an OCV file first.")
            return

        default_name = f"{self.data.source.stem}_ocv_data.csv"
        filename = filedialog.asksaveasfilename(
            title="Export OCV data",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        output = Path(filename)
        with output.open("w", encoding="utf-8", newline="") as export:
            writer = csv.writer(export)
            writer.writerow(["Time (sec)", "Potential (V)"])
            writer.writerows(zip(self.data.times_sec, self.data.potentials_v))
        self.status.set(f"Exported data to {output.name}")

    def on_y_range_change(self, _event: tk.Event) -> None:
        self.redraw()

    def clear_y_range(self) -> None:
        self.y_min.set("")
        self.y_max.set("")
        self.redraw()

    def get_y_range(self) -> tuple[float, float] | None:
        raw_min = self.y_min.get().strip()
        raw_max = self.y_max.get().strip()
        if not raw_min and not raw_max:
            return None
        if not raw_min or not raw_max:
            raise ValueError("Enter both Y min and Y max, or leave both blank.")

        y_min = float(raw_min)
        y_max = float(raw_max)
        if y_min >= y_max:
            raise ValueError("Y min must be smaller than Y max.")
        return y_min, y_max

    def redraw(self) -> None:
        if self.data is None:
            self._draw_empty_plot()
            return

        y_range_error = None
        try:
            y_range = self.get_y_range()
        except ValueError as exc:
            y_range = None
            y_range_error = str(exc)

        self.ax.clear()
        self.ax.plot(self.data.times_sec, self.data.potentials_v, color=ACCENT, linewidth=1.5)
        self.ax.set_xlabel("Time / s")
        self.ax.set_ylabel("Potential / V")
        self.ax.set_title(self.data.source.stem)
        if y_range is not None:
            self.ax.set_ylim(*y_range)
        self.ax.grid(self.show_grid.get(), alpha=0.3)
        if y_range_error is not None:
            self.status.set(y_range_error)
        elif self.data is not None:
            self.status.set(f"Loaded {self.data.source.name}")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_empty_plot(self) -> None:
        self.ax.clear()
        self.ax.set_title("Open Circuit Voltage")
        self.ax.set_xlabel("Time / s")
        self.ax.set_ylabel("Potential / V")
        self.ax.grid(True, alpha=0.3)
        self.ax.text(
            0.5,
            0.5,
            "Open an OCV text file",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color=MUTED,
        )
        self.figure.tight_layout()
        self.canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    root.title("Open circuit voltage")
    root.geometry("1100x720")
    app = OCVPlotApp(root, on_return=root.destroy)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
