"""Numerical analysis over intensity arrays.

Deliberately generic. Nothing here knows about any particular sample, substrate,
instrument, band position or spectral window, and nothing here is tuned to one
dataset. Every function operates on an arbitrary intensity array and takes its
parameters from the caller. If a future analysis genuinely needs a band
position, that position is configuration supplied by the caller, never a literal
in this module.

This module writes no files and prints nothing.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from ramsess.io import Spectrum


def fit_baseline(intensity: np.ndarray, lam: float, p: float, n_iter: int) -> np.ndarray:
    """Fit an asymmetric least squares baseline to an intensity array.

    Solves the Eilers and Boelens asymmetric least squares problem: a smooth
    curve is fitted through the data while points lying above the current
    estimate are weighted far less than points lying below it, so the result
    follows the background and passes under the peaks.

    All three parameters are required and have no defaults here. The caller
    resolves them from configuration.

    Args:
        intensity: The values to fit. Not modified.
        lam: Smoothness penalty. Larger values give a stiffer, flatter baseline
            that ignores narrow structure; smaller values let the baseline bend
            to follow the data more closely and risk absorbing real peaks.
        p: Asymmetry, strictly between 0 and 1. It is the weight given to points
            above the current baseline, while points below get ``1 - p``. Small
            values push the fit down towards the underside of the data; a value
            near 0.5 fits through the middle of it.
        n_iter: Number of reweighting passes, at least 1.

    Returns:
        The fitted baseline, a new array with the same shape as ``intensity``.

    Raises:
        ValueError: If ``intensity`` holds a non-finite value, if ``lam`` is not
            greater than 0, if ``n_iter`` is below 1, or if ``p`` is not
            strictly between 0 and 1.
    """
    values = np.asarray(intensity, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("intensity contains non-finite values (NaN or infinity)")
    # Guarded here as well as in the configuration layer, so a direct caller is
    # protected too. With lam = 0 the smoothness penalty vanishes and the solve
    # returns the data itself, making the correction identically zero; a
    # negative lam inverts the penalty. Both fail silently without this check.
    if not lam > 0.0:
        raise ValueError(f"lam must be greater than 0, got {lam}")
    if n_iter < 1:
        raise ValueError(f"n_iter must be at least 1, got {n_iter}")
    if not 0.0 < p < 1.0:
        raise ValueError(f"p must be strictly between 0 and 1, got {p}")

    size = values.size
    # Second-difference operator; lam * D'D is the smoothness penalty.
    differences = sparse.diags(
        diagonals=[1.0, -2.0, 1.0], offsets=[0, -1, -2], shape=(size, size - 2)
    )
    penalty = lam * differences.dot(differences.transpose())

    weights = np.ones(size, dtype=np.float64)
    baseline = np.zeros(size, dtype=np.float64)
    for _ in range(n_iter):
        weighted = sparse.spdiags(weights, 0, size, size)
        baseline = spsolve((weighted + penalty).tocsc(), weights * values)
        weights = np.where(values > baseline, p, 1.0 - p)
    return np.asarray(baseline, dtype=np.float64)


def correct_baseline(
    spectrum: Spectrum, lam: float, p: float, n_iter: int
) -> tuple[np.ndarray, np.ndarray]:
    """Subtract a fitted baseline from one spectrum.

    The spectrum is frozen and its arrays are the file contents, so nothing here
    writes to either. Both returned arrays are new.

    Args:
        spectrum: The spectrum to correct. Not modified.
        lam: Smoothness penalty, see :func:`fit_baseline`.
        p: Asymmetry, see :func:`fit_baseline`.
        n_iter: Number of reweighting passes.

    Returns:
        ``(corrected_intensity, fitted_baseline)``.

    Raises:
        ValueError: Anything :func:`fit_baseline` raises.
    """
    baseline = fit_baseline(spectrum.intensity, lam=lam, p=p, n_iter=n_iter)
    corrected = np.asarray(spectrum.intensity, dtype=np.float64) - baseline
    return corrected, baseline
