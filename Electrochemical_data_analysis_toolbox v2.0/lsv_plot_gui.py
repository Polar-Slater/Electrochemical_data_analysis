from __future__ import annotations

import csv
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plot_lsv_txt import LSVData, read_lsv_data, summarize_lsv_data
from scrollable_sidebar import ScrollableSidebar


BG = "#f7f8fa"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#637083"
ACCENT = "#1f6feb"

CURRENT_UNITS = {
    "A": 1.0,
    "mA": 1_000.0,
    "uA": 1_000_000.0,
    "nA": 1_000_000_000.0,
}
ORIGINAL_CURRENT_UNIT = "mA"


class LSVPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.files: list[Path] = []
        self.loaded_data: dict[Path, LSVData] = {}
        self.status = tk.StringVar(value="Choose one or more LSV text files.")
        self.show_grid = tk.BooleanVar(value=True)
        self.legend_enabled = tk.BooleanVar(value=True)
        self.current_unit = tk.StringVar(value="A")
        self.rhe_offset = tk.StringVar(value="")
        self.working_area = tk.StringVar(value="")
        self.solution_resistance = tk.StringVar(value="")
        self.compensation_level = tk.StringVar(value="")
        self.equilibrium_potential = tk.StringVar(value="1.23")
        self.plot_mode = tk.StringVar(value="LSV")
        self.tafel_min = tk.StringVar()
        self.tafel_max = tk.StringVar()

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
        style.map("Accent.TButton", background=[("active", "#1959bd"), ("!disabled", ACCENT)])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TRadiobutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=PANEL)
        style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT, font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = ScrollableSidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar = self.sidebar.content
        sidebar.rowconfigure(3, weight=1)
        sidebar.rowconfigure(9, weight=1)

        ttk.Label(sidebar, text="LSV Plotter", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(sidebar, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(
            sidebar,
            text="Reads data after 'Potential/V, Current/A'.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Open files", style="Accent.TButton", command=self.open_files).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(buttons, text="Clear", command=self.clear_files).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Save plot", command=self.save_plot).grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Export data", command=self.export_data).grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Tafel slope", command=self.show_tafel_plot).grid(
            row=4, column=0, sticky="ew", pady=(8, 0)
        )
        ttk.Button(buttons, text="LSV plot", command=self.show_lsv_plot).grid(
            row=5, column=0, sticky="ew", pady=(8, 0)
        )

        list_frame = ttk.Frame(sidebar, style="Panel.TFrame")
        list_frame.grid(row=3, column=0, sticky="nsew", pady=(6, 12))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.file_list = tk.Listbox(
            list_frame,
            width=38,
            height=12,
            bg="#ffffff",
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=1,
            highlightbackground="#d7dce2",
            relief="flat",
            font=("Segoe UI", 9),
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scrollbar.set)

        options = ttk.Frame(sidebar, style="Panel.TFrame")
        options.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ttk.Checkbutton(options, text="Grid", variable=self.show_grid, command=self.plot_files).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(options, text="Legend", variable=self.legend_enabled, command=self.plot_files).grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )

        units = ttk.Frame(sidebar, style="Panel.TFrame")
        units.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(units, text="Current units", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        for column, unit in enumerate(CURRENT_UNITS):
            ttk.Radiobutton(
                units,
                text=unit,
                value=unit,
                variable=self.current_unit,
                command=self.plot_files,
            ).grid(row=1, column=column, sticky="w", padx=(0, 10))

        ref_frame = ttk.LabelFrame(sidebar, text="Ref electrode potential (vs. RHE) :", padding=10)
        ref_frame.grid(row=6, column=0, sticky="ew", pady=(0, 12))
        ref_frame.columnconfigure(0, weight=1)
        self.rhe_entry = ttk.Entry(ref_frame, textvariable=self.rhe_offset, width=16)
        self.rhe_entry.grid(row=0, column=0, sticky="ew")
        self.rhe_entry.bind("<KeyRelease>", self.on_rhe_offset_change)
        ttk.Label(ref_frame, text="V added to Potential", style="Panel.TLabel").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Button(ref_frame, text="Clear", command=self.clear_rhe_offset).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(ref_frame, text="Equilibrium potential", style="Panel.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 2)
        )
        self.eq_entry = ttk.Entry(ref_frame, textvariable=self.equilibrium_potential, width=16)
        self.eq_entry.grid(row=3, column=0, sticky="ew")
        self.eq_entry.bind("<KeyRelease>", self.on_equilibrium_potential_change)
        ttk.Label(ref_frame, text="V vs. RHE", style="Panel.TLabel").grid(row=3, column=1, sticky="w", padx=(8, 0))
        ttk.Label(ref_frame, text="Tafel fit overpotential range / V", style="Panel.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 2))
        for row, label, variable in ((5, "Minimum", self.tafel_min), (6, "Maximum", self.tafel_max)):
            ttk.Label(ref_frame, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(ref_frame, textvariable=variable, width=12)
            entry.grid(row=row, column=1, sticky="ew")
            entry.bind("<Return>", self.on_equilibrium_potential_change)
        ttk.Button(ref_frame, text="Apply fit range", command=self.show_tafel_plot).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Label(ref_frame, text="Blank bounds include the full range.", style="Muted.TLabel").grid(
            row=8, column=0, columnspan=2, sticky="w")

        area_frame = ttk.LabelFrame(sidebar, text="Working area: ", padding=10)
        area_frame.grid(row=7, column=0, sticky="ew", pady=(0, 12))
        area_frame.columnconfigure(0, weight=1)
        self.area_entry = ttk.Entry(area_frame, textvariable=self.working_area, width=16)
        self.area_entry.grid(row=0, column=0, sticky="ew")
        self.area_entry.bind("<KeyRelease>", self.on_working_area_change)
        ttk.Label(area_frame, text="cm\u00b2", style="Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(area_frame, text="Clear", command=self.clear_working_area).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

        ir_frame = ttk.LabelFrame(sidebar, text="iR compensation", padding=10)
        ir_frame.grid(row=8, column=0, sticky="ew", pady=(0, 12))
        ir_frame.columnconfigure(1, weight=1)
        ttk.Label(ir_frame, text="Rs", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.rs_entry = ttk.Entry(ir_frame, textvariable=self.solution_resistance, width=12)
        self.rs_entry.grid(row=0, column=1, sticky="ew")
        self.rs_entry.bind("<KeyRelease>", self.on_ir_compensation_change)
        ttk.Label(ir_frame, text="ohm", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Label(ir_frame, text="Level", style="Panel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        self.comp_entry = ttk.Entry(ir_frame, textvariable=self.compensation_level, width=12)
        self.comp_entry.grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self.comp_entry.bind("<KeyRelease>", self.on_ir_compensation_change)
        ttk.Label(ir_frame, text="%", style="Panel.TLabel").grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Button(ir_frame, text="Clear", command=self.clear_ir_compensation).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )

        results_frame = ttk.Frame(sidebar, style="Panel.TFrame")
        results_frame.grid(row=9, column=0, sticky="nsew", pady=(0, 12))
        results_frame.rowconfigure(1, weight=1)
        results_frame.columnconfigure(0, weight=1)
        ttk.Label(results_frame, text="Parsed file info", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.results_text = tk.Text(
            results_frame,
            height=12,
            width=38,
            bg="#ffffff",
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d7dce2",
            font=("Consolas", 9),
            wrap="word",
        )
        self.results_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.set_results_text("Open an LSV file to view scan settings and plot the data.")

        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=310).grid(
            row=10, column=0, sticky="ew"
        )

        self.sidebar.enable_mousewheel()

        plot_area = ttk.Frame(self, padding=16)
        plot_area.grid(row=0, column=1, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(7, 6), dpi=100)
        self.ax_original = None
        self.ax_adjusted = None
        self._draw_empty_plot()

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(plot_area)
        toolbar_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=0, column=0, sticky="w")

    def _draw_empty_plot(self) -> None:
        if self.plot_mode.get() == "Tafel":
            self._prepare_tafel_axis()
            self.ax_original.set_xlabel("log10(|j| / mA cm$^{-2}$)")
            self.ax_original.set_ylabel("Overpotential / V")
            self.ax_original.set_title("Tafel slope")
            self.ax_original.grid(True, alpha=0.3)
            self.figure.tight_layout()
            return

        self._prepare_lsv_axes()
        self.ax_original.clear()
        self.ax_original.set_xlabel("Potential / V")
        self.ax_original.set_ylabel(f"Current / {ORIGINAL_CURRENT_UNIT}")
        self.ax_original.set_title("Original LSV")
        self.ax_original.grid(True, alpha=0.3)

        self.ax_adjusted.clear()
        self.ax_adjusted.set_xlabel(self.get_potential_axis_label())
        self.ax_adjusted.set_ylabel(self.get_current_axis_label())
        self.ax_adjusted.set_title("Adjusted LSV")
        self.ax_adjusted.grid(True, alpha=0.3)
        self.figure.tight_layout()

    def _prepare_lsv_axes(self) -> None:
        self.figure.clear()
        self.ax_original = self.figure.add_subplot(211)
        self.ax_adjusted = self.figure.add_subplot(212)

    def _prepare_tafel_axis(self) -> None:
        self.figure.clear()
        layout = self.figure.add_gridspec(2, 1, height_ratios=(1, 2))
        self.ax_adjusted = self.figure.add_subplot(layout[0])
        self.ax_original = self.figure.add_subplot(layout[1])
        self.ax_adjusted.set(title="Polarization curve", xlabel="Overpotential / V",
                             ylabel="j / mA cm$^{-2}$")

    def get_tafel_bounds(self):
        lower = float(self.tafel_min.get()) if self.tafel_min.get().strip() else -math.inf
        upper = float(self.tafel_max.get()) if self.tafel_max.get().strip() else math.inf
        if math.isnan(lower) or math.isnan(upper) or lower >= upper:
            raise ValueError("Tafel minimum must be less than maximum.")
        return lower, upper

    def open_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Choose LSV text files",
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

    def refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.files:
            self.file_list.insert(tk.END, path.name)

    def clear_files(self) -> None:
        self.files.clear()
        self.loaded_data.clear()
        self.refresh_file_list()
        self.status.set("Choose one or more LSV text files.")
        self.set_results_text("Open an LSV file to view scan settings and plot the data.")
        self._draw_empty_plot()
        self.canvas.draw_idle()

    def set_results_text(self, text: str) -> None:
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", text)
        self.results_text.configure(state="disabled")

    def on_rhe_offset_change(self, _event: tk.Event) -> None:
        self.plot_files()

    def clear_rhe_offset(self) -> None:
        self.rhe_offset.set("")
        self.plot_files()

    def on_working_area_change(self, _event: tk.Event) -> None:
        self.plot_files()

    def clear_working_area(self) -> None:
        self.working_area.set("")
        self.plot_files()

    def on_ir_compensation_change(self, _event: tk.Event) -> None:
        self.plot_files()

    def clear_ir_compensation(self) -> None:
        self.solution_resistance.set("")
        self.compensation_level.set("")
        self.plot_files()

    def on_equilibrium_potential_change(self, _event: tk.Event) -> None:
        if self.plot_mode.get() == "Tafel":
            self.plot_files()

    def show_tafel_plot(self) -> None:
        self.plot_mode.set("Tafel")
        self.plot_files()

    def show_lsv_plot(self) -> None:
        self.plot_mode.set("LSV")
        self.plot_files()

    def get_rhe_offset(self) -> float | None:
        raw_value = self.rhe_offset.get().strip()
        if not raw_value:
            return None
        return float(raw_value)

    def get_working_area(self) -> float | None:
        raw_value = self.working_area.get().strip()
        if not raw_value:
            return None
        area = float(raw_value)
        if area <= 0:
            raise ValueError
        return area

    def get_ir_compensation(self) -> tuple[float, float] | None:
        raw_rs = self.solution_resistance.get().strip()
        raw_level = self.compensation_level.get().strip()
        if not raw_rs and not raw_level:
            return None
        if not raw_rs or not raw_level:
            raise ValueError

        resistance = float(raw_rs)
        level_percent = float(raw_level)
        if resistance < 0 or level_percent < 0:
            raise ValueError
        return resistance, level_percent / 100

    def get_equilibrium_potential(self) -> float:
        raw_value = self.equilibrium_potential.get().strip()
        if not raw_value:
            return 1.23
        return float(raw_value)

    def get_potential_axis_label(self) -> str:
        try:
            offset = self.get_rhe_offset()
        except ValueError:
            offset = None
        try:
            ir_compensation = self.get_ir_compensation()
        except ValueError:
            ir_compensation = None
        if ir_compensation is not None and offset is not None:
            return "Potential (V vs. RHE, iR-corrected)"
        if ir_compensation is not None:
            return "Potential (V, iR-corrected)"
        if offset is None:
            return "Potential / V"
        return "Potential (V vs. RHE)"

    def get_current_axis_label(self) -> str:
        try:
            area = self.get_working_area()
        except ValueError:
            area = None
        if area is None:
            return f"Current / {self.current_unit.get()}"
        return "Current density / mA/cm\u00b2"

    def get_data(self, path: Path) -> LSVData:
        data = self.loaded_data.get(path)
        if data is None:
            data = read_lsv_data(path)
            self.loaded_data[path] = data
        return data

    def get_plot_settings(self) -> tuple[float | None, float | None, tuple[float, float] | None, list[str]]:
        errors: list[str] = []
        try:
            rhe_offset = self.get_rhe_offset()
        except ValueError:
            rhe_offset = None
            errors.append("Ref electrode potential must be a number.")

        try:
            working_area = self.get_working_area()
        except ValueError:
            working_area = None
            errors.append("Working area must be a positive number.")

        try:
            ir_compensation = self.get_ir_compensation()
        except ValueError:
            ir_compensation = None
            errors.append("Rs and compensation level must be non-negative numbers.")

        return rhe_offset, working_area, ir_compensation, errors

    def get_adjusted_potentials(
        self,
        data: LSVData,
        rhe_offset: float | None,
        ir_compensation: tuple[float, float] | None,
    ) -> list[float]:
        adjusted_potentials = data.potentials
        if rhe_offset is not None:
            adjusted_potentials = [potential + rhe_offset for potential in data.potentials]
        if ir_compensation is not None:
            resistance, compensation_fraction = ir_compensation
            adjusted_potentials = [
                potential - current * resistance * compensation_fraction
                for potential, current in zip(adjusted_potentials, data.currents)
            ]
        return adjusted_potentials

    def get_adjusted_y_values(
        self,
        data: LSVData,
        original_currents: list[float],
        working_area: float | None,
    ) -> list[float]:
        if working_area is None:
            return original_currents
        return [current * 1000 / working_area for current in data.currents]

    def plot_files(self) -> None:
        if not self.files:
            self._draw_empty_plot()
            self.canvas.draw_idle()
            return

        if self.plot_mode.get() == "Tafel":
            self.plot_tafel_files()
            return

        self._prepare_lsv_axes()
        self.ax_original.clear()
        self.ax_adjusted.clear()
        loaded = 0
        failures: list[str] = []
        summaries: list[str] = []
        unit = self.current_unit.get()
        scale = CURRENT_UNITS[unit]
        original_scale = CURRENT_UNITS[ORIGINAL_CURRENT_UNIT]
        rhe_offset, working_area, ir_compensation, setting_errors = self.get_plot_settings()

        for path in self.files:
            try:
                data = self.get_data(path)
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
                continue

            original_currents = [current * original_scale for current in data.currents]
            self.ax_original.plot(data.potentials, original_currents, linewidth=1.5, label=path.stem)

            adjusted_potentials = self.get_adjusted_potentials(data, rhe_offset, ir_compensation)
            adjusted_currents = [current * scale for current in data.currents]
            adjusted_y_values = self.get_adjusted_y_values(data, adjusted_currents, working_area)
            self.ax_adjusted.plot(adjusted_potentials, adjusted_y_values, linewidth=1.5, label=path.stem)
            summaries.append(f"{path.name}\n{summarize_lsv_data(data)}")
            loaded += 1

        self.ax_original.set_xlabel("Potential / V")
        self.ax_original.set_ylabel(f"Current / {ORIGINAL_CURRENT_UNIT}")
        self.ax_original.set_title("Original LSV")
        self.ax_original.grid(self.show_grid.get(), alpha=0.3)

        self.ax_adjusted.set_xlabel(self.get_potential_axis_label())
        self.ax_adjusted.set_ylabel(self.get_current_axis_label())
        self.ax_adjusted.set_title("Adjusted LSV")
        self.ax_adjusted.grid(self.show_grid.get(), alpha=0.3)

        if self.legend_enabled.get() and loaded:
            self.ax_original.legend(loc="best", fontsize=8)
            self.ax_adjusted.legend(loc="best", fontsize=8)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.set_results_text("\n\n".join(summaries) if summaries else "No readable LSV data.")

        if failures:
            self.status.set(f"Plotted {loaded} file(s). {len(failures)} file(s) could not be read.")
            messagebox.showwarning("Some files could not be read", "\n\n".join(failures))
        elif setting_errors:
            self.status.set(f"Plotted {loaded} file(s). {setting_errors[0]}")
        else:
            transforms: list[str] = []
            if rhe_offset is not None:
                transforms.append(f"added {rhe_offset:g} V to Potential")
            if ir_compensation is not None:
                resistance, compensation_fraction = ir_compensation
                transforms.append(f"iR-corrected with Rs {resistance:g} ohm at {compensation_fraction * 100:g}%")
            if working_area is not None:
                transforms.append(f"area-normalized with {working_area:g} cm\u00b2")
            if transforms:
                self.status.set(f"Plotted {loaded} file(s). Adjusted plot: {'; '.join(transforms)}.")
            else:
                self.status.set(f"Plotted {loaded} file(s).")

    def plot_tafel_files(self) -> None:
        try:
            lower, upper = self.get_tafel_bounds()
        except ValueError as exc:
            self.status.set(f"Invalid Tafel range: {exc}")
            return
        self._prepare_tafel_axis()
        loaded = 0
        failures: list[str] = []
        summaries: list[str] = []
        rhe_offset, working_area, ir_compensation, setting_errors = self.get_plot_settings()
        try:
            equilibrium_potential = self.get_equilibrium_potential()
        except ValueError:
            equilibrium_potential = 1.23
            setting_errors.append("Equilibrium potential must be a number.")

        if working_area is None:
            setting_errors.append("Working area is required for Tafel slope.")

        for path in self.files:
            try:
                data = self.get_data(path)
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
                continue

            adjusted_potentials = self.get_adjusted_potentials(data, rhe_offset, ir_compensation)
            if working_area is None:
                tafel_points = []
            else:
                tafel_points = self.tafel_points(data, adjusted_potentials, working_area, equilibrium_potential)

            if tafel_points:
                eta = [potential - equilibrium_potential for potential in adjusted_potentials]
                density = [current * 1000 / working_area for current in data.currents]
                line, = self.ax_adjusted.plot(eta, density, linewidth=1.5, label=path.stem)
                color = line.get_color()
                log_current = [point[0] for point in tafel_points]
                overpotential = [point[1] for point in tafel_points]
                label = path.stem
                selected = [(x, y) for x, y in tafel_points if lower <= y <= upper]
                fit = self.linear_regression(selected)
                if fit is not None:
                    slope, intercept = fit
                    label = f"{path.stem} ({slope * 1000:.4g} mV/dec)"
                    fit_x = [min(x for x, y in selected), max(x for x, y in selected)]
                    fit_y = [slope * value + intercept for value in fit_x]
                    self.ax_original.plot(fit_x, fit_y, color=color, linestyle="--", linewidth=2.4)
                    self.ax_adjusted.axvspan(min(y for x, y in selected), max(y for x, y in selected),
                                             color=color, alpha=0.15)
                    self.ax_original.scatter([x for x, y in selected], [y for x, y in selected],
                                             color=color, s=18, zorder=3)
                    summaries.append(f"{path.name}: fit uses {len(selected)} points; slope = {slope * 1000:.6g} mV/dec")
                else:
                    summaries.append(f"{path.name}: no fit — select at least two distinct log-current values.")
                self.ax_original.plot(log_current, overpotential, color=color, linewidth=1.5, label=label)
                loaded += 1

            summaries.append(f"{path.name}\n{summarize_lsv_data(data)}")

        self.ax_original.set_xlabel("log10(|j| / mA cm$^{-2}$)")
        self.ax_original.set_ylabel("Overpotential / V")
        self.ax_original.set_title("Tafel slope")
        self.ax_original.grid(self.show_grid.get(), alpha=0.3)
        self.ax_adjusted.grid(self.show_grid.get(), alpha=0.3)
        if self.legend_enabled.get() and loaded:
            self.ax_original.legend(loc="best", fontsize=8)
            self.ax_adjusted.legend(loc="best", fontsize=8)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.set_results_text("\n\n".join(summaries) if summaries else "No readable LSV data.")

        if failures:
            self.status.set(f"Plotted {loaded} Tafel curve(s). {len(failures)} file(s) could not be read.")
            messagebox.showwarning("Some files could not be read", "\n\n".join(failures))
        elif setting_errors:
            self.status.set(f"Tafel plot: {setting_errors[0]}")
        else:
            self.status.set(f"Plotted {loaded} Tafel curve(s). E_eq = {equilibrium_potential:g} V.")

    @staticmethod
    def tafel_points(
        data: LSVData,
        adjusted_potentials: list[float],
        working_area: float,
        equilibrium_potential: float,
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for potential, current in zip(adjusted_potentials, data.currents):
            current_density = current * 1000 / working_area
            if current_density == 0:
                continue
            overpotential = potential - equilibrium_potential
            points.append((math.log10(abs(current_density)), overpotential))
        return points

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

    def export_data(self) -> None:
        if not self.files:
            messagebox.showinfo("No data to export", "Choose a file first, then export the data.")
            return

        if self.plot_mode.get() == "Tafel":
            self.export_tafel_data()
            return

        output = filedialog.asksaveasfilename(
            title="Export data",
            initialfile=self.get_default_export_filename(),
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
        )
        if not output:
            return

        unit = self.current_unit.get()
        scale = CURRENT_UNITS[unit]
        original_scale = CURRENT_UNITS[ORIGINAL_CURRENT_UNIT]
        rhe_offset, working_area, ir_compensation, setting_errors = self.get_plot_settings()
        if setting_errors:
            messagebox.showwarning("Exporting without invalid transforms", setting_errors[0])

        rows_written = 0
        failures: list[str] = []
        with Path(output).open("w", encoding="utf-8-sig", newline="") as destination:
            writer = csv.writer(destination)
            writer.writerow(["Reference electrode potential (V vs. RHE)", self.format_optional_value(rhe_offset)])
            writer.writerow(["Working area (cm\u00b2)", self.format_optional_value(working_area)])
            if ir_compensation is None:
                writer.writerow(["Solution resistance (ohm)", "", "Compensation level (%)", ""])
            else:
                resistance, compensation_fraction = ir_compensation
                writer.writerow(
                    [
                        "Solution resistance (ohm)",
                        resistance,
                        "Compensation level (%)",
                        compensation_fraction * 100,
                    ]
                )
            writer.writerow([])
            writer.writerow(
                [
                    "File",
                    "Point",
                    "Original Potential (V)",
                    f"Original Current ({ORIGINAL_CURRENT_UNIT})",
                    self.get_potential_axis_label(),
                    self.get_current_axis_label(),
                ]
            )

            for path in self.files:
                try:
                    data = self.get_data(path)
                except Exception as exc:
                    failures.append(f"{path.name}: {exc}")
                    continue

                original_currents = [current * original_scale for current in data.currents]
                adjusted_currents = [current * scale for current in data.currents]
                adjusted_potentials = self.get_adjusted_potentials(data, rhe_offset, ir_compensation)
                adjusted_y_values = self.get_adjusted_y_values(data, adjusted_currents, working_area)

                for index, values in enumerate(
                    zip(data.potentials, original_currents, adjusted_potentials, adjusted_y_values),
                    start=1,
                ):
                    original_potential, original_current, adjusted_potential, adjusted_y = values
                    writer.writerow(
                        [
                            path.name,
                            index,
                            original_potential,
                            original_current,
                            adjusted_potential,
                            adjusted_y,
                        ]
                    )
                    rows_written += 1

        if failures:
            messagebox.showwarning("Some files could not be exported", "\n\n".join(failures))
        self.status.set(f"Exported {rows_written} data row(s) to {output}")

    def export_tafel_data(self) -> None:
        output = filedialog.asksaveasfilename(
            title="Export Tafel data",
            initialfile=self.get_default_tafel_export_filename(),
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
        )
        if not output:
            return

        rhe_offset, working_area, ir_compensation, setting_errors = self.get_plot_settings()
        try:
            equilibrium_potential = self.get_equilibrium_potential()
        except ValueError:
            equilibrium_potential = 1.23
            setting_errors.append("Equilibrium potential must be a number.")

        if working_area is None:
            messagebox.showwarning("Cannot export Tafel data", "Working area is required for Tafel export.")
            self.status.set("Tafel export needs a valid working area.")
            return
        if setting_errors:
            messagebox.showwarning("Exporting with warnings", setting_errors[0])

        rows_written = 0
        failures: list[str] = []
        with Path(output).open("w", encoding="utf-8-sig", newline="") as destination:
            writer = csv.writer(destination)
            writer.writerow(["Reference electrode potential (V vs. RHE)", self.format_optional_value(rhe_offset)])
            writer.writerow(["Equilibrium potential (V vs. RHE)", f"{equilibrium_potential:g}"])
            writer.writerow(["Working area (cm²)", self.format_optional_value(working_area)])
            if ir_compensation is None:
                writer.writerow(["Solution resistance (ohm)", "", "Compensation level (%)", ""])
            else:
                resistance, compensation_fraction = ir_compensation
                writer.writerow(
                    [
                        "Solution resistance (ohm)",
                        resistance,
                        "Compensation level (%)",
                        compensation_fraction * 100,
                    ]
                )
            writer.writerow([])
            writer.writerow(
                [
                    "File",
                    "Point",
                    "Corrected potential (V)",
                    "Current density (mA/cm²)",
                    "log10(|j| / mA cm^-2)",
                    "Overpotential (V)",
                ]
            )

            for path in self.files:
                try:
                    data = self.get_data(path)
                except Exception as exc:
                    failures.append(f"{path.name}: {exc}")
                    continue

                adjusted_potentials = self.get_adjusted_potentials(data, rhe_offset, ir_compensation)
                point_index = 0
                for potential, current in zip(adjusted_potentials, data.currents):
                    current_density = current * 1000 / working_area
                    if current_density == 0:
                        continue
                    point_index += 1
                    writer.writerow(
                        [
                            path.name,
                            point_index,
                            potential,
                            current_density,
                            math.log10(abs(current_density)),
                            potential - equilibrium_potential,
                        ]
                    )
                    rows_written += 1

        if failures:
            messagebox.showwarning("Some files could not be exported", "\n\n".join(failures))
        self.status.set(f"Exported {rows_written} Tafel data row(s) to {output}")

    def get_default_export_filename(self) -> str:
        if len(self.files) == 1:
            return f"{self.files[0].stem}_processed.csv"
        return "LSV_processed.csv"

    def get_default_tafel_export_filename(self) -> str:
        if len(self.files) == 1:
            return f"{self.files[0].stem}_tafel.csv"
        return "LSV_tafel.csv"

    @staticmethod
    def format_optional_value(value: float | None) -> str:
        if value is None:
            return ""
        return f"{value:g}"

    def save_plot(self) -> None:
        if not self.files:
            messagebox.showinfo("No plot to save", "Choose a file first, then save the plot.")
            return

        output = filedialog.asksaveasfilename(
            title="Save plot",
            defaultextension=".png",
            filetypes=[
                ("PNG image", "*.png"),
                ("PDF file", "*.pdf"),
                ("SVG file", "*.svg"),
                ("All files", "*.*"),
            ],
        )
        if not output:
            return

        self.figure.savefig(output, dpi=300)
        self.status.set(f"Saved plot to {output}")


def main() -> None:
    app = LSVPlotApp()
    app.mainloop()


if __name__ == "__main__":
    main()


