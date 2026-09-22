"""Plots and exports for the standalone fitter."""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
from numpy.polynomial import Polynomial

from tafel_core import FitResult, FitSettings
from tafel_io import Dataset, Preparation, Prepared
from tafel_version import __version__


def draw(figure, data: Prepared, settings: FitSettings, result: FitResult | None = None):
    figure.clear()
    lsv, tafel, derivative, stability = figure.subplots(2, 2).flat
    lsv.plot(data.eta, data.density, color="#1f6feb", lw=1.4)
    lsv.set(xlabel="Overpotential / V", ylabel="j / mA cm$^{-2}$", title="Polarization curve")
    tafel.plot(data.log_density, data.eta * 1000, color="#1f6feb", lw=1.4, label="Data")
    tafel.set(xlabel="log$_{10}$(|j| / mA cm$^{-2}$)", ylabel="Overpotential / mV", title="Tafel plot")
    direction = 1 if data.eta[0] > 0 else -1
    x = direction * data.eta
    dx = (x[1:] + x[:-1]) / 2
    dy = np.diff(np.abs(data.current_a)) / np.diff(x)
    polynomial = Polynomial.fit(dx, dy, min(settings.polynomial_order, len(dx) - 1))(dx)
    derivative.plot(direction*dx, dy, color="#a7b3c4", lw=1, label="Measured")
    derivative.plot(direction*dx, polynomial, color="#df7d22", label="Polynomial")
    if settings.derivative_cutoff:
        derivative.axvline(direction*dx[np.argmax(polynomial)], color="#cf4444", ls="--", label="Cutoff")
    derivative.set(xlabel="Overpotential / V", ylabel="d|I| / d|eta| / A V$^{-1}$", title="Derivative diagnostic")
    derivative.legend(fontsize=8)
    stability.set(xlabel="Requested window width / mV", ylabel="|Tafel slope| / mV decade$^{-1}$", title="Residual-minimized fits")
    if result is not None:
        b = result.best
        selected = slice(b.start, b.stop)
        # density/current is 1000/area, so the intercept conversion is log10(1000/area).
        fit_log_density = direction*1000/abs(b.slope_mv)*data.eta[selected] + b.log_i0_a + np.log10(abs(data.density[0]/data.current_a[0]))
        tafel.plot(fit_log_density, data.eta[selected]*1000, color="#d34940", lw=2.4, label=f"Fit: {b.slope_mv:.2f} mV/dec")
        tafel.scatter(data.log_density[[b.start, b.stop-1]], data.eta[[b.start, b.stop-1]]*1000, color="#d34940", s=22)
        lsv.axvspan(min(data.eta[selected]), max(data.eta[selected]), color="#d34940", alpha=0.15)
        values = result.minima
        dots = stability.scatter([v.width_mv for v in values], [abs(v.slope_mv) for v in values],
                                 c=[v.tafel_r2 for v in values], cmap="viridis", s=10, alpha=0.65)
        figure.colorbar(dots, ax=stability, label="Tafel R²", shrink=0.8)
        stability.scatter([b.width_mv], [abs(b.slope_mv)], marker="*", s=160, color="#d34940", zorder=5)
    else:
        stability.text(0.5, 0.5, "Run automatic fit to compare windows", ha="center", transform=stability.transAxes, color="#637083")
    tafel.legend(fontsize=8)
    for axis in (lsv, tafel, derivative, stability):
        axis.grid(alpha=0.18)
    figure.tight_layout(pad=2)


def export_bundle(parent: Path, source: Dataset, preparation: Preparation, settings: FitSettings,
                  data: Prepared, result: FitResult, figure) -> Path:
    """Each export gets a new folder; original input files are never overwritten."""
    safe = re.sub(r'[^\w .-]', '_', Path(source.name).stem).strip('. ') or "dataset"
    destination = parent / f"{safe}_tafel_{datetime.now():%Y%m%d_%H%M%S_%f}"
    destination.mkdir(parents=True, exist_ok=False)
    def write(name, rows):
        with (destination / name).open("w", encoding="utf-8-sig", newline="") as stream:
            csv.writer(stream).writerows(rows)
    def applied(key):
        return source.metadata.get(key, "") if source.mode == "eta" else getattr(preparation, key)
    metadata = [
        ["Software", "Tafel fitter"], ["Software version", __version__],
        ["Source file", str(source.source)], ["Dataset", source.name],
        ["Reference electrode potential (V vs. RHE)", applied("reference")],
        ["Equilibrium potential (V vs. RHE)", applied("equilibrium")],
        ["Working area (cm²)", preparation.area],
        ["Solution resistance (ohm)", applied("resistance"), "Compensation level (%)", applied("compensation")],
        ["Input mode", source.mode], ["Branch", preparation.branch], [],
    ]
    best = result.best
    # Same Tafel columns as the toolbox plus explicit fit membership.
    rows = metadata + [["File", "Point", "Corrected potential (V)", "Current density (mA/cm²)",
                        "log10(|j| / mA cm^-2)", "Overpotential (V)", "Used in selected fit"]]
    input_equilibrium = source.metadata.get("equilibrium") if source.mode == "eta" else preparation.equilibrium
    rows += [[source.name, int(data.source_indices[i])+1,
              float(eta + input_equilibrium) if input_equilibrium is not None else "",
              float(data.density[i]), float(data.log_density[i]), float(eta), int(best.start <= i < best.stop)]
             for i, eta in enumerate(data.eta)]
    write("tafel_data.csv", rows)
    header = ["R2 threshold", "Requested window width", "Actual window width", "Tafel slope",
              "Exchange current", "Exchange current density", "Tafel residual", "Starting overpotential",
              "Ending overpotential", "Tafel R2", "LSV R2", "Points"]
    units = ["", "mV", "mV", "mV/decade", "A", "mA/cm²", "A/V", "V", "V", "", "", ""]
    def candidate_row(c):
        return [c.threshold, c.width_mv, abs(data.eta[c.stop-1]-data.eta[c.start])*1000, c.slope_mv,
                c.i0_a, c.i0_a*1000/preparation.area, c.residue, data.eta[c.start], data.eta[c.stop-1],
                c.tafel_r2, c.lsv_r2, c.stop-c.start]
    write("fit_summary.csv", metadata + [header, units, candidate_row(best)])
    write("residual_minima.csv", [header, units] + [candidate_row(c) for c in result.minima])
    report = {"software": "Tafel fitter", "software_version": __version__,
              "method": "Adapted MEG-LBNL Tafel_Fitter v1.51; DOI 10.1021/acs.jpcc.9b06820",
              "source": str(source.source), "dataset": source.name, "input_mode": source.mode,
              "input_metadata": source.metadata, "preparation": asdict(preparation),
              "fit_settings": asdict(settings), "selected_fit": asdict(best),
              "candidates_tested": result.candidates_tested, "notes": result.notes}
    (destination / "settings_and_results.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    figure.savefig(destination / "tafel_fit.png", dpi=200)
    return destination
