"""Figure construction: the tripwire, the panel layout, and display settings.

These tests use ``build_sample_overlay``, which returns an open figure without
saving. They close it themselves. Nothing here writes to ``figures/``.
"""

from __future__ import annotations

import numpy as np
import pytest
import matplotlib.pyplot as plt

from conftest import vary
from ramsess.analysis import correct_baseline
from ramsess.io import load_experiment
from ramsess.plotting import (
    CONTROL_COLOR,
    CONTROL_LINESTYLE,
    build_baseline_diagnostic,
    build_sample_overlay,
    plot_sample_overlay,
)

# _assert_drawn_data_is_raw and _style_for_step are private, but the behaviour
# they guard is not reachable from outside: the tripwire only raises once the
# drawn data is already corrupt, which cannot be arranged through the public
# API, and the step-to-colour mapping is not otherwise exposed.
from ramsess.plotting import (
    _assert_drawn_data_is_corrected,
    _assert_drawn_data_is_raw,
    _style_for_step,
)


def data_lines(axes):
    """Real spectrum lines on an axes, excluding the break-mark artists."""
    return [line for line in axes.lines if line.get_linestyle() != "None"]


@pytest.fixture
def both_windows(make_experiment, low_lines, high_lines):
    """One sample, both windows, steps 0..2."""
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_high_0.txt": vary(high_lines, 0),
            "s_high_irr1.txt": vary(high_lines, 1),
            "s_high_irr2.txt": vary(high_lines, 2),
        }
    )
    return load_experiment(raw, "exp")


# --- the tripwire ----------------------------------------------------------


