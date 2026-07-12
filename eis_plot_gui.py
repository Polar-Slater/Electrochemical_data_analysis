from __future__ import annotations

import warnings
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plot_eis_txt import EISData, read_eis_data, summarize_eis_data, write_processed_eis_data


BG = "#f6f7f9"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#667085"
ACCENT = "#166534"


class EISPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.data: EISData | None = None
        self.status = tk.StringVar(value="Open an EIS text file to plot.")
        self.summary = tk.StringVar(value="No file loaded.")
        self.show_grid = tk.BooleanVar(value=True)
        self.equal_aspect = tk.BooleanVar(value=True)
        self.show_points = tk.BooleanVar(value=True)
        self.connect_points = tk.BooleanVar(value=True)
        self.plot_type = tk.StringVar(value="Nyquist")
        self.frequency_scale = tk.StringVar(value="log")
        self.bode_y_axis = tk.StringVar(value="Z")
        self.working_area = tk.StringVar(value="")

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
        style.map("Accent.TButton", background=[("active", "#14532d"), ("!disabled", ACCENT)])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TRadiobutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
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

        ttk.Label(sidebar, text="EIS Nyquist Plotter", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(sidebar, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(
            sidebar,
            text="Reads rows after the CHI EIS header.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Open EIS file", style="Accent.TButton", command=self.open_file).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(buttons, text="Save plot", command=self.save_plot).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Save data", command=self.save_data).grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Clear", command=self.clear_plot).grid(row=3, column=0, sticky="ew", pady=(8, 0))

        options = ttk.Frame(sidebar, style="Panel.TFrame")
        options.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(options, text="Plot type", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 2))
        ttk.Radiobutton(options, text="Nyquist", variable=self.plot_type, value="Nyquist", command=self.redraw).grid(
            row=1, column=0, sticky="w", pady=2
        )
        ttk.Radiobutton(options, text="Bode", variable=self.plot_type, value="Bode", command=self.redraw).grid(
            row=1, column=1, sticky="w", pady=2, padx=(14, 0)
        )
        ttk.Label(options, text="Frequency axis", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 2))
        ttk.Radiobutton(options, text="Normal", variable=self.frequency_scale, value="normal", command=self.redraw).grid(
            row=3, column=0, sticky="w", pady=2
        )
        ttk.Radiobutton(options, text="Log", variable=self.frequency_scale, value="log", command=self.redraw).grid(
            row=3, column=1, sticky="w", pady=2, padx=(14, 0)
        )
        ttk.Label(options, text="Bode y-axis", style="Panel.TLabel").grid(row=4, column=0, sticky="w", pady=(10, 2))
        ttk.Radiobutton(options, text="Z", variable=self.bode_y_axis, value="Z", command=self.redraw).grid(
            row=5, column=0, sticky="w", pady=2
        )
        ttk.Radiobutton(options, text="-Z''", variable=self.bode_y_axis, value="-Z''", command=self.redraw).grid(
            row=5, column=1, sticky="w", pady=2, padx=(14, 0)
        )
        ttk.Checkbutton(options, text="Grid", variable=self.show_grid, command=self.redraw).grid(
            row=6, column=0, sticky="w", pady=(10, 2)
        )
        ttk.Checkbutton(options, text="Equal axes", variable=self.equal_aspect, command=self.redraw).grid(
            row=7, column=0, sticky="w", pady=2
        )
        ttk.Checkbutton(options, text="Show points", variable=self.show_points, command=self.redraw).grid(
            row=8, column=0, sticky="w", pady=2
        )
        ttk.Checkbutton(options, text="Connect points", variable=self.connect_points, command=self.redraw).grid(
            row=9, column=0, sticky="w", pady=2
        )
        options.columnconfigure(1, weight=1)

        area_frame = ttk.LabelFrame(sidebar, text="Working area: ", padding=10)
        area_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        area_frame.columnconfigure(0, weight=1)
        self.area_entry = ttk.Entry(area_frame, textvariable=self.working_area, width=16)
        self.area_entry.grid(row=0, column=0, sticky="ew")
        self.area_entry.bind("<KeyRelease>", self.on_working_area_change)
        ttk.Label(area_frame, text="cm²", style="Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(area_frame, text="Clear", command=self.clear_working_area).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

        info = ttk.Frame(sidebar, style="Panel.TFrame")
        info.grid(row=5, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)
        ttk.Label(info, textvariable=self.summary, style="Panel.TLabel", wraplength=260, justify="left").grid(
            row=0, column=0, sticky="nw"
        )

        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=260).grid(
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
            title="Open EIS text file",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            self.data = read_eis_data(filename)
        except Exception as exc:
            messagebox.showerror("Could not read EIS file", str(exc))
            self.status.set("Failed to load file.")
            return

        stats = summarize_eis_data(self.data)
        self.summary.set(
            "\n".join(
                [
                    f"File: {self.data.source.name}",
                    f"Points: {stats['points']}",
                    f"Frequency: {stats['frequency_max_hz']:.3g} to {stats['frequency_min_hz']:.3g} Hz",
                    f"Z': {stats['z_real_min_ohm']:.4g} to {stats['z_real_max_ohm']:.4g} ohm",
                    f"-Z'': {stats['minus_z_imag_min_ohm']:.4g} to {stats['minus_z_imag_max_ohm']:.4g} ohm",
                ]
            )
        )
        self.status.set(f"Loaded {self.data.source.name}")
        self.redraw()

    def clear_plot(self) -> None:
        self.data = None
        self.summary.set("No file loaded.")
        self.status.set("Open an EIS text file to plot.")
        self._draw_empty_plot()

    def save_plot(self) -> None:
        if self.data is None:
            messagebox.showinfo("No plot to save", "Open an EIS file first.")
            return

        plot_suffix = "bode" if self.plot_type.get() == "Bode" else "nyquist"
        default_name = f"{self.data.source.stem}_{plot_suffix}.png"
        filename = filedialog.asksaveasfilename(
            title="Save EIS plot",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg"), ("All files", "*.*")],
        )
        if not filename:
            return

        self.figure.savefig(filename, dpi=300, bbox_inches="tight")
        self.status.set(f"Saved plot to {Path(filename).name}")

    def save_data(self) -> None:
        if self.data is None:
            messagebox.showinfo("No data to save", "Open an EIS file first.")
            return

        default_name = f"{self.data.source.stem}_processed.csv"
        filename = filedialog.asksaveasfilename(
            title="Save processed EIS data",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV file", "*.csv"), ("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            working_area = self.get_working_area()
        except ValueError:
            messagebox.showwarning("Invalid working area", "Working area must be a positive number.")
            working_area = None

        write_processed_eis_data(self.data, filename, working_area=working_area)
        self.status.set(f"Saved data to {Path(filename).name}")

    def on_working_area_change(self, _event: tk.Event) -> None:
        self.redraw()

    def clear_working_area(self) -> None:
        self.working_area.set("")
        self.redraw()

    def get_working_area(self) -> float | None:
        raw_value = self.working_area.get().strip()
        if not raw_value:
            return None
        area = float(raw_value)
        if area <= 0:
            raise ValueError
        return area

    def redraw(self) -> None:
        if self.data is None:
            self._draw_empty_plot()
            return
        if self.plot_type.get() == "Bode":
            self._draw_bode(self.data)
        else:
            self._draw_nyquist(self.data)

    def _draw_empty_plot(self) -> None:
        self._reset_figure()
        self.ax = self.figure.add_subplot(111)
        self.ax.clear()
        if self.plot_type.get() == "Bode":
            self.ax.set_title("Bode Plot")
            self.ax.set_xlabel("Frequency (Hz)")
            self.ax.set_ylabel(self._bode_y_label())
        else:
            self.ax.set_title("Nyquist Plot")
            self.ax.set_xlabel(f"Z' ({self._impedance_unit()})")
            self.ax.set_ylabel(f"-Z'' ({self._impedance_unit()})")
        self.ax.grid(True, alpha=0.3)
        self.ax.text(
            0.5,
            0.5,
            "Open an EIS text file",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color=MUTED,
        )
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_nyquist(self, data: EISData) -> None:
        self._reset_figure()
        self.ax = self.figure.add_subplot(111)
        self.ax.clear()

        marker = "o" if self.show_points.get() else None
        linestyle = "-" if self.connect_points.get() else "None"
        impedance_scale = self._impedance_scale()
        self.ax.plot(
            [value * impedance_scale for value in data.z_real_ohm],
            [value * impedance_scale for value in data.minus_z_imag_ohm],
            color=ACCENT,
            marker=marker,
            markersize=4,
            linewidth=1.5,
            linestyle=linestyle,
        )

        self.ax.set_title(f"Nyquist Plot - {data.source.stem}")
        self.ax.set_xlabel(f"Z' ({self._impedance_unit()})")
        self.ax.set_ylabel(f"-Z'' ({self._impedance_unit()})")
        self.ax.grid(self.show_grid.get(), alpha=0.3)

        if self.equal_aspect.get():
            self.ax.set_aspect("equal", adjustable="datalim")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_bode(self, data: EISData) -> None:
        self._reset_figure()
        ax_z = self.figure.add_subplot(211)
        ax_phase = self.figure.add_subplot(212, sharex=ax_z)
        self.ax = ax_z

        marker = "o" if self.show_points.get() else None
        linestyle = "-" if self.connect_points.get() else "None"
        frequencies, bode_y_values, phase_values = self._bode_series(data)

        if self.frequency_scale.get() == "log":
            positive_rows = [
                (frequency, y_value, phase)
                for frequency, y_value, phase in zip(frequencies, bode_y_values, phase_values)
                if frequency > 0
            ]
            if not positive_rows:
                self._draw_empty_plot()
                self.status.set("Bode log scale needs positive frequency values.")
                return
            frequencies = [row[0] for row in positive_rows]
            bode_y_values = [row[1] for row in positive_rows]
            phase_values = [row[2] for row in positive_rows]
            ax_z.set_xscale("log")
            ax_phase.set_xscale("log")

        ax_z.plot(
            frequencies,
            bode_y_values,
            color=ACCENT,
            marker=marker,
            markersize=4,
            linewidth=1.5,
            linestyle=linestyle,
        )
        ax_phase.plot(
            frequencies,
            phase_values,
            color="#1f6feb",
            marker=marker,
            markersize=4,
            linewidth=1.5,
            linestyle=linestyle,
        )

        ax_z.set_title(f"Bode Plot - {data.source.stem}")
        ax_z.set_ylabel(self._bode_y_label())
        ax_phase.set_xlabel("Frequency (Hz)")
        ax_phase.set_ylabel("Phase (deg)")
        ax_z.grid(self.show_grid.get(), alpha=0.3)
        ax_phase.grid(self.show_grid.get(), alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _bode_series(self, data: EISData) -> tuple[list[float], list[float], list[float]]:
        y_values = data.minus_z_imag_ohm if self.bode_y_axis.get() == "-Z''" else data.z_abs_ohm
        impedance_scale = self._impedance_scale()
        y_values = [value * impedance_scale for value in y_values]
        rows = sorted(zip(data.frequency_hz, y_values, data.phase_deg), key=lambda row: row[0])
        if not rows:
            return [], [], []
        frequencies, bode_y_values, phase_values = zip(*rows)
        return list(frequencies), list(bode_y_values), list(phase_values)

    def _bode_y_label(self) -> str:
        if self.bode_y_axis.get() == "-Z''":
            return f"-Z'' ({self._impedance_unit()})"
        return f"Z ({self._impedance_unit()})"

    def _impedance_scale(self) -> float:
        try:
            working_area = self.get_working_area()
        except ValueError:
            self.status.set("Working area must be a positive number.")
            return 1.0
        if working_area is None:
            return 1.0
        return working_area

    def _impedance_unit(self) -> str:
        try:
            working_area = self.get_working_area()
        except ValueError:
            return "ohm"
        if working_area is None:
            return "ohm"
        return "ohm⋅cm^2"

    def _reset_figure(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Attempt to set non-positive xlim on a log-scaled axis will be ignored.",
                category=UserWarning,
            )
            self.figure.clear()


if __name__ == "__main__":
    app = EISPlotApp()
    app.mainloop()


