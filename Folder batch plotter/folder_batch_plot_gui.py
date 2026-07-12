from __future__ import annotations

import math
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

TOOLBOX_DIR = Path(__file__).resolve().parents[1]
if str(TOOLBOX_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLBOX_DIR))

from cv_data import CVData as ECSACVData
from cv_data import read_cv_data as read_ecsa_cv_data
from cv_data import summarize_data as summarize_ecsa_data
from plot_cv_txt import CVData as ActiveCVData
from plot_cv_txt import read_cv_data as read_active_cv_data
from plot_cv_txt import summarize_cv_data
from plot_durability_txt import DurabilityData, read_durability_data, summarize_durability_data
from plot_eis_txt import EISData, read_eis_data, summarize_eis_data
from plot_lsv_txt import LSVData, read_lsv_data, summarize_lsv_data
from plot_ocv_txt import OCVData, read_ocv_data, summarize_ocv_data


BG = "#f6f7f9"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#667085"
ACCENT = "#0f766e"
ACCENT_DARK = "#115e59"

PLOT_TYPES = ("OCV", "LSV", "EIS", "ECSA", "CP", "CV active")
MEASUREMENT_ALIASES = {
    "OCV": "OCV",
    "LCV": "LSV",
    "LSV": "LSV",
    "EIS": "EIS",
    "CP": "CP",
    "CV": "CV",
}
INSTRUMENT_MEASUREMENTS = {
    "open circuit potential": "OCV",
    "open circuit voltage": "OCV",
    "linear sweep voltammetry": "LSV",
    "cyclic voltammetry": "CV",
    "multi-current steps": "CP",
    "chronopotentiometry": "CP",
    "impedance": "EIS",
}
FILENAME_MEASUREMENT = re.compile(r"\b(OCV|LCV|LSV|EIS|CP|CV)\b", re.IGNORECASE)
ECSA_SCAN_RATE = re.compile(r"\b\d+(?:\.\d+)?\s*mV\b", re.IGNORECASE)
CV_SCAN_LABEL = re.compile(r"(?<![A-Za-z0-9])cv[\s_-]*scan\b", re.IGNORECASE)
LSV_RS_VALUE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*ohm\b", re.IGNORECASE)
TEXT_SUFFIXES = {".txt", ".csv", ".dat"}


@dataclass(frozen=True)
class FolderFile:
    path: Path
    sample: str
    measurement: str
    suffix: str

    @property
    def label(self) -> str:
        return self.path.stem

    @property
    def display_name(self) -> str:
        suffix = f" | {self.suffix}" if self.suffix else ""
        return f"{self.measurement} | {self.sample}{suffix} | {self.path.name}"


class FolderBatchPlotApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master)
        self.on_return = on_return

        self.folder: Path | None = None
        self.files: list[FolderFile] = []
        self.included_files: set[Path] = set()
        self.status = tk.StringVar(value="Import a folder containing electrochemical data files.")
        self.summary = tk.StringVar(value="No folder loaded.")
        self.plot_type = tk.StringVar(value="OCV")
        self.show_grid = tk.BooleanVar(value=True)
        self.show_legend = tk.BooleanVar(value=True)
        self.eis_plot_type = tk.StringVar(value="Nyquist")
        self.eis_frequency_scale = tk.StringVar(value="log")
        self.eis_bode_y_axis = tk.StringVar(value="Z")
        self.eis_equal_aspect = tk.BooleanVar(value=True)
        self.show_points = tk.BooleanVar(value=True)
        self.connect_points = tk.BooleanVar(value=True)
        self.current_units = tk.StringVar(value="mA")
        self.selected_cycle = tk.IntVar(value=1)
        self.working_area = tk.StringVar(value="")
        self.compensation_level = tk.StringVar(value="0")
        self.rhe_offset = tk.StringVar(value="")
        self.equilibrium_potential = tk.StringVar(value="1.23")
        self.lsv_plot_mode = tk.StringVar(value="LSV")
        self.cp_solution_resistance = tk.StringVar(value="")
        self.cp_compensation_level = tk.StringVar(value="")
        self.y_min = tk.StringVar(value="")
        self.y_max = tk.StringVar(value="")
        self.tafel_overpotential_min = tk.StringVar(value="")
        self.tafel_overpotential_max = tk.StringVar(value="")
        self.previous_plot_type = self.plot_type.get()

        self.loaded_ocv: dict[Path, OCVData] = {}
        self.loaded_lsv: dict[Path, LSVData] = {}
        self.loaded_eis: dict[Path, EISData] = {}
        self.loaded_cp: dict[Path, DurabilityData] = {}
        self.loaded_ecsa_cv: dict[Path, ECSACVData] = {}
        self.loaded_active_cv: dict[Path, ActiveCVData] = {}
        self.lsv_rs_text: tk.Text | None = None

        self._configure_styles()
        self._build_layout()
        self._draw_empty_plot("Folder batch plotter")

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

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar_container = ttk.Frame(self, style="Panel.TFrame")
        sidebar_container.grid(row=0, column=0, sticky="nsew")
        sidebar_container.columnconfigure(0, weight=1)
        sidebar_container.rowconfigure(0, weight=1)

        sidebar_canvas = tk.Canvas(
            sidebar_container,
            width=430,
            bg=PANEL,
            highlightthickness=0,
            bd=0,
        )
        sidebar_canvas.grid(row=0, column=0, sticky="nsew")
        sidebar_scrollbar = ttk.Scrollbar(sidebar_container, orient="vertical", command=sidebar_canvas.yview)
        sidebar_scrollbar.grid(row=0, column=1, sticky="ns")
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        sidebar = ttk.Frame(sidebar_canvas, style="Panel.TFrame", padding=18)
        sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")

        def update_scroll_region(_event: tk.Event) -> None:
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))

        def update_sidebar_width(event: tk.Event) -> None:
            sidebar_canvas.itemconfigure(sidebar_window, width=event.width)

        def on_sidebar_mousewheel(event: tk.Event) -> None:
            sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        sidebar.bind("<Configure>", update_scroll_region)
        sidebar_canvas.bind("<Configure>", update_sidebar_width)
        sidebar_canvas.bind_all("<MouseWheel>", on_sidebar_mousewheel)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(5, weight=2)
        sidebar.rowconfigure(12, weight=3)

        title_row = ttk.Frame(sidebar, style="Panel.TFrame")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="Folder batch plotter", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        if self.on_return is not None:
            ttk.Button(title_row, text="Return", command=self.on_return).grid(row=0, column=1, sticky="e")
        ttk.Label(
            sidebar,
            text="Reads one folder and falls back to the instrument measurement line when needed.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))

        buttons = ttk.Frame(sidebar, style="Panel.TFrame")
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text="Import folder", style="Accent.TButton", command=self.import_folder).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(buttons, text="Save plot", command=self.save_plot).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Clear", command=self.clear_folder).grid(row=2, column=0, sticky="ew", pady=(8, 0))

        plot_frame = ttk.LabelFrame(sidebar, text="Plot", padding=10)
        plot_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        plot_frame.columnconfigure((0, 1), weight=1)
        for index, plot_name in enumerate(PLOT_TYPES):
            ttk.Radiobutton(
                plot_frame,
                text=plot_name,
                value=plot_name,
                variable=self.plot_type,
                command=self.refresh_plot,
            ).grid(row=index // 2, column=index % 2, sticky="w", pady=2)

        options = ttk.Frame(sidebar, style="Panel.TFrame")
        options.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ttk.Checkbutton(options, text="Grid", variable=self.show_grid, command=self.refresh_plot).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="Legend", variable=self.show_legend, command=self.refresh_plot).grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        eis_options = ttk.LabelFrame(options, text="EIS options", padding=10)
        eis_options.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        eis_options.columnconfigure((0, 1), weight=1)
        ttk.Radiobutton(eis_options, text="Nyquist", value="Nyquist", variable=self.eis_plot_type, command=self.refresh_plot).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Radiobutton(eis_options, text="Bode", value="Bode", variable=self.eis_plot_type, command=self.refresh_plot).grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Radiobutton(eis_options, text="Freq normal", value="normal", variable=self.eis_frequency_scale, command=self.refresh_plot).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Radiobutton(eis_options, text="Freq log", value="log", variable=self.eis_frequency_scale, command=self.refresh_plot).grid(
            row=1, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Radiobutton(eis_options, text="Bode Z", value="Z", variable=self.eis_bode_y_axis, command=self.refresh_plot).grid(
            row=2, column=0, sticky="w"
        )
        ttk.Radiobutton(eis_options, text="Bode -Z''", value="-Z''", variable=self.eis_bode_y_axis, command=self.refresh_plot).grid(
            row=2, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Checkbutton(eis_options, text="Equal axes", variable=self.eis_equal_aspect, command=self.refresh_plot).grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(eis_options, text="Points", variable=self.show_points, command=self.refresh_plot).grid(row=3, column=1, sticky="w", padx=(16, 0))
        ttk.Checkbutton(eis_options, text="Connect", variable=self.connect_points, command=self.refresh_plot).grid(row=4, column=0, sticky="w")
        ttk.Label(options, text="Current", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 2))
        ttk.Radiobutton(options, text="A", value="A", variable=self.current_units, command=self.refresh_plot).grid(
            row=3, column=0, sticky="w"
        )
        ttk.Radiobutton(options, text="mA", value="mA", variable=self.current_units, command=self.refresh_plot).grid(
            row=3, column=1, sticky="w", padx=(16, 0)
        )

        list_frame = ttk.Frame(sidebar, style="Panel.TFrame")
        list_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 12))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(
            list_frame,
            width=46,
            height=12,
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
        self.file_list.bind("<Double-Button-1>", lambda _event: self.toggle_selected_files())

        file_actions = ttk.Frame(sidebar, style="Panel.TFrame")
        file_actions.grid(row=6, column=0, sticky="ew", pady=(0, 12))
        file_actions.columnconfigure((0, 1), weight=1)
        ttk.Button(file_actions, text="Remove selected", command=self.exclude_selected_files).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(file_actions, text="Add selected", command=self.include_selected_files).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )
        ttk.Button(file_actions, text="Add all", command=self.include_all_files).grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 6))
        ttk.Button(file_actions, text="Only current plot", command=self.include_only_current_plot_files).grid(
            row=1, column=1, sticky="ew", pady=(8, 0), padx=(6, 0)
        )

        cycle_frame = ttk.LabelFrame(sidebar, text="CV cycle", padding=10)
        cycle_frame.grid(row=7, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(cycle_frame, text="Cycle", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cycle_spinbox = tk.Spinbox(
            cycle_frame,
            from_=1,
            to=1,
            textvariable=self.selected_cycle,
            command=self.refresh_plot,
            width=8,
            bg="#ffffff",
            fg=TEXT,
            highlightthickness=1,
            highlightbackground="#d5dde2",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.cycle_spinbox.grid(row=0, column=1, sticky="w")
        self.cycle_spinbox.bind("<Return>", lambda _event: self.refresh_plot())
        ttk.Button(cycle_frame, text="Last", command=self.use_last_cycle).grid(row=0, column=2, sticky="w", padx=(10, 0))

        area_frame = ttk.LabelFrame(sidebar, text="Working area", padding=10)
        area_frame.grid(row=8, column=0, sticky="ew", pady=(0, 12))
        area_frame.columnconfigure(0, weight=1)
        area_entry = ttk.Entry(area_frame, textvariable=self.working_area, width=16)
        area_entry.grid(row=0, column=0, sticky="ew")
        area_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(area_frame, text="cm^2", style="Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(area_frame, text="Clear", command=self.clear_working_area).grid(row=1, column=0, sticky="w", pady=(8, 0))

        y_range = ttk.LabelFrame(sidebar, text="OCV / CP Y range", padding=10)
        y_range.grid(row=9, column=0, sticky="ew", pady=(0, 12))
        y_range.columnconfigure((1, 3), weight=1)
        ttk.Label(y_range, text="Min", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        y_min_entry = ttk.Entry(y_range, textvariable=self.y_min, width=10)
        y_min_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        y_min_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(y_range, text="Max", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 6))
        y_max_entry = ttk.Entry(y_range, textvariable=self.y_max, width=10)
        y_max_entry.grid(row=0, column=3, sticky="ew")
        y_max_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Button(y_range, text="Auto", command=self.clear_y_range).grid(row=1, column=0, sticky="w", pady=(8, 0))

        lsv_frame = ttk.LabelFrame(sidebar, text="LSV iR compensation", padding=10)
        lsv_frame.grid(row=10, column=0, sticky="ew", pady=(0, 12))
        lsv_frame.columnconfigure(0, weight=1)
        mode_row = ttk.Frame(lsv_frame, style="Panel.TFrame")
        mode_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Radiobutton(mode_row, text="LSV plot", value="LSV", variable=self.lsv_plot_mode, command=self.refresh_plot).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Radiobutton(mode_row, text="Tafel plot", value="Tafel", variable=self.lsv_plot_mode, command=self.refresh_plot).grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        ref_row = ttk.Frame(lsv_frame, style="Panel.TFrame")
        ref_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ref_row.columnconfigure((1, 3), weight=1)
        ttk.Label(ref_row, text="Ref vs RHE", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ref_entry = ttk.Entry(ref_row, textvariable=self.rhe_offset, width=10)
        ref_entry.grid(row=0, column=1, sticky="ew")
        ref_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(ref_row, text="V", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(6, 12))
        ttk.Label(ref_row, text="Eeq", style="Panel.TLabel").grid(row=0, column=3, sticky="w", padx=(0, 8))
        eq_entry = ttk.Entry(ref_row, textvariable=self.equilibrium_potential, width=10)
        eq_entry.grid(row=0, column=4, sticky="ew")
        eq_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(ref_row, text="V", style="Panel.TLabel").grid(row=0, column=5, sticky="w", padx=(6, 0))
        tafel_range = ttk.LabelFrame(lsv_frame, text="Tafel overpotential range", padding=8)
        tafel_range.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        tafel_range.columnconfigure((1, 3), weight=1)
        ttk.Label(tafel_range, text="Min", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        tafel_min_entry = ttk.Entry(tafel_range, textvariable=self.tafel_overpotential_min, width=10)
        tafel_min_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        tafel_min_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(tafel_range, text="Max", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 6))
        tafel_max_entry = ttk.Entry(tafel_range, textvariable=self.tafel_overpotential_max, width=10)
        tafel_max_entry.grid(row=0, column=3, sticky="ew")
        tafel_max_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Button(tafel_range, text="Auto", command=self.clear_tafel_overpotential_range).grid(row=1, column=0, sticky="w", pady=(8, 0))
        compensation_row = ttk.Frame(lsv_frame, style="Panel.TFrame")
        compensation_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        compensation_row.columnconfigure(1, weight=1)
        ttk.Label(compensation_row, text="iR level", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        level_entry = ttk.Entry(compensation_row, textvariable=self.compensation_level, width=10)
        level_entry.grid(row=0, column=1, sticky="ew")
        level_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(compensation_row, text="%", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.lsv_rs_text = tk.Text(
            lsv_frame,
            height=4,
            width=42,
            bg="#ffffff",
            fg=TEXT,
            highlightthickness=1,
            highlightbackground="#d5dde2",
            relief="flat",
            font=("Consolas", 9),
            wrap="none",
        )
        self.lsv_rs_text.grid(row=4, column=0, sticky="ew")
        self.lsv_rs_text.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Button(lsv_frame, text="Auto Rs from filenames", command=self.refresh_lsv_rs_inputs).grid(
            row=5, column=0, sticky="w", pady=(8, 0)
        )

        cp_frame = ttk.LabelFrame(sidebar, text="CP transforms", padding=10)
        cp_frame.grid(row=11, column=0, sticky="ew", pady=(0, 12))
        cp_frame.columnconfigure((1, 3), weight=1)
        ttk.Label(cp_frame, text="Rs", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        cp_rs_entry = ttk.Entry(cp_frame, textvariable=self.cp_solution_resistance, width=10)
        cp_rs_entry.grid(row=0, column=1, sticky="ew")
        cp_rs_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(cp_frame, text="ohm", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(6, 12))
        ttk.Label(cp_frame, text="Level", style="Panel.TLabel").grid(row=0, column=3, sticky="w", padx=(0, 8))
        cp_level_entry = ttk.Entry(cp_frame, textvariable=self.cp_compensation_level, width=10)
        cp_level_entry.grid(row=0, column=4, sticky="ew")
        cp_level_entry.bind("<KeyRelease>", lambda _event: self.refresh_plot())
        ttk.Label(cp_frame, text="%", style="Panel.TLabel").grid(row=0, column=5, sticky="w", padx=(6, 0))

        ttk.Label(sidebar, textvariable=self.summary, style="Panel.TLabel", wraplength=360, justify="left").grid(
            row=12, column=0, sticky="ew", pady=(0, 8)
        )
        self.details_text = tk.Text(
            sidebar,
            width=46,
            height=12,
            bg="#ffffff",
            fg=TEXT,
            highlightthickness=1,
            highlightbackground="#d5dde2",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        self.details_text.grid(row=13, column=0, sticky="nsew", pady=(0, 12))
        self.set_details("No data loaded.")
        ttk.Label(sidebar, textvariable=self.status, style="Muted.TLabel", wraplength=360).grid(row=14, column=0, sticky="ew")

        plot_area = ttk.Frame(self, padding=16)
        plot_area.grid(row=0, column=1, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)
        self.figure = Figure(figsize=(8.2, 6.4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar = NavigationToolbar2Tk(self.canvas, plot_area, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ew", pady=(8, 0))

    def import_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose a folder of electrochemical data files")
        if not selected:
            return
        self.folder = Path(selected)
        self.files = self.scan_folder(self.folder)
        self.included_files = {item.path for item in self.files}
        self.clear_loaded_data()
        self.refresh_file_list()
        self.refresh_lsv_rs_inputs(refresh=False)
        self.summary.set(self.folder_summary())
        self.refresh_plot()

    def clear_folder(self) -> None:
        self.folder = None
        self.files.clear()
        self.included_files.clear()
        self.clear_loaded_data()
        self.file_list.delete(0, tk.END)
        self.set_lsv_rs_text("")
        self.summary.set("No folder loaded.")
        self.status.set("Import a folder containing electrochemical data files.")
        self.set_details("No data loaded.")
        self._draw_empty_plot("Folder batch plotter")

    def clear_loaded_data(self) -> None:
        self.loaded_ocv.clear()
        self.loaded_lsv.clear()
        self.loaded_eis.clear()
        self.loaded_cp.clear()
        self.loaded_ecsa_cv.clear()
        self.loaded_active_cv.clear()

    def refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for item in self.files:
            marker = "[x]" if item.path in self.included_files else "[ ]"
            self.file_list.insert(tk.END, f"{marker} {item.display_name}")

    def selected_file_items(self) -> list[FolderFile]:
        return [self.files[index] for index in self.file_list.curselection()]

    def include_selected_files(self) -> None:
        for item in self.selected_file_items():
            self.included_files.add(item.path)
        self.refresh_file_list()
        self.refresh_lsv_rs_inputs(refresh=False)
        self.summary.set(self.folder_summary())
        self.refresh_plot()

    def exclude_selected_files(self) -> None:
        for item in self.selected_file_items():
            self.included_files.discard(item.path)
        self.refresh_file_list()
        self.refresh_lsv_rs_inputs(refresh=False)
        self.summary.set(self.folder_summary())
        self.refresh_plot()

    def toggle_selected_files(self) -> None:
        for item in self.selected_file_items():
            if item.path in self.included_files:
                self.included_files.remove(item.path)
            else:
                self.included_files.add(item.path)
        self.refresh_file_list()
        self.refresh_lsv_rs_inputs(refresh=False)
        self.summary.set(self.folder_summary())
        self.refresh_plot()

    def include_all_files(self) -> None:
        self.included_files = {item.path for item in self.files}
        self.refresh_file_list()
        self.refresh_lsv_rs_inputs(refresh=False)
        self.summary.set(self.folder_summary())
        self.refresh_plot()

    def include_only_current_plot_files(self) -> None:
        selected = self.plot_type.get()
        self.included_files = {
            item.path
            for item in self.files
            if self.item_matches_plot_type(item, selected)
        }
        self.refresh_file_list()
        self.refresh_lsv_rs_inputs(refresh=False)
        self.summary.set(self.folder_summary())
        self.refresh_plot()

    @staticmethod
    def scan_folder(folder: Path) -> list[FolderFile]:
        found: list[FolderFile] = []
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            parsed = FolderBatchPlotApp.parse_data_name(path) or FolderBatchPlotApp.parse_data_header(path)
            if parsed is not None:
                found.append(parsed)
        return found

    @staticmethod
    def parse_data_name(path: Path) -> FolderFile | None:
        name = path.stem
        parts = [part.strip() for part in name.split("_") if part.strip()]
        if len(parts) >= 2:
            for index in range(1, len(parts)):
                match = FILENAME_MEASUREMENT.search(parts[index])
                if match is None:
                    continue
                measurement = MEASUREMENT_ALIASES[match.group(1).upper()]
                sample = "_".join(parts[:index])
                suffix_parts: list[str] = []
                local_suffix = parts[index][match.end() :].strip(" _-")
                if local_suffix:
                    suffix_parts.append(local_suffix)
                suffix_parts.extend(parts[index + 1 :])
                return FolderFile(path=path, sample=sample, measurement=measurement, suffix="_".join(suffix_parts))

        match = FILENAME_MEASUREMENT.search(name)
        if match is None:
            return None
        measurement = MEASUREMENT_ALIASES[match.group(1).upper()]
        sample = name[: match.start()].strip(" _-") or name
        suffix = name[match.end() :].strip(" _-")
        return FolderFile(path=path, sample=sample, measurement=measurement, suffix=suffix)

    @staticmethod
    def parse_data_header(path: Path) -> FolderFile | None:
        measurement_line = FolderBatchPlotApp.read_measurement_line(path)
        if measurement_line is None:
            return None
        measurement = FolderBatchPlotApp.measurement_from_instrument_line(measurement_line)
        if measurement is None:
            return None
        return FolderFile(path=path, sample=path.stem, measurement=measurement, suffix=measurement_line)

    @staticmethod
    def read_measurement_line(path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8-sig", errors="replace") as source:
                next(source, None)
                second_line = next(source, "")
        except OSError:
            return None
        stripped = second_line.strip()
        return stripped or None

    @staticmethod
    def measurement_from_instrument_line(line: str) -> str | None:
        normalized = line.strip().lower()
        direct = MEASUREMENT_ALIASES.get(normalized.upper())
        if direct is not None:
            return direct
        for marker, measurement in INSTRUMENT_MEASUREMENTS.items():
            if marker in normalized:
                return measurement
        return None

    def folder_summary(self) -> str:
        if self.folder is None:
            return "No folder loaded."
        counts = {plot_type: 0 for plot_type in PLOT_TYPES}
        for item in self.included_file_items():
            if item.measurement == "CV":
                if self.is_ecsa_scan_rate_file(item):
                    counts["ECSA"] += 1
                if self.is_cv_activation_file(item):
                    counts["CV active"] += 1
            elif item.measurement in counts:
                counts[item.measurement] += 1
        count_text = ", ".join(f"{name}: {count}" for name, count in counts.items())
        return f"Folder: {self.folder.name}\nFiles included: {len(self.included_files)} / {len(self.files)}\n{count_text}"

    def files_for_current_plot(self) -> list[FolderFile]:
        selected = self.plot_type.get()
        return [item for item in self.included_file_items() if self.item_matches_plot_type(item, selected)]

    def included_file_items(self) -> list[FolderFile]:
        return [item for item in self.files if item.path in self.included_files]

    def item_matches_plot_type(self, item: FolderFile, selected: str) -> bool:
        if selected == "ECSA":
            return self.is_ecsa_scan_rate_file(item)
        if selected == "CV active":
            return self.is_cv_activation_file(item)
        return item.measurement == selected

    @staticmethod
    def is_ecsa_scan_rate_file(item: FolderFile) -> bool:
        if item.measurement != "CV":
            return False
        label = f"{item.path.stem} {item.suffix}".lower()
        if "active" in label or CV_SCAN_LABEL.search(label):
            return False
        return ECSA_SCAN_RATE.search(label) is not None

    @staticmethod
    def is_cv_activation_file(item: FolderFile) -> bool:
        if item.measurement != "CV":
            return False
        label = f"{item.path.stem} {item.suffix}".lower()
        return "activation" in label or "active" in label or CV_SCAN_LABEL.search(label) is not None

    def refresh_plot(self) -> None:
        selected = self.plot_type.get()
        if selected == "ECSA" and self.previous_plot_type != "ECSA":
            self.use_last_cycle(refresh=False)
        items = self.files_for_current_plot()
        if not items:
            self.set_details(f"No {selected} files found.")
            self.status.set(f"No {selected} files found in the selected folder.")
            self._draw_empty_plot(selected)
            self.previous_plot_type = selected
            return
        if selected == "OCV":
            self.plot_ocv(items)
        elif selected == "LSV":
            if self.lsv_plot_mode.get() == "Tafel":
                self.plot_tafel(items)
            else:
                self.plot_lsv(items)
        elif selected == "EIS":
            self.plot_eis(items)
        elif selected == "ECSA":
            self.plot_ecsa(items)
        elif selected == "CP":
            self.plot_cp(items)
        elif selected == "CV active":
            self.plot_cv_active(items)
        self.previous_plot_type = selected

    def get_ocv(self, item: FolderFile) -> OCVData:
        if item.path not in self.loaded_ocv:
            self.loaded_ocv[item.path] = read_ocv_data(item.path)
        return self.loaded_ocv[item.path]

    def get_lsv(self, item: FolderFile) -> LSVData:
        if item.path not in self.loaded_lsv:
            self.loaded_lsv[item.path] = read_lsv_data(item.path)
        return self.loaded_lsv[item.path]

    def get_eis(self, item: FolderFile) -> EISData:
        if item.path not in self.loaded_eis:
            self.loaded_eis[item.path] = read_eis_data(item.path)
        return self.loaded_eis[item.path]

    def get_cp(self, item: FolderFile) -> DurabilityData:
        if item.path not in self.loaded_cp:
            self.loaded_cp[item.path] = read_durability_data(item.path)
        return self.loaded_cp[item.path]

    def get_ecsa_cv(self, item: FolderFile) -> ECSACVData:
        if item.path not in self.loaded_ecsa_cv:
            self.loaded_ecsa_cv[item.path] = read_ecsa_cv_data(item.path)
        return self.loaded_ecsa_cv[item.path]

    def get_active_cv(self, item: FolderFile) -> ActiveCVData:
        if item.path not in self.loaded_active_cv:
            self.loaded_active_cv[item.path] = read_active_cv_data(item.path)
        return self.loaded_active_cv[item.path]

    def plot_ocv(self, items: list[FolderFile]) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        loaded, failures, details = 0, [], []
        y_range, y_range_error = self.get_y_range()
        for item in items:
            try:
                data = self.get_ocv(item)
            except Exception as exc:
                failures.append(f"{item.path.name}: {exc}")
                continue
            self.ax.plot(data.times_sec, data.potentials_v, linewidth=1.4, label=item.label)
            details.append(f"{item.path.name}\n{summarize_ocv_data(data)}")
            loaded += 1
        self.decorate_axis("OCV", "Time / s", "Potential / V", loaded)
        if y_range is not None:
            self.ax.set_ylim(*y_range)
        if y_range_error is not None:
            failures.append(y_range_error)
        self.finish_plot("OCV", loaded, failures, details)

    def plot_lsv(self, items: list[FolderFile]) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        loaded, failures, details = 0, [], []
        scale = self.current_scale()
        rs_values = self.get_lsv_rs_values()
        compensation_fraction, compensation_error = self.get_compensation_fraction()
        rhe_offset, rhe_error = self.get_rhe_offset()
        for item in items:
            try:
                data = self.get_lsv(item)
            except Exception as exc:
                failures.append(f"{item.path.name}: {exc}")
                continue
            rs_value = rs_values.get(item.path)
            potentials = self.get_adjusted_lsv_potentials(data, rhe_offset, rs_value, compensation_fraction)
            self.ax.plot(potentials, [current * scale for current in data.currents], linewidth=1.4, label=item.label)
            rs_line = "Rs: --"
            if rs_value is not None:
                rs_line = f"Rs: {rs_value:g} ohm"
                if compensation_fraction is not None:
                    rs_line += f", compensation: {compensation_fraction * 100:g}%"
            if rhe_offset is not None:
                rs_line += f"\nRef electrode: +{rhe_offset:g} V vs RHE"
            details.append(f"{item.path.name}\n{rs_line}\n{summarize_lsv_data(data)}")
            loaded += 1
        x_label = self.lsv_potential_axis_label(rhe_offset, compensation_fraction, rs_values, items)
        self.decorate_axis("LSV", x_label, self.current_axis_label(), loaded)
        if compensation_error is not None:
            failures.append(compensation_error)
        if rhe_error is not None:
            failures.append(rhe_error)
        self.finish_plot("LSV", loaded, failures, details)

    def plot_tafel(self, items: list[FolderFile]) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        loaded, failures, details = 0, [], []
        rs_values = self.get_lsv_rs_values()
        compensation_fraction, compensation_error = self.get_compensation_fraction()
        rhe_offset, rhe_error = self.get_rhe_offset()
        try:
            working_area = self.get_working_area()
        except ValueError:
            working_area = None
            failures.append("Working area must be a positive number.")
        try:
            equilibrium_potential = self.get_equilibrium_potential()
        except ValueError:
            equilibrium_potential = 1.23
            failures.append("Equilibrium potential must be a number.")
        overpotential_range, overpotential_range_error = self.get_tafel_overpotential_range()

        if working_area is None:
            failures.append("Working area is required for Tafel plot.")

        for item in items:
            try:
                data = self.get_lsv(item)
            except Exception as exc:
                failures.append(f"{item.path.name}: {exc}")
                continue

            rs_value = rs_values.get(item.path)
            adjusted_potentials = self.get_adjusted_lsv_potentials(data, rhe_offset, rs_value, compensation_fraction)
            tafel_points = []
            if working_area is not None:
                tafel_points = self.tafel_points(data, adjusted_potentials, working_area, equilibrium_potential)
                if overpotential_range is not None:
                    tafel_points = [
                        point
                        for point in tafel_points
                        if overpotential_range[0] <= point[1] <= overpotential_range[1]
                    ]

            if tafel_points:
                log_current = [point[0] for point in tafel_points]
                overpotential = [point[1] for point in tafel_points]
                label = item.label
                fit = self.linear_regression(tafel_points)
                if fit is not None:
                    slope, intercept = fit
                    label = f"{item.label} ({slope * 1000:.4g} mV/dec)"
                    fit_x = [min(log_current), max(log_current)]
                    fit_y = [slope * value + intercept for value in fit_x]
                    self.ax.plot(fit_x, fit_y, linestyle="--", linewidth=1.2)
                self.ax.plot(log_current, overpotential, marker="o", linewidth=1.4, label=label)
                loaded += 1

            rs_line = "Rs: --"
            if rs_value is not None:
                rs_line = f"Rs: {rs_value:g} ohm"
                if compensation_fraction is not None:
                    rs_line += f", compensation: {compensation_fraction * 100:g}%"
            details.append(f"{item.path.name}\n{rs_line}\nEeq: {equilibrium_potential:g} V\n{summarize_lsv_data(data)}")

        self.decorate_axis("Tafel slope", "log10(|j| / mA cm^-2)", "Overpotential / V", loaded)
        if compensation_error is not None:
            failures.append(compensation_error)
        if rhe_error is not None:
            failures.append(rhe_error)
        if overpotential_range_error is not None:
            failures.append(overpotential_range_error)
        self.finish_plot("Tafel", loaded, failures, details)

    def plot_eis(self, items: list[FolderFile]) -> None:
        self.figure.clear()
        loaded, failures, details = 0, [], []
        impedance_scale = self.impedance_scale()
        impedance_unit = self.impedance_unit()
        marker = "o" if self.show_points.get() else None
        linestyle = "-" if self.connect_points.get() else "None"
        if self.eis_plot_type.get() == "Bode":
            ax_z = self.figure.add_subplot(211)
            ax_phase = self.figure.add_subplot(212, sharex=ax_z)
            self.ax = ax_z
            for item in items:
                try:
                    data = self.get_eis(item)
                except Exception as exc:
                    failures.append(f"{item.path.name}: {exc}")
                    continue
                y_values = data.minus_z_imag_ohm if self.eis_bode_y_axis.get() == "-Z''" else data.z_abs_ohm
                rows = sorted(zip(data.frequency_hz, [value * impedance_scale for value in y_values], data.phase_deg), key=lambda row: row[0])
                if self.eis_frequency_scale.get() == "log":
                    rows = [row for row in rows if row[0] > 0]
                if not rows:
                    continue
                frequencies, z_abs, phases = zip(*rows)
                ax_z.plot(frequencies, z_abs, marker=marker, markersize=3, linewidth=1.2, linestyle=linestyle, label=item.label)
                ax_phase.plot(frequencies, phases, marker=marker, markersize=3, linewidth=1.2, linestyle=linestyle, label=item.label)
                details.append(self.eis_detail(item, data))
                loaded += 1
            if self.eis_frequency_scale.get() == "log":
                ax_z.set_xscale("log")
                ax_phase.set_xscale("log")
            ax_z.set_title("EIS Bode")
            bode_label = "-Z''" if self.eis_bode_y_axis.get() == "-Z''" else "Z"
            ax_z.set_ylabel(f"{bode_label} / {impedance_unit}")
            ax_phase.set_xlabel("Frequency / Hz")
            ax_phase.set_ylabel("Phase / deg")
            ax_z.grid(self.show_grid.get(), alpha=0.3)
            ax_phase.grid(self.show_grid.get(), alpha=0.3)
            if self.show_legend.get() and loaded:
                ax_z.legend(loc="best", fontsize=8)
        else:
            self.ax = self.figure.add_subplot(111)
            for item in items:
                try:
                    data = self.get_eis(item)
                except Exception as exc:
                    failures.append(f"{item.path.name}: {exc}")
                    continue
                self.ax.plot(
                    [value * impedance_scale for value in data.z_real_ohm],
                    [value * impedance_scale for value in data.minus_z_imag_ohm],
                    marker=marker,
                    markersize=3,
                    linewidth=1.2,
                    linestyle=linestyle,
                    label=item.label,
                )
                details.append(self.eis_detail(item, data))
                loaded += 1
            self.decorate_axis("EIS Nyquist", f"Z' / {impedance_unit}", f"-Z'' / {impedance_unit}", loaded)
            if loaded and self.eis_equal_aspect.get():
                self.ax.set_aspect("equal", adjustable="datalim")
        self.finish_plot("EIS", loaded, failures, details)

    def eis_detail(self, item: FolderFile, data: EISData) -> str:
        stats = summarize_eis_data(data)
        return "\n".join(
            [
                item.path.name,
                f"Points: {stats['points']}",
                f"Frequency: {stats['frequency_max_hz']:.3g} to {stats['frequency_min_hz']:.3g} Hz",
                f"Z': {stats['z_real_min_ohm']:.4g} to {stats['z_real_max_ohm']:.4g} ohm",
                f"-Z'': {stats['minus_z_imag_min_ohm']:.4g} to {stats['minus_z_imag_max_ohm']:.4g} ohm",
            ]
        )

    def plot_cp(self, items: list[FolderFile]) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        loaded, failures, details = 0, [], []
        rhe_offset, rhe_error = self.get_rhe_offset()
        cp_ir, cp_ir_error = self.get_cp_ir_compensation()
        y_range, y_range_error = self.get_y_range()
        for item in items:
            try:
                data = self.get_cp(item)
            except Exception as exc:
                failures.append(f"{item.path.name}: {exc}")
                continue
            potentials = self.get_adjusted_cp_potentials(data, rhe_offset, cp_ir)
            self.ax.plot(data.times_sec, potentials, linewidth=1.4, label=item.label)
            current_density = self.cp_current_density(data)
            density_line = "" if current_density is None else f"\nCurrent density: {current_density:g} mA/cm^2"
            details.append(f"{item.path.name}{density_line}\n{summarize_durability_data(data)}")
            loaded += 1
        self.decorate_axis("CP", "Time / s", self.cp_potential_axis_label(rhe_offset, cp_ir), loaded)
        if y_range is not None:
            self.ax.set_ylim(*y_range)
        for error in (rhe_error, cp_ir_error, y_range_error):
            if error is not None:
                failures.append(error)
        self.finish_plot("CP", loaded, failures, details)

    def plot_ecsa(self, items: list[FolderFile]) -> None:
        data_sets, failures = [], []
        for item in items:
            try:
                data_sets.append(self.get_ecsa_cv(item))
            except Exception as exc:
                failures.append(f"{item.path.name}: {exc}")
        data_sets.sort(key=lambda data: data.sort_key)
        self.update_cycle_selector(data_sets)
        cycle = self.selected_cycle_number(data_sets)
        scale = self.current_scale()

        self.figure.clear()
        ax_cv = self.figure.add_subplot(211)
        ax_average = self.figure.add_subplot(212)
        self.ax = ax_cv
        for data in data_sets:
            ax_cv.plot(data.cycle_potentials(cycle), [current * scale for current in data.cycle_currents(cycle)], linewidth=1.3, label=data.path.stem)
        ax_cv.set_title(f"ECSA CV cycle {cycle}")
        ax_cv.set_xlabel("Potential / V")
        ax_cv.set_ylabel(self.current_axis_label())
        ax_cv.grid(self.show_grid.get(), alpha=0.3)
        if self.show_legend.get() and data_sets:
            ax_cv.legend(loc="best", fontsize=8)

        average_points = [
            (data.metadata.scan_rate_mv_s, data.midpoint_currents_for_cycle(cycle).average_current * scale)
            for data in data_sets
            if data.metadata.scan_rate_mv_s is not None and data.midpoint_currents_for_cycle(cycle) is not None
        ]
        average_points.sort(key=lambda point: point[0])
        if average_points:
            scan_rates = [point[0] for point in average_points]
            currents = [point[1] for point in average_points]
            ax_average.plot(scan_rates, currents, linestyle="None", marker="o", color=ACCENT, label="Data")
            fit = self.linear_regression(average_points)
            if fit is not None:
                slope, intercept = fit
                fit_x = [min(scan_rates), max(scan_rates)]
                fit_y = [slope * value + intercept for value in fit_x]
                ax_average.plot(fit_x, fit_y, linewidth=1.4, color="#b84a3a", label="Linear fit")
                ax_average.legend(loc="best", fontsize=8)
        ax_average.set_title(f"ECSA average current vs scan rate, cycle {cycle}")
        ax_average.set_xlabel("Scan rate / mV s^-1")
        ax_average.set_ylabel(self.average_axis_label())
        ax_average.grid(self.show_grid.get(), alpha=0.3)

        details = [summarize_ecsa_data(data_sets, self.current_units.get(), cycle)] if data_sets else []
        self.finish_plot("ECSA", len(data_sets), failures, details)

    def plot_cv_active(self, items: list[FolderFile]) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        loaded, failures, details = 0, [], []
        scale = 1000 if self.current_units.get() == "mA" else 1
        for item in items:
            try:
                data = self.get_active_cv(item)
            except Exception as exc:
                failures.append(f"{item.path.name}: {exc}")
                continue
            self.ax.plot(data.potentials, [current * scale for current in data.currents], linewidth=1.3, label=item.label)
            if data.zero_crossings:
                self.ax.scatter([crossing.potential for crossing in data.zero_crossings], [0 for _ in data.zero_crossings], s=20, zorder=3)
            details.append(f"{item.path.name}\n{summarize_cv_data(data)}")
            loaded += 1
        self.decorate_axis("CV active", "Potential / V", f"Current / {self.current_units.get()}", loaded)
        self.finish_plot("CV active", loaded, failures, details)

    def decorate_axis(self, title: str, xlabel: str, ylabel: str, loaded: int) -> None:
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.grid(self.show_grid.get(), alpha=0.3)
        if self.show_legend.get() and loaded:
            self.ax.legend(loc="best", fontsize=8)

    def finish_plot(self, plot_name: str, loaded: int, failures: list[str], details: list[str]) -> None:
        if loaded == 0:
            self._draw_empty_plot(plot_name)
        else:
            self.figure.tight_layout()
            self.canvas.draw_idle()
        self.set_details("\n\n".join(details) if details else f"No readable {plot_name} data.")
        if failures:
            file_failures = [failure for failure in failures if self.is_file_failure_message(failure)]
            setting_warnings = [failure for failure in failures if failure not in file_failures]
            if setting_warnings:
                self.status.set(f"Plotted {loaded} {plot_name} file(s). {setting_warnings[0]}")
            else:
                self.status.set(f"Plotted {loaded} {plot_name} file(s). {len(file_failures)} file(s) could not be read.")
            if file_failures:
                messagebox.showwarning("Some files could not be read", "\n\n".join(file_failures))
        else:
            self.status.set(f"Plotted {loaded} {plot_name} file(s).")

    @staticmethod
    def is_file_failure_message(message: str) -> bool:
        prefix = message.split(":", 1)[0].strip().lower()
        return prefix.endswith((".txt", ".csv", ".dat")) and ": " in message

    def _draw_empty_plot(self, title: str) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.grid(True, alpha=0.3)
        self.ax.text(0.5, 0.5, "Import a folder", transform=self.ax.transAxes, ha="center", va="center", color=MUTED)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def set_details(self, text: str) -> None:
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert("1.0", text)
        self.details_text.configure(state="disabled")

    def set_lsv_rs_text(self, text: str) -> None:
        if self.lsv_rs_text is None:
            return
        self.lsv_rs_text.delete("1.0", tk.END)
        self.lsv_rs_text.insert("1.0", text)

    def refresh_lsv_rs_inputs(self, refresh: bool = True) -> None:
        lines: list[str] = []
        for item in self.included_file_items():
            if item.measurement != "LSV":
                continue
            rs_value = self.rs_from_filename(item)
            value = "" if rs_value is None else f"{rs_value:g}"
            lines.append(f"{item.path.name} = {value}")
        self.set_lsv_rs_text("\n".join(lines))
        if refresh:
            self.refresh_plot()

    @staticmethod
    def rs_from_filename(item: FolderFile) -> float | None:
        match = LSV_RS_VALUE.search(item.path.stem)
        if match is None:
            match = LSV_RS_VALUE.search(item.suffix)
        if match is None:
            return None
        return float(match.group(1))

    def get_lsv_rs_values(self) -> dict[Path, float]:
        values: dict[Path, float] = {}
        if self.lsv_rs_text is None:
            return values
        by_name = {item.path.name.lower(): item.path for item in self.included_file_items() if item.measurement == "LSV"}
        by_stem = {item.path.stem.lower(): item.path for item in self.included_file_items() if item.measurement == "LSV"}
        for raw_line in self.lsv_rs_text.get("1.0", tk.END).splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            raw_name, raw_value = [part.strip() for part in line.split("=", 1)]
            if not raw_value:
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            path = by_name.get(raw_name.lower()) or by_stem.get(raw_name.lower())
            if path is not None:
                values[path] = value
        return values

    def get_compensation_fraction(self) -> tuple[float | None, str | None]:
        raw_value = self.compensation_level.get().strip()
        if not raw_value:
            return None, None
        try:
            level = float(raw_value)
        except ValueError:
            return None, "Compensation level must be a number."
        if level < 0:
            return None, "Compensation level must be non-negative."
        return level / 100, None

    def get_rhe_offset(self) -> tuple[float | None, str | None]:
        raw_value = self.rhe_offset.get().strip()
        if not raw_value:
            return None, None
        try:
            return float(raw_value), None
        except ValueError:
            return None, "Reference electrode potential must be a number."

    def get_equilibrium_potential(self) -> float:
        raw_value = self.equilibrium_potential.get().strip()
        if not raw_value:
            return 1.23
        return float(raw_value)

    @staticmethod
    def get_adjusted_lsv_potentials(
        data: LSVData,
        rhe_offset: float | None,
        rs_value: float | None,
        compensation_fraction: float | None,
    ) -> list[float]:
        adjusted = data.potentials
        if rhe_offset is not None:
            adjusted = [potential + rhe_offset for potential in adjusted]
        if rs_value is not None and compensation_fraction is not None:
            adjusted = [
                potential - current * rs_value * compensation_fraction
                for potential, current in zip(adjusted, data.currents)
            ]
        return adjusted

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
            points.append((math.log10(abs(current_density)), potential - equilibrium_potential))
        return points

    def lsv_potential_axis_label(
        self,
        rhe_offset: float | None,
        compensation_fraction: float | None,
        rs_values: dict[Path, float],
        items: list[FolderFile],
    ) -> str:
        has_ir = compensation_fraction is not None and any(item.path in rs_values for item in items)
        if has_ir and rhe_offset is not None:
            return "Potential (V vs. RHE, iR-corrected)"
        if has_ir:
            return "Potential (V, iR-corrected)"
        if rhe_offset is not None:
            return "Potential (V vs. RHE)"
        return "Potential / V"

    def save_plot(self) -> None:
        if not self.files_for_current_plot():
            messagebox.showinfo("No plot to save", "Import a folder with matching files first.")
            return
        output = filedialog.asksaveasfilename(
            title="Save current plot",
            defaultextension=".png",
            initialfile=f"{self.plot_type.get().replace(' ', '_')}_folder_plot.png",
            filetypes=[("PNG image", "*.png"), ("PDF file", "*.pdf"), ("SVG file", "*.svg"), ("All files", "*.*")],
        )
        if not output:
            return
        self.figure.savefig(output, dpi=300, bbox_inches="tight")
        self.status.set(f"Saved plot to {Path(output).name}")

    def get_working_area(self) -> float | None:
        raw_value = self.working_area.get().strip()
        if not raw_value:
            return None
        area = float(raw_value)
        if area <= 0:
            raise ValueError
        return area

    def get_y_range(self) -> tuple[tuple[float, float] | None, str | None]:
        raw_min = self.y_min.get().strip()
        raw_max = self.y_max.get().strip()
        if not raw_min and not raw_max:
            return None, None
        if not raw_min or not raw_max:
            return None, "Enter both Y min and Y max, or leave both blank."
        try:
            y_min = float(raw_min)
            y_max = float(raw_max)
        except ValueError:
            return None, "Y range values must be numbers."
        if y_min >= y_max:
            return None, "Y min must be smaller than Y max."
        return (y_min, y_max), None

    def clear_y_range(self) -> None:
        self.y_min.set("")
        self.y_max.set("")
        self.refresh_plot()

    def get_tafel_overpotential_range(self) -> tuple[tuple[float, float] | None, str | None]:
        raw_min = self.tafel_overpotential_min.get().strip()
        raw_max = self.tafel_overpotential_max.get().strip()
        if not raw_min and not raw_max:
            return None, None
        if not raw_min or not raw_max:
            return None, "Enter both Tafel overpotential min and max, or leave both blank."
        try:
            eta_min = float(raw_min)
            eta_max = float(raw_max)
        except ValueError:
            return None, "Tafel overpotential range values must be numbers."
        if eta_min >= eta_max:
            return None, "Tafel overpotential min must be smaller than max."
        return (eta_min, eta_max), None

    def clear_tafel_overpotential_range(self) -> None:
        self.tafel_overpotential_min.set("")
        self.tafel_overpotential_max.set("")
        self.refresh_plot()

    def impedance_scale(self) -> float:
        try:
            working_area = self.get_working_area()
        except ValueError:
            self.status.set("Working area must be a positive number.")
            return 1.0
        if working_area is None:
            return 1.0
        return working_area

    def impedance_unit(self) -> str:
        try:
            working_area = self.get_working_area()
        except ValueError:
            return "ohm"
        if working_area is None:
            return "ohm"
        return "ohm cm^2"

    def get_cp_ir_compensation(self) -> tuple[tuple[float, float] | None, str | None]:
        raw_rs = self.cp_solution_resistance.get().strip()
        raw_level = self.cp_compensation_level.get().strip()
        if not raw_rs and not raw_level:
            return None, None
        if not raw_rs or not raw_level:
            return None, "CP Rs and compensation level must both be filled, or both blank."
        try:
            resistance = float(raw_rs)
            level = float(raw_level)
        except ValueError:
            return None, "CP Rs and compensation level must be numbers."
        if resistance < 0 or level < 0:
            return None, "CP Rs and compensation level must be non-negative."
        return (resistance, level / 100), None

    @staticmethod
    def get_adjusted_cp_potentials(
        data: DurabilityData,
        rhe_offset: float | None,
        ir_compensation: tuple[float, float] | None,
    ) -> list[float]:
        adjusted = data.potentials_v
        if rhe_offset is not None:
            adjusted = [potential + rhe_offset for potential in adjusted]
        if ir_compensation is not None and data.display_current_a is not None:
            resistance, compensation_fraction = ir_compensation
            correction = data.display_current_a * resistance * compensation_fraction
            adjusted = [potential - correction for potential in adjusted]
        return adjusted

    def cp_potential_axis_label(
        self,
        rhe_offset: float | None,
        ir_compensation: tuple[float, float] | None,
    ) -> str:
        if ir_compensation is not None and rhe_offset is not None:
            return "Potential (V vs. RHE, iR-corrected)"
        if ir_compensation is not None:
            return "Potential (V, iR-corrected)"
        if rhe_offset is not None:
            return "Potential (V vs. RHE)"
        return "Potential / V"

    def cp_current_density(self, data: DurabilityData) -> float | None:
        try:
            working_area = self.get_working_area()
        except ValueError:
            return None
        if working_area is None or data.display_current_a is None:
            return None
        return data.display_current_a * 1000 / working_area

    def current_scale(self) -> float:
        try:
            area = self.get_working_area()
        except ValueError:
            self.status.set("Working area must be a positive number.")
            area = None
        if area is not None:
            return 1000 / area
        return 1000 if self.current_units.get() == "mA" else 1

    def current_axis_label(self) -> str:
        try:
            if self.get_working_area() is not None:
                return "Current density / mA cm^-2"
        except ValueError:
            pass
        return f"Current / {self.current_units.get()}"

    def average_axis_label(self) -> str:
        try:
            if self.get_working_area() is not None:
                return "Average current density / mA cm^-2"
        except ValueError:
            pass
        return f"Average current / {self.current_units.get()}"

    def clear_working_area(self) -> None:
        self.working_area.set("")
        self.refresh_plot()

    def update_cycle_selector(self, data_sets: list[ECSACVData] | None = None) -> None:
        max_cycle = max((data.cycle_count for data in data_sets or []), default=1)
        self.cycle_spinbox.configure(to=max_cycle)
        self.selected_cycle.set(min(max(1, self.selected_cycle.get()), max_cycle))

    def selected_cycle_number(self, data_sets: list[ECSACVData]) -> int:
        max_cycle = max((data.cycle_count for data in data_sets), default=1)
        try:
            cycle = int(self.selected_cycle.get())
        except tk.TclError:
            cycle = 1
        cycle = min(max(1, cycle), max_cycle)
        self.selected_cycle.set(cycle)
        return cycle

    def use_last_cycle(self, refresh: bool = True) -> None:
        data_sets: list[ECSACVData] = []
        for item in self.files_for_current_plot():
            if item.measurement != "CV":
                continue
            try:
                data_sets.append(self.get_ecsa_cv(item))
            except Exception:
                continue
        max_cycle = max((data.cycle_count for data in data_sets), default=1)
        self.selected_cycle.set(max_cycle)
        self.update_cycle_selector(data_sets)
        if refresh:
            self.refresh_plot()

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


def main() -> None:
    root = tk.Tk()
    root.title("Folder batch plotter")
    root.geometry("1280x820")
    root.minsize(1050, 680)
    app = FolderBatchPlotApp(root, on_return=root.destroy)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
