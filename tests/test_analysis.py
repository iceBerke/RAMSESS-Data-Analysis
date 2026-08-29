"""Baseline fitting: recovery, purity, and input validation.

Everything here is synthetic. No real data is read.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from ramsess.analysis import correct_baseline, fit_baseline
from ramsess.io import Spectrum

# Fit parameters used across these tests. Chosen to suit the synthetic signal
# below, not carried over from any dataset.
LAM = 1e5
P = 0.01
N_ITER = 10

# The synthetic peak must be recovered to within this fraction of its true
# height. See test_recovers_a_known_peak_height for what the fit actually
# achieves; the assertion is deliberately looser than the measured value so the
# test does not become a change detector.
PEAK_TOLERANCE = 0.05


def synthetic(
    n: int = 600, peak_height: float = 1000.0, peak_centre: float = 300.0, width: float = 8.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(wave, intensity, true_background)`` for a known signal.

    A quadratic background with a single Gaussian peak on top, so both the peak
    height and the background are known exactly.
    """
    wave = np.linspace(100.0, 700.0, n)
    background = 500.0 + 0.9 * (wave - 100.0) - 0.0011 * (wave - 100.0) ** 2
    peak = peak_height * np.exp(-0.5 * ((wave - peak_centre) / width) ** 2)
    return wave, background + peak, background


def make_spectrum(wave: np.ndarray, intensity: np.ndarray) -> Spectrum:
    return Spectrum(
        wave=wave,
        intensity=intensity,
        sample="s",
        window="low",
        step=0,
        experiment="exp",
        path=Path("s_low_0.txt"),
        has_header=True,
    )


# --- recovery --------------------------------------------------------------


def test_recovers_a_known_peak_height() -> None:
    """The corrected peak must match the Gaussian height that was added."""
    wave, intensity, _ = synthetic(peak_height=1000.0)
    baseline = fit_baseline(intensity, lam=LAM, p=P, n_iter=N_ITER)
    corrected = intensity - baseline
    recovered = float(corrected.max())
    relative_error = abs(recovered - 1000.0) / 1000.0
    assert relative_error < PEAK_TOLERANCE, (
        f"recovered {recovered:.2f} against a true height of 1000.0, "
        f"relative error {relative_error:.4f}"
    )


def test_recovers_the_background_shape() -> None:
    """Away from the peak the fit should track the true background closely."""
    wave, intensity, background = synthetic()
    baseline = fit_baseline(intensity, lam=LAM, p=P, n_iter=N_ITER)
    away = np.abs(wave - 300.0) > 60.0
    relative = np.abs(baseline[away] - background[away]) / np.abs(background[away])
    assert float(relative.max()) < 0.05


def test_flat_spectrum_gives_a_flat_baseline_and_near_zero_correction() -> None:
    flat = np.full(400, 1234.5)
    baseline = fit_baseline(flat, lam=LAM, p=0.5, n_iter=N_ITER)
    assert float(np.ptp(baseline)) < 1e-6, "a flat input must give a flat baseline"
    corrected = flat - baseline
    assert float(np.max(np.abs(corrected))) < 1e-6


# --- purity ----------------------------------------------------------------


def test_fit_baseline_does_not_mutate_its_input() -> None:
    _, intensity, _ = synthetic()
    before = intensity.copy()
    fit_baseline(intensity, lam=LAM, p=P, n_iter=N_ITER)
    assert np.array_equal(intensity, before)


def test_correct_baseline_does_not_mutate_the_spectrum() -> None:
    wave, intensity, _ = synthetic()
    spectrum = make_spectrum(wave, intensity)
    wave_before = spectrum.wave.copy()
    intensity_before = spectrum.intensity.copy()

    corrected, baseline = correct_baseline(spectrum, lam=LAM, p=P, n_iter=N_ITER)

    assert np.array_equal(spectrum.wave, wave_before)
    assert np.array_equal(spectrum.intensity, intensity_before)
    assert corrected is not spectrum.intensity
    assert baseline is not spectrum.intensity


