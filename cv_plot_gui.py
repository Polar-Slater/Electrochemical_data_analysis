from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plot_cv_txt import read_cv_data, summarize_cv_data


BG = "#f7f8fa"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#637083"
ACCENT = "#1f6feb"


class CVPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.files: list[Path] = []
        self.status = tk.StringVar(value="Choose one or more CV text files.")
        self.reference_potential = tk.StringVar(value="Reference electrode potential: -- V")
        self.show_grid = tk.BooleanVar(value=True)
        self.legend_enabled = tk.BooleanVar(value=True)

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

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, style="Panel.TFrame", padding=18)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.rowconfigure(3, weight=1)
        sidebar.rowconfigure(5, weight=1)

        ttk.Label(sidebar, text="Reference electrode potential", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
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

        list_frame = ttk.Frame(sidebar, style="Panel.TFrame")
        list_frame.grid(row=3, column=0, sticky="nsew", pady=(6, 12))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.file_list = tk.Listbox(
            list_frame,
            width=36,
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
            row=1, column=0, sticky="w"
        )

        reference_frame = ttk.Frame(sidebar, style="Panel.TFrame", padding=10)
        reference_frame.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(
            reference_frame,
            textvariable=self.reference_potential,
            style="Panel.TLabel",
            wraplength=280,
        ).grid(row=0, column=0, sticky="w")

        results_frame = ttk.Frame(sidebar, style="Panel.TFrame")
        results_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 12))
        results_frame.rowconfigure(1, weight=1)
        results_frame.columnconfigure(0, weight=1)
        ttk.Label(results_frame, text="Analysis", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.results_text = tk.Text(
            results_frame,
            width=36,
            height=10,
            bg="#ffffff",
            fg=TEXT,
            highlightthickness=1,
            highlightbackground="#d7dce2",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        self.results_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.results_text.insert("1.0", "Open a CV file to calculate zero-current intersections.")
        self.results_text.configure(state="disabled")

        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=300).grid(
            row=7, column=0, sticky="ew"
        )

        plot_area = ttk.Frame(self, padding=16)
        plot_area.grid(row=0, column=1, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self._draw_empty_plot()

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(plot_area)
        toolbar_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=0, column=0, sticky="w")

    def _draw_empty_plot(self) -> None:
        self.ax.clear()
        self.ax.set_xlabel("Potential / V")
        self.ax.set_ylabel("Current / A")
        self.ax.set_title("No file selected")
        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout()

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

    def refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.files:
            self.file_list.insert(tk.END, path.name)

    def clear_files(self) -> None:
        self.files.clear()
        self.refresh_file_list()
        self.status.set("Choose one or more CV text files.")
        self.reference_potential.set("Reference electrode potential: -- V")
        self.set_results_text("Open a CV file to calculate zero-current intersections.")
        self._draw_empty_plot()
        self.canvas.draw_idle()

    def set_results_text(self, text: str) -> None:
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", text)
        self.results_text.configure(state="disabled")

    def plot_files(self) -> None:
        if not self.files:
            self._draw_empty_plot()
            self.canvas.draw_idle()
            return

        self.ax.clear()
        loaded = 0
        failures: list[str] = []
        summaries: list[str] = []
        reference_values: list[float] = []

        for path in self.files:
            try:
                data = read_cv_data(path)
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
                continue

            self.ax.plot(data.potentials, data.currents, linewidth=1.4, label=path.stem)
            if data.zero_crossings:
                self.ax.scatter(
                    [crossing.potential for crossing in data.zero_crossings],
                    [0 for _ in data.zero_crossings],
                    s=28,
                    zorder=3,
                )
            if data.reference_electrode_potential is not None:
                reference_values.append(data.reference_electrode_potential)
            summaries.append(f"{path.name}\n{summarize_cv_data(data)}")
            loaded += 1

        self.ax.set_xlabel("Potential / V")
        self.ax.set_ylabel("Current / A")
        self.ax.set_title("Cyclic Voltammetry")
        self.ax.grid(self.show_grid.get(), alpha=0.3)

        if self.legend_enabled.get() and loaded:
            self.ax.legend(loc="best", fontsize=8)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.set_results_text("\n\n".join(summaries) if summaries else "No readable CV data.")
        if len(reference_values) == 1:
            self.reference_potential.set(f"Reference electrode potential: {reference_values[0]:.6g} V")
        elif len(reference_values) > 1:
            average_reference = sum(reference_values) / len(reference_values)
            self.reference_potential.set(
                f"Reference electrode potential: {average_reference:.6g} V avg ({len(reference_values)} files)"
            )
        else:
            self.reference_potential.set("Reference electrode potential: -- V")

        if failures:
            self.status.set(f"Plotted {loaded} file(s). {len(failures)} file(s) could not be read.")
            messagebox.showwarning("Some files could not be read", "\n\n".join(failures))
        else:
            self.status.set(f"Plotted {loaded} file(s).")

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
    app = CVPlotApp()
    app.mainloop()


if __name__ == "__main__":
    main()


