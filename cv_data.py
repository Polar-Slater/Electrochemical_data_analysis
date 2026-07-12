from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


DATA_HEADER = ("Potential/V", "Current/A")
SCAN_RATE_FROM_NAME = re.compile(r"(\d+(?:\.\d+)?)\s*mV", re.IGNORECASE)
METADATA_KEYS = {
    "Init E (V)": "init_e",
    "High E (V)": "high_e",
    "Low E (V)": "low_e",
    "Segment": "segments",
    "Scan Rate (V/s)": "scan_rate_v_s",
}


@dataclass(frozen=True)
class CVMetadata:
    init_e: float | None = None
    high_e: float | None = None
    low_e: float | None = None
    segments: int | None = None
    scan_rate_v_s: float | None = None

    @property
    def scan_rate_mv_s(self) -> float | None:
        if self.scan_rate_v_s is None:
            return None
        return self.scan_rate_v_s * 1000

    @property
    def cycles(self) -> float | None:
        if self.segments is None:
            return None
        return self.segments / 2

    @property
    def middle_potential(self) -> float | None:
        if self.low_e is None or self.high_e is None:
            return None
        return (self.low_e + self.high_e) / 2


@dataclass(frozen=True)
class MidpointCurrents:
    potential: float
    current_high: float
    current_low: float
    branch_currents: tuple[float, ...]

    @property
    def average_current(self) -> float:
        return (self.current_high + self.current_low) / 2


