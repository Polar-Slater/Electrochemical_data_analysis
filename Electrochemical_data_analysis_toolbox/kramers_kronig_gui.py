"""Single-window toolbox page for EIS Kramers--Kronig validation."""

from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from kramers_kronig_relations import EISData, KKResult, linear_kk, load_eis


PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#667085"
ACCENT = "#166534"


class KKPlotApp(ttk.Frame):
    """Kramers--Kronig validator embedded in the toolbox window."""

    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return
        self.data: EISData | None = None
        self.result: KKResult | None = None
        self.file_text = tk.StringVar(value="No spectrum loaded")
        self.status_text = tk.StringVar(value="Load an EIS data file to begin.")
        self.result_text = tk.StringVar(value="Run the KK test to calculate χ².")
        self.verdict_text = tk.StringVar(value="No results yet")
        self.max_rc = tk.IntVar(value=40)
        self.mu_threshold = tk.DoubleVar(value=0.85)
        self.include_capacitance = tk.BooleanVar(value=True)
        self._configure_styles()
        self._build_layout()
        self._draw_empty()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f7f9")
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background="#f6f7f9", foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 6))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.map("Accent.TButton", foreground=[("active", "#ffffff"), ("!disabled", "#ffffff")])
        style.map("Accent.TButton", background=[("active", "#14532d"), ("!disabled", ACCENT)])
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
        sidebar.rowconfigure(7, weight=1)

        ttk.Label(sidebar, text="Kramers–Kronig Validator", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(sidebar, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(
            sidebar,
            text="Linear K–K consistency screening for EIS spectra.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Open EIS data", style="Accent.TButton", command=self.load_file).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(buttons, textvariable=self.file_text, style="Muted.TLabel", wraplength=285).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

        options = ttk.LabelFrame(sidebar, text="Test settings", padding=10)
        options.grid(row=4, column=0, columnspan=2, sticky="ew")
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="Maximum RC elements", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(options, from_=2, to=100, width=7, textvariable=self.max_rc).grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(options, text="μ cutoff", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(options, width=9, textvariable=self.mu_threshold).grid(row=1, column=1, sticky="e", pady=(8, 0))
        ttk.Checkbutton(options, text="Include series capacitance", variable=self.include_capacitance).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        self.run_button = ttk.Button(sidebar, text="Run KK test", command=self.run_test, state=tk.DISABLED)
        self.run_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self.export_button = ttk.Button(sidebar, text="Export results", command=self.export_results, state=tk.DISABLED)
        self.export_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        result_box = ttk.Frame(sidebar, style="Panel.TFrame")
        result_box.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
        ttk.Label(result_box, text="Results", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(result_box, textvariable=self.verdict_text, style="Section.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(result_box, textvariable=self.result_text, style="Panel.TLabel", wraplength=285, justify="left").grid(
            row=2, column=0, sticky="nw", pady=(6, 0)
        )
        ttk.Label(sidebar, textvariable=self.status_text, style="Muted.TLabel", wraplength=285).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(14, 0)
        )

        plot_area = ttk.Frame(self, padding=(12, 12, 12, 8))
        plot_area.grid(row=0, column=1, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)
        self.figure = Figure(figsize=(10, 7), dpi=100, constrained_layout=True)
        grid = self.figure.add_gridspec(3, 2)
        self.ax_nyquist = self.figure.add_subplot(grid[0, 0])
        self.ax_bode = self.figure.add_subplot(grid[0, 1])
        self.ax_real = self.figure.add_subplot(grid[1, 0])
        self.ax_imaginary = self.figure.add_subplot(grid[1, 1])
        self.ax_phase = self.figure.add_subplot(grid[2, 0])
        self.ax_residual = self.figure.add_subplot(grid[2, 1])
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar = NavigationToolbar2Tk(self.canvas, plot_area, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    def _axes(self) -> tuple:
        return (
            self.ax_nyquist,
            self.ax_bode,
            self.ax_real,
            self.ax_imaginary,
            self.ax_phase,
            self.ax_residual,
        )

    def _draw_empty(self) -> None:
        for axis in self._axes():
            axis.clear()
            axis.grid(True, alpha=0.25)
        self._label_axes()
        self.ax_nyquist.text(
            0.5,
            0.5,
            "Open an EIS spectrum",
            transform=self.ax_nyquist.transAxes,
            ha="center",
            va="center",
            color=MUTED,
        )
        self.canvas.draw_idle()

    def _label_axes(self) -> None:
        self.ax_nyquist.set(title="Nyquist", xlabel="Z′ / Ω", ylabel="−Z″ / Ω")
        self.ax_bode.set(title="Bode magnitude", xlabel="Frequency / Hz", ylabel="|Z| / Ω")
        self.ax_real.set(title="Real impedance", xlabel="Frequency / Hz", ylabel="Z′ / Ω")
        self.ax_imaginary.set(title="Imaginary impedance", xlabel="Frequency / Hz", ylabel="−Z″ / Ω")
        self.ax_phase.set(title="Phase", xlabel="Frequency / Hz", ylabel="Phase / °")
        self.ax_residual.set(title="Normalized residuals", xlabel="Frequency / Hz", ylabel="Residual / %")

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open EIS spectrum",
            filetypes=[("EIS data", "*.txt *.csv *.tsv *.dta"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.data = load_eis(path)
        except Exception as exc:
            messagebox.showerror("Could not read EIS data", str(exc), parent=self)
            self.status_text.set("Failed to load the selected spectrum.")
            return

        self.result = None
        self.verdict_text.set("No results yet")
        self.result_text.set("Run the KK test to calculate χ².")
        self.file_text.set(f"{Path(path).name}  •  {self.data.frequency.size} points")
        self.status_text.set(
            f"Loaded {self.data.frequency.min():.4g}–{self.data.frequency.max():.4g} Hz. Ready to test."
        )
        self.run_button.configure(state=tk.NORMAL)
        self.export_button.configure(state=tk.DISABLED)
        self._plot()

    def run_test(self) -> None:
        if self.data is None:
            return
        try:
            result = linear_kk(
                self.data.frequency,
                self.data.impedance,
                max_rc=self.max_rc.get(),
                mu_threshold=self.mu_threshold.get(),
                include_capacitance=self.include_capacitance.get(),
            )
        except Exception as exc:
            messagebox.showerror("KK test failed", str(exc), parent=self)
            self.status_text.set("The KK test could not be completed.")
            return

        self.result = result
        verdict = "Consistent" if result.rms_residual_pct <= 5.0 else "Review recommended"
        self.verdict_text.set(verdict)
        self.result_text.set(
            f"χ²: {result.chi_squared:.3e}\n"
            f"RMS residual: {result.rms_residual_pct:.2f}%\n"
            f"Maximum residual: {result.max_residual_pct:.2f}%\n"
            f"RC elements: {result.rc_count}\n"
            f"μ: {result.mu:.3f}"
        )
        self.status_text.set("KK analysis complete. The 5% RMS threshold is a practical screening guide.")
        self.export_button.configure(state=tk.NORMAL)
        self._plot()

    def _plot(self) -> None:
        if self.data is None:
            self._draw_empty()
            return
        frequency = self.data.frequency
        impedance = self.data.impedance
        for axis in self._axes():
            axis.clear()
            axis.grid(True, which="both", alpha=0.25)

        self.ax_nyquist.plot(impedance.real, -impedance.imag, "o", ms=4, label="Measured")
        self.ax_bode.loglog(frequency, np.abs(impedance), "o", ms=4, label="Measured")
        self.ax_real.semilogx(frequency, impedance.real, "o", ms=4, label="Measured")
        self.ax_imaginary.semilogx(frequency, -impedance.imag, "o", ms=4, label="Measured")
        self.ax_phase.semilogx(frequency, np.angle(impedance, deg=True), "o", ms=4, label="Measured")

        if self.result is not None:
            fitted = self.result.fitted
            self.ax_nyquist.plot(fitted.real, -fitted.imag, "-", lw=1.6, label="KK fit")
            self.ax_bode.loglog(frequency, np.abs(fitted), "-", lw=1.6, label="KK fit")
            self.ax_real.semilogx(frequency, fitted.real, "-", lw=1.6, label="KK fit")
            self.ax_imaginary.semilogx(frequency, -fitted.imag, "-", lw=1.6, label="KK fit")
            self.ax_phase.semilogx(frequency, np.angle(fitted, deg=True), "-", lw=1.6, label="KK fit")
            self.ax_residual.semilogx(
                frequency, self.result.residual_real_pct, "o-", ms=3, label="Real"
            )
            self.ax_residual.semilogx(
                frequency, self.result.residual_imag_pct, "o-", ms=3, label="Imaginary"
            )
            self.ax_residual.axhline(0, color="black", lw=0.8)
            self.ax_residual.legend()

        self._label_axes()
        self.ax_nyquist.axis("equal")
        for axis in (self.ax_nyquist, self.ax_bode, self.ax_real, self.ax_imaginary, self.ax_phase):
            axis.legend()
        self.canvas.draw_idle()

    def export_results(self) -> None:
        if self.result is None:
            return
        initialfile = "kk_results.csv"
        if self.data is not None:
            initialfile = f"{self.data.source.stem}_kk_results.csv"
        path = filedialog.asksaveasfilename(
            title="Export KK results",
            defaultextension=".csv",
            initialfile=initialfile,
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(
                    [
                        "frequency_hz",
                        "z_real_ohm",
                        "z_imag_ohm",
                        "phase_deg",
                        "kk_real_ohm",
                        "kk_imag_ohm",
                        "kk_phase_deg",
                        "residual_real_pct",
                        "residual_imag_pct",
                    ]
                )
                writer.writerows(
                    zip(
                        self.result.frequency,
                        self.result.measured.real,
                        self.result.measured.imag,
                        np.angle(self.result.measured, deg=True),
                        self.result.fitted.real,
                        self.result.fitted.imag,
                        np.angle(self.result.fitted, deg=True),
                        self.result.residual_real_pct,
                        self.result.residual_imag_pct,
                    )
                )
        except OSError as exc:
            messagebox.showerror("Could not export results", str(exc), parent=self)
            return
        self.status_text.set(f"Exported results to {Path(path).name}")
