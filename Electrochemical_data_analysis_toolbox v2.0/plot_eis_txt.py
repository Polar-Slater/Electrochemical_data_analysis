from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HEADER_MARKER = 'Freq/Hz, Z\'/ohm, Z"/ohm, Z/ohm, Phase/deg'


@dataclass(frozen=True)
class EISData:
    source: Path
    frequency_hz: list[float]
    z_real_ohm: list[float]
    z_imag_ohm: list[float]
    z_abs_ohm: list[float]
    phase_deg: list[float]

    @property
    def minus_z_imag_ohm(self) -> list[float]:
        return [-value for value in self.z_imag_ohm]


def _is_header(line: str) -> bool:
    return line.strip().lower() == HEADER_MARKER.lower()


def _numeric_rows(lines: Iterable[str]) -> Iterable[list[float]]:
    reader = csv.reader(lines, skipinitialspace=True)
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) < 5:
            continue
        try:
            yield [float(cell.strip()) for cell in row[:5]]
        except ValueError:
            continue


def read_eis_data(path: str | Path) -> EISData:
    source = Path(path)
    lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()

    data_start = None
    for index, line in enumerate(lines):
        if _is_header(line):
            data_start = index + 1
            break

    if data_start is None:
        raise ValueError(f"Could not find EIS data header: {HEADER_MARKER}")

    frequency_hz: list[float] = []
    z_real_ohm: list[float] = []
    z_imag_ohm: list[float] = []
    z_abs_ohm: list[float] = []
    phase_deg: list[float] = []

    for frequency, z_real, z_imag, z_abs, phase in _numeric_rows(lines[data_start:]):
        frequency_hz.append(frequency)
        z_real_ohm.append(z_real)
        z_imag_ohm.append(z_imag)
        z_abs_ohm.append(z_abs)
        phase_deg.append(phase)

    if not frequency_hz:
        raise ValueError("Found the EIS header, but no numeric data rows were parsed.")

    return EISData(
        source=source,
        frequency_hz=frequency_hz,
        z_real_ohm=z_real_ohm,
        z_imag_ohm=z_imag_ohm,
        z_abs_ohm=z_abs_ohm,
        phase_deg=phase_deg,
    )


def write_processed_eis_data(data: EISData, path: str | Path, working_area: float | None = None) -> None:
    destination = Path(path)
    impedance_scale = working_area if working_area is not None else 1.0
    impedance_unit = "ohm⋅cm^2" if working_area is not None else "ohm"
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        if working_area is not None:
            writer.writerow(["Working area (cm^2)", f"{working_area:g}"])
        writer.writerow(
            [
                "Frequency (Hz)",
                f"Z' ({impedance_unit})",
                f"-Z'' ({impedance_unit})",
                f"Z ({impedance_unit})",
                "Phase (deg)",
            ]
        )
        writer.writerows(
            zip(
                data.frequency_hz,
                [value * impedance_scale for value in data.z_real_ohm],
                [value * impedance_scale for value in data.minus_z_imag_ohm],
                [value * impedance_scale for value in data.z_abs_ohm],
                data.phase_deg,
            )
        )


def summarize_eis_data(data: EISData) -> dict[str, float | int]:
    return {
        "points": len(data.frequency_hz),
        "frequency_max_hz": max(data.frequency_hz),
        "frequency_min_hz": min(data.frequency_hz),
        "z_real_min_ohm": min(data.z_real_ohm),
        "z_real_max_ohm": max(data.z_real_ohm),
        "minus_z_imag_min_ohm": min(data.minus_z_imag_ohm),
        "minus_z_imag_max_ohm": max(data.minus_z_imag_ohm),
    }
