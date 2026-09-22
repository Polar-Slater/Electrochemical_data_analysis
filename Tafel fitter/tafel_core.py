"""Python 3 adaptation of MEG-LBNL Tafel_Fitter v1.51's selection method.

Agbo & Danilovic, J. Phys. Chem. C (2019), DOI 10.1021/acs.jpcc.9b06820.
Window regressions -> residual minima -> window-width span -> Tafel R squared.
The physical residual uses the paper's i0*n*F/(R*T), not v1.51's i0*F/(n*R*T).
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Event

import numpy as np
from numpy.polynomial import Polynomial

from tafel_io import Prepared

R, F = 8.314462618, 96485.33212


class FitCancelled(Exception):
    pass


@dataclass(frozen=True)
class FitSettings:
    width_min_mv: float = 10
    width_max_mv: float = 50
    width_step_mv: float = 1
    r2_min: float = 0.9
    r2_max: float = 0.999
    r2_step: float = 0.001
    bin_mv: float = 1
    temperature: float = 293
    electrons: float = 1
    min_points: int = 5
    derivative_cutoff: bool = False
    polynomial_order: int = 15


@dataclass(frozen=True)
class Candidate:
    start: int
    stop: int  # exclusive; indices into Prepared
    width_mv: float
    slope_mv: float
    i0_a: float
    log_i0_a: float
    residue: float
    tafel_r2: float
    lsv_r2: float
    threshold: float


@dataclass
class FitResult:
    best: Candidate
    minima: list[Candidate]
    candidates_tested: int
    derivative_eta: np.ndarray
    derivative: np.ndarray
    derivative_fit: np.ndarray
    cutoff_index: int
    notes: list[str]


def _grid(low, high, step):
    return low + np.arange(int(np.floor((high - low) / step + 1e-8)) + 1) * step


def validate(settings: FitSettings):
    values = [v for v in vars(settings).values() if isinstance(v, (float, int))]
    if not np.isfinite(values).all():
        raise ValueError("Fit settings must be finite.")
    if not 0 < settings.width_min_mv <= settings.width_max_mv or settings.width_step_mv <= 0:
        raise ValueError("Window widths and step must be positive, with minimum <= maximum.")
    if not 0 <= settings.r2_min <= settings.r2_max <= 1 or settings.r2_step <= 0:
        raise ValueError("R² bounds must satisfy 0 <= minimum <= maximum <= 1; step must be positive.")
    if settings.bin_mv <= 0 or settings.temperature <= 0 or settings.electrons <= 0:
        raise ValueError("Bin width, temperature and electron number must be positive.")
    if settings.min_points < 3 or int(settings.min_points) != settings.min_points:
        raise ValueError("Minimum points must be an integer of at least 3.")
    if not 1 <= settings.polynomial_order <= 30 or int(settings.polynomial_order) != settings.polynomial_order:
        raise ValueError("Polynomial order must be an integer from 1 to 30.")
    nw = (settings.width_max_mv - settings.width_min_mv) / settings.width_step_mv + 1
    nr = (settings.r2_max - settings.r2_min) / settings.r2_step + 1
    if nw * nr > 200_000 or nw > 5000 or nr > 5000:
        raise ValueError("Too many fit settings. Increase width or R² steps.")


def fit(data: Prepared, settings: FitSettings, cancel: Event | None = None, progress=None) -> FitResult:
    validate(settings)
    def check():
        if cancel is not None and cancel.is_set():
            raise FitCancelled("Fitting cancelled.")
    check()
    eta = data.eta
    direction = 1 if eta[0] > 0 else -1
    x = direction * eta
    current = np.abs(data.current_a)
    if len(x) < settings.min_points or np.any(np.diff(x) <= 0):
        raise ValueError("Fitting needs enough strictly ordered overpotential points.")
    derivative = np.diff(current) / np.diff(x)
    dx = (x[1:] + x[:-1]) / 2
    degree = min(settings.polynomial_order, len(dx) - 1)
    curve = Polynomial.fit(dx, derivative, degree)(dx)
    cutoff = len(x)
    notes = list(data.notes)
    if settings.derivative_cutoff:
        peak = int(np.argmax(curve))
        cutoff = peak + 1
        notes.append(f"Derivative cutoff enabled: fitting only points below |eta| = {dx[peak]:.6g} V.")
        if cutoff < settings.min_points:
            raise ValueError("Derivative cutoff leaves too few points. Inspect the derivative or disable the cutoff.")
    else:
        notes.append("Derivative cutoff disabled; the selected potential range defines the candidate kinetic region.")
    widths = _grid(settings.width_min_mv, settings.width_max_mv, settings.width_step_mv)
    thresholds = _grid(settings.r2_min, settings.r2_max, settings.r2_step)
    if len(widths) * len(x) > 2_000_000:
        raise ValueError("Too many candidate windows. Narrow the potential range or increase the width step.")
    logi = np.log10(current)
    # Prefix sums allow O(1) regression per candidate window.
    def prefix(v):
        return np.concatenate(([0.0], np.cumsum(v)))
    px, pxx = prefix(x), prefix(x*x)
    py, pyy, pxy = prefix(logi), prefix(logi*logi), prefix(x*logi)
    pi, pii, pxi = prefix(current), prefix(current*current), prefix(x*current)
    minima = []
    tested = 0
    for wi, width in enumerate(widths):
        check()
        starts = np.arange(cutoff)
        targets = x[:cutoff] + width / 1000
        # End at the last acquired point within the requested width, inclusive.
        stops = np.searchsorted(x[:cutoff], targets + 1e-12, side="right")
        good = (targets <= x[cutoff - 1] + 1e-12) & (stops - starts >= settings.min_points)
        starts, stops = starts[good], stops[good]
        # Never bridge filtered-out points (current sign/range gaps).
        good = np.abs(data.source_indices[stops - 1] - data.source_indices[starts]) == stops - starts - 1
        starts, stops = starts[good], stops[good]
        tested += len(starts)
        if not len(starts):
            continue
        count = stops - starts
        sx = px[stops] - px[starts]
        sxx = pxx[stops] - pxx[starts] - sx*sx/count
        def regression(pv, pvv, pxv):
            sy = pv[stops] - pv[starts]
            syy = pvv[stops] - pvv[starts] - sy*sy/count
            sxy = pxv[stops] - pxv[starts] - sx*sy/count
            with np.errstate(divide="ignore", invalid="ignore"):
                slope = sxy/sxx
                intercept = (sy-slope*sx)/count
                r2 = sxy*sxy/(sxx*syy)
            return slope, intercept, np.clip(r2, 0, 1)
        slope, intercept, r2t = regression(py, pyy, pxy)
        slope_i, _, r2i = regression(pi, pii, pxi)
        with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
            i0 = 10.0**intercept
            residual = np.abs(slope_i - i0*settings.electrons*F/(R*settings.temperature))
            slopes_mv = direction*1000/slope
        valid = (slope > 0) & (slope_i > 0) & (i0 > 0) & np.isfinite(residual) & np.isfinite(slopes_mv)
        for threshold in thresholds:
            allowed = np.flatnonzero(valid & (r2t >= threshold) & (r2i >= threshold))
            if not len(allowed):
                continue
            k = allowed[np.argmin(residual[allowed])]
            minima.append(Candidate(int(starts[k]), int(stops[k]), float(width), float(slopes_mv[k]),
                                    float(i0[k]), float(intercept[k]), float(residual[k]), float(r2t[k]),
                                    float(r2i[k]), float(threshold)))
        if progress:
            progress((wi + 1) / len(widths))
    check()
    if not minima:
        raise ValueError("No admissible fits. Check the selected region, window widths, minimum points and R² thresholds.")
    # Fixed bins anchored to zero; count DISTINCT window widths, not repeated thresholds.
    bins = {}
    for candidate in minima:
        key = int(np.floor(np.round(abs(candidate.slope_mv) / settings.bin_mv, 9)))
        bins.setdefault(key, []).append(candidate)
    spans = {key: len({c.width_mv for c in values}) for key, values in bins.items()}
    max_span = max(spans.values())
    finalists = [c for key, values in bins.items() if spans[key] == max_span for c in values]
    best = max(finalists, key=lambda c: (c.tafel_r2, c.lsv_r2, -c.residue, c.width_mv))
    notes.append(f"Winning slope bin spans {max_span} distinct window width(s); {len(minima)} residual minima retained.")
    if max_span == 1:
        notes.append("Only one window width supports the selected bin; window-width stability is not established.")
    return FitResult(best, minima, tested, direction*dx, derivative, curve, cutoff, notes)