def test_correction_reconstructs_the_original() -> None:
    """corrected + baseline must return the input, to float64 tolerance."""
    wave, intensity, _ = synthetic()
    spectrum = make_spectrum(wave, intensity)
    corrected, baseline = correct_baseline(spectrum, lam=LAM, p=P, n_iter=N_ITER)
    scale = float(np.max(np.abs(intensity)))
    residual = float(np.max(np.abs(corrected + baseline - intensity)))
    assert residual < 1e-9 * scale, f"max reconstruction residual {residual:.3g}"


def test_the_frozen_spectrum_cannot_be_reassigned() -> None:
    wave, intensity, _ = synthetic()
    spectrum = make_spectrum(wave, intensity)
    with pytest.raises(dataclasses.FrozenInstanceError):
        spectrum.intensity = np.zeros_like(intensity)  # type: ignore[misc]


# --- validation ------------------------------------------------------------


@pytest.mark.parametrize("bad_p", [0.0, 1.0, -0.1, 1.5])
def test_invalid_p_raises(bad_p: float) -> None:
    _, intensity, _ = synthetic()
    with pytest.raises(ValueError, match="p must be strictly between 0 and 1"):
        fit_baseline(intensity, lam=LAM, p=bad_p, n_iter=N_ITER)


@pytest.mark.parametrize("bad_lam", [0, 0.0, -1.0, -1e6])
def test_invalid_lam_raises(bad_lam: float) -> None:
    """Guarded in the module itself, not only in the configuration layer.

    With lam = 0 the penalty vanishes and the fit returns the data, making the
    correction identically zero; without this guard that failed silently.
    """
    _, intensity, _ = synthetic()
    with pytest.raises(ValueError, match="lam must be greater than 0"):
        fit_baseline(intensity, lam=bad_lam, p=P, n_iter=N_ITER)


def test_correct_baseline_propagates_the_lam_guard() -> None:
    wave, intensity, _ = synthetic()
    spectrum = make_spectrum(wave, intensity)
    with pytest.raises(ValueError, match="lam must be greater than 0"):
        correct_baseline(spectrum, lam=0.0, p=P, n_iter=N_ITER)


@pytest.mark.parametrize("bad_iter", [0, -1, -10])
def test_invalid_n_iter_raises(bad_iter: int) -> None:
    _, intensity, _ = synthetic()
    with pytest.raises(ValueError, match="n_iter must be at least 1"):
        fit_baseline(intensity, lam=LAM, p=P, n_iter=bad_iter)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_non_finite_input_raises(bad_value: float) -> None:
    _, intensity, _ = synthetic()
    intensity = intensity.copy()
    intensity[10] = bad_value
    with pytest.raises(ValueError, match="non-finite"):
        fit_baseline(intensity, lam=LAM, p=P, n_iter=N_ITER)


def test_correct_baseline_propagates_validation_errors() -> None:
    wave, intensity, _ = synthetic()
    spectrum = make_spectrum(wave, intensity)
    with pytest.raises(ValueError, match="p must be strictly"):
        correct_baseline(spectrum, lam=LAM, p=0.0, n_iter=N_ITER)


def test_output_shape_matches_input() -> None:
    for size in (50, 137, 600):
        values = np.linspace(10.0, 20.0, size)
        assert fit_baseline(values, lam=LAM, p=P, n_iter=N_ITER).shape == (size,)


def test_smaller_lam_follows_the_data_more_closely() -> None:
    """Documented behaviour of lam: smaller is more flexible."""
    _, intensity, _ = synthetic()
    stiff = fit_baseline(intensity, lam=1e8, p=P, n_iter=N_ITER)
    flexible = fit_baseline(intensity, lam=1e2, p=P, n_iter=N_ITER)
    assert float(np.sum(np.abs(flexible - intensity))) < float(
        np.sum(np.abs(stiff - intensity))
    )
