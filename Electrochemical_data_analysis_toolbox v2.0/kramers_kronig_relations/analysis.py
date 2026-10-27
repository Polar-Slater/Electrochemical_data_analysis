"""Linear Kramers--Kronig consistency testing for impedance spectra."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class KKResult:
    frequency: np.ndarray
    measured: np.ndarray
    fitted: np.ndarray
    residual_real_pct: np.ndarray
    residual_imag_pct: np.ndarray
    rc_count: int
    mu: float
    rms_residual_pct: float
    max_residual_pct: float
    chi_squared: float
    parameters: np.ndarray
    time_constants: np.ndarray


def _design_matrix(omega: np.ndarray, tau: np.ndarray, include_capacitance: bool) -> np.ndarray:
    n = omega.size
    real = [np.ones(n), np.zeros(n)]
    imag = [np.zeros(n), omega]
    if include_capacitance:
        real.append(np.zeros(n))
        imag.append(-1.0 / omega)
    wt = omega[:, None] * tau[None, :]
    real.extend((1.0 / (1.0 + wt**2)).T)
    imag.extend((-wt / (1.0 + wt**2)).T)
    return np.vstack((np.column_stack(real), np.column_stack(imag)))


def _fit(frequency: np.ndarray, impedance: np.ndarray, rc_count: int, include_capacitance: bool):
    omega = 2.0 * np.pi * frequency
    tau = np.logspace(np.log10(1.0 / omega.max()), np.log10(1.0 / omega.min()), rc_count)
    matrix = _design_matrix(omega, tau, include_capacitance)
    target = np.concatenate((impedance.real, impedance.imag))
    scale = np.maximum(np.abs(impedance), np.finfo(float).eps)
    weights = np.concatenate((1.0 / scale, 1.0 / scale))
    parameters, *_ = np.linalg.lstsq(matrix * weights[:, None], target * weights, rcond=None)
    prediction = matrix @ parameters
    fitted = prediction[: frequency.size] + 1j * prediction[frequency.size :]
    resistances = parameters[3 if include_capacitance else 2 :]
    positive = resistances[resistances >= 0].sum()
    negative = np.abs(resistances[resistances < 0]).sum()
    mu = 1.0 - negative / positive if positive > 0 else -np.inf
    return fitted, parameters, tau, float(mu)


def linear_kk(
    frequency: np.ndarray,
    impedance: np.ndarray,
    *,
    max_rc: int = 40,
    mu_threshold: float = 0.85,
    include_capacitance: bool = True,
) -> KKResult:
    """Fit a linear RC basis and return Kramers--Kronig residual diagnostics."""

    frequency = np.asarray(frequency, dtype=float)
    impedance = np.asarray(impedance, dtype=complex)
    if frequency.ndim != 1 or impedance.ndim != 1 or frequency.size != impedance.size:
        raise ValueError("frequency and impedance must be one-dimensional arrays of equal length")
    if frequency.size < 4 or np.any(~np.isfinite(frequency)) or np.any(frequency <= 0):
        raise ValueError("at least four finite, positive frequencies are required")
    if np.any(~np.isfinite(impedance)):
        raise ValueError("impedance contains non-finite values")
    if not 0.0 < mu_threshold <= 1.0:
        raise ValueError("mu_threshold must be in (0, 1]")

    parameter_count = 3 if include_capacitance else 2
    upper = min(max(2, int(max_rc)), max(2, frequency.size - parameter_count))
    selected = None
    for rc_count in range(2, upper + 1):
        candidate = _fit(frequency, impedance, rc_count, include_capacitance)
        if candidate[3] < mu_threshold and selected is not None:
            break
        selected = (rc_count, *candidate)

    assert selected is not None
    rc_count, fitted, parameters, tau, mu = selected
    magnitude = np.maximum(np.abs(impedance), np.finfo(float).eps)
    residual_real = 100.0 * (impedance.real - fitted.real) / magnitude
    residual_imag = 100.0 * (impedance.imag - fitted.imag) / magnitude
    combined = np.sqrt(residual_real**2 + residual_imag**2)
    chi_squared = float(np.mean(np.abs((impedance - fitted) / magnitude) ** 2))
    return KKResult(
        frequency,
        impedance,
        fitted,
        residual_real,
        residual_imag,
        rc_count,
        mu,
        float(np.sqrt(np.mean(combined**2))),
        float(np.max(combined)),
        chi_squared,
        parameters,
        tau,
    )
