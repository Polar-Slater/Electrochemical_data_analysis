from pathlib import Path
import sys
import tempfile
import unittest

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plot_editor import PlotEditor, apply_axis, apply_legend, validate_axis


def settings(**changes):
    values = dict(title="Custom title", xlabel="Potential / V", ylabel="Current",
                  xscale="linear", yscale="linear", xmin="", xmax="", ymin="", ymax="",
                  xstep="", ystep="", xreverse=False, yreverse=False, minor=True,
                  tick_direction="in", grid=True, font="DejaVu Sans", fontsize=11,
                  bold=False, italic=False, legend=True, legend_location="best",
                  legend_size=9, legend_columns=1, legend_frame=False)
    values.update(changes)
    return values


def editor():
    result = PlotEditor.__new__(PlotEditor)
    result.figure = Figure()
    result.canvas = FigureCanvasAgg(result.figure)
    result.figure.add_subplot().plot([1, 2, 3], [3, 2, 1], label="Sample")
    result.contexts, result.context, result.artists = {}, "", []
    result.window = None
    result.export = dict(width=10.16, height=7.62, dpi=100, transparent=False)
    result.refresh()
    return result


class PlotEditorTests(unittest.TestCase):
    def test_legend_reorder_rename_hide_and_new_curves(self):
        edit = editor()
        ax = edit.figure.axes[0]
        ax.plot([1, 2], [2, 3], label="Second")
        ax.plot([1, 2], [3, 4], label="New")
        original_labels = [line.get_label() for line in ax.lines]
        options = dict(entries=[dict(index=1, label="Renamed", visible=True),
                                dict(index=0, label="Hidden", visible=False)],
                       show=True, title="Samples", location="upper left", columns=1,
                       frame=False, font="Times New Roman", size=12)
        apply_legend(ax, options)
        self.assertEqual([text.get_text() for text in ax.get_legend().get_texts()],
                         ["Renamed", "New"])
        self.assertEqual([line.get_label() for line in ax.lines], original_labels)
        self.assertTrue(all(line.get_visible() for line in ax.lines))
        self.assertEqual(ax.get_legend().get_title().get_text(), "Samples")

    def test_legend_edits_survive_rebuild_and_separate_export(self):
        edit = editor()
        edit.state["legends"] = {"0": dict(
            entries=[dict(index=0, label="Edited sample", visible=True)], show=True,
            title="", location="best", columns=1, frame=True, font="Times New Roman", size=10)}
        edit.figure.axes[0].clear()
        edit.figure.axes[0].plot([1, 2], [2, 3], label="Sample")
        edit.refresh()
        self.assertEqual(edit.figure.axes[0].get_legend().get_texts()[0].get_text(), "Edited sample")
        output = Figure()
        output.add_subplot().plot([1, 2], [2, 3], label="Sample")
        with tempfile.TemporaryDirectory() as folder:
            edit.save_figure(Path(folder) / "panel.svg", output, source_axis=0)
        self.assertEqual(output.axes[0].get_legend().get_texts()[0].get_text(), "Edited sample")

    def test_limits_reverse_log_and_automatic_reset(self):
        ax = editor().figure.axes[0]
        apply_axis(ax, settings(xmin="1", xmax="10", xreverse=True, xscale="log"), {})
        self.assertEqual(ax.get_xlim(), (10, 1))
        apply_axis(ax, settings(), {})
        self.assertEqual(ax.get_xscale(), "linear")
        self.assertLess(ax.get_xlim()[0], 1)
        self.assertGreater(ax.get_xlim()[1], 3)

    def test_invalid_limits_rejected(self):
        for changes in (dict(xmin="1"), dict(xmin="3", xmax="2"),
                        dict(xscale="log", xmin="-1", xmax="2"), dict(fontsize="nan")):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_axis(settings(**changes))

    def test_annotations_survive_rebuild_and_views_remain_separate(self):
        edit = editor()
        edit.state["texts"].append(dict(axis=0, x=.2, y=.8, text="Sample A",
                                       size=12, color="black", font="DejaVu Sans", bold=True,
                                       italic=False, rotation=0, coordinates="Plot area"))
        edit.apply()
        edit.figure.clear()
        ax = edit.figure.add_subplot()
        ax.plot([1, 2], [2, 3])
        edit.refresh()
        self.assertEqual([t.get_text() for t in ax.texts], ["Sample A"])
        ax.clear()
        ax.set_title("Different mode")
        edit.refresh()
        self.assertEqual(len(ax.texts), 0)

    def test_export_exact_dimensions_and_restore_preview(self):
        edit = editor()
        size = edit.figure.get_size_inches().copy()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "figure.png"
            edit.save_figure(path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (400, 300))
        self.assertEqual(list(edit.figure.get_size_inches()), list(size))

    def test_separate_panel_export_retains_annotation_and_style(self):
        edit = editor()
        edit.state["axes"]["0"] = settings(title="Export title")
        edit.state["texts"].append(dict(axis=0, x=1, y=2, text=r"$R_{ct}$",
                                       size=12, color="blue", font="DejaVu Sans", bold=False,
                                       italic=True, rotation=10, coordinates="Data"))
        output = Figure()
        output.add_subplot().plot([1, 2], [2, 3])
        with tempfile.TemporaryDirectory() as folder:
            edit.save_figure(Path(folder) / "panel.svg", output, source_axis=0)
        self.assertEqual(output.axes[0].get_title(), "Export title")
        self.assertEqual(output.axes[0].texts[0].get_text(), r"$R_{ct}$")


if __name__ == "__main__":
    unittest.main()
