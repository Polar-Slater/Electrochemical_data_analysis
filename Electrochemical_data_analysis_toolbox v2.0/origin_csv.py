from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from cv_data import CVData, read_cv_data
from plot_durability_txt import DurabilityData, read_durability_data
from plot_eis_txt import EISData, read_eis_data
from plot_lsv_txt import LSVData, read_lsv_data
from plot_ocv_txt import OCVData, read_ocv_data


AREA_FROM_FOLDER = re.compile(r"(?P<area>\d+(?:\.\d+)?)\s*cm(?:\^?2|²)\s*$", re.IGNORECASE)
RS_FROM_NAME = re.compile(r"(?P<rs>\d+(?:\.\d+)?)\s*ohm", re.IGNORECASE)
SCAN_RATE_FROM_NAME = re.compile(r"(?P<rate>\d+(?:\.\d+)?)\s*mV", re.IGNORECASE)


@dataclass(frozen=True)
class ProcessingSettings:
    working_area_cm2: float
    reference_potential_v: float = 0.0
    equilibrium_potential_v: float = 1.23
    solution_resistance_ohm: float | None = None
    compensation_percent: float = 0.0
    ecsa_cycle_number: int | None = None
    cp_solution_resistance_ohm: float | None = None
    cp_compensation_percent: float = 0.0

    def validate(self) -> None:
        if self.working_area_cm2 <= 0:
            raise ValueError("Working area must be greater than zero.")
        if self.solution_resistance_ohm is not None and self.solution_resistance_ohm < 0:
            raise ValueError("Solution resistance cannot be negative.")
        if self.cp_solution_resistance_ohm is not None and self.cp_solution_resistance_ohm < 0:
            raise ValueError("CP solution resistance cannot be negative.")
        if not 0 <= self.compensation_percent <= 100:
            raise ValueError("Compensation level must be between 0 and 100 percent.")
        if self.ecsa_cycle_number is not None and self.ecsa_cycle_number < 1:
            raise ValueError("ECSA cycle number must be at least 1.")
        if not 0 <= self.cp_compensation_percent <= 100:
            raise ValueError("CP compensation level must be between 0 and 100 percent.")


@dataclass(frozen=True)
class ProcessingReport:
    created: tuple[Path, ...]
    skipped: tuple[str, ...]
    failures: tuple[str, ...]


def infer_working_area(folder: str | Path) -> float | None:
    match = AREA_FROM_FOLDER.search(Path(folder).name)
    return float(match.group("area")) if match else None


def infer_sample_name(folder: str | Path) -> str:
    name = Path(folder).name
    match = AREA_FROM_FOLDER.search(name)
    return name[: match.start()].strip(" _-") if match else name


def infer_solution_resistance(path: str | Path) -> float | None:
    match = RS_FROM_NAME.search(Path(path).stem)
    return float(match.group("rs")) if match else None


def measurement_type(path: str | Path) -> str:
    source = Path(path)
    lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    instrument_name = lines[1].strip().lower() if len(lines) > 1 else ""
    stem = source.stem.lower()
    if "open circuit" in instrument_name or re.search(r"(?:^|[_ -])ocv(?:$|[_ -])", stem):
        return "OCV"
    if "linear sweep" in instrument_name or re.search(r"(?:^|[_ -])l[cs]v(?:$|[_ -])", stem):
        return "LSV"
    if "impedance" in instrument_name or re.search(r"(?:^|[_ -])eis(?:$|[_ -])", stem):
        return "EIS"
    if "cyclic voltammetry" in instrument_name or re.search(r"(?:^|[_ -])cv(?:$|[_ -])", stem):
        return "CV"
    if any(token in instrument_name for token in ("chronopotentiometry", "multi-current", "amperometric")):
        return "DURABILITY"
    if re.search(r"(?:^|[_ -])(?:cp|ca|it)(?:$|[_ -])", stem):
        return "DURABILITY"
    raise ValueError("Unsupported or unrecognized CHI text file.")


def is_scan_rate_cv(path: str | Path) -> bool:
    source = Path(path)
    return measurement_type(source) == "CV" and SCAN_RATE_FROM_NAME.search(source.stem) is not None


def is_deposition_it(path: str | Path) -> bool:
    stem = Path(path).stem.lower()
    return re.search(r"(?:^|[_ -])it(?:$|[_ -])", stem) is not None


def _format(value: float | None) -> str:
    return "" if value is None else f"{value:.12g}"


