import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

TOOLBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLBOX))
sys.path.insert(0, str(TOOLBOX / "Folder batch plotter"))

from durability_plot_gui import DurabilityPlotApp
from folder_batch_plot_gui import FolderBatchPlotApp
from origin_csv import ProcessingSettings, write_durability_csv
from plot_durability_txt import (
    DurabilityData, DurabilityMetadata, MODE_CHRONOPOTENTIOMETRY,
    MODE_MULTI_CURRENT, parse_metadata,
)


def trace(current=-0.01, mode=MODE_CHRONOPOTENTIOMETRY, segment=1):
    return DurabilityData(
        DurabilityMetadata(mode=mode, current_a=current, segment=segment),
        Path("cp.txt"), [1, 2], [0.5, 0.7], "potential",
    )


class CPCorrectionTests(unittest.TestCase):
    def test_recorded_sign_is_preserved_in_summary_and_calculation(self):
        metadata = parse_metadata(["Multi-Current Steps", "i1 (A) = -0.01", "T1 (s) = 10"])
        self.assertEqual(replace(trace(), metadata=metadata).display_current_a, -0.01)
        for current, expected in [(-0.01, [0.8, 1.0]), (0.01, [0.6, 0.8]), (0, [0.7, 0.9])]:
            with self.subTest(current=current):
                actual = trace(current).corrected_potentials(0.2, 10, 1)
                for value, wanted in zip(actual, expected):
                    self.assertAlmostEqual(value, wanted)

    def test_all_cp_paths_use_the_same_signed_correction(self):
        data = trace()
        page = SimpleNamespace(data=data)
        expected = data.corrected_potentials(0.2, 10, 0.5)
        self.assertEqual(DurabilityPlotApp.get_adjusted_potentials(page, 0.2, (10, 0.5)), expected)
        self.assertEqual(FolderBatchPlotApp.get_adjusted_cp_potentials(data, 0.2, (10, 0.5)), expected)
        settings = ProcessingSettings(1, reference_potential_v=0.2,
                                      cp_solution_resistance_ohm=10, cp_compensation_percent=50)
        with patch("origin_csv._write_rows") as write:
            write_durability_csv(data, Path("unused.csv"), settings)
        rows = write.call_args.args[1]
        self.assertEqual(rows[1][1], "-0.01")
        self.assertEqual(rows[6][1], "-10")
        for row, wanted in zip(rows[11:], expected):
            self.assertAlmostEqual(float(row[2]), wanted)

    def test_multistep_correction_is_rejected_in_all_paths(self):
        for data in [trace(mode=MODE_MULTI_CURRENT), trace(segment=2)]:
            with self.subTest(mode=data.metadata.mode):
                with self.assertRaisesRegex(ValueError, "multi-step CP"):
                    data.corrected_potentials(0, 10, 1)
                with self.assertRaisesRegex(ValueError, "multi-step CP"):
                    DurabilityPlotApp.get_adjusted_potentials(SimpleNamespace(data=data), 0, (10, 1))
                with self.assertRaisesRegex(ValueError, "multi-step CP"):
                    FolderBatchPlotApp.get_adjusted_cp_potentials(data, 0, (10, 1))
                with patch("origin_csv._write_rows") as write:
                    with self.assertRaisesRegex(ValueError, "multi-step CP"):
                        write_durability_csv(data, Path("unused.csv"), ProcessingSettings(
                            1, cp_solution_resistance_ohm=10, cp_compensation_percent=100))
                    write.assert_not_called()

    def test_zero_compensation_keeps_multistep_and_missing_current_usable(self):
        for data in [trace(mode=MODE_MULTI_CURRENT), trace(segment=2), trace(current=None)]:
            with self.subTest(data=data):
                actual = data.corrected_potentials(0.2)
                self.assertAlmostEqual(actual[0], 0.7)
                self.assertAlmostEqual(actual[1], 0.9)

    def test_invalid_correction_inputs_fail(self):
        for current in (None, float("nan"), float("inf")):
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, "current"):
                trace(current).corrected_potentials(0, 10, 1)
        for resistance in (None, -1, float("nan"), float("inf")):
            with self.subTest(resistance=resistance), self.assertRaisesRegex(ValueError, "resistance"):
                trace().corrected_potentials(0, resistance, 1)
        for fraction in (-0.1, 1.01, float("nan"), float("inf")):
            with self.subTest(fraction=fraction), self.assertRaisesRegex(ValueError, "(?i)compensation"):
                trace().corrected_potentials(0, 10, fraction)

    def test_ca_export_does_not_apply_cp_correction(self):
        data = replace(trace(), value_kind="current", values=[-0.01, 0.02])
        with patch("origin_csv._write_rows") as write:
            write_durability_csv(data, Path("unused.csv"), ProcessingSettings(
                2, reference_potential_v=0.929, cp_solution_resistance_ohm=10, cp_compensation_percent=100))
        rows = write.call_args.args[1]
        self.assertEqual([float(row[2]) for row in rows[11:]], [-5, 10])

    def test_single_export_reports_error_before_opening_output(self):
        data = trace(mode=MODE_MULTI_CURRENT)
        page = SimpleNamespace(data=data, status=Mock(),
                               get_plot_settings=lambda: (0, None, (10, 1), []))
        page.get_adjusted_potentials = lambda offset, ir: DurabilityPlotApp.get_adjusted_potentials(page, offset, ir)
        with patch("durability_plot_gui.filedialog.asksaveasfilename", return_value="unused.csv"), \
                patch("durability_plot_gui.messagebox.showerror") as error, patch.object(Path, "open") as opened:
            DurabilityPlotApp.export_data(page)
        error.assert_called_once()
        opened.assert_not_called()

    def test_batch_export_checks_all_traces_before_writing(self):
        items = [SimpleNamespace(path=Path("constant.txt"), measurement="CP"),
                 SimpleNamespace(path=Path("steps.txt"), measurement="CP")]
        page = SimpleNamespace(
            validate_correction_settings=lambda *args, **kwargs: None,
            included_file_items=lambda: items, is_deposition_file=lambda item: False,
            get_rhe_offset=lambda: (0, None), get_cp_ir_compensation=lambda: ((10, 1), None),
            get_cp=lambda item: trace(mode=MODE_MULTI_CURRENT) if item is items[1] else trace(),
            get_adjusted_cp_potentials=FolderBatchPlotApp.get_adjusted_cp_potentials,
        )
        with patch.object(Path, "open") as opened:
            with self.assertRaisesRegex(ValueError, "steps.txt:.*multi-step CP"):
                FolderBatchPlotApp.export_cp_data(page, Path("unused"))
        opened.assert_not_called()


if __name__ == "__main__":
    unittest.main()
