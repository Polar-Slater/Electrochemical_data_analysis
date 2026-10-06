from dataclasses import replace
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import deareis
from deareis.config.defaults import DEFAULT_DRT_SETTINGS


class AnalysisTests(unittest.TestCase):
    def test_fitting_drt_and_project_round_trip(self):
        frequency = np.logspace(5, -1, 61)
        circuit = deareis.parse_cdc("R{R=5}(R{R=100}C{C=0.0001})")
        data = deareis.DataSet(frequency, circuit.get_impedances(frequency), label="Synthetic RC")
        fit = deareis.fit_circuit(data, deareis.FitSettings(
            cdc="R{R=4}(R{R=80}C{C=0.0002})", method=deareis.CNLSMethod.LEAST_SQUARES,
            weight=deareis.Weight.PROPORTIONAL, max_nfev=300, timeout=60,
        ), num_procs=1)
        # Integration check: the default optimizer should recover this spectrum
        # within 0.1%, without requiring a specific numerical stopping point.
        np.testing.assert_allclose(fit.get_impedances(), data.get_impedances(), rtol=1e-3)
        drt = deareis.calculate_drt(data, replace(
            DEFAULT_DRT_SETTINGS, method=deareis.DRTMethod.TR_NNLS,
            mode=deareis.DRTMode.REAL, lambda_value=1e-3,
            tr_nnls_lambda_method=deareis.TRNNLSLambdaMethod.NONE,
        ), num_procs=1)
        self.assertTrue(np.isfinite(drt.real_gammas).all())
        peak_tau = drt.time_constants[np.argmax(drt.real_gammas)]
        self.assertLess(abs(np.log10(peak_tau / 0.01)), 0.5)
        project = deareis.Project()
        project.add_data_set(data)
        project.add_fit(data, fit)
        project.add_drt(data, drt)
        restored = deareis.Project.from_dict(project.to_dict(session=False))
        restored_data = restored.get_data_sets()[0]
        self.assertEqual(len(restored.get_fits(restored_data)), 1)
        self.assertEqual(len(restored.get_drts(restored_data)), 1)
        np.testing.assert_allclose(restored_data.get_impedances(), data.get_impedances())


if __name__ == "__main__":
    unittest.main()
