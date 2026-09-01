"""Excluding the reference band from a panel's upper limit.

A band tens of times taller than its neighbours sets the panel's limit and
flattens everything else against the floor. The exclusion scales the panel to
the rest of the data instead. Three properties matter and none is visible from a
filename, so they are asserted here rather than in ``test_output_filenames.py``:

* the panel that does NOT hold the reference band is untouched - the exclusion
  is per panel, keyed on the band's own window;
* the reference band's peak ends up ABOVE the new limit, which is the whole
  point and the thing a no-op rename would fail;
* the title says which band was excluded, because a reader whose peak is off the
  top has no other way to know.

Everything is built in ``tmp_path`` and in memory. Nothing is saved, and the
project's ``figures/`` tree is never touched.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest

from conftest import vary, write_spectrum_file
from ramsess.io import load_experiment
from ramsess.plotting import build_sample_overlay
from ramsess.report import BandSpec

BASELINE = {
    "low": {"lam": 1e6, "p": 0.01, "n_iter": 10},
    "high": {"lam": 1e8, "p": 0.01, "n_iter": 10},
}

# A tall band in the low window and ordinary ones either side, so excluding the
# tall one changes the low panel a lot and the high panel not at all.
TALL = BandSpec(name="tall", centre=250.0, half_width=6.0, window="low")
BANDS = {
    "tall": TALL,
    "small": BandSpec(name="small", centre=290.0, half_width=6.0, window="low"),
    "other": BandSpec(name="other", centre=2450.0, half_width=6.0, window="high"),
}

COMBINATIONS = [(False, False), (False, True), (True, False), (True, True)]  # baseline, logy


def spectrum(start: float, spacing: float, n: int, base: float, spikes: dict[int, float]):
    """A flat spectrum with named spikes, so peak heights are controlled."""
    lines, wave = [], start
    for i in range(n):
        wave += spacing * (1.0 + 0.1 * (i % 3))
        lines.append(f"{wave:.6f}\t{base * spikes.get(i, 1.0):.6f}")
    return lines


@pytest.fixture(scope="module")
def spectra(tmp_path_factory):
    """One sample, both windows, three steps.

    The low window carries a spike 40x the baseline inside ``tall`` and a modest
    one inside ``small``; the high window carries an ordinary peak. The 40x
    factor is what makes the exclusion's effect unmistakable.
    """
    folder = tmp_path_factory.mktemp("exclusion") / "raw" / "exp"
    folder.mkdir(parents=True)
    for index, step in enumerate(("0", "irr1", "irr2")):
        write_spectrum_file(
            folder / f"s_low_{step}.txt",
            vary(spectrum(200.0, 2.5, 40, 1000.0, {17: 40.0, 32: 3.0}), index),
        )
        write_spectrum_file(
            folder / f"s_high_{step}.txt",
            vary(spectrum(2400.0, 2.0, 40, 5000.0, {20: 4.0}), index),
        )
    return load_experiment(folder.parent, "exp")


def panel_peak(panel, low: float, high: float) -> float:
    """The tallest drawn value between two wave positions, in data units."""
    peak = -np.inf
    for line in panel.lines:
        wave = np.asarray(line.get_xdata())
        if wave.size < 5:
            continue
        values = np.asarray(line.get_ydata())
        inside = (wave >= low) & (wave <= high)
        if inside.any():
            peak = max(peak, float(values[inside].max()))
    return peak


def test_the_tall_band_really_does_dominate_the_unexcluded_panel(spectra) -> None:
    """Guards the tests below: without a dominating band they prove nothing."""
    figure = build_sample_overlay(spectra)
    try:
        panel = figure.axes[0]
        bottom, top = panel.get_ylim()
        tall = panel_peak(panel, TALL.centre - TALL.half_width, TALL.centre + TALL.half_width)
        small = panel_peak(panel, 284.0, 296.0)
        assert (tall - bottom) / (top - bottom) > 0.9
        assert (small - bottom) / (top - bottom) < 0.2, (
            "the other band is not flattened, so the fixture does not reproduce "
            "the problem the exclusion exists to fix"
        )
    finally:
        plt.close(figure)


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_the_excluded_band_ends_up_above_the_upper_limit(
    spectra, baseline: bool, logy: bool
) -> None:
    """The point of the change. A no-op rename fails this."""
    figure = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        exclude_from_scale=TALL,
    )
    try:
        panel = figure.axes[0]
        _, top = panel.get_ylim()
        peak = panel_peak(panel, TALL.centre - TALL.half_width, TALL.centre + TALL.half_width)
        assert peak > top, (
            f"the excluded band peaks at {peak:.1f} but the panel's limit is "
            f"{top:.1f}: it was not excluded from the scale"
        )
    finally:
        plt.close(figure)


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_the_other_band_is_no_longer_flattened(spectra, baseline: bool, logy: bool) -> None:
    """The benefit, stated as a number rather than assumed from the limit."""
    plain = build_sample_overlay(spectra, logy=logy, baseline_params=BASELINE if baseline else None)
    excluded = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        exclude_from_scale=TALL,
    )
    try:
        def fraction(figure):
            panel = figure.axes[0]
            bottom, top = panel.get_ylim()
            return (panel_peak(panel, 284.0, 296.0) - bottom) / (top - bottom)

        before, after = fraction(plain), fraction(excluded)
        assert after > before * 2, (
            f"the other band occupies {100 * before:.1f}% of the panel before and "
            f"{100 * after:.1f}% after: the exclusion bought almost nothing"
        )
    finally:
        plt.close(plain)
        plt.close(excluded)


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_the_panel_without_the_reference_band_is_untouched(
    spectra, baseline: bool, logy: bool
) -> None:
    """The exclusion is per panel, keyed on the band's own window."""
    plain = build_sample_overlay(spectra, logy=logy, baseline_params=BASELINE if baseline else None)
    excluded = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        exclude_from_scale=TALL,
    )
    try:
        assert TALL.window == "low"
        assert excluded.axes[1].get_ylim() == plain.axes[1].get_ylim()
        assert excluded.axes[1].get_xlim() == plain.axes[1].get_xlim()
        for a, b in zip(excluded.axes[1].lines, plain.axes[1].lines):
            assert np.array_equal(a.get_xdata(), b.get_xdata())
            assert np.array_equal(a.get_ydata(), b.get_ydata())
    finally:
        plt.close(plain)
        plt.close(excluded)


