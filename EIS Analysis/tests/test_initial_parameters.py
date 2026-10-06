from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pyimpspec
from eis_app.initial_parameters import apply_parameters, parameter_rows


class InitialParameterTests(unittest.TestCase):
    def test_values_bounds_and_fixed_survive_serialization(self):
        circuit = pyimpspec.parse_cdc("R(RQ)(RQ)")
        rows = parameter_rows(circuit)
        self.assertEqual(len(rows), 7)
        rows[0].update(value="2.5", lower="1", upper="5", fixed=True)
        rows[2].update(value="1.58e-3", lower="1e-8", upper="inf")
        edited = pyimpspec.parse_cdc(apply_parameters(circuit, rows).serialize())
        resistor = edited.get_elements()[0]
        self.assertEqual(resistor.get_value("R"), 2.5)
        self.assertEqual(resistor.get_lower_limit("R"), 1)
        self.assertEqual(resistor.get_upper_limit("R"), 5)
        self.assertTrue(resistor.is_fixed("R"))
        self.assertAlmostEqual(edited.get_elements()[2].get_value("Y"), 1.58e-3)
        self.assertNotEqual(circuit.get_elements()[0].get_value("R"), 2.5)

    def test_invalid_edits_are_atomic(self):
        circuit = pyimpspec.parse_cdc("R(RQ)")
        original = circuit.serialize()
        for invalid in (dict(value="nan"), dict(value="abc"), dict(lower="4", upper="3"),
                        dict(value="20", upper="10"), dict(upper="nan")):
            with self.subTest(invalid=invalid):
                rows = parameter_rows(circuit)
                rows[0]["value"] = "3"
                rows[-1].update(invalid)
                with self.assertRaises(ValueError):
                    apply_parameters(circuit, rows)
                self.assertEqual(circuit.serialize(), original)

    def test_sample_fitting_respects_initial_bounds_and_fixed(self):
        import deareis
        import numpy as np
        from eis_app.importer import parse_data
        sample = Path(__file__).resolve().parents[2] / "Sample" / "SS310 1 cm2" / "SS310_EIS 0p786 V.txt"
        if not sample.exists():
            self.skipTest("Workspace samples unavailable")
        data = deareis.DataSet.from_dict(parse_data(sample)[0].to_dict())
        circuit = pyimpspec.parse_cdc("R{R=0.229}(R{R=5.01}Q{Y=0.00158,n=0.871})(R{R=11.6}Q{Y=1.47e-7,n=0.901})")
        rows = parameter_rows(circuit)
        rows[0].update(value="0.25", lower="0.1", upper="0.5", fixed=True)
        rows[1].update(lower="4", upper="6")
        edited = apply_parameters(circuit, rows)
        fit = deareis.fit_circuit(data, deareis.FitSettings(
            cdc=edited.serialize(), method=deareis.CNLSMethod.LEASTSQ,
            weight=deareis.Weight.MODULUS, max_nfev=2000, timeout=60,
        ), num_procs=1)
        self.assertEqual(fit.circuit.get_elements()[0].get_value("R"), 0.25)
        self.assertTrue(4 <= fit.circuit.get_elements()[1].get_value("R") <= 6)
        self.assertTrue(np.isfinite(fit.get_impedances()).all())
        restored_settings = pyimpspec.parse_cdc(fit.settings.cdc)
        self.assertTrue(restored_settings.get_elements()[0].is_fixed("R"))
