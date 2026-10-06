"""Import toolbox EIS data without changing the physical impedance convention.

All returned spectra use Hz and Z = Z' + j Z'' in ohms. No data points are
averaged or discarded. GPL-3.0-or-later.
"""
import csv
from pathlib import Path
import re

import numpy as np


class EISImportError(ValueError):
    pass


def _label(value):
    value = value.lower().replace("′", "'").replace("″", "''").replace('"', "''")
    value = value.replace("−", "-").replace("²", "2").replace("ω", "ohm")
    return re.sub(r"[\s_\[\]()^·⋅]", "", value)


def _split(line):
    if "," in line:
        return next(csv.reader([line], skipinitialspace=True))
    if "\t" in line:
        return line.split("\t")
    return re.split(r"\s+", line.strip())


def _columns(row):
    found = {}
    for i, cell in enumerate(row):
        name = _label(cell)
        bare = name.lstrip("-")
        if name.startswith("freq") or name in ("f", "f/hz"):
            found["frequency"] = i
        elif bare.startswith(("z''", "zim", "imz", "imagz", "imaginary")):
            found["imaginary"] = i
        elif bare.startswith(("z'", "zre", "rez", "realz", "real")):
            found["real"] = i
    return found if len(found) == 3 else None


def read_table(path):
    """Return frequency and complex impedance arrays for a text table."""
    path = Path(path)
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
    rows = [(n, _split(line)) for n, line in enumerate(text.splitlines(), 1) if line.strip()]
    area = None
    for _, row in rows:
        if _label(row[0]).startswith("workingarea") and len(row) > 1:
            try:
                area = float(row[1])
            except ValueError as exc:
                raise EISImportError("Working area must be a positive number in cm^2.") from exc

    header = None
    columns = None
    start = 0
    for index, (_, row) in enumerate(rows):
        columns = _columns(row)
        if columns:
            header, start = row, index + 1
            break
    if header is None:
        columns = {"frequency": 0, "real": 1, "imaginary": 2}
        # Headerless inputs must be numeric tables, not unrecognized instrument metadata.
        if not rows or len(rows[0][1]) != 3:
            raise EISImportError("No EIS header found. Use a CHI export or frequency, Z', Z'' table.")
        try:
            [float(cell) for cell in rows[0][1]]
        except ValueError as exc:
            raise EISImportError("Unrecognized EIS columns. Expected frequency, Z', and Z'' (or -Z'').") from exc

    units = header[:] if header else ["Hz", "ohm", "ohm"]
    # Toolbox/Origin exports place units on the line immediately after the column labels.
    if header and start < len(rows):
        unit_row = rows[start][1]
        fi = columns["frequency"]
        if len(unit_row) > fi and _label(unit_row[fi]) in ("hz", "khz", "mhz"):
            if len(unit_row) < len(header):
                raise EISImportError("Incomplete units row.")
            units = [a + " " + b for a, b in zip(header, unit_row)]
            start += 1

    frequency_unit = _label(units[columns["frequency"]])
    if "khz" in frequency_unit or "mhz" in frequency_unit:
        raise EISImportError("Frequency must be in Hz; convert kHz/MHz before importing.")
    real_unit = _label(units[columns["real"]])
    imag_unit = _label(units[columns["imaginary"]])
    normalized = "cm2" in real_unit or "cm2" in imag_unit
    if normalized:
        if not ("cm2" in real_unit and "cm2" in imag_unit):
            raise EISImportError("Real and imaginary impedance units must match.")
        if area is None or not np.isfinite(area) or area <= 0:
            raise EISImportError("Area-normalized data need a 'Working area (cm^2),value' row to recover ohms. Open the raw CHI file instead.")
    scale = area if normalized else 1.0
    sign = -1 if header and _label(header[columns["imaginary"]]).startswith("-") else 1
    values = []
    max_column = max(columns.values())
    for line, row in rows[start:]:
        if row[0].strip().startswith("#"):
            continue
        if len(row) <= max_column:
            raise EISImportError(f"Line {line}: incomplete data row.")
        try:
            values.append([float(row[columns[key]]) for key in ("frequency", "real", "imaginary")])
        except ValueError as exc:
            raise EISImportError(f"Line {line}: nonnumeric data; no points have been discarded.") from exc
    array = np.asarray(values, dtype=float)
    if len(array) < 3:
        raise EISImportError("At least three EIS points are required.")
    if not np.isfinite(array).all() or (array[:, 0] <= 0).any():
        raise EISImportError("All values must be finite and frequencies must be positive.")
    if len(np.unique(array[:, 0])) != len(array):
        raise EISImportError("Repeated frequencies found. Import each measurement sweep separately; points were not averaged.")
    order = np.argsort(array[:, 0])[::-1]
    return array[order, 0], (array[order, 1] + 1j * sign * array[order, 2]) / scale


def parse_data(path):
    """Use the toolbox importer for text files and upstream parsers otherwise."""
    import pyimpspec
    if Path(path).suffix.lower() not in (".txt", ".csv", ".tsv"):
        return pyimpspec.parse_data(path)
    frequency, impedance = read_table(path)
    return [pyimpspec.DataSet(frequency, impedance, path=str(path), label=Path(path).stem)]