def _write_rows(destination: Path, rows: Iterable[Sequence[object]]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as output:
        csv.writer(output).writerows(rows)


def write_ocv_csv(data: OCVData, destination: Path) -> None:
    rows: list[Sequence[object]] = [["Time", "Potential"], ["sec", "V"]]
    rows.extend((_format(time), _format(potential)) for time, potential in zip(data.times_sec, data.potentials_v))
    _write_rows(destination, rows)


def write_active_cv_csv(data: CVData, destination: Path) -> None:
    rows: list[Sequence[object]] = [["Potential", "Current"], ["V", "A"]]
    rows.extend((_format(potential), _format(current)) for potential, current in zip(data.potentials, data.currents))
    _write_rows(destination, rows)


def write_eis_csv(data: EISData, destination: Path, settings: ProcessingSettings) -> None:
    area = settings.working_area_cm2
    rows: list[Sequence[object]] = [
        ["Working area (cm^2)", _format(area), "", "", ""],
        ["Frequency", "Z'", "-Z''", "Z", "Phase"],
        ["Hz", "ohm cm2", "ohm cm2", "ohm cm2", "deg"],
    ]
    rows.extend(
        tuple(_format(value) for value in row)
        for row in zip(
            data.frequency_hz,
            (value * area for value in data.z_real_ohm),
            (-value * area for value in data.z_imag_ohm),
            (value * area for value in data.z_abs_ohm),
            data.phase_deg,
        )
    )
    _write_rows(destination, rows)


def _effective_resistance(source: Path, settings: ProcessingSettings) -> float | None:
    return settings.solution_resistance_ohm if settings.solution_resistance_ohm is not None else infer_solution_resistance(source)


def write_lsv_csv(data: LSVData, source: Path, destination: Path, settings: ProcessingSettings) -> None:
    resistance = _effective_resistance(source, settings)
    fraction = settings.compensation_percent / 100
    area = settings.working_area_cm2
    rows: list[Sequence[object]] = [
        ["Reference electrode potential (V vs. RHE)", _format(settings.reference_potential_v), "", "", ""],
        ["Water-splitting equilibrium potential (V vs. RHE)", _format(settings.equilibrium_potential_v), "", "", ""],
        ["Working area (cm²)", _format(area), "", "", ""],
        ["Solution resistance (ohm)", _format(resistance), "Compensation level (%)", _format(settings.compensation_percent), ""],
        ["", "", "", "", ""],
        ["File", "Point", "Original Potential", "Original Current", "Potential (V vs. RHE, iR-corrected)", "Current density"],
        ["", "", "V", "mA", "V vs. RHE, iR-corrected", "mA/cm²"],
    ]
    for point, (potential, current_a) in enumerate(zip(data.potentials, data.currents), start=1):
        correction = current_a * (resistance or 0.0) * fraction
        rows.append(
            [source.name, point, _format(potential), _format(current_a * 1000), _format(potential + settings.reference_potential_v - correction), _format(current_a * 1000 / area)]
        )
    _write_rows(destination, rows)


def write_durability_csv(
    data: DurabilityData,
    destination: Path,
    settings: ProcessingSettings,
) -> None:
    metadata = data.metadata
    area = settings.working_area_cm2
    resistance = settings.cp_solution_resistance_ohm
    fraction = settings.cp_compensation_percent / 100
    applied_current = data.display_current_a
    current_density = None if applied_current is None else applied_current * 1000 / area
    rows: list[Sequence[object]] = [
        ["Mode", metadata.mode or "", ""],
        ["Applied current (A)", _format(applied_current), ""],
        ["Applied potential (V)", _format(metadata.applied_potential_v), ""],
        ["Time (s)", _format(metadata.duration_s), ""],
        ["Reference electrode potential (V vs. RHE)", _format(None if data.is_amperometric else settings.reference_potential_v), ""],
        ["Working area (cm^2)", _format(area), ""],
        ["Applied current density (mA/cm^2)", _format(current_density), ""],
        ["Solution resistance (ohm)", _format(None if data.is_amperometric else resistance), "Compensation level (%)", _format(None if data.is_amperometric else settings.cp_compensation_percent)],
        ["", "", ""],
    ]
    if data.is_amperometric:
        rows.extend([["Time", "Original Current", "Current density"], ["sec", "A", "mA/cm²"]])
        rows.extend((_format(time), _format(current), _format(current * 1000 / area)) for time, current in zip(data.times_sec, data.values))
    else:
        label = "V vs. RHE, iR-corrected"
        rows.extend([["Time", "Original Potential", "Potential", ""], ["sec", "V", label, ""]])
        current_for_ir = applied_current or 0.0
        rows.extend(
            (_format(time), _format(potential), _format(potential + settings.reference_potential_v - current_for_ir * (resistance or 0.0) * fraction), "")
            for time, potential in zip(data.times_sec, data.values)
        )
    _write_rows(destination, rows)


def _scan_rate(data: CVData) -> float:
    if data.metadata.scan_rate_mv_s is not None:
        return data.metadata.scan_rate_mv_s
    match = SCAN_RATE_FROM_NAME.search(data.path.stem)
    if not match:
        raise ValueError(f"No scan rate found for {data.path.name}")
    return float(match.group("rate"))


def _common_ecsa_prefix(paths: Sequence[Path]) -> str:
    first = paths[0].stem
    match = re.search(r"(?i)(.*?[_ -]CV)(?:[_ -]|$)", first)
    return match.group(1) if match else f"{first}_CV"


def _linear_regression(points: Sequence[tuple[float, float]]) -> tuple[float, float] | None:
    if len(points) < 2:
        return None
    x_mean = sum(x for x, _ in points) / len(points)
    y_mean = sum(y for _, y in points) / len(points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    if denominator == 0:
        return None
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    return slope, y_mean - slope * x_mean


def write_ecsa_csvs(cv_paths: Sequence[Path], output_dir: Path, settings: ProcessingSettings) -> tuple[Path, Path]:
    data_sets = sorted((read_cv_data(path) for path in cv_paths), key=_scan_rate)
    prefix = _common_ecsa_prefix(cv_paths)
    cycle_path = output_dir / f"{prefix} cycle_CV.csv"
    delta_path = output_dir / f"{prefix} scan_rate_delta_j.csv"
    area_scale = 1000 / settings.working_area_cm2

    cycle_rows: list[Sequence[object]] = []
    header: list[str] = []
    units: list[str] = []
    labels: list[str] = []
    for data in data_sets:
        rate = _scan_rate(data)
        header.extend(["Potential", "Current density"])
        units.extend(["V", "mA/cm²"])
        labels.extend([f"{rate:g} mV/s", f"{rate:g} mV/s"])
    cycle_rows.extend([header, units, labels])
    selected_cycles = [settings.ecsa_cycle_number or data.cycle_count for data in data_sets]
    max_points = max(len(data.cycle_potentials(cycle)) for data, cycle in zip(data_sets, selected_cycles))
    for index in range(max_points):
        row: list[object] = []
        for data, cycle in zip(data_sets, selected_cycles):
            potentials = data.cycle_potentials(cycle)
            currents = data.cycle_currents(cycle)
            if index < len(potentials):
                row.extend([_format(potentials[index]), _format(currents[index] * area_scale)])
            else:
                row.extend(["", ""])
        cycle_rows.append(row)
    _write_rows(cycle_path, cycle_rows)

    points: list[tuple[float, float]] = []
    for data, cycle in zip(data_sets, selected_cycles):
        midpoint = data.midpoint_currents_for_cycle(cycle)
        if midpoint is None:
            raise ValueError(f"Could not calculate midpoint currents for {data.path.name}")
        points.append((_scan_rate(data), midpoint.half_current_difference * area_scale))
    fit = _linear_regression(points)
    formula = ""
    if fit is not None:
        slope, intercept = fit
        formula = f"delta j (mA/cm^2) = {slope:.10g} * scan rate (mV/s) + {intercept:.10g}"
    delta_rows: list[Sequence[object]] = [
        ["Scan rate", "Delta j mA/cm^2", "Fitted line formula"],
        ["mV s-1", "mA/cm²", ""],
    ]
    delta_rows.extend((_format(rate), _format(value), formula if index == 0 else "") for index, (rate, value) in enumerate(points))
    _write_rows(delta_path, delta_rows)
    return cycle_path, delta_path


def process_files(
    paths: Sequence[str | Path],
    output_dir: str | Path,
    settings: ProcessingSettings,
) -> ProcessingReport:
    settings.validate()
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    sources = [Path(path) for path in paths]
    created: list[Path] = []
    skipped: list[str] = []
    failures: list[str] = []
    scan_rate_cvs: list[Path] = []

    for source in sources:
        try:
            kind = measurement_type(source)
            if kind == "CV" and is_scan_rate_cv(source):
                scan_rate_cvs.append(source)
                continue
            output = destination / f"{source.stem}.csv"
            if kind == "OCV":
                write_ocv_csv(read_ocv_data(source), output)
            elif kind == "LSV":
                write_lsv_csv(read_lsv_data(source), source, output, settings)
            elif kind == "EIS":
                write_eis_csv(read_eis_data(source), output, settings)
            elif kind == "DURABILITY":
                write_durability_csv(read_durability_data(source), output, settings)
            elif kind == "CV":
                write_active_cv_csv(read_cv_data(source), output)
            else:
                skipped.append(f"{source.name}: unsupported measurement")
                continue
            created.append(output)
        except Exception as exc:
            failures.append(f"{source.name}: {exc}")

    if scan_rate_cvs:
        try:
            created.extend(write_ecsa_csvs(scan_rate_cvs, destination, settings))
        except Exception as exc:
            failures.append(f"ECSA group: {exc}")
    return ProcessingReport(tuple(created), tuple(skipped), tuple(failures))


def process_sample_folder(
    folder: str | Path,
    settings: ProcessingSettings,
    output_dir: str | Path | None = None,
) -> ProcessingReport:
    sample_folder = Path(folder)
    sources = sorted(sample_folder.glob("*.txt"), key=lambda path: path.name.lower())
    reporting_sources = [path for path in sources if not is_deposition_it(path)]
    skipped = [f"{path.name}: deposition i-t file" for path in sources if is_deposition_it(path)]
    report = process_files(reporting_sources, output_dir or sample_folder / "Processed", settings)
    return ProcessingReport(report.created, tuple(skipped) + report.skipped, report.failures)
