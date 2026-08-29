"""Band measurement over corrected spectra.

Deliberately generic, like :mod:`ramsess.analysis`. Nothing here knows about any
particular sample, substrate, instrument or wavenumber: every band position,
width and noise region is supplied by the caller from configuration. There are
no literals describing any dataset in this module, and it writes no files and
prints nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# A band measured over fewer points than this is not worth reporting: a located
# maximum and a trapezoid area both stop meaning much on a handful of samples.
# The caller controls the width, so this is a floor, not a tuning knob.
MIN_POINTS = 5


@dataclass(frozen=True, eq=False)
class BandMeasurement:
    """One band measured in one spectrum."""

    centre: float
    """The centre requested by the configuration."""

    half_width: float
    """Half-width of the search window requested by the configuration."""

    position: float
    """Where the maximum was actually found. Bands shift; this is measured."""

    height: float
    """Corrected intensity at ``position``."""

    area: float
    """Trapezoid integral of the corrected intensity across the search window."""

    n_points: int
    """How many samples fell inside the search window."""

    at_edge: bool
    """True when the maximum sits on the first or last point of the window.

    That usually means the true peak lies outside the window and the
    measurement is unreliable, so it is flagged rather than silently reported.
    """

    noise: float | None = None
    """Local noise estimate supplied by the caller, or None if unavailable."""

    @property
    def signal_to_noise(self) -> float | None:
        """Height divided by the noise estimate, or None if there is none."""
        if self.noise is None or self.noise <= 0.0:
            return None
        return self.height / self.noise


def estimate_noise(wave: np.ndarray, intensity: np.ndarray, region: tuple[float, float]) -> float:
    """Estimate local noise as the spread of a featureless stretch of spectrum.

    The region is configuration: which stretch of a given spectral window is
    genuinely featureless is a property of the experiment, not of this code.

    Args:
        wave: Wave axis.
        intensity: Corrected intensity, same length as ``wave``.
        region: ``(low, high)`` bounds of a featureless stretch, in wave units.

    Returns:
        The standard deviation of the corrected intensity inside the region.

    Raises:
        ValueError: If the region falls outside the data or holds too few points.
    """
    low, high = region
    if low >= high:
        raise ValueError(f"noise region {region} must have low < high")
    mask = (wave >= low) & (wave <= high)
    if not mask.any():
        raise ValueError(
            f"noise region [{low}, {high}] lies outside the data range "
            f"[{float(wave.min()):.3f}, {float(wave.max()):.3f}]"
        )
    if int(mask.sum()) < MIN_POINTS:
        raise ValueError(
            f"noise region [{low}, {high}] holds {int(mask.sum())} points, "
            f"fewer than the minimum of {MIN_POINTS}"
        )
    return float(np.std(intensity[mask]))


def measure_band(
    wave: np.ndarray,
    intensity: np.ndarray,
    centre: float,
    half_width: float,
    noise: float | None = None,
) -> BandMeasurement:
    """Measure one band in one spectrum.

    The peak is located as the maximum inside ``centre ± half_width`` rather
    than assumed to sit at ``centre``, because bands shift. A maximum landing on
    either edge of that window is flagged: the real peak is probably outside it.

    Args:
        wave: Wave axis, ascending.
        intensity: Corrected intensity, same length as ``wave``.
        centre: Centre of the search window, from configuration.
        half_width: Half-width of the search window, from configuration.
        noise: Optional local noise estimate, used only to fill in
            :attr:`BandMeasurement.noise`. Supplied by the caller because the
            featureless region it comes from is configuration.

    Returns:
        The measurement.

    Raises:
        ValueError: If ``half_width`` is not positive, if the search window
            falls outside the data range, or if it holds fewer than
            :data:`MIN_POINTS` points.
    """
    if half_width <= 0:
        raise ValueError(f"half_width must be greater than 0, got {half_width}")

    low, high = centre - half_width, centre + half_width
    data_low, data_high = float(wave.min()), float(wave.max())
    if low < data_low or high > data_high:
        raise ValueError(
            f"search window [{low:.3f}, {high:.3f}] for centre {centre} falls outside "
            f"the data range [{data_low:.3f}, {data_high:.3f}]"
        )

    mask = (wave >= low) & (wave <= high)
    count = int(mask.sum())
    if count < MIN_POINTS:
        raise ValueError(
            f"search window [{low:.3f}, {high:.3f}] for centre {centre} holds {count} "
            f"points, fewer than the minimum of {MIN_POINTS}"
        )

    window_wave = wave[mask]
    window_intensity = intensity[mask]
    peak = int(np.argmax(window_intensity))

    return BandMeasurement(
        centre=float(centre),
        half_width=float(half_width),
        position=float(window_wave[peak]),
        height=float(window_intensity[peak]),
        area=float(np.trapezoid(window_intensity, window_wave)),
        n_points=count,
        at_edge=peak in (0, count - 1),
        noise=noise,
    )
