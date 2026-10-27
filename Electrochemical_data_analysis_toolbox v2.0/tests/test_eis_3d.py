import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLBOX))
sys.path.insert(0, str(TOOLBOX / "Folder batch plotter"))

from plot_eis_txt import EISData, HEADER_MARKER, read_eis_data, read_operating_voltage
from eis_plot_gui import EISPlotApp
from folder_batch_plot_gui import FolderBatchPlotApp


class VoltageTests(unittest.TestCase):
    def test_metadata_not_filename_or_amplitude(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "EIS 9 V.txt"
            path.write_text('Init E (V) = -2.5e-1\nAmplitude (V) = 0.005\n' + HEADER_MARKER + '\n100, 2, -3, 4, -45\n')
            data = read_eis_data(path)
            self.assertEqual(data.operating_voltage_v, -0.25)
            self.assertEqual(data.minus_z_imag_ohm, [3])
        for value in ("nan", "inf", "bad"):
            self.assertIsNone(read_operating_voltage([f"Init E (V) = {value}"]))
        self.assertIsNone(read_operating_voltage(["Amplitude (V) = 0.005"]))
        self.assertEqual(read_operating_voltage(["Init E (V) = 0"]), 0)


class PlotTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.data = EISData(Path("EIS.txt"), [100, 10, 1], [2, 3, 4], [1, -2, -1], [3, 4, 5], [20, -30, -20], 0.7)

    def tearDown(self):
        self.root.destroy()

    def test_single_plot_and_export(self):
        app = EISPlotApp(self.root)
        app.plot_type.set("3D Nyquist")
        app.redraw()  # Empty 3D axes must also render.
        app.data = self.data
        app.operating_voltage.set("0.7")
        app.working_area.set("2")
        app.redraw()
        x, y, z = app.ax.lines[0].get_data_3d()
        self.assertEqual(list(x), [4, 6, 8])
        self.assertEqual(list(y), [0.7] * 3)
        self.assertEqual(list(z), [-2, 4, 2])
        self.assertEqual(app.ax.get_ylabel(), "Operating voltage (V)")
        self.assertTrue(app.ax.get_zlabel().startswith("-Z''"))
        self.assertEqual(app.ax.get_aspect(), "equalxz")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "3d.png"
            app.plot_editor.save_figure(str(path))
            self.assertGreater(path.stat().st_size, 1000)
        app.operating_voltage.set("nan")
        app.redraw()
        self.assertEqual(len(app.ax.lines), 0)
        for mode in ("Nyquist", "Bode", "3D Nyquist"):
            app.plot_type.set(mode)
            app.operating_voltage.set("0")
            app.redraw()
            app.canvas.draw()
        app.clear_plot()
        self.assertIsNone(app.data)

    def test_batch_stacks_and_reports_missing_voltage(self):
        app = FolderBatchPlotApp(self.root)
        app.eis_plot_type.set("3D Nyquist")
        items = [SimpleNamespace(path=Path(f"{i}.txt"), label=f"Sample {i}") for i in range(3)]
        data = [self.data, EISData(Path("b.txt"), [1], [3], [-2], [4], [-30], 0.8),
                EISData(Path("missing.txt"), [1], [3], [-2], [4], [-30])]
        with patch.object(app, "get_eis", side_effect=data), patch("folder_batch_plot_gui.messagebox.showwarning") as warning:
            app.plot_eis(items)
            warning.assert_called_once()
            self.assertIn("missing or invalid CHI Init E", warning.call_args.args[1])
        self.assertEqual(len(app.ax.lines), 2)
        self.assertEqual(list(app.ax.lines[0].get_data_3d()[1]), [0.7] * 3)
        self.assertEqual(list(app.ax.lines[1].get_data_3d()[1]), [0.8])
        self.assertEqual(list(app.ax.lines[0].get_data_3d()[2]), [-1, 2, 1])
        self.assertTrue(app.ax.get_zlabel().startswith("-Z''"))
        app.canvas.draw()


if __name__ == "__main__":
    unittest.main()
