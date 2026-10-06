from pathlib import Path
import tempfile
import unittest

import numpy as np
from eis_app.importer import EISImportError, read_table


class ImportTests(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text(text, encoding="utf-8-sig")
            return read_table(path)

    def test_signed_and_negated_imaginary(self):
        f, z = self.read("Freq/Hz,Z'/ohm,Z\"/ohm\n1,2,-3\n10,4,5\n100,6,-7\n")
        np.testing.assert_array_equal(f, [100, 10, 1])
        np.testing.assert_array_equal(z, [6-7j, 4+5j, 2-3j])
        _, negated = self.read("Frequency (Hz),Z' (ohm),-Z'' (ohm)\n1,2,3\n10,4,-5\n100,6,7\n")
        np.testing.assert_array_equal(z, negated)

    def test_origin_units_and_area(self):
        f, z = self.read("Working area (cm^2),2\nFrequency,Z',-Z''\nHz,ohm cm2,ohm cm2\n1,4,6\n10,8,-10\n100,12,14\n")
        np.testing.assert_array_equal(z, [6-7j, 4+5j, 2-3j])

    def test_headerless_delimiters(self):
        for separator in (",", "\t", " "):
            with self.subTest(separator=separator):
                _, z = self.read("\n".join(separator.join(row) for row in [("1", "2", "-3"), ("10", "4", "5"), ("100", "6", "-7")]))
                np.testing.assert_array_equal(z, [6-7j, 4+5j, 2-3j])

    def test_reject_invalid_data_without_silent_changes(self):
        for text in (
            "1,2,-3\n1,4,-5\n100,6,-7",  # duplicates
            "0,2,-3\n10,4,-5\n100,6,-7",
            "1,2,-3\n10,nan,-5\n100,6,-7",
            "1,2,-3\n10,4,-5\n100,6",
            "Frequency,Z',-Z''\nHz,ohm cm2,ohm cm2\n1,2,3\n10,4,5\n100,6,7",
            "Frequency (kHz),Z',Z''\n1,2,-3\n10,4,-5\n100,6,-7",
        ):
            with self.subTest(text=text):
                with self.assertRaises(EISImportError):
                    self.read(text)

    def test_toolbox_samples_round_trip_to_raw_ohms(self):
        samples = Path(__file__).resolve().parents[2] / "Sample" / "Ni foil 2 cm2"
        if not samples.exists():
            self.skipTest("Workspace sample data are not available on this computer")
        for raw in samples.glob("*EIS*.txt"):
            freq, z = read_table(raw)
            for exported in (samples / "Processed data" / (raw.stem + "_processed.csv"), samples / "Processed" / (raw.stem + ".csv")):
                if exported.exists():
                    f2, z2 = read_table(exported)
                    np.testing.assert_allclose(freq, f2)
                    np.testing.assert_allclose(z, z2)


if __name__ == "__main__":
    unittest.main()
