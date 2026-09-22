"""Import electrochemical impedance spectra from common text formats."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class EISData:
    """A single spectrum using the mathematical Z = Z' + jZ'' sign."""

    frequency: np.ndarray
    real: np.ndarray
    imaginary: np.ndarray
    source: Path

    @property
    def impedance(self) -> np.ndarray:
        return self.real + 1j * self.imaginary


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9+-]", "", value.lower().replace("ω", "omega"))


def _column_kind(header: str) -> tuple[str | None, bool]:
    raw = header.strip().lower()
    key = _normalise_header(header)
    if any(token in key for token in ("freq", "frequency", "fhz")) or key in {"hz", "f"}:
        return "frequency", False
    if re.match(r"^z\s*['′]", raw):
        return "real", False
    if re.match(r'^z\s*(?:"|[″]|\'{2})', raw):
        return "imaginary", False
    if key in {"zreal", "rez", "zre", "real", "zprime", "z1", "ohmreal"} or (
        "real" in key and "z" in key
    ):
        return "real", False
    if key in {"zimag", "imz", "zim", "imag", "zimaginary", "z2", "ohmimag"} or (
        "imag" in key and "z" in key
    ):
        displayed_negative = raw.lstrip().startswith("-") or "-zim" in raw or "-im" in raw
        return "imaginary", displayed_negative
    return None, False


def _split(line: str, delimiter: str | None) -> list[str]:
    return re.split(r"\s+", line.strip()) if delimiter is None else next(csv.reader([line], delimiter=delimiter))


def _float(value: str) -> float:
    text = value.strip().replace("−", "-")
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    return float(text)


def load_eis(path: str | Path) -> EISData:
    """Load CHI, CSV, TSV, TXT, or Gamry-style DTA impedance data."""

    source = Path(path)
    lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    if not lines:
        raise ValueError("The selected file is empty.")
    sample = "\n".join(lines[:30])
    counts = {delimiter: sample.count(delimiter) for delimiter in (",", "\t", ";")}
    delimiter = max(counts, key=counts.get) if max(counts.values()) else None

    header_index: int | None = None
    indices: dict[str, int] = {}
    negate_imaginary = False
    for line_index, line in enumerate(lines):
        found: dict[str, int] = {}
        negative = False
        for column_index, field in enumerate(_split(line, delimiter)):
            kind, shown_negative = _column_kind(field)
            if kind and kind not in found:
                found[kind] = column_index
                if kind == "imaginary":
                    negative = shown_negative
        if {"frequency", "real", "imaginary"}.issubset(found):
            header_index, indices, negate_imaginary = line_index, found, negative
            break

    rows: list[tuple[float, float, float]] = []
    start = (header_index + 1) if header_index is not None else 0
    for line in lines[start:]:
        fields = _split(line, delimiter)
        try:
            if indices:
                values = tuple(_float(fields[indices[name]]) for name in ("frequency", "real", "imaginary"))
            else:
                numeric: list[float] = []
                for field in fields:
                    try:
                        numeric.append(_float(field))
                    except ValueError:
                        continue
                if len(numeric) < 3:
                    continue
                values = tuple(numeric[:3])
            rows.append(values)  # type: ignore[arg-type]
        except (ValueError, IndexError):
            continue
    if len(rows) < 4:
        raise ValueError("Could not find at least four EIS rows (frequency, Z real, Z imaginary).")

    values = np.asarray(rows, dtype=float)
    frequency, real, imaginary = values.T
    if negate_imaginary:
        imaginary = -imaginary
    valid = np.isfinite(values).all(axis=1) & (frequency > 0)
    frequency, real, imaginary = frequency[valid], real[valid], imaginary[valid]
    if frequency.size < 4:
        raise ValueError("The file has fewer than four finite, positive-frequency EIS points.")
    order = np.argsort(frequency)[::-1]
    return EISData(frequency[order], real[order], imaginary[order], source)
