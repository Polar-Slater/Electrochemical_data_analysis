"""Native dialog in a separate process to keep Tk on its own main thread."""
import json
import os
from pathlib import Path
import subprocess
import sys


def _run_dialog(directory, mode, filename=""):
    command = [sys.executable, str(Path(__file__).resolve()), directory or "", mode, filename]
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        check=True,
    )
    return json.loads(completed.stdout)


def choose_files(directory="", projects=False):
    return _run_dialog(directory, "project" if projects else "data")


def choose_save_path(directory="", filename="Project.json"):
    return _run_dialog(directory, "save", filename)


def last_save_directory(fallback=""):
    from eis_app import user_directory
    try:
        folder = json.loads((Path(user_directory("config")) / "dialogs.json").read_text())["save_directory"]
        return folder if Path(folder).is_dir() else fallback
    except (OSError, ValueError, KeyError, TypeError):
        return fallback


def remember_save_directory(path):
    from eis_app import user_directory
    target = Path(user_directory("config")) / "dialogs.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"save_directory": str(Path(path).resolve().parent)}), encoding="utf-8")


def show_dialog():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    projects = sys.argv[2] == "project"
    try:
        if sys.argv[2] == "save":
            path = filedialog.asksaveasfilename(
                parent=root, title="Save EIS project",
                initialdir=sys.argv[1] or None,
                initialfile=sys.argv[3] or "Project.json",
                defaultextension=".json", filetypes=[("EIS project", "*.json")],
                confirmoverwrite=True,
            )
            print(json.dumps(path, ensure_ascii=True))
            return
        paths = filedialog.askopenfilenames(
            parent=root,
            title="Open saved project" if projects else "Open EIS files",
            initialdir=sys.argv[1] or None,
            filetypes=[("DearEIS project", "*.json")] if projects else [
                ("EIS text and CSV files", "*.txt *.csv *.tsv"),
                ("All files", "*.*"),
            ],
        )
        print(json.dumps(list(paths), ensure_ascii=True))
    finally:
        root.destroy()


if __name__ == "__main__":
    show_dialog()
