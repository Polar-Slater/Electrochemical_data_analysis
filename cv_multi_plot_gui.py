from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from cv_data import CVData, read_cv_data, summarize_data


BG = "#f5f7f8"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#5f6f7f"
ACCENT = "#1d6f68"
ACCENT_DARK = "#16524d"


class CVMultiPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.files: list[Path] = []
        self.data_sets: list[CVData] = []
        self.status = tk.StringVar(value="Load CV text files to plot a selected cycle.")
        self.show_grid = tk.BooleanVar(value=True)
        self.show_legend = tk.BooleanVar(value=True)
        self.current_units = tk.StringVar(value="mA")
        self.line_width = tk.DoubleVar(value=1.4)
        self.selected_cycle = tk.IntVar(value=1)
        self.working_area = tk.StringVar(value="")

        self._configure_styles()
        self._build_layout()

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
        style.map("Accent.TButton", background=[("active", ACCENT_DARK), ("!disabled", ACCENT)])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TRadiobutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=PANEL)
        style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("Horizontal.TScale", background=PANEL)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, style="Panel.TFrame", padding=18)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(3, weight=2)
        sidebar.rowconfigure(7, weight=3)

        ttk.Label(sidebar, text="ECSA identifier", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(sidebar, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(
            sidebar,
            text="Plots the selected complete CV cycle from each file.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Open files", style="Accent.TButton", command=self.open_files).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(buttons, text="Open folder", command=self.open_folder).grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )
        ttk.Button(buttons, text="Clear", command=self.clear_files).grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Save plot", command=self.save_plot).grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Export data", command=self.export_data).grid(row=4, column=0, sticky="ew", pady=(8, 0))

        list_frame = ttk.Frame(sidebar, style="Panel.TFrame")
        list_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(
            list_frame,
            width=38,
            height=10,
            bg="#ffffff",
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=1,
            highlightbackground="#d5dde2",
            relief="flat",
            font=("Segoe UI", 9),
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scrollbar.set)

        options = ttk.Frame(sidebar, style="Panel.TFrame")
        options.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(options, text="Cycle", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.cycle_spinbox = tk.Spinbox(
            options,
            from_=1,
            to=1,
            textvariable=self.selected_cycle,
            command=self.refresh_display,
            width=8,
            bg="#ffffff",
            fg=TEXT,
            highlightthickness=1,
            highlightbackground="#d5dde2",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.cycle_spinbox.grid(row=1, column=0, sticky="w", pady=(2, 8))
        self.cycle_spinbox.bind("<Return>", lambda _event: self.refresh_display())
        self.cycle_spinbox.bind("<FocusOut>", lambda _event: self.refresh_display())
        ttk.Button(options, text="Last", command=self.use_last_cycle).grid(row=1, column=1, sticky="w", pady=(2, 8), padx=(14, 0))

        ttk.Label(options, text="Current units", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Radiobutton(options, text="A", variable=self.current_units, value="A", command=self.refresh_display).grid(
            row=3, column=0, sticky="w", pady=(2, 0)
        )
        ttk.Radiobutton(options, text="mA", variable=self.current_units, value="mA", command=self.refresh_display).grid(
            row=3, column=1, sticky="w", pady=(2, 0), padx=(14, 0)
        )
        ttk.Checkbutton(options, text="Grid", variable=self.show_grid, command=self.plot_loaded_data).grid(
            row=4, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(options, text="Legend", variable=self.show_legend, command=self.plot_loaded_data).grid(
            row=4, column=1, sticky="w", pady=(8, 0), padx=(14, 0)
        )
        ttk.Label(options, text="Line width", style="Panel.TLabel").grid(row=5, column=0, sticky="w", pady=(10, 0))
        ttk.Scale(
            options,
            from_=0.7,
            to=3.0,
            variable=self.line_width,
            command=lambda _value: self.plot_loaded_data(),
        ).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        options.columnconfigure(1, weight=1)

        area_frame = ttk.LabelFrame(sidebar, text="Working area: ", padding=10)
        area_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        area_frame.columnconfigure(0, weight=1)
        self.area_entry = ttk.Entry(area_frame, textvariable=self.working_area, width=16)
        self.area_entry.grid(row=0, column=0, sticky="ew")
        self.area_entry.bind("<KeyRelease>", self.on_working_area_change)
        ttk.Label(area_frame, text="cm²", style="Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(area_frame, text="Clear", command=self.clear_working_area).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

        ttk.Label(sidebar, text="Metadata", style="Panel.TLabel").grid(row=6, column=0, sticky="w")
        self.metadata_text = tk.Text(
            sidebar,
            width=38,
            height=12,
            bg="#ffffff",
            fg=TEXT,
            highlightthickness=1,
            highlightbackground="#d5dde2",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        self.metadata_text.grid(row=7, column=0, sticky="nsew", pady=(4, 12))
        self.set_metadata_text("No CV files loaded.")

        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=320).grid(
            row=8, column=0, sticky="ew"
        )

        plot_area = ttk.Frame(self, padding=16)
        plot_area.grid(row=0, column=1, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(8, 6.5), dpi=100)
        self.ax_cv = self.figure.add_subplot(211)
        self.ax_average = self.figure.add_subplot(212)
        self._draw_empty_plot()

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(plot_area)
        toolbar_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=0, column=0, sticky="w")

    def _draw_empty_plot(self) -> None:
        self.ax_cv.clear()
        self.ax_average.clear()
        self.ax_cv.set_xlabel("Potential / V")
        self.ax_cv.set_ylabel(self.current_axis_label())
        self.ax_cv.set_title("No CV files loaded")
        self.ax_cv.grid(True, alpha=0.3)
        self.ax_average.set_xlabel("Scan rate / mV s$^{-1}$")
        self.ax_average.set_ylabel(self.average_axis_label())
        self.ax_average.set_title(self.average_plot_title())
        self.ax_average.grid(True, alpha=0.3)
        self.figure.tight_layout()

    def set_metadata_text(self, text: str) -> None:
        self.metadata_text.configure(state="normal")
        self.metadata_text.delete("1.0", tk.END)
        self.metadata_text.insert("1.0", text)
        self.metadata_text.configure(state="disabled")

    def open_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Choose cyclic voltammetry text files",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not selected:
            return
        for filename in selected:
            path = Path(filename)
            if path not in self.files:
                self.files.append(path)
        self.refresh_file_list()
        self.plot_files()

    def open_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Choose a folder of CV text files",
        )
        if not selected:
            return
        folder = Path(selected)
        self.files = sorted(folder.glob("*.txt"))
        if not self.files:
            messagebox.showwarning("No text files found", f"No .txt files were found in:\n{folder}")
            return
        self.refresh_file_list()
        self.plot_files()

    def refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.files:
            self.file_list.insert(tk.END, path.name)

    def clear_files(self) -> None:
        self.files.clear()
        self.data_sets.clear()
        self.refresh_file_list()
        self.selected_cycle.set(1)
        self.update_cycle_selector()
        self.set_metadata_text("No CV files loaded.")
        self.status.set("Load CV text files to plot a selected cycle.")
        self._draw_empty_plot()
        self.canvas.draw_idle()

    def plot_files(self) -> None:
        loaded: list[CVData] = []
        failures: list[str] = []
        for path in self.files:
            try:
                loaded.append(read_cv_data(path))
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")

        self.data_sets = sorted(loaded, key=lambda item: item.sort_key)
        self.use_last_cycle(refresh=False)
        self.update_cycle_selector()
        self.refresh_metadata_text()
        self.plot_loaded_data()

        if failures:
            self.status.set(f"Plotted {len(self.data_sets)} file(s). {len(failures)} file(s) could not be read.")
            messagebox.showwarning("Some files could not be read", "\n\n".join(failures))
        else:
            self.status.set(f"Plotted {len(self.data_sets)} file(s), cycle {self.selected_cycle_number()}.")

    def refresh_display(self) -> None:
        self.clamp_selected_cycle()
        self.refresh_metadata_text()
        self.plot_loaded_data()

    def refresh_metadata_text(self) -> None:
        self.set_metadata_text(summarize_data(self.data_sets, self.current_units.get(), self.selected_cycle_number()))

    def on_working_area_change(self, _event: tk.Event) -> None:
        self.refresh_metadata_text()
        self.plot_loaded_data()

    def clear_working_area(self) -> None:
        self.working_area.set("")
        self.refresh_metadata_text()
        self.plot_loaded_data()

    def get_working_area(self) -> float | None:
        raw_value = self.working_area.get().strip()
        if not raw_value:
            return None
        area = float(raw_value)
        if area <= 0:
            raise ValueError
        return area

    def use_current_density(self) -> bool:
        try:
            return self.get_working_area() is not None
        except ValueError:
            self.status.set("Working area must be a positive number.")
            return False

    def current_scale(self) -> float:
        if self.use_current_density():
            area = self.get_working_area()
            return 1000 / area if area else 1000
        return 1000 if self.current_units.get() == "mA" else 1

    def current_axis_label(self) -> str:
        if self.use_current_density():
            return "Current density / mA cm$^{-2}$"
        return f"Current / {self.current_units.get()}"

    def average_axis_label(self) -> str:
        if self.use_current_density():
            return "Average current density / mA cm$^{-2}$"
        return f"Average current / {self.current_units.get()}"

    def average_plot_title(self) -> str:
        if self.use_current_density():
            return f"Average current density vs scan rate, cycle {self.selected_cycle_number()}"
        return f"Average current vs scan rate, cycle {self.selected_cycle_number()}"

    def max_cycle_count(self) -> int:
        if not self.data_sets:
            return 1
        return max(data.cycle_count for data in self.data_sets)

    def selected_cycle_number(self) -> int:
        try:
            cycle = int(self.selected_cycle.get())
        except tk.TclError:
            cycle = 1
        return min(max(1, cycle), self.max_cycle_count())

    def clamp_selected_cycle(self) -> None:
        self.selected_cycle.set(self.selected_cycle_number())
        self.update_cycle_selector()

    def update_cycle_selector(self) -> None:
        if hasattr(self, "cycle_spinbox"):
            self.cycle_spinbox.configure(to=self.max_cycle_count())

    def use_last_cycle(self, refresh: bool = True) -> None:
        self.selected_cycle.set(self.max_cycle_count())
        self.update_cycle_selector()
        if refresh:
            self.refresh_display()

    def _plot_cv_axis(self, ax) -> None:
        scale = self.current_scale()
        cycle_number = self.selected_cycle_number()
        ax.clear()
        for data in self.data_sets:
            currents = [current * scale for current in data.cycle_currents(cycle_number)]
            ax.plot(
                data.cycle_potentials(cycle_number),
                currents,
                linewidth=self.line_width.get(),
                label=data.label,
            )

        ax.set_xlabel("Potential / V")
        ax.set_ylabel(self.current_axis_label())
        ax.set_title(f"CV cycle {cycle_number} by scan rate")
        ax.grid(self.show_grid.get(), alpha=0.3)
        if self.show_legend.get():
            ax.legend(loc="best", fontsize=8)

    def _plot_average_axis(self, ax) -> None:
        scale = self.current_scale()
        cycle_number = self.selected_cycle_number()
        ax.clear()
        average_points = [
            (
                data.metadata.scan_rate_mv_s,
                data.midpoint_currents_for_cycle(cycle_number).average_current * scale,
            )
            for data in self.data_sets
            if data.metadata.scan_rate_mv_s is not None and data.midpoint_currents_for_cycle(cycle_number) is not None
        ]
        average_points.sort(key=lambda point: point[0])
        if average_points:
            scan_rates = [point[0] for point in average_points]
            average_currents = [point[1] for point in average_points]
            ax.plot(
                scan_rates,
                average_currents,
                linestyle="None",
                marker="o",
                color=ACCENT,
                label="Data",
            )

            fit = self.linear_regression(average_points)
            if fit is not None:
                slope_display, intercept_display = fit
                fit_x = [min(scan_rates), max(scan_rates)]
                fit_y = [slope_display * value + intercept_display for value in fit_x]
                ax.plot(fit_x, fit_y, linewidth=1.5, color="#b84a3a", label="Linear fit")
                slope_f = self.linear_regression_slope_farads(cycle_number)
                if slope_f is not None:
                    ax.text(
                        0.04,
                        0.94,
                        self.capacitance_label(slope_f),
                        transform=ax.transAxes,
                        va="top",
                        ha="left",
                        fontsize=10,
                        bbox={"facecolor": "white", "edgecolor": "#d5dde2", "alpha": 0.85},
                    )
                ax.legend(loc="best", fontsize=8)

        ax.set_xlabel("Scan rate / mV s$^{-1}$")
        ax.set_ylabel(self.average_axis_label())
        ax.set_title(self.average_plot_title())
        ax.grid(self.show_grid.get(), alpha=0.3)

    @staticmethod
    def linear_regression(points: list[tuple[float, float]]) -> tuple[float, float] | None:
        if len(points) < 2:
            return None
        x_values = [point[0] for point in points]
        y_values = [point[1] for point in points]
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(y_values) / len(y_values)
        denominator = sum((x_value - x_mean) ** 2 for x_value in x_values)
        if denominator == 0:
            return None
        slope = sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in points) / denominator
        intercept = y_mean - slope * x_mean
        return slope, intercept

    def linear_regression_slope_farads(self, cycle_number: int) -> float | None:
        si_points: list[tuple[float, float]] = []
        for data in self.data_sets:
            midpoint_currents = data.midpoint_currents_for_cycle(cycle_number)
            scan_rate_mv_s = data.metadata.scan_rate_mv_s
            if midpoint_currents is None or scan_rate_mv_s is None:
                continue
            si_points.append((scan_rate_mv_s / 1000, midpoint_currents.average_current))
        fit = self.linear_regression(si_points)
        if fit is None:
            return None
        slope, _intercept = fit
        if self.use_current_density():
            area = self.get_working_area()
            if area:
                slope = slope / area
        return slope

    def capacitance_label(self, slope_f: float) -> str:
        if self.use_current_density():
            return f"k = {slope_f:.6g} F cm$^{{-2}}$\nC_dl = {slope_f * 1000:.6g} mF cm$^{{-2}}$"
        return f"k = {slope_f:.6g} F\nC_dl = {slope_f * 1000:.6g} mF"

    def plot_loaded_data(self) -> None:
        if not self.data_sets:
            self._draw_empty_plot()
            self.canvas.draw_idle()
            return

        self._plot_cv_axis(self.ax_cv)
        self._plot_average_axis(self.ax_average)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def save_plot(self) -> None:
        if not self.data_sets:
            messagebox.showinfo("No plot to save", "Load CV files first, then save the plot.")
            return
        output = filedialog.asksaveasfilename(
            title="Save plot",
            defaultextension=".png",
            initialfile="CV_multi_scan_rate_plot.png",
            filetypes=[
                ("PNG image", "*.png"),
                ("PDF file", "*.pdf"),
                ("SVG file", "*.svg"),
                ("All files", "*.*"),
            ],
        )
        if not output:
            return

        base_path = Path(output)
        if not base_path.suffix:
            base_path = base_path.with_suffix(".png")
        cycle_number = self.selected_cycle_number()
        cv_path = base_path.with_name(f"{base_path.stem}_cycle_{cycle_number}_cv{base_path.suffix}")
        average_path = base_path.with_name(f"{base_path.stem}_cycle_{cycle_number}_average_current_vs_scan_rate{base_path.suffix}")

        cv_figure = Figure(figsize=(7, 5), dpi=100)
        cv_axis = cv_figure.add_subplot(111)
        self._plot_cv_axis(cv_axis)
        cv_figure.tight_layout()
        cv_figure.savefig(cv_path, dpi=300)

        average_figure = Figure(figsize=(7, 5), dpi=100)
        average_axis = average_figure.add_subplot(111)
        self._plot_average_axis(average_axis)
        average_figure.tight_layout()
        average_figure.savefig(average_path, dpi=300)

        self.status.set(f"Saved separate plots to {cv_path.name} and {average_path.name}")

    def export_data(self) -> None:
        if not self.data_sets:
            messagebox.showinfo("No data to export", "Load CV files first, then export the data.")
            return

        output = filedialog.asksaveasfilename(
            title="Export data",
            defaultextension=".csv",
            initialfile=self.default_export_filename(),
            filetypes=[
                ("CSV file", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not output:
            return

        base_path = Path(output)
        if not base_path.suffix:
            base_path = base_path.with_suffix(".cvs")
        cycle_number = self.selected_cycle_number()
        average_path = base_path.with_name(f"{base_path.stem}_scan_rate_current{base_path.suffix}")
        cv_path = base_path

        self._export_average_current_data(average_path)
        self._export_last_cycle_cv_data(cv_path)
        self.status.set(f"Exported data to {average_path.name} and {cv_path.name}")

    def default_export_filename(self) -> str:
        if self.files:
            return f"{self.files[0].stem}.cvs"
        return "CV_multi_scan_rate_data.cvs"

    def _export_average_current_data(self, output_path: Path) -> None:
        rows: list[tuple[float, float]] = []
        cycle_number = self.selected_cycle_number()
        scale = self.current_scale()
        for data in self.data_sets:
            midpoint_currents = data.midpoint_currents_for_cycle(cycle_number)
            scan_rate = data.metadata.scan_rate_mv_s
            if midpoint_currents is None or scan_rate is None:
                continue
            rows.append((scan_rate, midpoint_currents.average_current * scale))
        rows.sort(key=lambda row: row[0])
        fit = self.linear_regression(rows)
        formula = ""
        if fit is not None:
            slope, intercept = fit
            y_label = "current density" if self.use_current_density() else "current"
            y_unit = "mA/cm^2" if self.use_current_density() else self.current_units.get()
            formula = f"{y_label} ({y_unit}) = {slope:.10g} * scan rate (mV/s) + {intercept:.10g}"

        with output_path.open("w", encoding="utf-8", newline="") as export:
            writer = csv.writer(export)
            value_header = "Current density mA/cm^2" if self.use_current_density() else f"Current {self.current_units.get()}"
            writer.writerow(["Scan rate mV/s", value_header, "Fitted line formula"])
            for scan_rate, value in rows:
                writer.writerow([f"{scan_rate:g}", f"{value:.10g}", formula])

    def _export_last_cycle_cv_data(self, output_path: Path) -> None:
        data_sets = sorted(self.data_sets, key=lambda data: data.sort_key)
        cycle_number = self.selected_cycle_number()
        max_points = max((len(data.cycle_potentials(cycle_number)) for data in data_sets), default=0)

        header: list[str] = []
        scan_rate_row: list[str] = []
        for data in data_sets:
            current_header = (
                "Current density mA/cm^2" if self.use_current_density() else f"Current {self.current_units.get()}"
            )
            header.extend(["Potential V", current_header])
            scan_rate_label = data.label.replace("Scan rate = ", "")
            scan_rate_row.extend([scan_rate_label, scan_rate_label])

        with output_path.open("w", encoding="utf-8", newline="") as export:
            writer = csv.writer(export)
            writer.writerow(header)
            writer.writerow(scan_rate_row)
            for index in range(max_points):
                row: list[str] = []
                for data in data_sets:
                    potentials = data.cycle_potentials(cycle_number)
                    currents = data.cycle_currents(cycle_number)
                    if index < len(potentials):
                        row.append(f"{potentials[index]:.10g}")
                        row.append(f"{currents[index] * self.current_scale():.10g}")
                    else:
                        row.extend(["", ""])
                writer.writerow(row)


def main() -> None:
    app = CVMultiPlotApp()
    app.mainloop()


if __name__ == "__main__":
    main()


