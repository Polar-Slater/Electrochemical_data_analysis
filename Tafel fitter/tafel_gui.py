"""Standalone Tk GUI; TafelApp can later be hosted in the project toolbox."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from tafel_core import FitCancelled, FitSettings, fit, validate
from tafel_io import Preparation, prepare, read_datasets
from tafel_output import draw, export_bundle
from tafel_version import __version__


class TafelApp(ttk.Frame):
    def __init__(self, master, on_return=None):
        super().__init__(master, padding=10)
        self.datasets = []
        self.result = None
        self.snapshot = None
        self.busy = False
        self.messages = queue.Queue()
        self.cancel_event = threading.Event()
        self.status = tk.StringVar(value="Open a CHI LSV .txt or toolbox .csv file to begin.")
        self.info = tk.StringVar(value="No dataset selected")
        self.values = {}
        self.entries = {}
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f7f8fa")
        style.configure("TLabel", background="#f7f8fa", foreground="#17202a", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(9, 5))
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        title = ttk.Frame(self)
        title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(title, text=f"Tafel fitter v{__version__}", style="Title.TLabel").pack(side="left")
        ttk.Label(title, text="   Automatic region selection · standalone workspace").pack(side="left")
        ttk.Button(title, text="Credits", command=self.show_credits).pack(side="right")
        if on_return:
            ttk.Button(title, text="Return", command=on_return).pack(side="right")
        sidebar = ttk.Frame(self, padding=(0, 0, 12, 0))
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(3, weight=1)
        self.open_button = ttk.Button(sidebar, text="Open LSV / Tafel files…", command=self.open_files)
        self.open_button.grid(row=0, column=0, sticky="ew")
        self.selector = ttk.Combobox(sidebar, state="readonly", width=45)
        self.selector.grid(row=1, column=0, sticky="ew", pady=8)
        self.selector.bind("<<ComboboxSelected>>", self.select_dataset)
        ttk.Label(sidebar, textvariable=self.info, wraplength=350).grid(row=2, column=0, sticky="ew", pady=(0, 8))
        # Scroll settings independently so action buttons remain reachable on
        # small screens and at Windows display scaling above 100 percent.
        settings_frame = ttk.Frame(sidebar)
        settings_frame.grid(row=3, column=0, sticky="nsew")
        settings_frame.rowconfigure(0, weight=1)
        settings_frame.columnconfigure(0, weight=1)
        settings_canvas = tk.Canvas(settings_frame, width=405, height=400,
                                    highlightthickness=0, background="#f7f8fa")
        settings_canvas.grid(row=0, column=0, sticky="nsew")
        settings_scroll = ttk.Scrollbar(settings_frame, orient="vertical", command=settings_canvas.yview)
        settings_scroll.grid(row=0, column=1, sticky="ns")
        settings_canvas.configure(yscrollcommand=settings_scroll.set)
        tabs = ttk.Notebook(settings_canvas)
        tabs_window = settings_canvas.create_window((0, 0), window=tabs, anchor="nw")
        tabs.bind("<Configure>", lambda _: settings_canvas.configure(scrollregion=settings_canvas.bbox("all")))
        settings_canvas.bind("<Configure>", lambda event: settings_canvas.itemconfigure(tabs_window, width=event.width))
        prep_tab, fit_tab = ttk.Frame(tabs, padding=10), ttk.Frame(tabs, padding=10)
        tabs.add(prep_tab, text="Data preparation")
        tabs.add(fit_tab, text="Fitting settings")
        fields = [
            ("area", "Working area / cm²", "1"),
            ("reference", "Reference potential vs. RHE / V", "0"),
            ("equilibrium", "Equilibrium vs. RHE / V", "1.23"),
            ("resistance", "Solution resistance / ohm", "0"),
            ("compensation", "iR compensation / %", "0"),
            ("eta_min", "Minimum overpotential / V (optional)", ""),
            ("eta_max", "Maximum overpotential / V (optional)", ""),
            ("min_density", "Minimum |j| / mA cm⁻²", "0"),
        ]
        for row, (key, label, default) in enumerate(fields):
            self.field(prep_tab, row, key, label, default)
        ttk.Label(prep_tab, text="Reaction branch").grid(row=8, column=0, sticky="w", pady=4)
        self.branch = tk.StringVar(value="Anodic")
        branch = ttk.Combobox(prep_tab, textvariable=self.branch, values=["Anodic", "Cathodic"], state="readonly", width=13)
        branch.grid(row=8, column=1)
        self.branch.trace_add("write", self.invalidate)
        ttk.Label(prep_tab, text="OER: equilibrium 1.23 V; HER: 0 V.\nUse signed overpotential bounds. Check the\nreference offset before fitting raw LSV data.",
                  wraplength=345, foreground="#637083").grid(row=9, column=0, columnspan=2, sticky="w", pady=8)
        fit_fields = [
            ("width_min_mv", "Minimum window width / mV", "10"),
            ("width_max_mv", "Maximum window width / mV", "50"),
            ("width_step_mv", "Window step / mV", "1"),
            ("r2_min", "Minimum R² threshold", "0.9"),
            ("r2_max", "Maximum R² threshold", "0.999"),
            ("r2_step", "R² threshold step", "0.001"),
            ("bin_mv", "Slope bin width / mV decade⁻¹", "1"),
            ("temperature", "Temperature / K", "293"),
            ("electrons", "Effective electron number n", "1"),
            ("min_points", "Minimum points per window", "5"),
            ("polynomial_order", "Derivative polynomial order", "15"),
        ]
        for row, (key, label, default) in enumerate(fit_fields):
            self.field(fit_tab, row, key, label, default)
        self.cutoff = tk.BooleanVar(value=False)
        self.cutoff.trace_add("write", self.invalidate)
        ttk.Checkbutton(fit_tab, text="Exclude points beyond derivative maximum", variable=self.cutoff).grid(row=11, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Label(fit_tab, text="Preview the derivative before enabling cutoff.\nR² is checked for both Tafel and LSV regressions.",
                  foreground="#637083").grid(row=12, column=0, columnspan=2, sticky="w")
        actions = ttk.Frame(sidebar)
        actions.grid(row=5, column=0, sticky="ew", pady=10)
        self.preview_button = ttk.Button(actions, text="Preview", command=self.preview)
        self.preview_button.pack(side="left")
        self.fit_button = ttk.Button(actions, text="Run automatic fit", command=self.run_fit)
        self.fit_button.pack(side="left", padx=6)
        self.cancel_button = ttk.Button(actions, text="Cancel", command=self.cancel_event.set, state="disabled")
        self.cancel_button.pack(side="left")
        self.export_button = ttk.Button(sidebar, text="Export results + plots…", command=self.export, state="disabled")
        self.export_button.grid(row=6, column=0, sticky="ew")
        right = ttk.Frame(self)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.figure = Figure(figsize=(9, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar = ttk.Frame(right)
        toolbar.grid(row=1, column=0, sticky="ew")
        NavigationToolbar2Tk(self.canvas, toolbar)
        report_frame = ttk.Frame(right)
        report_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        report_frame.columnconfigure(0, weight=1)
        self.report = tk.Text(report_frame, height=7, wrap="word", font=("Segoe UI", 10), relief="flat", padx=10, pady=8)
        self.report.grid(row=0, column=0, sticky="ew")
        scroll = ttk.Scrollbar(report_frame, orient="vertical", command=self.report.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.report.configure(yscrollcommand=scroll.set)
        self.set_report("1. Open data and verify the preparation settings.\n2. Preview and choose a kinetic overpotential range.\n3. Run the fit; inspect the highlighted region and stability plot.\n4. Export the selected fit, candidate results, settings and figure.")
        self.progress = ttk.Progressbar(self, maximum=100)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 3))
        ttk.Label(self, textvariable=self.status, wraplength=1100).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Label(self, text="Adapted from MEG-LBNL Tafel_Fitter v1.51 · Method: Peter Agbo and Nemanja Danilovic (2019)",
                  foreground="#637083", font=("Segoe UI", 9)).grid(
                      row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.after(100, self.poll)

    def show_credits(self):
        dialog = tk.Toplevel(self)
        dialog.title(f"Tafel fitter v{__version__} — Credits")
        dialog.transient(self.winfo_toplevel())
        panel = ttk.Frame(dialog, padding=20)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Credits", style="Title.TLabel").pack(anchor="w", pady=(0, 12))
        credit = (
            f"Project adaptation version: {__version__}\n\n"
            "Original fitting software: Peter Agbo, MEG-LBNL Tafel_Fitter v1.51, "
            "Lawrence Berkeley National Laboratory.\n\n"
            "Fitting methodology: Peter Agbo and Nemanja Danilovic, "
            "An Algorithm for the Extraction of Tafel Slopes. "
            "J. Phys. Chem. C 2019, 123, 30252–30264.\n"
            "DOI: 10.1021/acs.jpcc.9b06820\n\n"
            "This project's adaptation adds a Python 3 GUI, project data-format support, "
            "and implementation corrections, developed with AI assistance. "
            "See the README for differences from the original implementation."
        )
        ttk.Label(panel, text=credit, wraplength=550, justify="left").pack(anchor="w")
        links = ttk.Frame(panel)
        links.pack(fill="x", pady=(16, 0))
        ttk.Button(links, text="Original project", command=lambda: webbrowser.open(
            "https://github.com/MEG-LBNL/Tafel_Fitter")).pack(side="left")
        ttk.Button(links, text="Research paper", command=lambda: webbrowser.open(
            "https://doi.org/10.1021/acs.jpcc.9b06820")).pack(side="left", padx=8)
        ttk.Button(links, text="Close", command=dialog.destroy).pack(side="right")

    def field(self, parent, row, key, label, default):
        var = tk.StringVar(value=default)
        self.values[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        entry = ttk.Entry(parent, textvariable=var, width=12)
        entry.grid(row=row, column=1, sticky="e")
        self.entries[key] = entry
        var.trace_add("write", self.invalidate)

    def invalidate(self, *_):
        self.result = None
        self.snapshot = None
        if hasattr(self, "export_button"):
            self.export_button.configure(state="disabled")
            self.status.set("Settings changed. Preview or run a new fit.")
            if not self.busy:
                self.set_report("Settings changed; previous results are no longer active. Preview or run a new fit.")
                self.figure.clear()
                self.canvas.draw_idle()

    def set_report(self, text):
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.configure(state="disabled")

    def open_files(self):
        paths = filedialog.askopenfilenames(title="Open polarization data", filetypes=[("LSV / Tafel data", "*.txt *.csv"), ("All files", "*.*")])
        if not paths:
            return
        datasets, errors = [], []
        for path in paths:
            try:
                datasets.extend(read_datasets(path))
            except Exception as exc:
                errors.append(f"{Path(path).name}: {exc}")
        if datasets:
            self.datasets = datasets
            self.selector.configure(values=[f"{d.source.name} | {d.name}" for d in datasets])
            self.selector.current(0)
            self.select_dataset()
        if errors:
            messagebox.showerror("Some files could not be loaded", "\n\n".join(errors))

    def select_dataset(self, *_):
        if self.selector.current() < 0:
            return
        data = self.datasets[self.selector.current()]
        defaults = {"area": 1, "reference": 0, "equilibrium": 1.23, "resistance": 0, "compensation": 0}
        for key, default in defaults.items():
            self.values[key].set(str(data.metadata.get(key, default)))
        for key in ("eta_min", "eta_max"):
            self.values[key].set("")
        self.branch.set("Cathodic" if float(np.median(data.current)) < 0 else "Anodic")
        for key in ("reference", "equilibrium", "resistance", "compensation"):
            self.entries[key].configure(state="disabled" if data.mode == "eta" else "normal")
        mode = "Exported overpotential: corrections are not reapplied." if data.mode == "eta" else "Raw/original E and I: correction settings apply once."
        missing = " Reference offset is not recorded; verify its value." if data.mode == "raw" and "reference" not in data.metadata else ""
        self.info.set(f"{len(data.potential)} points. {mode}{missing}")
        self.invalidate()
        self.figure.clear()
        self.canvas.draw_idle()
        self.status.set("Data loaded. Verify settings, then preview.")

    def collect(self):
        if self.selector.current() < 0:
            raise ValueError("Open and select a dataset first.")
        values = {}
        for key, var in self.values.items():
            value = var.get().strip()
            try:
                values[key] = None if key in ("eta_min", "eta_max") and not value else float(value)
            except ValueError:
                raise ValueError(f"Enter a valid number for {key.replace('_', ' ')}.") from None
        preparation = Preparation(**{key: values[key] for key in Preparation.__dataclass_fields__ if key != "branch"}, branch=self.branch.get())
        fs = {key: values[key] for key in FitSettings.__dataclass_fields__ if key != "derivative_cutoff"}
        for key in ("min_points", "polynomial_order"):
            if not float(fs[key]).is_integer():
                raise ValueError(f"{key.replace('_', ' ')} must be an integer.")
            fs[key] = int(fs[key])
        settings = FitSettings(**fs, derivative_cutoff=self.cutoff.get())
        validate(settings)
        source = self.datasets[self.selector.current()]
        data = prepare(source, preparation)
        return source, preparation, settings, data

    def preview(self):
        try:
            _, _, settings, data = self.collect()
            self.invalidate()
            draw(self.figure, data, settings)
            self.canvas.draw_idle()
            self.status.set("Preview ready. Inspect the kinetic region and derivative before fitting.")
            self.set_report("\n".join(data.notes))
        except Exception as exc:
            messagebox.showerror("Cannot preview", str(exc))

    def set_busy(self, busy):
        self.busy = busy
        for button in (self.open_button, self.preview_button, self.fit_button):
            button.configure(state="disabled" if busy else "normal")
        self.selector.configure(state="disabled" if busy else "readonly")
        self.cancel_button.configure(state="normal" if busy else "disabled")

    def run_fit(self):
        try:
            snapshot = self.collect()
        except Exception as exc:
            messagebox.showerror("Cannot fit", str(exc))
            return
        self.invalidate()
        self.set_busy(True)
        self.cancel_event.clear()
        self.progress["value"] = 0
        self.status.set("Testing fitting windows… You can cancel at any time.")
        def work():
            try:
                result = fit(snapshot[3], snapshot[2], self.cancel_event,
                             lambda fraction: self.messages.put(("progress", fraction)))
                self.messages.put(("done", (snapshot, result)))
            except Exception as exc:
                self.messages.put(("error", exc))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "progress":
                    self.progress["value"] = payload*100
                elif kind == "error":
                    self.set_busy(False)
                    self.status.set(str(payload))
                    if not isinstance(payload, FitCancelled):
                        messagebox.showerror("Fit could not complete", str(payload))
                else:
                    self.set_busy(False)
                    snapshot, result = payload
                    try:
                        current = self.collect()
                        unchanged = current[0] is snapshot[0] and current[1:3] == snapshot[1:3]
                    except Exception:
                        unchanged = False
                    if not unchanged or self.cancel_event.is_set():
                        self.status.set("Fit discarded: settings changed or cancellation requested. Run again.")
                        continue
                    self.snapshot, self.result = snapshot, result
                    source, preparation, settings, data = snapshot
                    draw(self.figure, data, settings, result)
                    self.canvas.draw_idle()
                    b = result.best
                    self.set_report(
                        f"Tafel slope: {b.slope_mv:.3f} mV/decade (magnitude {abs(b.slope_mv):.3f})\n"
                        f"i₀ = {b.i0_a:.5g} A    j₀ = {b.i0_a*1000/preparation.area:.5g} mA/cm²\n"
                        f"Selected eta: {data.eta[b.start]:.6g} to {data.eta[b.stop-1]:.6g} V; {b.stop-b.start} points\n"
                        f"Tafel R² = {b.tafel_r2:.6f}; LSV R² = {b.lsv_r2:.6f}; residual = {b.residue:.5g} A/V\n"
                        + "\n".join(result.notes))
                    self.export_button.configure(state="normal")
                    self.progress["value"] = 100
                    self.status.set(f"Fit complete: {result.candidates_tested:,} candidate windows tested for {source.name}.")
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def export(self):
        if self.result is None or self.snapshot is None:
            return
        folder = filedialog.askdirectory(title="Choose parent folder for a new results folder")
        if not folder:
            return
        try:
            source, preparation, settings, data = self.snapshot
            destination = export_bundle(Path(folder), source, preparation, settings, data, self.result, self.figure)
            self.status.set(f"Saved results to {destination}")
            messagebox.showinfo("Export complete", str(destination))
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))


def main():
    root = tk.Tk()
    root.title(f"Tafel fitter v{__version__} — standalone")
    root.geometry("1380x900")
    root.minsize(1120, 720)
    app = TafelApp(root)
    app.pack(fill="both", expand=True)
    def close():
        app.cancel_event.set()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()


if __name__ == "__main__":
    main()
