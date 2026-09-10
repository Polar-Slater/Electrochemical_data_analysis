from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


DATA_HEADER = ("Potential/V", "Current/A")
METADATA_KEYS = {
    "Init E (V)": "init_e",
    "Final E (V)": "final_e",
    "Scan Rate (V/s)": "scan_rate",
    "Sample Interval (V)": "sample_interval",
    "Quiet Time (sec)": "quiet_time",
    "Sensitivity (A/V)": "sensitivity",
}


@dataclass(frozen=True)
class LSVMetadata:
    init_e: float | None = None
    final_e: float | None = None
    scan_rate: float | None = None
    sample_interval: float | None = None
    quiet_time: float | None = None
    sensitivity: float | None = None


@dataclass(frozen=True)
class LSVData:
    metadata: LSVMetadata
    potentials: list[float]
    currents: list[float]

    @property
    def point_count(self) -> int:
        return len(self.potentials)

    @property
    def min_current(self) -> float:
        return min(self.currents)

    @property
    def max_current(self) -> float:
        return max(self.currents)

    @property
    def min_potential(self) -> float:
        return min(self.potentials)

    @property
    def max_potential(self) -> float:
        return max(self.potentials)


def parse_metadata(lines: list[str]) -> LSVMetadata:
    values: dict[str, float] = {}

    for line in lines:
        if "=" not in line:
            continue

        key, raw_value = [part.strip() for part in line.split("=", 1)]
        field = METADATA_KEYS.get(key)
        if field is None:
            continue

        values[field] = float(raw_value)

    return LSVMetadata(
        init_e=values.get("init_e"),
        final_e=values.get("final_e"),
        scan_rate=values.get("scan_rate"),
        sample_interval=values.get("sample_interval"),
        quiet_time=values.get("quiet_time"),
        sensitivity=values.get("sensitivity"),
    )


def read_lsv_data(input_path: Path) -> LSVData:
    """Read CHI-style linear sweep voltammetry text data and metadata."""
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

    return LSVData(
        metadata=parse_metadata(lines[:data_start]),
        potentials=potentials,
        currents=currents,
    )


def read_lsv_txt(input_path: Path) -> tuple[list[float], list[float]]:
    """Read potential and current arrays from a CHI-style LSV text file."""
    data = read_lsv_data(input_path)
    return data.potentials, data.currents


def format_optional_voltage(label: str, value: float | None) -> str | None:
    if value is None:
        return None
    return f"{label}: {value:g} V"


def summarize_lsv_data(data: LSVData) -> str:
    metadata = data.metadata
    lines = [
        format_optional_voltage("Init E", metadata.init_e),
        format_optional_voltage("Final E", metadata.final_e),
    ]
    if metadata.scan_rate is not None:
        lines.append(f"Scan rate: {metadata.scan_rate:g} V/s")
    if metadata.sample_interval is not None:
        lines.append(f"Sample interval: {metadata.sample_interval:g} V")
    if metadata.quiet_time is not None:
        lines.append(f"Quiet time: {metadata.quiet_time:g} s")
    if metadata.sensitivity is not None:
        lines.append(f"Sensitivity: {metadata.sensitivity:g} A/V")

    lines = [line for line in lines if line is not None]
    if lines:
        lines.append("")

    lines.extend(
        [
            f"Points: {data.point_count}",
            f"Potential range: {data.min_potential:.6g} to {data.max_potential:.6g} V",
            f"Current range: {data.min_current:.6g} to {data.max_current:.6g} A",
        ]
    )
    return "\n".join(lines)


def plot_lsv(input_path: Path, output_path: Path | None = None, show: bool = True) -> None:
    data = read_lsv_data(input_path)

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    ax.plot(data.potentials, data.currents, linewidth=1.5)
    ax.set_xlabel("Potential / V")
    ax.set_ylabel("Current / A")
    ax.set_title(input_path.stem)
    ax.grid(True, alpha=0.3)

    if output_path is not None:
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot a CHI-style LSV text file.")
    parser.add_argument("input", type=Path, help="Input LSV .txt file")
    parser.add_argument("-o", "--output", type=Path, help="Optional plot output path")
    parser.add_argument("--no-show", action="store_true", help="Save only; do not show the plot window")
    args = parser.parse_args()

    plot_lsv(args.input, args.output, show=not args.no_show)


if __name__ == "__main__":
    main()
