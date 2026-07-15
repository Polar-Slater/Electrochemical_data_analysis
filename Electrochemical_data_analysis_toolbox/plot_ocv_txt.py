from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


DATA_HEADER = ("Time/sec", "Potential/V")
METADATA_KEYS = {
    "Sample Interval (V)": "sample_interval",
    "Run Time (sec)": "run_time",
}


@dataclass(frozen=True)
class OCVMetadata:
    sample_interval: float | None = None
    run_time: float | None = None


@dataclass(frozen=True)
class OCVData:
    metadata: OCVMetadata
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


def parse_metadata(lines: list[str]) -> OCVMetadata:
    values: dict[str, float] = {}
    for line in lines:
        if "=" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split("=", 1)]
        field = METADATA_KEYS.get(key)
        if field is None:
            continue
        values[field] = float(raw_value)
    return OCVMetadata(
        sample_interval=values.get("sample_interval"),
        run_time=values.get("run_time"),
    )


def read_ocv_data(path: str | Path) -> OCVData:
    source = Path(path)
    lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()

    data_start = None
    for index, line in enumerate(lines):
        columns = [value.strip() for value in line.split(",")]
        if len(columns) >= 2 and columns[0] == DATA_HEADER[0] and columns[1] == DATA_HEADER[1]:
            data_start = index + 1
            break

    if data_start is None:
        raise ValueError(f"Could not find OCV data header: {', '.join(DATA_HEADER)}")

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
        raise ValueError("Found the OCV header, but no numeric data rows were read.")

    return OCVData(
        metadata=parse_metadata(lines[:data_start]),
        source=source,
        times_sec=times_sec,
        potentials_v=potentials_v,
    )


def summarize_ocv_data(data: OCVData) -> str:
    lines: list[str] = []
    if data.metadata.sample_interval is not None:
        lines.append(f"Sample interval: {data.metadata.sample_interval:g}")
    if data.metadata.run_time is not None:
        lines.append(f"Run time: {data.metadata.run_time:g} s")
    if lines:
        lines.append("")

    lines.extend(
        [
            f"File: {data.source.name}",
            f"Points: {data.point_count}",
            f"Time: {data.min_time:.6g} to {data.max_time:.6g} s",
            f"Potential: {data.min_potential:.6g} to {data.max_potential:.6g} V",
            f"Final potential: {data.final_potential:.6g} V",
        ]
    )
    return "\n".join(lines)


def plot_ocv(input_path: Path, output_path: Path | None = None, show: bool = True) -> None:
    data = read_ocv_data(input_path)

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
    parser = argparse.ArgumentParser(description="Plot a CHI-style OCV text file.")
    parser.add_argument("input", type=Path, help="Input OCV .txt file")
    parser.add_argument("-o", "--output", type=Path, help="Optional plot output path")
    parser.add_argument("--no-show", action="store_true", help="Save only; do not show the plot window")
    args = parser.parse_args()

    plot_ocv(args.input, args.output, show=not args.no_show)


if __name__ == "__main__":
    main()
