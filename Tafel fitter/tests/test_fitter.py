from __future__ import annotations

from contextlib import contextmanager
import shutil
import sys
import threading
import unittest
import uuid
from dataclasses import replace
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT))
from tafel_core import F, R, FitCancelled, FitSettings, fit
from tafel_io import Dataset, Preparation, prepare, read_datasets
from tafel_output import draw, export_bundle


def synthetic(sign=1):
    eta = np.linspace(0.01, 0.18, 171)
    current = 2e-6 * 10**(eta / 0.060)
    return Dataset(Path("synthetic.csv"), "synthetic", sign*eta, sign*current, "eta")


@contextmanager
def test_directory():
    # Python 3.14's Windows private-temp ACLs exclude some sandbox tokens.
    directory = ROOT / ("test-work-" + uuid.uuid4().hex)
    directory.mkdir()
    try:
        yield directory
    finally:
        if directory.resolve().parent != ROOT.resolve():
            raise RuntimeError("Refusing to clean outside the test workspace.")
        shutil.rmtree(directory)


class FitTests(unittest.TestCase):
    def test_known_anodic_and_cathodic_slopes(self):
        for sign, branch in [(1, "Anodic"), (-1, "Cathodic")]:
            with self.subTest(branch=branch):
                data = prepare(synthetic(sign), Preparation(area=2, branch=branch))
                result = fit(data, FitSettings(width_max_mv=20, width_step_mv=5, r2_step=0.02))
                self.assertAlmostEqual(result.best.slope_mv, sign*60, places=5)
                self.assertAlmostEqual(result.best.i0_a, 2e-6, places=11)
                c = result.best
                xs = data.eta[c.start:c.stop]
                ys = np.log10(np.abs(data.current_a[c.start:c.stop]))
                regression = np.polyfit(xs, ys, 1)
                self.assertAlmostEqual(c.slope_mv, 1000/regression[0], places=5)
                self.assertLessEqual(abs(xs[-1]-xs[0])*1000, c.width_mv+1e-7)

    def test_paper_residual_and_nonunit_n(self):
        data = prepare(synthetic(), Preparation())
        settings = FitSettings(width_max_mv=12, r2_step=0.02, electrons=2)
        result = fit(data, settings)
        c = result.best
        observed = np.polyfit(data.eta[c.start:c.stop], data.current_a[c.start:c.stop], 1)[0]
        expected = abs(observed - c.i0_a*2*F/(R*settings.temperature))
        self.assertAlmostEqual(c.residue, expected, places=10)

    def test_ir_and_area_units(self):
        source = synthetic()
        raw = replace(source, potential=source.potential + 1.23 - 0.929 + source.current*2.3*0.9, mode="raw")
        data = prepare(raw, Preparation(area=2, reference=0.929, resistance=2.3, compensation=90))
        np.testing.assert_allclose(data.eta, source.potential, atol=1e-14)
        np.testing.assert_allclose(data.density, source.current*500)

    def test_already_prepared_data_are_not_corrected_again(self):
        source = synthetic()
        a = prepare(source, Preparation())
        b = prepare(source, Preparation(reference=1, equilibrium=4, resistance=900, compensation=100))
        np.testing.assert_array_equal(a.eta, b.eta)

    def test_reject_invalid_settings_and_folded_curve(self):
        source = synthetic()
        data = prepare(source, Preparation())
        for settings in [FitSettings(width_step_mv=0), FitSettings(r2_min=1.1), FitSettings(temperature=0),
                         FitSettings(bin_mv=float("nan")), FitSettings(width_step_mv=1e-9)]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                fit(data, settings)
        with self.assertRaisesRegex(ValueError, "monotonic"):
            prepare(replace(source, potential=np.r_[source.potential[:100], source.potential[99::-1]],
                            current=np.r_[source.current[:100], source.current[99::-1]]), Preparation())

    def test_cancel_and_no_fits(self):
        data = prepare(synthetic(), Preparation())
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(FitCancelled):
            fit(data, FitSettings(), cancel)
        with self.assertRaisesRegex(ValueError, "No admissible"):
            fit(data, FitSettings(width_min_mv=500, width_max_mv=600))

    def test_derivative_cutoff_and_minimum_points(self):
        source = synthetic()
        x = np.linspace(0.005, 0.3, 301)
        # A saturating polarization curve with a known derivative maximum.
        source = replace(source, potential=x, current=0.01/(1+np.exp(-(x-0.15)/0.02)))
        data = prepare(source, Preparation())
        result = fit(data, FitSettings(derivative_cutoff=True, polynomial_order=9, r2_step=0.02))
        self.assertLess(abs(data.eta[result.cutoff_index-1]-0.15), 0.025)
        self.assertLessEqual(result.best.stop, result.cutoff_index)


