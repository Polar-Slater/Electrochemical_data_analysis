"""Run directly on a desktop to exercise all seven Tk integrations."""
import importlib
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import patch

TOOLBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLBOX))
sys.path.insert(0, str(TOOLBOX / "Folder batch plotter"))
from matplotlib.backend_bases import MouseEvent


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button(window, text):
    return next(w for w in descendants(window)
                if w.winfo_class() == "TButton" and w.cget("text") == text)


def main():
    root = tk.Tk()
    root.withdraw()
    failures = []
    root.report_callback_exception = lambda *args: failures.append(args)
    try:
        for module, name in (
            ("ocv_plot_gui", "OCVPlotApp"), ("durability_plot_gui", "DurabilityPlotApp"),
            ("eis_plot_gui", "EISPlotApp"), ("lsv_plot_gui", "LSVPlotApp"),
            ("cv_plot_gui", "CVPlotApp"), ("cv_multi_plot_gui", "CVMultiPlotApp"),
            ("folder_batch_plot_gui", "FolderBatchPlotApp"),
        ):
            app = getattr(importlib.import_module(module), name)(root)
            editor = app.plot_editor
            ax = app.figure.axes[0]
            ax.plot([1, 2, 3], [2, 4, 3], label="Test sample")
            ax.plot([1, 2, 3], [3, 5, 4], label="Second sample")
            ax.legend()
            editor.refresh()
            editor.open()
            root.update()
            with patch("plot_editor.messagebox.showerror", side_effect=AssertionError):
                button(editor.window, "Apply / Preview").invoke()
                root.update()
                assert editor.state["axes"]["0"]["legend_columns"] == "1"
                with tempfile.TemporaryDirectory() as folder:
                    preset = str(Path(folder) / "style.json")
                    with patch("plot_editor.filedialog.asksaveasfilename", return_value=preset):
                        editor.save_preset()
                    with patch("plot_editor.filedialog.askopenfilename", return_value=preset):
                        editor.load_preset()
                    root.update()
                editor.window.destroy()
                editor.window = None
                editor.canvas.draw()
                # Click to place text and save through the real annotation dialog.
                x, y = ax.transAxes.transform((.3, .7))
                editor.placing = True
                editor.press(MouseEvent("button_press_event", editor.canvas, x, y, button=1))
                root.update()
                annotation_window = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
                text_entry = next(w for w in descendants(annotation_window) if w.winfo_class() == "TEntry")
                text_entry.insert(0, "Sample A")
                button(annotation_window, "Save").invoke()
                root.update()
                assert editor.state["texts"][0]["text"] == "Sample A"
                editor.canvas.draw()
                artist, spec = editor.artists[0]
                start = artist.get_window_extent().get_points().mean(axis=0)
                editor.press(MouseEvent("button_press_event", editor.canvas, *start, button=1))
                assert editor.drag is not None
                old_x = spec["x"]
                editor.motion(MouseEvent("motion_notify_event", editor.canvas, start[0]+20, start[1]+10))
                editor.release(None)
                assert spec["x"] > old_x
                editor.edit_text(spec)
                root.update()
                annotation_window = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
                button(annotation_window, "Delete").invoke()
                assert not editor.state["texts"]
                editor.edit_legend()
                root.update()
                legend_win = editor.legend_window
                entry = next(w for w in descendants(legend_win) if w.winfo_class() == "TEntry")
                entry.delete(0, "end")
                entry.insert(0, "Renamed sample")
                button(legend_win, "Move down").invoke()
                button(legend_win, "Apply / Preview").invoke()
                root.update()
                assert [text.get_text() for text in ax.get_legend().get_texts()] == [
                    "Second sample", "Renamed sample"]
                checkbox = next(w for w in descendants(legend_win)
                                if w.winfo_class() == "TCheckbutton" and w.cget("text") == "Show entry")
                checkbox.invoke()
                button(legend_win, "Apply / Preview").invoke()
                root.update()
                assert [text.get_text() for text in ax.get_legend().get_texts()] == ["Second sample"]
                assert all(line.get_visible() for line in ax.lines)
                legend_win.destroy()
                assert not failures, failures
                editor.reset()
                root.update()
            app.destroy()
            root.update()
            print(name, "OK: settings, preset, text placement/drag/delete, legend rename/reorder/hide, reset")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