def test_the_title_names_the_excluded_band(spectra) -> None:
    """A reader whose peak is off the top has no other way to know."""
    figure = build_sample_overlay(spectra, exclude_from_scale=TALL)
    try:
        title = figure._suptitle.get_text()
        assert TALL.name in title
        assert "EXCLUDES" in title.upper()
    finally:
        plt.close(figure)


def test_a_plain_figure_says_nothing_about_exclusion(spectra) -> None:
    figure = build_sample_overlay(spectra)
    try:
        assert "EXCLUD" not in figure._suptitle.get_text().upper()
    finally:
        plt.close(figure)


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_the_lower_limit_never_moves(spectra, baseline: bool, logy: bool) -> None:
    """Only the ceiling is the exclusion's business; the floor is the clamp's."""
    plain = build_sample_overlay(spectra, logy=logy, baseline_params=BASELINE if baseline else None)
    excluded = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        exclude_from_scale=TALL,
    )
    try:
        assert excluded.axes[0].get_ylim()[0] == plain.axes[0].get_ylim()[0]
    finally:
        plt.close(plain)
        plt.close(excluded)


def test_excluding_the_only_signal_refuses_rather_than_inverting_the_axis(
    tmp_path,
) -> None:
    """Reachable, and it was: a corrected spectrum whose only peak is excluded.

    Baseline correction flattens everything that is not a peak to about zero, so
    masking the sole peak leaves values below the panel's clamped floor. Setting
    a top under the bottom draws an inverted axis that still looks like a
    figure, which is worse than refusing.
    """
    folder = tmp_path / "raw" / "exp"
    folder.mkdir(parents=True)
    for index, step in enumerate(("0", "irr1")):
        write_spectrum_file(
            folder / f"s_low_{step}.txt",
            vary(spectrum(200.0, 2.5, 40, 1000.0, {17: 40.0}), index),
        )
    only_peak = load_experiment(folder.parent, "exp")

    with pytest.raises(ValueError, match="leaves nothing above the panel's floor"):
        build_sample_overlay(
            only_peak, baseline_params=BASELINE, exclude_from_scale=TALL
        )


def test_the_default_leaves_the_figure_exactly_as_it_was(spectra) -> None:
    """No new artist, no limit change, when the parameter is not supplied."""
    plain = build_sample_overlay(spectra)
    explicit = build_sample_overlay(spectra, exclude_from_scale=None)
    try:
        for a, b in zip(plain.axes, explicit.axes):
            assert a.get_ylim() == b.get_ylim()
            assert len(a.lines) == len(b.lines)
        assert plain._suptitle.get_text() == explicit._suptitle.get_text()
    finally:
        plt.close(plain)
        plt.close(explicit)
