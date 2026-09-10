from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plot_durability_txt import DurabilityData, read_durability_data, summarize_durability_data


BG = "#f6f7f9"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#667085"
ACCENT = "#b45309"


class DurabilityPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.data: DurabilityData | None = None
        self.status = tk.StringVar(value="Open a durability text file to plot.")
        self.summary = tk.StringVar(value="No file loaded.")
        self.show_grid = tk.BooleanVar(value=True)
        self.rhe_offset = tk.StringVar(value="")
        self.working_area = tk.StringVar(value="")
        self.current_density_text = tk.StringVar(value="")
        self.solution_resistance = tk.StringVar(value="")
        self.compensation_level = tk.StringVar(value="")
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
        style.map("Accent.TButton", background=[("active", "#92400e"), ("!disabled", ACCENT)])
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
        sidebar.rowconfigure(8, weight=1)

        ttk.Label(sidebar, text="Durability", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(sidebar, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(
            sidebar,
            text="Plots CP potential or chronoamperometry current over time.",
            style="Muted.TLabel",
            wraplength=280,
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Open durability file", style="Accent.TButton", command=self.open_file).grid(
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

        ref_frame = ttk.LabelFrame(sidebar, text="Ref electrode potential (vs. RHE)", padding=10)
        ref_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ref_frame.columnconfigure(0, weight=1)
        rhe_entry = ttk.Entry(ref_frame, textvariable=self.rhe_offset, width=16)
        rhe_entry.grid(row=0, column=0, sticky="ew")
        rhe_entry.bind("<KeyRelease>", self.on_transform_change)
        rhe_entry.bind("<Return>", self.on_transform_change)
        ttk.Label(ref_frame, text="V added to Potential", style="Panel.TLabel").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Button(ref_frame, text="Clear", command=self.clear_rhe_offset).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

        area_frame = ttk.LabelFrame(sidebar, text="Working area", padding=10)
        area_frame.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        area_frame.columnconfigure(0, weight=1)
        area_entry = ttk.Entry(area_frame, textvariable=self.working_area, width=16)
        area_entry.grid(row=0, column=0, sticky="ew")
        area_entry.bind("<KeyRelease>", self.on_transform_change)
        area_entry.bind("<Return>", self.on_transform_change)
        ttk.Label(area_frame, text="cm^2", style="Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(area_frame, text="Clear", command=self.clear_working_area).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(area_frame, textvariable=self.current_density_text, style="Panel.TLabel").grid(
            row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        ir_frame = ttk.LabelFrame(sidebar, text="iR compensation", padding=10)
        ir_frame.grid(row=6, column=0, sticky="ew", pady=(0, 12))
        ir_frame.columnconfigure(1, weight=1)
        ttk.Label(ir_frame, text="Rs", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        rs_entry = ttk.Entry(ir_frame, textvariable=self.solution_resistance, width=12)
        rs_entry.grid(row=0, column=1, sticky="ew")
        rs_entry.bind("<KeyRelease>", self.on_transform_change)
        rs_entry.bind("<Return>", self.on_transform_change)
        ttk.Label(ir_frame, text="ohm", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Label(ir_frame, text="Level", style="Panel.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
        )
        comp_entry = ttk.Entry(ir_frame, textvariable=self.compensation_level, width=12)
        comp_entry.grid(row=1, column=1, sticky="ew", pady=(8, 0))
        comp_entry.bind("<KeyRelease>", self.on_transform_change)
        comp_entry.bind("<Return>", self.on_transform_change)
        ttk.Label(ir_frame, text="%", style="Panel.TLabel").grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Button(ir_frame, text="Clear", command=self.clear_ir_compensation).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )

        y_range = ttk.LabelFrame(sidebar, text="Y axis range", padding=10)
        y_range.grid(row=7, column=0, sticky="ew", pady=(0, 14))
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
        info.grid(row=8, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)
        ttk.Label(info, textvariable=self.summary, style="Panel.TLabel", wraplength=280, justify="left").grid(
            row=0, column=0, sticky="nw"
        )

        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=280).grid(
            row=9, column=0, sticky="ew", pady=(14, 0)
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
            title="Open durability text file",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            self.data = read_durability_data(filename)
        except Exception as exc:
            messagebox.showerror("Could not read durability file", str(exc))
            self.status.set("Failed to load file.")
            return

        self.refresh_summary()
        self.status.set(f"Loaded {self.data.source.name}")
        self.redraw()

    def clear_plot(self) -> None:
        self.data = None
        self.summary.set("No file loaded.")
        self.current_density_text.set("")
        self.status.set("Open a durability text file to plot.")
        self._draw_empty_plot()

    def save_plot(self) -> None:
        if self.data is None:
            messagebox.showinfo("No plot to save", "Open a durability file first.")
            return

        default_name = f"{self.data.source.stem}_durability.png"
        filename = filedialog.asksaveasfilename(
            title="Save durability plot",
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
            messagebox.showinfo("No data to export", "Open a durability file first.")
            return

        default_name = f"{self.data.source.stem}_durability_data.csv"
        filename = filedialog.asksaveasfilename(
            title="Export durability data",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        rhe_offset, working_area, ir_compensation, setting_errors = self.get_plot_settings()
        if setting_errors:
            messagebox.showwarning("Exporting without invalid transforms", setting_errors[0])

        adjusted_potentials = self.get_adjusted_potentials(rhe_offset, ir_compensation)
        output = Path(filename)
        with output.open("w", encoding="utf-8", newline="") as export:
            writer = csv.writer(export)
            writer.writerow(["Mode", self.data.metadata.mode or ""])
            writer.writerow(["Applied current (A)", self.format_optional_value(self.data.display_current_a)])
            writer.writerow(["Applied potential (V)", self.format_optional_value(self.data.metadata.applied_potential_v)])
            writer.writerow(["Time (s)", "" if self.data.metadata.duration_s is None else f"{self.data.metadata.duration_s:g}"])
            writer.writerow(["Reference electrode potential (V vs. RHE)", self.format_optional_value(rhe_offset)])
            writer.writerow(["Working area (cm^2)", self.format_optional_value(working_area)])
            writer.writerow(["Applied current density (mA/cm^2)", self.format_optional_value(self.get_current_density(working_area))])
            if ir_compensation is None:
                writer.writerow(["Solution resistance (ohm)", "", "Compensation level (%)", ""])
            else:
                resistance, compensation_fraction = ir_compensation
                writer.writerow(
                    ["Solution resistance (ohm)", f"{resistance:g}", "Compensation level (%)", f"{compensation_fraction * 100:g}"]
                )
            writer.writerow([])
            if self.data.is_amperometric:
                output_label = "Current density (mA/cm^2)" if working_area is not None else "Current (A)"
                writer.writerow(["Time (sec)", "Original Current (A)", output_label])
            else:
                writer.writerow(["Time (sec)", "Original Potential (V)", self.get_potential_axis_label()])
            writer.writerows(zip(self.data.times_sec, self.data.values, adjusted_potentials))
        self.status.set(f"Exported data to {output.name}")

    def refresh_summary(self) -> None:
        if self.data is None:
            self.summary.set("No file loaded.")
            self.current_density_text.set("")
            return

        lines = [summarize_durability_data(self.data)]
        try:
            working_area = self.get_working_area()
        except ValueError:
            working_area = None
        current_density = self.get_current_density(working_area)
        if current_density is not None:
            self.current_density_text.set(f"j = {current_density:g} mA/cm^2")
            lines.extend(["", f"Current density: {current_density:g} mA/cm^2"])
        else:
            if self.data.is_amperometric and working_area is not None:
                self.current_density_text.set("Plotting mA/cm^2")
            else:
                self.current_density_text.set("")
        self.summary.set("\n".join(lines))

    def on_transform_change(self, _event: tk.Event) -> None:
        self.refresh_summary()
        self.redraw()

    def clear_rhe_offset(self) -> None:
        self.rhe_offset.set("")
        self.redraw()

    def clear_working_area(self) -> None:
        self.working_area.set("")
        self.refresh_summary()
        self.redraw()

    def clear_ir_compensation(self) -> None:
        self.solution_resistance.set("")
        self.compensation_level.set("")
        self.redraw()

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

    def get_current_density(self, working_area: float | None) -> float | None:
        if self.data is None or self.data.display_current_a is None or working_area is None:
            return None
        return self.data.display_current_a * 1000 / working_area

    def get_adjusted_potentials(
        self,
        rhe_offset: float | None,
        ir_compensation: tuple[float, float] | None,
    ) -> list[float]:
        if self.data is None:
            return []

        if self.data.is_amperometric:
            if working_area := self._valid_working_area_or_none():
                return [current * 1000 / working_area for current in self.data.currents_a]
            return self.data.currents_a

        adjusted = self.data.potentials_v
        if rhe_offset is not None:
            adjusted = [potential + rhe_offset for potential in adjusted]
        if ir_compensation is not None and self.data.display_current_a is not None:
            resistance, compensation_fraction = ir_compensation
            correction = self.data.display_current_a * resistance * compensation_fraction
            adjusted = [potential - correction for potential in adjusted]
        return adjusted

    def _valid_working_area_or_none(self) -> float | None:
        try:
            return self.get_working_area()
        except ValueError:
            return None

    def get_value_axis_label(self) -> str:
        if self.data is not None and self.data.is_amperometric:
            return "Current density / mA cm$^{-2}$" if self._valid_working_area_or_none() is not None else "Current / A"
        return self.get_potential_axis_label()

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

    def format_optional_value(self, value: float | None) -> str:
        if value is None:
            return ""
        return f"{value:g}"

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

        rhe_offset, _working_area, ir_compensation, setting_errors = self.get_plot_settings()
        y_range_error = None
        try:
            y_range = self.get_y_range()
        except ValueError as exc:
            y_range = None
            y_range_error = str(exc)

        self.ax.clear()
        adjusted_potentials = self.get_adjusted_potentials(rhe_offset, ir_compensation)
        self.ax.plot(self.data.times_sec, adjusted_potentials, color=ACCENT, linewidth=1.5)
        self.ax.set_xlabel("Time / s")
        self.ax.set_ylabel(self.get_value_axis_label())
        self.ax.set_title(self.data.source.stem)
        if y_range is not None:
            self.ax.set_ylim(*y_range)
        self.ax.grid(self.show_grid.get(), alpha=0.3)
        if setting_errors:
            self.status.set(setting_errors[0])
        elif y_range_error is not None:
            self.status.set(y_range_error)
        elif self.data is not None:
            self.status.set(f"Loaded {self.data.source.name}")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_empty_plot(self) -> None:
        self.ax.clear()
        self.ax.set_title("Durability")
        self.ax.set_xlabel("Time / s")
        self.ax.set_ylabel("Potential / V")
        self.ax.grid(True, alpha=0.3)
        self.ax.text(
            0.5,
            0.5,
            "Open a durability text file",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color=MUTED,
        )
        self.figure.tight_layout()
        self.canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    root.title("Durability")
    root.geometry("1100x720")
    app = DurabilityPlotApp(root, on_return=root.destroy)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
