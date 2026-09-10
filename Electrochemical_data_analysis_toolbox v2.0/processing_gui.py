from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from origin_csv import ProcessingSettings, infer_solution_resistance, infer_working_area, process_files, process_sample_folder


class DataProcessingPage(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master, style="Panel.TFrame", padding=24)
        self.on_return = on_return
        self.selected_files: list[Path] = []
        self.sample_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.working_area = tk.StringVar()
        self.reference_potential = tk.StringVar(value="0.929")
        self.equilibrium_potential = tk.StringVar(value="1.23")
        self.solution_resistance = tk.StringVar()
        self.compensation = tk.StringVar(value="0")
        self.ecsa_cycle = tk.StringVar()
        self.cp_solution_resistance = tk.StringVar()
        self.cp_compensation = tk.StringVar(value="0")
        self.status = tk.StringVar(value="Choose a sample folder or one or more CHI .txt files.")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Origin-ready CSV processor", style="HomeTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            self,
            text="Process an entire sample folder or selected measurements using the same CSV layouts as the reference Processed folder.",
            style="HomeSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 18))

        settings = ttk.LabelFrame(self, text="Sample and correction settings", padding=12)
        settings.grid(row=2, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)
        fields = [
            ("Sample folder", self.sample_folder),
            ("Output folder", self.output_folder),
            ("Working area (cm²)", self.working_area),
            ("Reference potential (V vs. RHE)", self.reference_potential),
            ("Water-splitting equilibrium potential (V)", self.equilibrium_potential),
            ("LSV resistance (ohm; blank = filename)", self.solution_resistance),
            ("LSV compensation level (%)", self.compensation),
            ("CP solution resistance (ohm)", self.cp_solution_resistance),
            ("CP compensation level (%)", self.cp_compensation),
            ("ECSA cycle number (blank = last)", self.ecsa_cycle),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(settings, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=3)
            ttk.Entry(settings, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=3)
        ttk.Button(settings, text="Browse sample folder", command=self.choose_folder).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(settings, text="Browse output", command=self.choose_output).grid(row=1, column=2, padx=(8, 0))

        files_frame = ttk.LabelFrame(self, text="Individual measurement selection", padding=12)
        files_frame.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(files_frame, height=8)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scrollbar.set)
        ttk.Button(files_frame, text="Choose .txt files", command=self.choose_files).grid(row=1, column=0, sticky="w", pady=(8, 0))

        actions = ttk.Frame(self, style="Panel.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="Process sample folder", command=self.process_folder).pack(side="left")
        ttk.Button(actions, text="Process selected files", command=self.process_selected).pack(side="left", padx=8)
        ttk.Button(actions, text="Return", command=self.on_return).pack(side="right")
        ttk.Label(self, textvariable=self.status, style="HomeMuted.TLabel", wraplength=1100).grid(row=5, column=0, sticky="ew", pady=(12, 0))

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose sample folder")
        if not selected:
            return
        folder = Path(selected)
        self.sample_folder.set(str(folder))
        self.output_folder.set(str(folder / "Processed"))
        area = infer_working_area(folder)
        if area is not None:
            self.working_area.set(f"{area:g}")
        lsv_files = list(folder.glob("*LSV*.txt")) + list(folder.glob("*LCV*.txt"))
        if lsv_files and not self.solution_resistance.get().strip():
            resistance = infer_solution_resistance(lsv_files[0])
            if resistance is not None:
                self.solution_resistance.set(f"{resistance:g}")
                if not self.cp_solution_resistance.get().strip():
                    self.cp_solution_resistance.set(f"{resistance:g}")
        self.status.set(f"Loaded sample folder: {folder.name}")

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if selected:
            self.output_folder.set(selected)

    def choose_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Choose CHI text files", filetypes=[("CHI text files", "*.txt"), ("All files", "*.*")])
        if not selected:
            return
        self.selected_files = [Path(path) for path in selected]
        self.file_list.delete(0, tk.END)
        for path in self.selected_files:
            self.file_list.insert(tk.END, str(path))
        if not self.output_folder.get().strip():
            self.output_folder.set(str(self.selected_files[0].parent / "Processed"))
        if not self.working_area.get().strip():
            area = infer_working_area(self.selected_files[0].parent)
            if area is not None:
                self.working_area.set(f"{area:g}")
        self.status.set(f"Selected {len(self.selected_files)} file(s).")

    def _settings(self) -> ProcessingSettings:
        raw_resistance = self.solution_resistance.get().strip()
        raw_cycle = self.ecsa_cycle.get().strip()
        raw_cp_resistance = self.cp_solution_resistance.get().strip()
        return ProcessingSettings(
            working_area_cm2=float(self.working_area.get()),
            reference_potential_v=float(self.reference_potential.get()),
            equilibrium_potential_v=float(self.equilibrium_potential.get()),
            solution_resistance_ohm=float(raw_resistance) if raw_resistance else None,
            compensation_percent=float(self.compensation.get()),
            ecsa_cycle_number=int(raw_cycle) if raw_cycle else None,
            cp_solution_resistance_ohm=float(raw_cp_resistance) if raw_cp_resistance else None,
            cp_compensation_percent=float(self.cp_compensation.get()),
        )

    def _show_report(self, report) -> None:
        message = f"Created {len(report.created)} CSV file(s)."
        if report.skipped:
            message += f" Skipped {len(report.skipped)} file(s)."
        if report.failures:
            message += f" Failed {len(report.failures)} file(s)."
        self.status.set(message)
        if report.failures:
            messagebox.showwarning("Processing completed with errors", message + "\n\n" + "\n".join(report.failures))
        else:
            messagebox.showinfo("Processing complete", message)

    @staticmethod
    def _confirm_output(output: Path) -> bool:
        if not output.is_dir() or not any(output.glob("*.csv")):
            return True
        return messagebox.askyesno(
            "Existing CSV files",
            "The output folder already contains CSV files. Continue and replace files with matching names?",
        )

    def process_folder(self) -> None:
        try:
            folder = Path(self.sample_folder.get().strip())
            if not folder.is_dir():
                raise ValueError("Choose a valid sample folder.")
            output = Path(self.output_folder.get().strip()) if self.output_folder.get().strip() else folder / "Processed"
            if not self._confirm_output(output):
                self.status.set("Processing cancelled; existing files were not changed.")
                return
            self._show_report(process_sample_folder(folder, self._settings(), output))
        except Exception as exc:
            messagebox.showerror("Could not process folder", str(exc))
            self.status.set(str(exc))

    def process_selected(self) -> None:
        try:
            if not self.selected_files:
                raise ValueError("Choose one or more .txt files first.")
            output_text = self.output_folder.get().strip()
            output = Path(output_text) if output_text else self.selected_files[0].parent / "Processed"
            if not self._confirm_output(output):
                self.status.set("Processing cancelled; existing files were not changed.")
                return
            self._show_report(process_files(self.selected_files, output, self._settings()))
        except Exception as exc:
            messagebox.showerror("Could not process files", str(exc))
            self.status.set(str(exc))
