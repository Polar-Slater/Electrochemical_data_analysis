from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plot_eis_txt import HEADER_MARKER
from zview_converter import convert_eis_to_zview, read_zview_rows


class ZViewConversionTests(unittest.TestCase):
    def test_target_folder_export_matches_preview_and_preserves_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sample.txt"
            source.write_text(HEADER_MARKER + "\n100, 2, -3, 4, -50\n")
            target = Path(folder) / "exports" / "ZView"
            rows = read_zview_rows(source)
            destination = convert_eis_to_zview(source, target)
            self.assertEqual(destination, target / "sample_ZView.txt")
            exported = [tuple(map(float, line.split("\t"))) for line in destination.read_text().splitlines()]
            self.assertEqual(exported, rows)
            self.assertFalse(source.with_name("sample_ZView.txt").exists())
            with self.assertRaises(FileExistsError):
                convert_eis_to_zview(source, target)
            self.assertEqual(destination.read_text(), "100.0\t2.0\t-3.0\n")

    def test_export_layout_values_signs_and_source_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sample EIS.txt"
            original = "CHI measurement\n\n" + HEADER_MARKER + "\n1000, 2.5, -3.25, 4.1, -52\n10, 4, 0.5, 4.03, 7\n"
            source.write_text(original, encoding="utf-8")
            result = convert_eis_to_zview(source)
            self.assertEqual(result, source.with_name("sample EIS_ZView.txt"))
            self.assertEqual(result.read_text(), "1000.0\t2.5\t-3.25\n10.0\t4.0\t0.5\n")
            self.assertEqual(source.read_text(), original)

    def test_existing_export_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sample.txt"
            source.write_text(HEADER_MARKER + "\n100, 2, -3, 4, -50\n")
            destination = source.with_name("sample_ZView.txt")
            destination.write_text("previous export")
            with self.assertRaises(FileExistsError):
                convert_eis_to_zview(source)
            self.assertEqual(destination.read_text(), "previous export")

    def test_invalid_input_creates_no_export(self) -> None:
        for content in ("not EIS data", HEADER_MARKER, HEADER_MARKER + "\n100, nan, -3, 4, -50", HEADER_MARKER + "\n0, 2, -3, 4, -50"):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "invalid.txt"
                source.write_text(content)
                with self.assertRaises(ValueError):
                    convert_eis_to_zview(source)
                self.assertFalse(source.with_name("invalid_ZView.txt").exists())


if __name__ == "__main__":
    unittest.main()