@dataclass(frozen=True)
class CVData:
    path: Path
    metadata: CVMetadata
    potentials: list[float]
    currents: list[float]

    @property
    def label(self) -> str:
        scan_rate = self.metadata.scan_rate_mv_s
        if scan_rate is not None:
            return f"Scan rate = {scan_rate:g} mV/s"
        match = SCAN_RATE_FROM_NAME.search(self.path.stem)
        if match:
            return f"Scan rate = {float(match.group(1)):g} mV/s"
        return f"Scan rate unknown ({self.path.stem})"

    @property
    def sort_key(self) -> tuple[float, str]:
        scan_rate = self.metadata.scan_rate_mv_s
        if scan_rate is None:
            match = SCAN_RATE_FROM_NAME.search(self.path.stem)
            if match:
                scan_rate = float(match.group(1))
        if scan_rate is None:
            scan_rate = float("inf")
        return scan_rate, self.path.name.lower()

    @property
    def cycle_count(self) -> int:
        segments = self.metadata.segments
        if segments is None or segments < 2:
            return 1
        return max(1, segments // 2)

    @property
    def points_per_segment(self) -> int:
        segments = self.metadata.segments
        if segments is None or segments < 1:
            return len(self.potentials)
        points_per_segment = len(self.potentials) // segments
        return points_per_segment if points_per_segment > 0 else len(self.potentials)

    def cycle_start_index(self, cycle_number: int) -> int:
        if self.metadata.segments is None or self.metadata.segments < 2:
            return 0
        clamped_cycle = min(max(1, cycle_number), self.cycle_count)
        return (clamped_cycle - 1) * self.points_per_segment * 2

    def cycle_end_index(self, cycle_number: int) -> int:
        if self.metadata.segments is None or self.metadata.segments < 2:
            return len(self.potentials)
        return min(len(self.potentials), self.cycle_start_index(cycle_number) + self.points_per_segment * 2)

    def cycle_potentials(self, cycle_number: int) -> list[float]:
        return self.potentials[self.cycle_start_index(cycle_number) : self.cycle_end_index(cycle_number)]

    def cycle_currents(self, cycle_number: int) -> list[float]:
        return self.currents[self.cycle_start_index(cycle_number) : self.cycle_end_index(cycle_number)]

    @property
    def last_cycle_start_index(self) -> int:
        return self.cycle_start_index(self.cycle_count)

    @property
    def last_cycle_potentials(self) -> list[float]:
        return self.cycle_potentials(self.cycle_count)

    @property
    def last_cycle_currents(self) -> list[float]:
        return self.cycle_currents(self.cycle_count)

    def midpoint_currents_for_cycle(self, cycle_number: int) -> MidpointCurrents | None:
        potential = self.metadata.middle_potential
        if potential is None:
            return None

        branch_currents: list[float] = []
        for branch_potentials, branch_currents_values in split_monotonic_branches(
            self.cycle_potentials(cycle_number),
            self.cycle_currents(cycle_number),
        ):
            current = interpolate_current_at_potential(branch_potentials, branch_currents_values, potential)
            if current is not None:
                branch_currents.append(current)

        if not branch_currents:
            return None

        return MidpointCurrents(
            potential=potential,
            current_high=max(branch_currents),
            current_low=min(branch_currents),
            branch_currents=tuple(branch_currents),
        )

    @property
    def midpoint_currents(self) -> MidpointCurrents | None:
        return self.midpoint_currents_for_cycle(self.cycle_count)


def split_monotonic_branches(
    potentials: list[float],
    currents: list[float],
) -> list[tuple[list[float], list[float]]]:
    if len(potentials) < 2 or len(potentials) != len(currents):
        return []

    branches: list[tuple[list[float], list[float]]] = []
    start = 0
    previous_direction = 0

    for index in range(1, len(potentials)):
        delta = potentials[index] - potentials[index - 1]
        direction = 1 if delta > 0 else -1 if delta < 0 else previous_direction
        if previous_direction and direction and direction != previous_direction:
            branches.append((potentials[start:index], currents[start:index]))
            start = index - 1
        if direction:
            previous_direction = direction

    branches.append((potentials[start:], currents[start:]))
    return [(branch_e, branch_i) for branch_e, branch_i in branches if len(branch_e) >= 2]


def interpolate_current_at_potential(
    potentials: list[float],
    currents: list[float],
    target_potential: float,
) -> float | None:
    if len(potentials) < 2 or len(potentials) != len(currents):
        return None

    for index in range(len(potentials) - 1):
        e1 = potentials[index]
        e2 = potentials[index + 1]
        i1 = currents[index]
        i2 = currents[index + 1]

        if e1 == target_potential:
            return i1
        if e2 == target_potential:
            return i2
        if (e1 <= target_potential <= e2) or (e2 <= target_potential <= e1):
            if e1 == e2:
                return (i1 + i2) / 2
            fraction = (target_potential - e1) / (e2 - e1)
            return i1 + fraction * (i2 - i1)

    return None


def parse_metadata(lines: list[str]) -> CVMetadata:
    values: dict[str, float | int] = {}

    for line in lines:
        if "=" not in line:
            continue

        key, raw_value = [part.strip() for part in line.split("=", 1)]
        field = METADATA_KEYS.get(key)
        if field is None:
            continue

        try:
            if field == "segments":
                values[field] = int(float(raw_value))
            else:
                values[field] = float(raw_value)
        except ValueError:
            continue

    return CVMetadata(
        init_e=values.get("init_e"),
        high_e=values.get("high_e"),
        low_e=values.get("low_e"),
        segments=values.get("segments"),
        scan_rate_v_s=values.get("scan_rate_v_s"),
    )


def read_cv_data(input_path: Path) -> CVData:
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        lines = source.readlines()

    data_start = None
    for index, line in enumerate(lines):
        columns = [value.strip() for value in line.split(",")]
        if len(columns) >= 2 and columns[0] == DATA_HEADER[0] and columns[1] == DATA_HEADER[1]:
            data_start = index + 1
            break

    if data_start is None:
        raise ValueError(f"Could not find data header: {', '.join(DATA_HEADER)}")

    potentials: list[float] = []
    currents: list[float] = []
    for row in csv.reader(lines[data_start:], skipinitialspace=True):
        if len(row) < 2 or not row[0].strip():
            continue
        try:
            potentials.append(float(row[0]))
            currents.append(float(row[1]))
        except ValueError:
            if potentials:
                break
            raise

    if not potentials:
        raise ValueError("Found the data header, but no numeric data rows were read.")

    return CVData(
        path=input_path,
        metadata=parse_metadata(lines[:data_start]),
        potentials=potentials,
        currents=currents,
    )


def summarize_data(data_sets: list[CVData], current_unit: str = "mA", cycle_number: int | None = None) -> str:
    if not data_sets:
        return "No CV files loaded."

    current_scale = 1000 if current_unit == "mA" else 1
    lines: list[str] = []
    for data in data_sets:
        metadata = data.metadata
        selected_cycle = cycle_number if cycle_number is not None else data.cycle_count
        midpoint_currents = data.midpoint_currents_for_cycle(selected_cycle)
        lines.append(data.path.name)
        lines.append(f"  Scan rate: {metadata.scan_rate_mv_s:g} mV/s" if metadata.scan_rate_mv_s is not None else "  Scan rate: --")
        if metadata.low_e is not None and metadata.high_e is not None:
            lines.append(f"  Scan range: {metadata.low_e:g} to {metadata.high_e:g} V")
        else:
            lines.append("  Scan range: --")
        lines.append(f"  Cycles: {metadata.cycles:g}" if metadata.cycles is not None else "  Cycles: --")
        lines.append(f"  Selected cycle: {min(max(1, selected_cycle), data.cycle_count)}")
        if midpoint_currents is not None:
            lines.append(f"  Middle E: {midpoint_currents.potential:g} V")
            lines.append(f"  current_high: {midpoint_currents.current_high * current_scale:.6g} {current_unit}")
            lines.append(f"  current_low: {midpoint_currents.current_low * current_scale:.6g} {current_unit}")
            lines.append(f"  average_current: {midpoint_currents.average_current * current_scale:.6g} {current_unit}")
        else:
            lines.append("  Middle E: --")
            lines.append(f"  current_high: -- {current_unit}")
            lines.append(f"  current_low: -- {current_unit}")
            lines.append(f"  average_current: -- {current_unit}")
        lines.append("")

    return "\n".join(lines).strip()