class ReaderTests(unittest.TestCase):
    sample = PROJECT / "Sample/Ni foil 2 cm2"

    def test_all_project_sample_lsv_formats(self):
        raw = read_datasets(self.sample / "Ni_foil_LSV 2.3 ohm.txt")[0]
        self.assertEqual(raw.metadata["area"], 2)
        self.assertEqual(raw.metadata["resistance"], 2.3)
        for folder, name in [("Processed", "Ni_foil_LSV 2.3 ohm.csv"),
                             ("Processed data", "Ni_foil_LSV 2.3 ohm_processed.csv")]:
            processed = read_datasets(self.sample / folder / name)[0]
            np.testing.assert_allclose(processed.potential, raw.potential)
            np.testing.assert_allclose(processed.current, raw.current, atol=1.1e-11)
        tafel = read_datasets(self.sample / "Processed data/Ni_foil_LSV 2.3 ohm_tafel.csv")[0]
        self.assertEqual(tafel.mode, "eta")
        self.assertTrue(tafel.density)
        np.testing.assert_allclose(tafel.current, raw.current*500)
        processed = read_datasets(self.sample / "Processed/Ni_foil_LSV 2.3 ohm.csv")[0]
        settings = Preparation(**processed.metadata, eta_min=0.28, eta_max=0.43)
        data = prepare(processed, settings)
        result = fit(data, FitSettings(r2_step=0.01))
        self.assertGreater(result.best.slope_mv, 0)

    def test_original_fitter_examples(self):
        folder = PROJECT / "Tafel_Fitter_v1.51/Input_files"
        for path in folder.glob("*.csv"):
            if "minimized" in path.name:
                continue
            data = read_datasets(path)[0]
            self.assertEqual(data.mode, "eta")
            branch = "Cathodic" if "Pt-" in path.name else "Anodic"
            result = fit(prepare(data, Preparation(branch=branch)), FitSettings(width_step_mv=10, r2_step=0.02))
            self.assertTrue(np.isfinite(result.best.slope_mv))

    def test_combined_export_separates_files_and_rejects_malformed_rows(self):
        with test_directory() as directory:
            path = Path(directory)/"combined.csv"
            path.write_text("File,Point,Original Potential,Original Current\n,,V,mA\na,1,0.5,2\nb,1,0.6,3\n", encoding="utf-8")
            datasets = read_datasets(path)
            self.assertEqual([d.name for d in datasets], ["a", "b"])
            self.assertEqual(datasets[0].current[0], 0.002)
            path.write_text("Potential/V,Current/A\n0.1,1\n0.2,bad\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 3"):
                read_datasets(path)

    def test_export_round_trip_and_figures(self):
        source = synthetic()
        prep = Preparation(area=2)
        data = prepare(source, prep)
        settings = FitSettings(width_step_mv=10, r2_step=0.02)
        result = fit(data, settings)
        figure = Figure(figsize=(10, 7))
        draw(figure, data, settings, result)
        # The plotted fit must use the same current-density convention as the data.
        fitted = figure.axes[1].lines[1]
        np.testing.assert_allclose(fitted.get_xdata(), data.log_density[result.best.start:result.best.stop], atol=1e-8)
        with test_directory() as directory:
            output = export_bundle(Path(directory), source, prep, settings, data, result, figure)
            self.assertEqual(len(list(output.iterdir())), 5)
            loaded = read_datasets(output/"tafel_data.csv")[0]
            np.testing.assert_allclose(loaded.potential, data.eta)
            np.testing.assert_allclose(loaded.current, data.density)
            self.assertGreater((output/"tafel_fit.png").stat().st_size, 10000)


if __name__ == "__main__":
    unittest.main()
