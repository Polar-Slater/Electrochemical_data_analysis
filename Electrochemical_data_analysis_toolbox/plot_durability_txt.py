from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


DATA_HEADER = ("Time/sec", "Potential/V")
MODE_MULTI_CURRENT = "Multi-Current Steps"
MODE_CHRONOPOTENTIOMETRY = "Chronopotentiometry"
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


@dataclass(frozen=True)
class DurabilityData:
    metadata: DurabilityMetadata
    source: Path
    times_sec: list[float]
    potentials_v: list[float]

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
        return min(self.potentials_v)

    @property
    def max_potential(self) -> float:
        return max(self.potentials_v)

    @property
    def final_potential(self) -> float:
        return self.potentials_v[-1]

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
        if stripped in {MODE_MULTI_CURRENT, MODE_CHRONOPOTENTIOMETRY}:
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
    )


def read_durability_data(path: str | Path) -> DurabilityData:
    source = Path(path)
    lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()

    data_start = None
    for index, line in enumerate(lines):
        columns = [value.strip() for value in line.split(",")]
        if len(columns) >= 2 and columns[0] == DATA_HEADER[0] and columns[1] == DATA_HEADER[1]:
            data_start = index + 1
            break

    if data_start is None:
        raise ValueError(f"Could not find durability data header: {', '.join(DATA_HEADER)}")

    times_sec: list[float] = []
    potentials_v: list[float] = []
    for row in csv.reader(lines[data_start:], skipinitialspace=True):
        if len(row) < 2 or not row[0].strip():
            continue
        try:
            times_sec.append(float(row[0]))
            potentials_v.append(float(row[1]))
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
        potentials_v=potentials_v,
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
            f"Potential: {data.min_potential:.6g} to {data.max_potential:.6g} V",
            f"Final potential: {data.final_potential:.6g} V",
        ]
    )
    return "\n".join(lines)


def plot_durability(input_path: Path, output_path: Path | None = None, show: bool = True) -> None:
    data = read_durability_data(input_path)

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    ax.plot(data.times_sec, data.potentials_v, linewidth=1.5)
    ax.set_xlabel("Time / s")
    ax.set_ylabel("Potential / V")
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