def test_clean_figure_passes_the_tripwire(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        assert len(figure.axes) == 2
    finally:
        plt.close(figure)


def test_tripwire_fires_on_a_single_intensity_change(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        line = data_lines(figure.axes[0])[1]
        spectrum = next(s for s in both_windows if s.window == "low" and s.step == 1)
        y = np.array(line.get_ydata(), dtype=float)
        y[2] += 1.0
        line.set_ydata(y)
        with pytest.raises(ValueError, match="intensity data differs"):
            _assert_drawn_data_is_raw([(line, spectrum)])
    finally:
        plt.close(figure)


def test_tripwire_fires_on_a_single_wave_change(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        line = data_lines(figure.axes[1])[0]
        spectrum = next(s for s in both_windows if s.window == "high" and s.step == 0)
        x = np.array(line.get_xdata(), dtype=float)
        x[3] += 0.001
        line.set_xdata(x)
        with pytest.raises(ValueError, match="wave data differs"):
            _assert_drawn_data_is_raw([(line, spectrum)])
    finally:
        plt.close(figure)


def test_tripwire_message_names_sample_window_and_step(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        line = data_lines(figure.axes[0])[2]
        spectrum = next(s for s in both_windows if s.window == "low" and s.step == 2)
        line.set_ydata(np.zeros(spectrum.intensity.size))
        with pytest.raises(ValueError) as excinfo:
            _assert_drawn_data_is_raw([(line, spectrum)])
        message = str(excinfo.value)
        assert "'s'" in message and "'low'" in message and "step 2" in message
    finally:
        plt.close(figure)


def test_drawn_data_equals_the_source_arrays(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        for index, window in enumerate(("low", "high")):
            source = sorted(
                [s for s in both_windows if s.window == window], key=lambda s: s.step
            )
            for line, spectrum in zip(data_lines(figure.axes[index]), source):
                assert np.array_equal(line.get_xdata(), spectrum.wave)
                assert np.array_equal(line.get_ydata(), spectrum.intensity)
    finally:
        plt.close(figure)


# --- layout ----------------------------------------------------------------


def test_single_window_sample_has_one_panel_and_no_break_marks(
    make_experiment, low_lines
) -> None:
    raw = make_experiment(
        {"s_low_0.txt": vary(low_lines, 0), "s_low_irr1.txt": vary(low_lines, 1)}
    )
    figure = build_sample_overlay(load_experiment(raw, "exp"))
    try:
        assert len(figure.axes) == 1
        axes = figure.axes[0]
        assert [ln for ln in axes.lines if ln.get_linestyle() == "None"] == []
        assert axes.spines["right"].get_visible() is True
        assert "low window only" in figure._suptitle.get_text()
    finally:
        plt.close(figure)


def test_two_window_sample_hides_facing_spines_and_draws_break_marks(
    both_windows,
) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        left, right = figure.axes
        assert left.spines["right"].get_visible() is False
        assert right.spines["left"].get_visible() is False
        assert len([ln for ln in left.lines if ln.get_linestyle() == "None"]) == 1
        assert len([ln for ln in right.lines if ln.get_linestyle() == "None"]) == 1
    finally:
        plt.close(figure)


def test_panel_width_ratio_equals_span_ratio(both_windows) -> None:
    """Equal cm-1 per inch across the break."""
    figure = build_sample_overlay(both_windows)
    try:
        left, right = figure.axes
        spans = []
        for window in ("low", "high"):
            group = [s for s in both_windows if s.window == window]
            spans.append(
                max(float(s.wave.max()) for s in group)
                - min(float(s.wave.min()) for s in group)
            )
        widths = [ax.get_position().width for ax in (left, right)]
        assert spans[0] / widths[0] == pytest.approx(spans[1] / widths[1], rel=1e-9)
    finally:
        plt.close(figure)


def test_y_axes_are_not_shared(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        left, right = figure.axes
        assert not left.get_shared_y_axes().joined(left, right)
    finally:
        plt.close(figure)


def test_each_panel_legend_lists_only_its_own_steps(
    make_experiment, low_lines, high_lines
) -> None:
    """ech3-shaped: low is missing step 2, high is missing step 1."""
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr3.txt": vary(low_lines, 3),
            "s_high_0.txt": vary(high_lines, 0),
            "s_high_irr2.txt": vary(high_lines, 2),
            "s_high_irr3.txt": vary(high_lines, 3),
        }
    )
    figure = build_sample_overlay(load_experiment(raw, "exp"))
    try:
        left, right = figure.axes
        assert [t.get_text() for t in left.get_legend().get_texts()] == [
            "control",
            "irr1",
            "irr3",
        ]
        assert [t.get_text() for t in right.get_legend().get_texts()] == [
            "control",
            "irr2",
            "irr3",
        ]
        assert figure.legends == []
    finally:
        plt.close(figure)


# --- colours ---------------------------------------------------------------


def test_control_is_black_dashed(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        control = data_lines(figure.axes[0])[0]
        assert control.get_color() == CONTROL_COLOR
        assert control.get_linestyle() == CONTROL_LINESTYLE
    finally:
        plt.close(figure)


def test_controls_only_sample_draws_black_dashed_without_dividing_by_zero(
    make_experiment, low_lines, high_lines
) -> None:
    raw = make_experiment(
        {"s_low_0.txt": vary(low_lines, 0), "s_high_0.txt": vary(high_lines, 0)}
    )
    figure = build_sample_overlay(load_experiment(raw, "exp"))
    try:
        for axes in figure.axes:
            lines = data_lines(axes)
            assert len(lines) == 1
            assert lines[0].get_color() == CONTROL_COLOR
            assert lines[0].get_linestyle() == CONTROL_LINESTYLE
    finally:
        plt.close(figure)


def test_same_step_gives_same_colour_across_different_step_sets() -> None:
    """A gapped sequence must not shift the colour of the steps it does have."""
    contiguous = {step: _style_for_step(step, 0, 6) for step in range(7)}
    gapped_steps = [0, 1, 3, 4, 6]
    gapped = {step: _style_for_step(step, 0, 6) for step in gapped_steps}
    for step in gapped_steps:
        assert gapped[step] == contiguous[step]


def test_step_colours_are_distinct_and_not_the_control_colour() -> None:
    colours = [_style_for_step(step, 0, 6)[0] for step in range(1, 7)]
    assert len(set(colours)) == 6
    assert CONTROL_COLOR not in colours


def test_degenerate_step_range_falls_back_to_the_control_style() -> None:
    assert _style_for_step(0, 0, 0) == (CONTROL_COLOR, CONTROL_LINESTYLE)
    assert _style_for_step(3, 3, 3) == (CONTROL_COLOR, CONTROL_LINESTYLE)


# --- y-axis clamping -------------------------------------------------------


def test_y_lower_bound_is_clamped_to_zero_when_autoscale_goes_negative(
    make_experiment, low_lines, high_lines
) -> None:
    """A trace with a tall peak over a near-zero floor drags autoscale below 0."""
    peaky = [f"{line.split()[0]}\t1.0" for line in low_lines]
    peaky[3] = f"{low_lines[3].split()[0]}\t100000.0"
    raw = make_experiment(
        {
            "s_low_0.txt": peaky,
            "s_low_irr1.txt": vary(peaky, 1),
            "s_high_0.txt": vary(high_lines, 0),
        }
    )
    figure = build_sample_overlay(load_experiment(raw, "exp"))
    try:
        assert figure.axes[0].get_ylim()[0] == 0.0
    finally:
        plt.close(figure)


def test_y_lower_bound_is_left_alone_when_autoscale_stays_positive(
    make_experiment, low_lines, high_lines
) -> None:
    """A high baseline must keep its tight autoscale, not gain empty space."""
    lifted = [
        f"{line.split()[0]}\t{float(line.split()[1]) + 100000.0:.6f}"
        for line in low_lines
    ]
    raw = make_experiment(
        {
            "s_low_0.txt": lifted,
            "s_low_irr1.txt": vary(lifted, 1),
            "s_high_0.txt": vary(high_lines, 0),
        }
    )
    figure = build_sample_overlay(load_experiment(raw, "exp"))
    try:
        bottom = figure.axes[0].get_ylim()[0]
        assert bottom > 0.0, "a positive autoscale floor must not be reset to zero"
    finally:
        plt.close(figure)


def test_logy_leaves_both_bounds_alone(both_windows) -> None:
    """Zero is invalid on a log axis, so no clamping may happen."""
    figure = build_sample_overlay(both_windows, logy=True)
    try:
        for axes in figure.axes:
            assert axes.get_yscale() == "log"
            assert axes.get_ylim()[0] > 0.0
    finally:
        plt.close(figure)


# --- the saving wrapper ----------------------------------------------------


def test_plot_sample_overlay_writes_the_path_it_returns(both_windows, tmp_path) -> None:
    target = tmp_path / "nested" / "s_overlay.png"
    returned = plot_sample_overlay(both_windows, target)
    assert returned == target
    assert target.exists() and target.stat().st_size > 0


def test_plot_sample_overlay_closes_the_figure(both_windows, tmp_path) -> None:
    before = len(plt.get_fignums())
    plot_sample_overlay(both_windows, tmp_path / "s_overlay.png")
    assert len(plt.get_fignums()) == before


# --- baseline modes --------------------------------------------------------

# Per-window mapping, matching the shape the plotting layer now takes. The two
# windows deliberately use different lam so the tests exercise the per-window
# path rather than a single shared value.
BASELINE = {
    "low": {"lam": 1e6, "p": 0.01, "n_iter": 10},
    "high": {"lam": 1e8, "p": 0.01, "n_iter": 10},
}


def test_baseline_overlay_draws_the_corrected_values(both_windows) -> None:
    figure = build_sample_overlay(both_windows, baseline_params=BASELINE)
    try:
        for index, window in enumerate(("low", "high")):
            source = sorted(
                [s for s in both_windows if s.window == window], key=lambda s: s.step
            )
            for line, spectrum in zip(data_lines(figure.axes[index]), source):
                corrected, fitted = correct_baseline(spectrum, **BASELINE[spectrum.window])
                assert np.array_equal(line.get_ydata(), corrected)
                assert not np.array_equal(line.get_ydata(), spectrum.intensity)
    finally:
        plt.close(figure)


def test_baseline_overlay_title_says_it_is_corrected(both_windows) -> None:
    figure = build_sample_overlay(both_windows, baseline_params=BASELINE)
    try:
        assert "BASELINE CORRECTED" in figure._suptitle.get_text()
    finally:
        plt.close(figure)


def test_title_names_each_window_when_parameters_differ(both_windows) -> None:
    """A figure must not hide that its panels were corrected differently."""
    figure = build_sample_overlay(both_windows, baseline_params=BASELINE)
    try:
        title = figure._suptitle.get_text()
        assert "low: lam=1e+06" in title
        assert "high: lam=1e+08" in title
    finally:
        plt.close(figure)


def test_title_states_parameters_once_when_they_match(both_windows) -> None:
    shared = {w: {"lam": 1e6, "p": 0.01, "n_iter": 10} for w in ("low", "high")}
    figure = build_sample_overlay(both_windows, baseline_params=shared)
    try:
        title = figure._suptitle.get_text()
        assert "lam=1e+06" in title
        assert "low:" not in title and "high:" not in title
    finally:
        plt.close(figure)


def test_each_window_is_corrected_with_its_own_parameters(both_windows) -> None:
    figure = build_sample_overlay(both_windows, baseline_params=BASELINE)
    try:
        for index, window in enumerate(("low", "high")):
            source = sorted(
                [s for s in both_windows if s.window == window], key=lambda s: s.step
            )
            other = "high" if window == "low" else "low"
            for line, spectrum in zip(data_lines(figure.axes[index]), source):
                mine, _ = correct_baseline(spectrum, **BASELINE[window])
                theirs, _ = correct_baseline(spectrum, **BASELINE[other])
                assert np.array_equal(line.get_ydata(), mine)
                assert not np.array_equal(mine, theirs), "lam must actually differ"
    finally:
        plt.close(figure)


def test_raw_overlay_title_does_not_claim_correction(both_windows) -> None:
    figure = build_sample_overlay(both_windows)
    try:
        assert "BASELINE" not in figure._suptitle.get_text().upper()
    finally:
        plt.close(figure)


def test_reconstruction_assertion_fires_when_corrected_is_perturbed(both_windows) -> None:
    """corrected + baseline must return the raw data, or the tripwire trips."""
    spectrum = both_windows[0]
    corrected, fitted = correct_baseline(spectrum, **BASELINE[spectrum.window])
    figure = build_sample_overlay(both_windows, baseline_params=BASELINE)
    try:
        line = data_lines(figure.axes[0])[0]
        broken = corrected.copy()
        broken[5] += 1.0
        line.set_ydata(broken)
        with pytest.raises(ValueError, match="does not reconstruct the raw data"):
            _assert_drawn_data_is_corrected([(line, spectrum, broken, fitted)])
    finally:
        plt.close(figure)


def test_corrected_tripwire_fires_when_the_line_leaves_the_corrected_array(
    both_windows,
) -> None:
    spectrum = both_windows[0]
    corrected, fitted = correct_baseline(spectrum, **BASELINE[spectrum.window])
    figure = build_sample_overlay(both_windows, baseline_params=BASELINE)
    try:
        line = data_lines(figure.axes[0])[0]
        line.set_ydata(np.zeros(corrected.size))
        with pytest.raises(ValueError, match="differs from the correction"):
            _assert_drawn_data_is_corrected([(line, spectrum, corrected, fitted)])
    finally:
        plt.close(figure)


def test_baseline_writes_a_different_file_and_leaves_raw_alone(
    both_windows, tmp_path
) -> None:
    raw_path = tmp_path / "s_overlay.png"
    baseline_path = tmp_path / "s_overlay_baseline.png"

    plot_sample_overlay(both_windows, raw_path)
    raw_bytes = raw_path.read_bytes()

    plot_sample_overlay(both_windows, baseline_path, baseline_params=BASELINE)

    assert baseline_path.exists()
    assert baseline_path != raw_path
    assert raw_path.exists(), "the raw figure must not be deleted"
    assert raw_path.read_bytes() == raw_bytes, "the raw figure must not be modified"
    assert baseline_path.read_bytes() != raw_bytes


# --- the diagnostic figure -------------------------------------------------


def test_diagnostic_grid_has_one_row_per_step_and_two_columns(
    make_experiment, low_lines
) -> None:
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr3.txt": vary(low_lines, 3),
        }
    )
    spectra = load_experiment(raw, "exp")
    figure = build_baseline_diagnostic(spectra, BASELINE)
    try:
        assert len(figure.axes) == 3 * 2
        labels = [figure.axes[row * 2].get_ylabel() for row in range(3)]
        assert labels == ["control", "irr1", "irr3"], "rows must ascend by step"
    finally:
        plt.close(figure)


def test_diagnostic_left_column_is_raw_plus_baseline(make_experiment, low_lines) -> None:
    raw = make_experiment({"s_low_0.txt": vary(low_lines, 0)})
    spectra = load_experiment(raw, "exp")
    figure = build_baseline_diagnostic(spectra, BASELINE)
    try:
        left, right = figure.axes[0], figure.axes[1]
        assert len(data_lines(left)) == 2, "raw and fitted baseline"
        assert np.array_equal(data_lines(left)[0].get_ydata(), spectra[0].intensity)
        corrected, _ = correct_baseline(spectra[0], **BASELINE[spectra[0].window])
        # The right panel also carries a zero reference line, which is short.
        drawn_right = [
            ln for ln in data_lines(right) if len(ln.get_ydata()) == corrected.size
        ]
        assert len(drawn_right) == 1
        assert np.array_equal(drawn_right[0].get_ydata(), corrected)
    finally:
        plt.close(figure)


def test_diagnostic_rejects_mixed_samples_or_windows(both_windows) -> None:
    with pytest.raises(ValueError, match="one sample in one window"):
        build_baseline_diagnostic(both_windows, BASELINE)
    with pytest.raises(ValueError, match="no spectra given"):
        build_baseline_diagnostic([], BASELINE)


def test_build_rejects_empty_and_multi_sample_input(both_windows) -> None:
    with pytest.raises(ValueError, match="no spectra given"):
        build_sample_overlay([])
    mixed = list(both_windows)
    import dataclasses

    mixed.append(dataclasses.replace(both_windows[0], sample="other"))
    with pytest.raises(ValueError, match="exactly one sample"):
        build_sample_overlay(mixed)
