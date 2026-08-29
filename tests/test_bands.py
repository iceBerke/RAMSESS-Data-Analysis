"""Band measurement: peak location, area, edge flag, noise and validation.

Everything here is synthetic. No real data is read.
"""

from __future__ import annotations

import numpy as np
import pytest

from ramsess.bands import MIN_POINTS, estimate_noise, measure_band

WAVE = np.linspace(400.0, 700.0, 601)  # 0.5 cm-1 spacing


def gaussian(wave: np.ndarray, centre: float, height: float, sigma: float) -> np.ndarray:
    return height * np.exp(-0.5 * ((wave - centre) / sigma) ** 2)


# --- peak location ---------------------------------------------------------


def test_locates_a_peak_sitting_at_the_configured_centre() -> None:
    intensity = gaussian(WAVE, 550.0, 1000.0, 4.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=15.0)
    assert result.position == pytest.approx(550.0, abs=0.5)
    assert result.height == pytest.approx(1000.0, rel=1e-6)
    assert result.at_edge is False


@pytest.mark.parametrize("shift", [-8.0, -3.0, 3.0, 8.0])
def test_locates_a_shifted_peak(shift: float) -> None:
    """Bands move; the maximum is found, not assumed to be at centre."""
    true_centre = 550.0 + shift
    intensity = gaussian(WAVE, true_centre, 1000.0, 4.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=15.0)
    assert result.position == pytest.approx(true_centre, abs=0.5)
    assert result.centre == 550.0
    assert result.at_edge is False


def test_reports_the_requested_centre_and_half_width_unchanged() -> None:
    intensity = gaussian(WAVE, 552.0, 500.0, 3.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=12.0)
    assert result.centre == 550.0
    assert result.half_width == 12.0


# --- the edge flag ---------------------------------------------------------


def test_edge_flag_fires_when_the_true_peak_is_outside_the_window() -> None:
    """The peak sits well outside the search window, so the max lands on a rim."""
    intensity = gaussian(WAVE, 600.0, 1000.0, 4.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=15.0)
    assert result.at_edge is True
    assert result.position == pytest.approx(565.0, abs=0.5)


def test_edge_flag_stays_clear_for_a_contained_peak() -> None:
    intensity = gaussian(WAVE, 550.0, 1000.0, 2.0)
    assert measure_band(WAVE, intensity, centre=550.0, half_width=15.0).at_edge is False


# --- area ------------------------------------------------------------------


def test_area_matches_the_analytic_gaussian_integral() -> None:
    """A Gaussian integrates to height * sigma * sqrt(2 pi).

    The search window is +/- 5 sigma, which captures all but ~6e-7 of the true
    integral, so a 0.5% tolerance is loose enough for the trapezoid error on
    this sampling and tight enough to catch a real mistake.
    """
    height, sigma = 1000.0, 3.0
    intensity = gaussian(WAVE, 550.0, height, sigma)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=5 * sigma)
    analytic = height * sigma * np.sqrt(2.0 * np.pi)
    assert result.area == pytest.approx(analytic, rel=0.005)


def test_area_of_a_flat_window_is_height_times_width() -> None:
    intensity = np.full_like(WAVE, 7.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=10.0)
    assert result.area == pytest.approx(7.0 * 20.0, rel=1e-3)


def test_n_points_counts_the_window() -> None:
    result = measure_band(WAVE, np.zeros_like(WAVE), centre=550.0, half_width=10.0)
    assert result.n_points == 41  # 20 cm-1 at 0.5 cm-1 spacing, inclusive


# --- validation ------------------------------------------------------------


@pytest.mark.parametrize("centre", [405.0, 695.0])
def test_window_outside_the_data_range_raises(centre: float) -> None:
    with pytest.raises(ValueError, match="falls outside the data range"):
        measure_band(WAVE, np.zeros_like(WAVE), centre=centre, half_width=15.0)


def test_too_few_points_raises() -> None:
    coarse = np.linspace(400.0, 700.0, 31)  # 10 cm-1 spacing
    with pytest.raises(ValueError, match=f"fewer than the minimum of {MIN_POINTS}"):
        measure_band(coarse, np.zeros_like(coarse), centre=550.0, half_width=10.0)


@pytest.mark.parametrize("half_width", [0.0, -5.0])
def test_non_positive_half_width_raises_in_measure_band(half_width: float) -> None:
    with pytest.raises(ValueError, match="half_width must be greater than 0"):
        measure_band(WAVE, np.zeros_like(WAVE), centre=550.0, half_width=half_width)


# --- noise and signal to noise ---------------------------------------------


def test_estimate_noise_recovers_a_known_standard_deviation() -> None:
    generator = np.random.default_rng(12345)
    intensity = generator.normal(0.0, 25.0, WAVE.size)
    noise = estimate_noise(WAVE, intensity, (500.0, 620.0))
    assert noise == pytest.approx(25.0, rel=0.1)


def test_signal_to_noise_is_height_over_noise() -> None:
    intensity = gaussian(WAVE, 550.0, 900.0, 3.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=12.0, noise=30.0)
    assert result.signal_to_noise == pytest.approx(30.0, rel=1e-9)


def test_signal_to_noise_is_none_without_a_noise_estimate() -> None:
    intensity = gaussian(WAVE, 550.0, 900.0, 3.0)
    assert measure_band(WAVE, intensity, centre=550.0, half_width=12.0).signal_to_noise is None


def test_signal_to_noise_is_none_for_zero_noise() -> None:
    intensity = gaussian(WAVE, 550.0, 900.0, 3.0)
    result = measure_band(WAVE, intensity, centre=550.0, half_width=12.0, noise=0.0)
    assert result.signal_to_noise is None


def test_noise_region_outside_the_data_raises() -> None:
    with pytest.raises(ValueError, match="outside the data range"):
        estimate_noise(WAVE, np.zeros_like(WAVE), (900.0, 1000.0))


def test_noise_region_with_too_few_points_raises() -> None:
    coarse = np.linspace(400.0, 700.0, 31)
    with pytest.raises(ValueError, match="fewer than the minimum"):
        estimate_noise(coarse, np.zeros_like(coarse), (550.0, 560.0))


def test_noise_region_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="must have low < high"):
        estimate_noise(WAVE, np.zeros_like(WAVE), (600.0, 500.0))


def test_measurement_does_not_mutate_its_input() -> None:
    intensity = gaussian(WAVE, 550.0, 1000.0, 4.0)
    before = intensity.copy()
    measure_band(WAVE, intensity, centre=550.0, half_width=15.0)
    assert np.array_equal(intensity, before)
