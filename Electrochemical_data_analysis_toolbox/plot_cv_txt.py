from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


DATA_HEADER = ("Potential/V", "Current/A")
METADATA_KEYS = {
    "Init E (V)": "init_e",
    "High E (V)": "high_e",
    "Low E (V)": "low_e",
    "Segment": "segments",
}


@dataclass(frozen=True)
class CVMetadata:
    init_e: float | None = None
    high_e: float | None = None
    low_e: float | None = None
    segments: int | None = None

    @property
    def cycles(self) -> float | None:
        if self.segments is None:
            return None
        return self.segments / 2


@dataclass(frozen=True)
class ZeroCurrentCrossing:
    potential: float
    point_before: int
    point_after: int
    scan_direction: str


@dataclass(frozen=True)
class CVData:
    metadata: CVMetadata
    potentials: list[float]
    currents: list[float]
    zero_crossings: list[ZeroCurrentCrossing]

    @property
    def reference_electrode_potential(self) -> float | None:
        if len(self.zero_crossings) < 2:
            return None
        last_cycle_crossings = self.zero_crossings[-2:]
        return sum(crossing.potential for crossing in last_cycle_crossings) / 2


def parse_metadata(lines: list[str]) -> CVMetadata:
    values: dict[str, float | int] = {}

    for line in lines:
        if "=" not in line:
            continue

        key, raw_value = [part.strip() for part in line.split("=", 1)]
        field = METADATA_KEYS.get(key)
        if field is None:
            continue

        if field == "segments":
            values[field] = int(float(raw_value))
        else:
            values[field] = float(raw_value)

    return CVMetadata(
        init_e=values.get("init_e"),
        high_e=values.get("high_e"),
        low_e=values.get("low_e"),
        segments=values.get("segments"),
    )


def find_zero_current_crossings(
    potentials: list[float],
    currents: list[float],
) -> list[ZeroCurrentCrossing]:
    crossings: list[ZeroCurrentCrossing] = []

    for index in range(len(currents) - 1):
        current_1 = currents[index]
        current_2 = currents[index + 1]
        potential_1 = potentials[index]
        potential_2 = potentials[index + 1]

        if current_1 == 0:
            crossing_potential = potential_1
        elif current_1 * current_2 > 0 or current_1 == current_2:
            continue
        else:
            fraction = -current_1 / (current_2 - current_1)
            crossing_potential = potential_1 + fraction * (potential_2 - potential_1)

        if potential_2 > potential_1:
            direction = "positive-going"
        elif potential_2 < potential_1:
            direction = "negative-going"
        else:
            direction = "flat"

        crossings.append(
            ZeroCurrentCrossing(
                potential=crossing_potential,
                point_before=index + 1,
                point_after=index + 2,
                scan_direction=direction,
            )
        )

    return crossings


def read_cv_data(input_path: Path) -> CVData:
    """Read CHI-style cyclic voltammetry text data and metadata."""
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
            # Stop cleanly if the instrument adds non-numeric notes after the data.
            if potentials:
                break
            raise

    if not potentials:
        raise ValueError("Found the data header, but no numeric data rows were read.")

    return CVData(
        metadata=parse_metadata(lines[:data_start]),
        potentials=potentials,
        currents=currents,
        zero_crossings=find_zero_current_crossings(potentials, currents),
    )


def read_cv_txt(input_path: Path) -> tuple[list[float], list[float]]:
    """Read CHI-style cyclic voltammetry text data after the data header."""
    data = read_cv_data(input_path)
    return data.potentials, data.currents


def format_metadata(metadata: CVMetadata) -> list[str]:
    lines: list[str] = []
    if metadata.init_e is not None:
        lines.append(f"Init E: {metadata.init_e:g} V")
    if metadata.high_e is not None:
        lines.append(f"High E: {metadata.high_e:g} V")
    if metadata.low_e is not None:
        lines.append(f"Low E: {metadata.low_e:g} V")
    if metadata.segments is not None:
        lines.append(f"Segments: {metadata.segments}")
    if metadata.cycles is not None:
        lines.append(f"Cycles: {metadata.cycles:g}")
    return lines


def format_zero_crossings(crossings: list[ZeroCurrentCrossing]) -> list[str]:
    if not crossings:
        return ["Current = 0 A intersections: none found"]

    lines = ["Current = 0 A intersections:"]
    for number, crossing in enumerate(crossings, start=1):
        lines.append(
            f"  {number}. E = {crossing.potential:.6g} V "
            f"({crossing.scan_direction}, points {crossing.point_before}-{crossing.point_after})"
        )
    return lines


def summarize_cv_data(data: CVData) -> str:
    lines = format_metadata(data.metadata)
    if lines:
        lines.append("")
    lines.extend(format_zero_crossings(data.zero_crossings))
    if data.reference_electrode_potential is not None:
        lines.append("")
        lines.append(f"Reference electrode potential: {data.reference_electrode_potential:.6g} V")
    return "\n".join(lines)


def plot_cv(
    input_path: Path,
    output_path: Path | None = None,
    show: bool = True,
) -> None:
    data = read_cv_data(input_path)

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    ax.plot(data.potentials, data.currents, linewidth=1.5)
    if data.zero_crossings:
        ax.scatter(
            [crossing.potential for crossing in data.zero_crossings],
            [0 for _ in data.zero_crossings],
            color="red",
            s=28,
            zorder=3,
            label="Current = 0 A",
        )
    ax.set_xlabel("Potential / V")
    ax.set_ylabel("Current / A")
    ax.set_title(input_path.stem)
    ax.grid(True, alpha=0.3)
    if data.zero_crossings:
        ax.legend(loc="best")

    if output_path is not None:
        fig.savefig(output_path, dpi=300)
        print(f"Saved plot to {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    print(summarize_cv_data(data))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read a CHI-style cyclic voltammetry .txt file and plot current vs potential."
    )
    parser.add_argument("input_file", type=Path, help="Path to the CV text file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional image path to save the plot, such as cv_plot.png.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Save/read the plot without opening a plot window.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plot_cv(args.input_file, output_path=args.output, show=not args.no_show)


if __name__ == "__main__":
    main()
