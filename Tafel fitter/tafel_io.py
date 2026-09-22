"""Project LSV readers and preparation; no GUI or toolbox imports required."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Dataset:
    source: Path
    name: str
    potential: np.ndarray
    current: np.ndarray
    mode: str  # raw: V/reference, A; eta: overpotential V, A or mA/cm2
    density: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Preparation:
    area: float = 1.0
    reference: float = 0.0
    equilibrium: float = 1.23
    resistance: float = 0.0
    compensation: float = 0.0
    branch: str = "Anodic"
    eta_min: float | None = None
    eta_max: float | None = None
    min_density: float = 0.0


@dataclass
class Prepared:
    eta: np.ndarray
    current_a: np.ndarray
    density: np.ndarray
    log_density: np.ndarray
    source_indices: np.ndarray
    notes: list[str]


def _norm(text):
    return text.strip().lower().replace("²", "2")


def read_datasets(path: str | Path) -> list[Dataset]:
    """Read CHI TXT, both toolbox CSV generations, or original fitter CSV.

    Toolbox LSV exports are rebuilt from Original Potential/Current and recorded
    settings, so editing correction settings never compounds existing corrections.
    Tafel exports already contain eta and are used without further corrections.
    A combined toolbox export yields a separate dataset for each File value.
    """
    path = Path(path)
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines(), skipinitialspace=True))
    metadata = {}
    header = None
    for idx, row in enumerate(rows):
        cols = [_norm(c) for c in row]
        if any(c.startswith("original potential") for c in cols) and any(c.startswith("original current") for c in cols):
            header = (idx, cols, "original")
            break
        if any(c.startswith("overpotential") for c in cols):
            header = (idx, cols, "eta")
            break
        if len(cols) >= 2 and cols[:2] == ["potential/v", "current/a"]:
            header = (idx, cols, "chi")
            break
        for key, token in (("reference", "reference electrode"), ("equilibrium", "equilibrium potential"),
                           ("area", "working area"), ("resistance", "solution resistance")):
            if cols and token in cols[0] and len(row) > 1 and row[1].strip():
                metadata[key] = float(row[1])
        if "compensation level (%)" in cols:
            k = cols.index("compensation level (%)") + 1
            if k < len(row) and row[k].strip():
                metadata["compensation"] = float(row[k])
    if header is None:
        raise ValueError("Unsupported file. Use CHI LSV TXT, toolbox LSV/Tafel CSV, or the original fitter CSV.")
    idx, cols, kind = header
    units = [_norm(c) for c in rows[idx + 1]] if idx + 1 < len(rows) else []
    file_col = cols.index("file") if "file" in cols else None
    if kind == "original":
        xcol = next(i for i, c in enumerate(cols) if c.startswith("original potential"))
        ycol = next(i for i, c in enumerate(cols) if c.startswith("original current"))
        unit = cols[ycol] + " " + (units[ycol] if ycol < len(units) else "")
        if "ma" in unit:
            scale = 0.001
        elif "(a)" in unit or (ycol < len(units) and units[ycol] == "a"):
            scale = 1.0
        else:
            raise ValueError("Original Current must specify A or mA in its header or units row.")
        density = False
    elif kind == "chi":
        xcol, ycol, scale, density = 0, 1, 1.0, False
    else:
        xcol = next(i for i, c in enumerate(cols) if c.startswith("overpotential"))
        density_cols = [i for i, c in enumerate(cols) if c.startswith("current density")]
        density = bool(density_cols)
        if density:
            ycol = density_cols[0]
            unit = cols[ycol] + " " + (units[ycol] if ycol < len(units) else "")
            if "ma" not in unit:
                raise ValueError("Tafel current density must be in mA/cm2.")
        else:
            # The bundled Ir OER example uses this historical label for amperes.
            current_cols = [i for i, c in enumerate(cols) if c in ("<i>/a", "current/a", "current / a", "lsv, baseline adjusted")]
            if not current_cols:
                raise ValueError("Overpotential data need Current/A or Current density (mA/cm2).")
            ycol = current_cols[0]
        scale = 1.0
    groups = {}
    started = False
    for line, row in enumerate(rows[idx + 1:], start=idx + 2):
        if not any(c.strip() for c in row):
            continue
        try:
            x, y = float(row[xcol]), float(row[ycol]) * scale
        except (ValueError, IndexError):
            # Only the explicit Origin units row may be nonnumeric.
            if not started and line == idx + 2 and kind == "original" and len(row) > xcol and row[xcol].strip() == "V":
                continue
            raise ValueError(f"Invalid numeric data at line {line}.") from None
        started = True
        if not np.isfinite([x, y]).all():
            raise ValueError(f"Non-finite data at line {line}.")
        name = row[file_col].strip() if file_col is not None else path.stem
        groups.setdefault(name, []).append((x, y))
    if not groups:
        raise ValueError("The file contains no numeric data.")
    # Match the toolbox's folder-area and filename-resistance conventions.
    for parent in path.parents:
        match = re.search(r"(\d+(?:\.\d+)?)\s*cm(?:\^?2|²)\s*$", parent.name, re.I)
        if match:
            metadata.setdefault("area", float(match[1]))
            break
    match = re.search(r"(\d+(?:\.\d+)?)\s*ohm", path.stem, re.I)
    if match:
        metadata.setdefault("resistance", float(match[1]))
    return [Dataset(path, name, np.array(values)[:, 0], np.array(values)[:, 1],
                    "eta" if kind == "eta" else "raw", density, metadata.copy())
            for name, values in groups.items()]


def prepare(data: Dataset, settings: Preparation) -> Prepared:
    numeric = [settings.area, settings.reference, settings.equilibrium, settings.resistance,
               settings.compensation, settings.min_density]
    numeric += [v for v in (settings.eta_min, settings.eta_max) if v is not None]
    if not np.isfinite(numeric).all():
        raise ValueError("Preparation settings must be finite numbers.")
    if settings.area <= 0 or settings.resistance < 0 or settings.min_density < 0:
        raise ValueError("Area must be positive; resistance and minimum |j| cannot be negative.")
    if not 0 <= settings.compensation <= 100:
        raise ValueError("Compensation must be between 0 and 100 percent.")
    if settings.branch not in ("Anodic", "Cathodic"):
        raise ValueError("Choose Anodic or Cathodic.")
    if settings.eta_min is not None and settings.eta_max is not None and settings.eta_min >= settings.eta_max:
        raise ValueError("Minimum overpotential must be below maximum overpotential.")
    current = data.current * settings.area / 1000 if data.density else data.current.copy()
    eta = data.potential.copy()
    if data.mode == "raw":
        eta = eta + settings.reference - current * settings.resistance * settings.compensation / 100 - settings.equilibrium
    density = current * 1000 / settings.area
    direction = 1 if settings.branch == "Anodic" else -1
    mask = (direction * eta > 0) & (direction * current > 0) & (np.abs(density) > settings.min_density)
    if settings.eta_min is not None:
        mask &= eta >= settings.eta_min
    if settings.eta_max is not None:
        mask &= eta <= settings.eta_max
    indices = np.flatnonzero(mask)
    if len(indices) < 5:
        raise ValueError("Fewer than five points remain. Check branch, reference/equilibrium potentials, and range.")
    # Do not silently merge separate sweeps or sort a folded iR-corrected curve.
    diffs = np.diff(eta[indices])
    if not (np.all(diffs > 0) or np.all(diffs < 0)):
        raise ValueError("Selected overpotential is not strictly monotonic. Select one sweep/range or reduce iR compensation.")
    order = np.argsort(direction * eta[indices])
    indices = indices[order]
    notes = [f"Retained {len(indices)} of {len(eta)} points for the selected branch and range."]
    if data.mode == "eta":
        notes.append("Input overpotential is used as exported; reference, equilibrium and iR settings are not reapplied.")
    return Prepared(eta[indices], current[indices], density[indices], np.log10(np.abs(density[indices])), indices, notes)
