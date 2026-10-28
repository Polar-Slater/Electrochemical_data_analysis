import csv
import sys
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLBOX))
sys.path.insert(0, str(TOOLBOX / "Folder batch plotter"))

from correction_settings import parse_ir_fields, resolve_lsv_resistance
from origin_csv import ProcessingSettings, process_files, write_lsv_csv
from plot_lsv_txt import LSVData, LSVMetadata
from lsv_plot_gui import LSVPlotApp
from durability_plot_gui import DurabilityPlotApp
from folder_batch_plot_gui import FolderBatchPlotApp
from processing_gui import DataProcessingPage


class SettingsTests(unittest.TestCase):
    def test_all_numeric_settings_reject_nonfinite_values(self):
        fields = ("working_area_cm2", "reference_potential_v", "equilibrium_potential_v",
                  "solution_resistance_ohm", "compensation_percent",
                  "cp_solution_resistance_ohm", "cp_compensation_percent", "ecsa_cycle_number")
        for field in fields:
            for value in (float("nan"), float("inf"), -float("inf"), True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(ProcessingSettings(1), **{field: value}).validate()

    def test_domains_and_valid_negative_reference(self):
        for changes in ({"working_area_cm2": 0}, {"working_area_cm2": -1},
                        {"solution_resistance_ohm": -1}, {"cp_solution_resistance_ohm": -1},
                        {"compensation_percent": -1}, {"compensation_percent": 101},
                        {"cp_compensation_percent": 101}, {"ecsa_cycle_number": 1.5}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(ProcessingSettings(1), **changes).validate()
        ProcessingSettings(1, reference_potential_v=-0.2, solution_resistance_ohm=0,
                           compensation_percent=100).validate()

    def test_resolution_precedence_and_percentage_rules(self):
        self.assertEqual(resolve_lsv_resistance('a_LSV_2.3 ohm.txt', None, 90), (2.3, .9, 'filename'))
        self.assertEqual(resolve_lsv_resistance('a_LSV_2.3 ohm.txt', 4, 90), (4, .9, 'explicit'))
        self.assertEqual(resolve_lsv_resistance('a_LSV.txt', None, 0), (None, 0, 'not supplied'))
        with self.assertRaisesRegex(ValueError, 'requires a solution resistance'):
            resolve_lsv_resistance('a_LSV.txt', None, 90)
        for name in ('a_LSV -2 ohm.txt', 'a_LSV 1e309 ohm.txt'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                resolve_lsv_resistance(name, None, 90)

    def test_gui_fields_accept_zero_without_resistance_but_reject_invalid_values(self):
        self.assertIsNone(parse_ir_fields('', ''))
        self.assertEqual(parse_ir_fields('', '0'), (None, 0))
        for rs, percent in [('', '90'), ('nan', '0'), ('inf', '90'), ('-1', '90'),
                            ('1', '101'), ('1', 'nan'), ('1', '')]:
            with self.subTest(rs=rs, percent=percent), self.assertRaises(ValueError):
                parse_ir_fields(rs, percent)

    def test_export_labels_and_provenance_match_applied_correction(self):
        data = LSVData(LSVMetadata(), [0.5], [0.01])
        for rs, percent, name, expected, source, applied in [
                (None, 0, 'LSV.txt', .5, 'not supplied', 'no'),
                (None, 100, 'LSV 2 ohm.txt', .48, 'filename', 'yes'),
                (4, 50, 'LSV 2 ohm.txt', .48, 'explicit', 'yes'),
                (0, 100, 'LSV.txt', .5, 'explicit', 'no')]:
            with self.subTest(rs=rs, percent=percent), patch('origin_csv._write_rows') as write:
                write_lsv_csv(data, Path(name), Path('unused.csv'), ProcessingSettings(
                    1, solution_resistance_ohm=rs, compensation_percent=percent))
                rows = write.call_args.args[1]
                self.assertEqual(rows[4], ['Resistance source', source, 'iR correction applied', applied])
                self.assertEqual('iR-corrected' in rows[5][4], applied == 'yes')
                self.assertAlmostEqual(float(rows[7][4]), expected)

    def test_batch_files_resolve_independently_and_fail_without_replacing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            files = [folder / name for name in ['A_LSV 2 ohm.txt', 'B_LSV 4 ohm.txt', 'C_LSV.txt']]
            for source in files:
                source.write_text('date\nLinear Sweep Voltammetry\nPotential/V,Current/A\n0.5,0.01\n')
            output = folder / 'out'
            output.mkdir()
            existing = output / 'C_LSV.csv'
            existing.write_text('preserve existing result')
            report = process_files(files, output, ProcessingSettings(1, compensation_percent=100))
            self.assertEqual(len(report.created), 2)
            self.assertEqual(len(report.failures), 1)
            self.assertIn('C_LSV.txt', report.failures[0])
            self.assertEqual(existing.read_text(), 'preserve existing result')
            for source, expected in zip(files, [.48, .46]):
                with (output / f'{source.stem}.csv').open(encoding='utf-8-sig') as stream:
                    rows = list(csv.reader(stream))
                self.assertAlmostEqual(float(rows[7][4]), expected)


class CorrectionGuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_single_plotter_validation_and_zero_labels(self):
        for cls in (LSVPlotApp, DurabilityPlotApp):
            with self.subTest(plotter=cls.__name__):
                page = cls(self.root)
                page.solution_resistance.set('')
                page.compensation_level.set('90')
                self.assertTrue(page.get_plot_settings()[3])
                page.compensation_level.set('0')
                self.assertFalse(page.get_plot_settings()[3])
                self.assertNotIn('iR-corrected', page.get_potential_axis_label())
                page.rhe_offset.set('nan')
                self.assertTrue(page.get_plot_settings()[3])
                page.destroy()

    def test_folder_selection_does_not_copy_first_resistance(self):
        page = DataProcessingPage(self.root)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'A_LSV 2 ohm.txt').touch()
            with patch('processing_gui.filedialog.askdirectory', return_value=str(folder)):
                page.choose_folder()
            self.assertEqual(page.solution_resistance.get(), '')
            self.assertEqual(page.cp_solution_resistance.get(), '')
            page.solution_resistance.set('7')
            with patch('processing_gui.filedialog.askdirectory', return_value=str(folder)):
                page.choose_folder()
            self.assertEqual(page.solution_resistance.get(), '7')

    def test_batch_missing_and_invalid_resistance_are_reported(self):
        page = FolderBatchPlotApp(self.root)
        item = SimpleNamespace(path=Path('sample_LSV.txt'), measurement='LSV')
        page.included_file_items = lambda: [item]
        page.set_lsv_rs_text('sample_LSV.txt = nan')
        with self.assertRaises(ValueError):
            page.get_lsv_rs_values()
        page.set_lsv_rs_text('sample_LSV.txt = ')
        page.compensation_level.set('90')
        with self.assertRaisesRegex(ValueError, 'sample_LSV.txt'):
            page.validate_correction_settings([item])
        page.compensation_level.set('0')
        page.validate_correction_settings([item])
        self.assertNotIn('iR-corrected', page.lsv_potential_axis_label(0.929, 0, {item.path: 2}, [item]))

    def test_invalid_lsv_gui_export_preserves_existing_file(self):
        page = LSVPlotApp(self.root)
        page.files = [Path('sample_LSV.txt')]
        page.solution_resistance.set('nan')
        page.compensation_level.set('90')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'existing.csv'
            target.write_text('previous results')
            with patch('lsv_plot_gui.filedialog.asksaveasfilename', return_value=str(target)), \
                    patch('lsv_plot_gui.messagebox.showerror') as error:
                page.export_data()
            error.assert_called_once()
            self.assertEqual(target.read_text(), 'previous results')

    def test_ca_gui_export_does_not_claim_cp_correction(self):
        from plot_durability_txt import DurabilityData, DurabilityMetadata
        page = DurabilityPlotApp(self.root)
        page.data = DurabilityData(DurabilityMetadata(), Path('CA.txt'), [1], [.01], 'current')
        page.solution_resistance.set('10')
        page.compensation_level.set('100')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'CA.csv'
            with patch('durability_plot_gui.filedialog.asksaveasfilename', return_value=str(target)):
                page.export_data()
            with target.open(encoding='utf-8') as stream:
                rows = list(csv.reader(stream))
            self.assertIn(['iR correction applied', 'not applicable'], rows)
            self.assertAlmostEqual(float(rows[-1][-1]), .01)


if __name__ == '__main__':
    unittest.main()
