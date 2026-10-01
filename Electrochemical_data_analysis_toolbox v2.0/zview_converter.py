from __future__ import annotations

import csv
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from plot_eis_txt import read_eis_data
from scrollable_sidebar import ScrollableSidebar


def read_zview_rows(source: str | Path) -> list[tuple[float, float, float]]:
    """Read and validate the same raw values used for preview and export."""
    data = read_eis_data(source)
    rows = list(zip(data.frequency_hz, data.z_real_ohm, data.z_imag_ohm))
    if any(not all(math.isfinite(value) for value in row) or row[0] <= 0 for row in rows):
        raise ValueError("EIS data must contain finite values and positive frequencies.")
    return rows


def convert_eis_to_zview(source: str | Path, output_folder: str | Path | None = None) -> Path:
    """Export raw CHI EIS values to the selected folder (default: source folder)."""
    source = Path(source)
    rows = read_zview_rows(source)
    folder = Path(output_folder) if output_folder is not None else source.parent
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{source.stem}_ZView.txt"
    # Exclusive creation protects any previously exported data.
    with destination.open("x", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerows(rows)
    return destination


class ZViewConverterPage(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.selected_files: list[Path] = []
        self.output_folder = tk.StringVar()
        self.preview_status = tk.StringVar(value="Select a file to preview its output values.")
        self.status = tk.StringVar(value="Choose one or more CHI EIS .txt files.")
        style = ttk.Style(self)
        style.configure("ZView.Title.TLabel", background="#ffffff", foreground="#17202a", font=("Segoe UI", 16, "bold"))
        style.configure("ZView.Muted.TLabel", background="#ffffff", foreground="#667085", font=("Segoe UI", 9))
        style.configure("ZView.TButton", font=("Segoe UI", 10), padding=(12, 6))
        style.configure("ZView.Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.map("ZView.Accent.TButton", foreground=[("!disabled", "#ffffff")],
                  background=[("active", "#14532d"), ("!disabled", "#166534")])
        style.configure("ZView.TLabelframe", background="#ffffff")
        style.configure("ZView.TLabelframe.Label", background="#ffffff", foreground="#17202a", font=("Segoe UI", 10, "bold"))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.sidebar = ScrollableSidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar = self.sidebar.content
        sidebar.columnconfigure(0, weight=1)
        ttk.Label(sidebar, text="EIS to ZView", style="ZView.Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(sidebar, text="Return", style="ZView.TButton", command=on_return).grid(row=0, column=1, padx=(12, 0), sticky="e")
        ttk.Label(sidebar, text="Convert CHI EIS text files.", style="ZView.Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))
        actions = ttk.Frame(sidebar, style="Panel.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="Choose EIS files", style="ZView.Accent.TButton", command=self.choose_files).grid(row=0, column=0, sticky="ew")
        ttk.Button(actions, text="Convert to ZView", style="ZView.TButton", command=self.convert_selected).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="Clear", style="ZView.TButton", command=self.clear_files).grid(row=2, column=0, sticky="ew", pady=(8, 0))

        files = ttk.LabelFrame(sidebar, text="Selected files", style="ZView.TLabelframe", padding=8)
        files.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        files.columnconfigure(0, weight=1)
        self.file_list = tk.Listbox(files, width=28, height=8, exportselection=False)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(files, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(files, orient="horizontal", command=self.file_list.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.file_list.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
        self.file_list.bind("<<ListboxSelect>>", self.preview_selected)

        target = ttk.LabelFrame(sidebar, text="Target folder", style="ZView.TLabelframe", padding=10)
        target.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        target.columnconfigure(0, weight=1)
        ttk.Entry(target, textvariable=self.output_folder, width=26).grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Button(target, text="Browse…", style="ZView.TButton", command=self.choose_output).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Button(target, text="Use source folders", style="ZView.TButton", command=lambda: self.output_folder.set("")).grid(row=1, column=1, sticky="e", pady=(8, 0), padx=(6, 0))
        ttk.Label(target, text="Blank = save beside each source.", style="ZView.Muted.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(sidebar, text="Frequency (Hz), Z′ (ohm), Z″ (ohm)\nTab-separated, without a header.\nOutput: <name>_ZView.txt\nExisting exports are skipped.", style="ZView.Muted.TLabel", wraplength=290).grid(row=5, column=0, columnspan=2, sticky="w")
        ttk.Label(sidebar, textvariable=self.status, style="ZView.Muted.TLabel", wraplength=290).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self.sidebar.enable_mousewheel()
        # Keep the file list's own wheel scrolling when the sidebar is scrollable.
        self.file_list.unbind("<MouseWheel>")
        self.file_list.unbind("<Button-4>")
        self.file_list.unbind("<Button-5>")

        preview_area = ttk.Frame(self, padding=(14, 14, 14, 10))
        preview_area.grid(row=0, column=1, sticky="nsew")
        preview_area.columnconfigure(0, weight=1)
        preview_area.rowconfigure(0, weight=1)
        preview_frame = ttk.Frame(preview_area, style="Panel.TFrame", padding=14)
        preview_frame.grid(row=0, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        ttk.Label(preview_frame, text="Output preview", style="ZView.Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.preview = ttk.Treeview(preview_frame, columns=("frequency", "real", "imag"), show="headings", height=7)
        for column, title in zip(("frequency", "real", "imag"), ("Frequency (Hz)", "Z′ (ohm)", "Z″ (ohm)")):
            self.preview.heading(column, text=title)
            self.preview.column(column, width=150, minwidth=100, anchor="e")
        self.preview.grid(row=1, column=0, sticky="nsew")
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        preview_scrollbar.grid(row=1, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scrollbar.set)
        preview_note = ttk.Label(preview_frame, textvariable=self.preview_status, style="ZView.Muted.TLabel", wraplength=500)
        preview_note.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        preview_note.bind("<Configure>", lambda event: preview_note.configure(wraplength=max(100, event.width)))

    def clear_files(self) -> None:
        self.selected_files.clear()
        self.file_list.delete(0, tk.END)
        self.preview_selected()
        self.status.set("Choose one or more CHI EIS .txt files.")

    def choose_files(self) -> None:
        selected = filedialog.askopenfilenames(
            parent=self, title="Choose CHI EIS files", filetypes=[("EIS text files", "*.txt"), ("All files", "*.*")]
        )
        if selected:
            self.selected_files = [Path(path) for path in selected]
            self.file_list.delete(0, tk.END)
            for path in self.selected_files:
                self.file_list.insert(tk.END, path.name)
            self.status.set(f"Selected {len(self.selected_files)} file(s).")
            self.file_list.selection_set(0)
            self.preview_selected()

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(parent=self, title="Choose target folder")
        if selected:
            self.output_folder.set(selected)

    def preview_selected(self, _event=None) -> None:
        self.preview.delete(*self.preview.get_children())
        selection = self.file_list.curselection()
        if not selection:
            self.preview_status.set("Select a file to preview its output values.")
            return
        source = self.selected_files[selection[0]]
        try:
            rows = read_zview_rows(source)
        except (OSError, ValueError) as exc:
            self.preview_status.set(f"Cannot preview {source.name}: {exc}")
            return
        for row in rows[:500]:
            self.preview.insert("", "end", values=tuple(str(value) for value in row))
        self.preview_status.set(
            f"{source.name}: showing {min(len(rows), 500)} of {len(rows)} rows. "
            "All rows are exported; column headings are preview-only."
        )

    def convert_selected(self) -> None:
        if not self.selected_files:
            messagebox.showerror("No EIS files selected", "Choose one or more EIS files first.", parent=self)
            return
        created = 0
        output_text = self.output_folder.get().strip()
        output_folder = Path(output_text).expanduser() if output_text else None
        failures: list[str] = []
        for source in self.selected_files:
            try:
                convert_eis_to_zview(source, output_folder)
                created += 1
            except FileExistsError:
                failures.append(f"{source.name}: the _ZView.txt output already exists; skipped.")
            except (OSError, ValueError) as exc:
                failures.append(f"{source.name}: {exc}")
        location = f"in {output_folder}" if output_folder is not None else "beside the source files"
        summary = f"Created {created} ZView file(s) {location}."
        if failures:
            summary += f" Could not convert {len(failures)} file(s)."
        self.status.set(summary)
        if failures:
            messagebox.showwarning("ZView conversion", summary + "\n\n" + "\n".join(failures), parent=self)
        else:
            messagebox.showinfo("ZView conversion complete", summary, parent=self)
