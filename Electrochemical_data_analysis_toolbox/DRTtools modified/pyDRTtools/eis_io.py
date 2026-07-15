# -*- coding: utf-8 -*-
"""Robust EIS file loading for pyDRTtools.

The original project expected headerless files with exactly three numeric
columns: frequency, real impedance, and imaginary impedance. This loader keeps
that path working, but also accepts CHI text exports and CHI-extracted tables
with headers such as ``Freq/Hz``, ``Z'/ohm`` and ``Z"/ohm``.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np


class EISFileError(ValueError):
    """Raised when an EIS file cannot be interpreted as impedance data."""


def load_eis_file(filename: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load frequency, Z real, and Z imaginary arrays from an EIS data file.

    Supported inputs include:
    - headerless csv/txt files with frequency, Z', Z" in the first 3 columns
    - CHI-extracted EIS files with labels like Freq/Hz, Z'/ohm, Z"/ohm
    - raw CHI text exports where the EIS table begins after metadata
    """

    path = Path(filename)
    text = _read_text(path)
    rows = [_split_row(line) for line in text.splitlines()]
    rows = [row for row in rows if row]

    header_index, column_map = _find_header(rows)
    if column_map is not None:
        data = _numeric_rows_after_header(rows, header_index + 1, column_map)
    else:
        data = _headerless_numeric_rows(rows)

    if not data:
        raise EISFileError(
            "Could not find EIS columns. Expected CHI-style columns like "
            "Freq/Hz, Z'/ohm, Z\"/ohm, or a headerless numeric 3-column table."
        )

    array = np.asarray(data, dtype=float)
    freq = array[:, 0]
    z_real = array[:, 1]
    z_imag = array[:, 2]

    keep = np.isfinite(freq) & np.isfinite(z_real) & np.isfinite(z_imag) & (freq > 0)
    if not np.any(keep):
        raise EISFileError("No valid EIS rows remain after removing invalid frequencies.")

    freq = freq[keep]
    z_real = z_real[keep]
    z_imag = z_imag[keep]

    freq, z_real, z_imag = _average_duplicate_frequencies(freq, z_real, z_imag)
    if freq.size < 3:
        raise EISFileError("At least 3 valid EIS data points are required.")

    order = np.argsort(freq)[::-1]
    return freq[order], z_real[order], z_imag[order]


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    raise EISFileError(f"Could not decode file: {path}")


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []

    if "," in stripped:
        row = next(csv.reader([stripped], skipinitialspace=True))
    elif "\t" in stripped:
        row = stripped.split("\t")
    else:
        row = re.split(r"\s+", stripped)

    return [value.strip() for value in row if value.strip()]


def _find_header(rows: list[list[str]]) -> tuple[int, dict[str, int] | None]:
    for index, row in enumerate(rows):
        column_map = _map_columns(row)
        if column_map is not None:
            return index, column_map
    return -1, None


def _map_columns(row: list[str]) -> dict[str, int] | None:
    labels = [_normalize_label(value) for value in row]
    freq = _first_matching(labels, _is_frequency_label)
    z_real = _first_matching(labels, _is_real_impedance_label)
    z_imag = _first_matching(labels, _is_imag_impedance_label)

    if freq is None or z_real is None or z_imag is None:
        return None
    return {"freq": freq, "real": z_real, "imag": z_imag}


def _normalize_label(label: str) -> str:
    normalized = label.strip().lower()
    normalized = normalized.replace("omega", "ohm")
    normalized = normalized.replace("ω", "ohm")
    normalized = normalized.replace("′", "'").replace("″", '"')
    return re.sub(r"[\s_\-\[\]\(\)]", "", normalized)


def _first_matching(labels: list[str], predicate) -> int | None:
    for index, label in enumerate(labels):
        if predicate(label):
            return index
    return None


def _is_frequency_label(label: str) -> bool:
    return label in {"freq", "freq/hz", "frequency", "frequency/hz", "f", "f/hz"} or (
        "freq" in label and "hz" in label
    )


def _is_real_impedance_label(label: str) -> bool:
    return (
        (label.startswith("z'") and not label.startswith("z''"))
        or label.startswith("zreal")
        or label.startswith("zre")
        or label.startswith("rez")
        or label.startswith("realz")
        or label in {"zre/ohm", "zreal/ohm"}
    )


def _is_imag_impedance_label(label: str) -> bool:
    return (
        label.startswith('z"')
        or label.startswith("z''")
        or label.startswith("zimag")
        or label.startswith("zim")
        or label.startswith("imz")
        or label.startswith("imagz")
        or label in {"zim/ohm", "zimag/ohm"}
    )


def _numeric_rows_after_header(
    rows: list[list[str]], start: int, column_map: dict[str, int]
) -> list[tuple[float, float, float]]:
    parsed = []
    max_col = max(column_map.values())
    for row in rows[start:]:
        if len(row) <= max_col:
            continue
        try:
            parsed.append(
                (
                    _to_float(row[column_map["freq"]]),
                    _to_float(row[column_map["real"]]),
                    _to_float(row[column_map["imag"]]),
                )
            )
        except ValueError:
            continue
    return parsed


def _headerless_numeric_rows(rows: list[list[str]]) -> list[tuple[float, float, float]]:
    parsed = []
    for row in rows:
        if len(row) < 3:
            continue
        try:
            parsed.append((_to_float(row[0]), _to_float(row[1]), _to_float(row[2])))
        except ValueError:
            continue
    return parsed


def _to_float(value: str) -> float:
    cleaned = value.strip().replace(",", "")
    return float(cleaned)


def _average_duplicate_frequencies(
    freq: np.ndarray, z_real: np.ndarray, z_imag: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique_freq, inverse = np.unique(freq, return_inverse=True)
    if unique_freq.size == freq.size:
        return freq, z_real, z_imag

    real_sum = np.bincount(inverse, weights=z_real)
    imag_sum = np.bincount(inverse, weights=z_imag)
    counts = np.bincount(inverse)
    return unique_freq, real_sum / counts, imag_sum / counts
