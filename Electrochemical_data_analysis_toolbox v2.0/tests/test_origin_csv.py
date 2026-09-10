from __future__ import annotations

import csv
import shutil
import sys
import unittest
import uuid
from pathlib import Path


TOOLBOX = Path(__file__).resolve().parents[1]
WORKSPACE = TOOLBOX.parent
SAMPLE = WORKSPACE / "Sample" / "Ni foil 2 cm2"
sys.path.insert(0, str(TOOLBOX))

from origin_csv import ProcessingSettings, infer_sample_name, infer_working_area, process_files, process_sample_folder


def rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.reader(source))


@unittest.skipUnless(SAMPLE.is_dir(), "Ni foil reference sample is not available")
class OriginCsvIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = TOOLBOX / ".test_output" / str(uuid.uuid4())
        self.output.mkdir(parents=True)
        self.settings = ProcessingSettings(
            working_area_cm2=2,
            reference_potential_v=0.929,
            equilibrium_potential_v=1.23,
            solution_resistance_ohm=2.3,
            compensation_percent=90,
            ecsa_cycle_number=9,
            cp_solution_resistance_ohm=2.3,
            cp_compensation_percent=0,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.output)

    def test_folder_name_metadata(self) -> None:
        self.assertEqual(infer_sample_name(SAMPLE), "Ni foil")
        self.assertEqual(infer_working_area(SAMPLE), 2)

    def test_complete_folder_matches_reference_schemas_and_values(self) -> None:
        report = process_sample_folder(SAMPLE, self.settings, self.output)
        self.assertFalse(report.failures)
        self.assertEqual(len(report.created), 12)
        self.assertEqual(len(report.skipped), 5)

        ocv = rows(self.output / "Ni_foil_OCV 30 min.csv")
        self.assertEqual(ocv[:2], [["Time", "Potential"], ["sec", "V"]])
        self.assertEqual(ocv[2], ["1", "-0.3079"])

        active = rows(self.output / "Ni_foil_CV active.csv")
        self.assertEqual(active[:2], [["Potential", "Current"], ["V", "A"]])

        eis = rows(self.output / "Ni_foil_EIS 0.668 V.csv")
        self.assertEqual(eis[:3], [
            ["Working area (cm^2)", "2", "", "", ""],
            ["Frequency", "Z'", "-Z''", "Z", "Phase"],
            ["Hz", "ohm cm2", "ohm cm2", "ohm cm2", "deg"],
        ])
        self.assertEqual(eis[3], ["999000", "6.888", "-1.1336", "6.98", "9.3"])

        lsv = rows(self.output / "Ni_foil_LSV 2.3 ohm.csv")
        self.assertEqual(lsv[1][:2], ["Water-splitting equilibrium potential (V vs. RHE)", "1.23"])
        self.assertEqual(lsv[5], ["File", "Point", "Original Potential", "Original Current", "Potential (V vs. RHE, iR-corrected)", "Current density"])
        self.assertAlmostEqual(float(lsv[7][4]), 0.92901633, places=8)
        self.assertAlmostEqual(float(lsv[7][5]), -0.0039445, places=10)

        cp = rows(self.output / "Ni_foil_CP 10 mA cm2.csv")
        self.assertEqual(cp[0][:2], ["Mode", "Chronopotentiometry"])
        self.assertEqual(cp[7], ["Solution resistance (ohm)", "2.3", "Compensation level (%)", "0"])
        self.assertAlmostEqual(float(cp[11][2]), 1.5273, places=8)

        ca = rows(self.output / "Ni_foil_CA 0.768 V.csv")
        self.assertEqual(ca[4][1], "")
        self.assertEqual(ca[7][1], "")
        self.assertEqual(ca[11], ["0.1", "0.01438", "7.19"])

        cycle = rows(self.output / "Ni_foil_CV cycle_CV.csv")
        self.assertEqual(cycle[0][:2], ["Potential", "Current density"])
        self.assertEqual(cycle[2][:2], ["10 mV/s", "10 mV/s"])
        self.assertEqual(cycle[3][:2], ["0.15", "-0.00016285"])

        delta = rows(self.output / "Ni_foil_CV scan_rate_delta_j.csv")
        self.assertEqual(delta[:2], [["Scan rate", "Delta j mA/cm^2", "Fitted line formula"], ["mV s-1", "mA/cm²", ""]])
        self.assertEqual(delta[2][:2], ["10", "0.0013215"])

    def test_individual_processing_uses_the_same_writers(self) -> None:
        selected = [SAMPLE / "Ni_foil_OCV 30 min.txt", SAMPLE / "Ni_foil_EIS 0.768 V.txt"]
        report = process_files(selected, self.output, self.settings)
        self.assertFalse(report.failures)
        self.assertEqual({path.name for path in report.created}, {"Ni_foil_OCV 30 min.csv", "Ni_foil_EIS 0.768 V.csv"})


if __name__ == "__main__":
    unittest.main()
