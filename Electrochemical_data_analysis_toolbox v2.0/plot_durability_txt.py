from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


POTENTIAL_DATA_HEADER = ("Time/sec", "Potential/V")
CURRENT_DATA_HEADER = ("Time/sec", "Current/A")
MODE_MULTI_CURRENT = "Multi-Current Steps"
MODE_CHRONOPOTENTIOMETRY = "Chronopotentiometry"
MODE_AMPEROMETRIC = "Amperometric i-t Curve"
METADATA_KEYS = {
    "i1 (A)": "current_a",
    "T1 (s)": "duration_s",
    "Anodic Current (A)": "current_a",
    "Anodic Time (s)": "duration_s",
    "Cathodic Current (A)": "cathodic_current_a",
    "Cathodic Time (s)": "cathodic_time_s",
    "Sample Interval (s)": "sample_interval_s",
    "Data Storage Interval (s)": "sample_interval_s",
    "Cycle": "cycle",
    "Segment": "segment",
    "Init E (V)": "applied_potential_v",
    "Run Time (sec)": "duration_s",
}


@dataclass(frozen=True)
class DurabilityMetadata:
    mode: str | None = None
    current_a: float | None = None
    duration_s: float | None = None
    cathodic_current_a: float | None = None
    cathodic_time_s: float | None = None
    sample_interval_s: float | None = None
    cycle: float | None = None
    segment: float | None = None
    applied_potential_v: float | None = None


@dataclass(frozen=True)
class DurabilityData:
    metadata: DurabilityMetadata
    source: Path
    times_sec: list[float]
    values: list[float]
    value_kind: str

    @property
    def potentials_v(self) -> list[float]:
        """Potential values for CP files (kept as a compatibility accessor)."""
        return self.values if self.value_kind == "potential" else []

    @property
    def currents_a(self) -> list[float]:
        return self.values if self.value_kind == "current" else []

    @property
    def is_amperometric(self) -> bool:
        return self.value_kind == "current"

    @property
    def point_count(self) -> int:
        return len(self.times_sec)

    @property
    def min_time(self) -> float:
        return min(self.times_sec)

    @property
    def max_time(self) -> float:
        return max(self.times_sec)

    @property
    def min_potential(self) -> float:
        return min(self.values)

    @property
    def max_potential(self) -> float:
        return max(self.values)

    @property
    def final_potential(self) -> float:
        return self.values[-1]

    @property
    def display_current_a(self) -> float | None:
        if self.metadata.current_a is None:
            return None
        if self.metadata.mode == MODE_MULTI_CURRENT:
            return abs(self.metadata.current_a)
        return self.metadata.current_a


def parse_metadata(lines: list[str]) -> DurabilityMetadata:
    values: dict[str, float] = {}
    mode = None

    for line in lines:
        stripped = line.strip()
        if stripped in {MODE_MULTI_CURRENT, MODE_CHRONOPOTENTIOMETRY, MODE_AMPEROMETRIC}:
            mode = stripped
            continue
        if "=" not in stripped:
            continue

        key, raw_value = [part.strip() for part in stripped.split("=", 1)]
        field = METADATA_KEYS.get(key)
        if field is None:
            continue
        values[field] = float(raw_value)

    return DurabilityMetadata(
        mode=mode,
        current_a=values.get("current_a"),
        duration_s=values.get("duration_s"),
        cathodic_current_a=values.get("cathodic_current_a"),
        cathodic_time_s=values.get("cathodic_time_s"),
        sample_interval_s=values.get("sample_interval_s"),
        cycle=values.get("cycle"),
        segment=values.get("segment"),
        applied_potential_v=values.get("applied_potential_v"),
    )


def read_durability_data(path: str | Path) -> DurabilityData:
    source = Path(path)
    lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()

    data_start = None
    value_kind = None
    for index, line in enumerate(lines):
        columns = [value.strip() for value in line.split(",")]
        if len(columns) >= 2:
            header = (columns[0], columns[1])
            if header == POTENTIAL_DATA_HEADER:
                data_start, value_kind = index + 1, "potential"
                break
            if header == CURRENT_DATA_HEADER:
                data_start, value_kind = index + 1, "current"
                break

    if data_start is None:
        expected = " or ".join(", ".join(header) for header in (POTENTIAL_DATA_HEADER, CURRENT_DATA_HEADER))
        raise ValueError(f"Could not find a supported durability data header: {expected}")

    times_sec: list[float] = []
    values: list[float] = []
    for row in csv.reader(lines[data_start:], skipinitialspace=True):
        if len(row) < 2 or not row[0].strip():
            continue
        try:
            times_sec.append(float(row[0]))
            values.append(float(row[1]))
        except ValueError:
            if times_sec:
                break
            raise

    if not times_sec:
        raise ValueError("Found the durability header, but no numeric data rows were read.")

    return DurabilityData(
        metadata=parse_metadata(lines[:data_start]),
        source=source,
        times_sec=times_sec,
        values=values,
        value_kind=value_kind,
    )


def summarize_durability_data(data: DurabilityData) -> str:
    metadata = data.metadata
    lines: list[str] = []
    if metadata.mode is not None:
        lines.append(f"Mode: {metadata.mode}")
    if data.display_current_a is not None:
        lines.append(f"Current: {data.display_current_a:g} A")
    if metadata.duration_s is not None:
        lines.append(f"Time: {metadata.duration_s:g} s")
    if metadata.sample_interval_s is not None:
        lines.append(f"Sample interval: {metadata.sample_interval_s:g} s")
    if metadata.applied_potential_v is not None:
        lines.append(f"Applied potential: {metadata.applied_potential_v:g} V")
    if metadata.cathodic_current_a is not None:
        lines.append(f"Cathodic current: {metadata.cathodic_current_a:g} A")
    if metadata.cathodic_time_s is not None:
        lines.append(f"Cathodic time: {metadata.cathodic_time_s:g} s")
    if lines:
        lines.append("")

    lines.extend(
        [
            f"File: {data.source.name}",
            f"Points: {data.point_count}",
            f"Measured time: {data.min_time:.6g} to {data.max_time:.6g} s",
            (
                f"Current: {min(data.values):.6g} to {max(data.values):.6g} A"
                if data.is_amperometric
                else f"Potential: {data.min_potential:.6g} to {data.max_potential:.6g} V"
            ),
            (
                f"Final current: {data.values[-1]:.6g} A"
                if data.is_amperometric
                else f"Final potential: {data.final_potential:.6g} V"
            ),
        ]
    )
    return "\n".join(lines)


def plot_durability(input_path: Path, output_path: Path | None = None, show: bool = True) -> None:
    data = read_durability_data(input_path)

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    ax.plot(data.times_sec, data.values, linewidth=1.5)
    ax.set_xlabel("Time / s")
    ax.set_ylabel("Current / A" if data.is_amperometric else "Potential / V")
    ax.set_title(input_path.stem)
    ax.grid(True, alpha=0.3)

    if output_path is not None:
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot a CHI-style durability text file.")
    parser.add_argument("input", type=Path, help="Input durability .txt file")
    parser.add_argument("-o", "--output", type=Path, help="Optional plot output path")
    parser.add_argument("--no-show", action="store_true", help="Save only; do not show the plot window")
    args = parser.parse_args()

    plot_durability(args.input, args.output, show=not args.no_show)


if __name__ == "__main__":
    main()
