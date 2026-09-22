"""Real Tk lifecycle and asynchronous fitting tests (skip if no display)."""
import sys
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tafel_gui import TafelApp
from tafel_io import read_datasets


class GuiTests(unittest.TestCase):
    def test_load_preview_async_fit_and_invalidation(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        root.withdraw()
        root.geometry("1380x900")
        errors = []
        try:
            app = TafelApp(root)
            app.pack(fill="both", expand=True)
            with patch("tafel_gui.messagebox.showerror", side_effect=lambda *args: errors.append(args)):
                source = ROOT.parent / "Sample/Ni foil 2 cm2/Processed/Ni_foil_LSV 2.3 ohm.csv"
                app.datasets = read_datasets(source)
                app.selector.configure(values=[d.name for d in app.datasets])
                app.selector.current(0)
                app.select_dataset()
                self.assertEqual(app.values["reference"].get(), "0.929")
                app.values["eta_min"].set("0.28")
                app.values["eta_max"].set("0.43")
                app.preview()
                app.run_fit()
                deadline = time.monotonic()+10
                while app.busy and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.01)
                self.assertFalse(errors, errors)
                self.assertFalse(app.busy)
                self.assertIsNotNone(app.result)
                self.assertEqual(str(app.export_button["state"]), "normal")
                app.preview()
                self.assertIsNone(app.result)
                self.assertEqual(str(app.export_button["state"]), "disabled")
                # Invalid input is handled without starting a worker.
                app.values["area"].set("0")
                app.run_fit()
                self.assertFalse(app.busy)
                self.assertTrue(errors)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
