from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk
from typing import Callable

from cv_multi_plot_gui import CVMultiPlotApp
from cv_plot_gui import CVPlotApp
from eis_plot_gui import EISPlotApp
from lsv_plot_gui import LSVPlotApp


APP_TITLE = "Electrochemical data analysis toolbox"

BG = "#f5f6f8"
PANEL = "#ffffff"
TEXT = "#17202a"
MUTED = "#637083"
BORDER = "#d8dee7"
BASE_DIR = Path(__file__).resolve().parent
DRTTOOLS_DIR = BASE_DIR / "DRTtools modified"
DRTTOOLS_LAUNCHER = DRTTOOLS_DIR / "launch.py"


@dataclass(frozen=True)
class ToolDefinition:
    title: str
    subtitle: str
    page_factory: Callable[..., ttk.Frame]


class DRTToolsPage(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None, on_return=None) -> None:
        super().__init__(master, style="Panel.TFrame", padding=28)
        self.on_return = on_return
        self.process: subprocess.Popen[bytes] | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="DRTtools", style="HomeTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            self,
            text="Credits: Dr. Francesco Ciucci's LAB",
            style="HomeSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 24))

        actions = ttk.Frame(self, style="Panel.TFrame")
        actions.grid(row=2, column=0, sticky="nw")
        ttk.Button(actions, text="Open DRTtools", command=self.launch_drttools).grid(row=0, column=0, sticky="ew")
        ttk.Button(actions, text="Return", command=self.on_return).grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, style="HomeMuted.TLabel").grid(row=3, column=0, sticky="w")

        self.launch_drttools()

    def launch_drttools(self) -> None:
        if not DRTTOOLS_LAUNCHER.exists():
            messagebox.showerror("DRTtools not found", f"Could not find:\n{DRTTOOLS_LAUNCHER}")
            self.status.set("DRTtools launcher was not found.")
            return

        if self.process is not None and self.process.poll() is None:
            self.status.set("DRTtools is already open.")
            return

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(DRTTOOLS_LAUNCHER)],
                cwd=str(DRTTOOLS_DIR),
            )
        except Exception as exc:
            messagebox.showerror("Could not open DRTtools", str(exc))
            self.status.set("Could not open DRTtools.")
            return

        self.status.set("Opened DRTtools.")


TOOLS = [
    ToolDefinition(
        title="Reference electrode potential",
        subtitle="Find ref electrode potential from CV scan",
        page_factory=CVPlotApp,
    ),
    ToolDefinition(
        title="ECSA identifier",
        subtitle="C_dl from CV scan",
        page_factory=CVMultiPlotApp,
    ),
    ToolDefinition(
        title="LSV Plotter",
        subtitle="LSV plotting with RHE, area, and iR compensation",
        page_factory=LSVPlotApp,
    ),
    ToolDefinition(
        title="EIS Plotter",
        subtitle="Nyquist plotting and processed EIS data export",
        page_factory=EISPlotApp,
    ),
    ToolDefinition(
        title="DRTtools",
        subtitle="Credits: Dr. Francesco Ciucci's LAB",
        page_factory=DRTToolsPage,
    ),
]


class ElectrochemicalToolbox(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x860")
        self.minsize(980, 650)
        self.configure(bg=BG)

        self.active_page: ttk.Frame | None = None
        self.home_page: ttk.Frame | None = None
        self.status = tk.StringVar(value="Choose a function.")

        self._configure_home_styles()
        self.show_home()

    def _configure_home_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("HomeTitle.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 24, "bold"))
        style.configure("HomeSubtitle.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 11))
        style.configure("HomeMuted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))

    def show_home(self) -> None:
        self._clear_pages()
        self._configure_home_styles()
        self.title(APP_TITLE)

        self.home_page = ttk.Frame(self, style="Panel.TFrame", padding=28)
        self.home_page.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.home_page.columnconfigure(0, weight=1)
        self.home_page.rowconfigure(2, weight=1)

        ttk.Label(self.home_page, text=APP_TITLE, style="HomeTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            self.home_page,
            text="Select one electrochemical analysis workflow.",
            style="HomeSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 24))

        button_grid = ttk.Frame(self.home_page, style="Panel.TFrame")
        button_grid.grid(row=2, column=0, sticky="nsew")
        button_grid.columnconfigure((0, 1), weight=1, uniform="tool")
        button_grid.rowconfigure((0, 1, 2), weight=1, uniform="tool")

        for index, tool in enumerate(TOOLS):
            button = tk.Button(
                button_grid,
                text=f"{tool.title}\n{tool.subtitle}",
                command=lambda selected=tool: self.show_tool(selected),
                anchor="w",
                justify="left",
                padx=22,
                pady=18,
                bd=0,
                relief="flat",
                bg="#f9fafb",
                fg=TEXT,
                activebackground="#eef4ff",
                activeforeground=TEXT,
                highlightthickness=1,
                highlightbackground=BORDER,
                font=("Segoe UI", 15, "bold"),
                cursor="hand2",
                wraplength=440,
            )
            button.grid(row=index // 2, column=index % 2, sticky="nsew", padx=10, pady=10)

        ttk.Label(self.home_page, textvariable=self.status, style="HomeMuted.TLabel").grid(
            row=3, column=0, sticky="w", pady=(22, 0)
        )
        self.status.set("Choose a function.")

    def show_tool(self, tool: ToolDefinition) -> None:
        self._clear_pages()
        self.title(f"{APP_TITLE} - {tool.title}")
        self.active_page = tool.page_factory(self, on_return=self.show_home)
        self.active_page.grid(row=0, column=0, sticky="nsew")
        self.status.set(f"Opened {tool.title}.")

    def _clear_pages(self) -> None:
        if self.active_page is not None:
            self.active_page.destroy()
            self.active_page = None
        if self.home_page is not None:
            self.home_page.destroy()
            self.home_page = None


if __name__ == "__main__":
    app = ElectrochemicalToolbox()
    app.mainloop()
