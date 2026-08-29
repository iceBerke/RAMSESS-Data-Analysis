"""Characterisation tests for the four band-trend figure builders.

``build_sample_band_trends``, ``build_all_sample_band_trends`` and their two
save-wrappers are reached only from ``quantify_experiment``, and nothing tested
them. These lock in the current figure structure and, in the spirit of the
raw-data tripwire in ``plotting.py``, assert that what is drawn is exactly the
data that was passed in.

The builders take measurement rows, not files, so the rows here are the fixture.
``trend_row`` builds them, and its key set is pinned by
``conftest.assert_row_contract`` - the same contract the pipeline tests in
``test_quantify_experiment.py`` assert against real rows, so the two cannot
drift apart unnoticed. Only that contract is shared: ``trend_row`` and
``test_band_summary_output.summary_row`` invent different data for different
purposes and each stays in the file that needs it.

Nothing here writes outside ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pytest

from conftest import assert_row_contract
from ramsess.io import WINDOW_ORDER
from ramsess.plotting import (
    build_all_sample_band_trends,
    build_sample_band_trends,
    plot_all_sample_band_trends,
    plot_sample_band_trends,
)
from ramsess.report import MIN_SIGNAL_TO_NOISE

# Importing ramsess.plotting has already fixed the backend to Agg; pyplot is
# only safe to import afterwards, which is why this import sits below it.
import matplotlib.pyplot as plt  # noqa: E402

LOW, HIGH = WINDOW_ORDER

SAMPLES = ("sa", "sb")
BANDS = ("ref_band", "mid_band", "top_band")
REFERENCE = BANDS[0]
CROSS_BAND = BANDS[2]
# A gap in the sequence, which the builders must show as a gap. Also chosen so
# no series ever has x-data of [0, 1], which is what an axhline carries: that
# keeps the reference line unambiguously identifiable below.
STEPS = (0, 2)

WEAK_SNR = MIN_SIGNAL_TO_NOISE / 2.0
STRONG_SNR = MIN_SIGNAL_TO_NOISE * 5.0
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def trend_row(
    sample: str,
    window: str,
    step: int,
    band: str,
    *,
    height_norm: float,
    snr: float,
    cross_window: bool,
) -> dict[str, object]:
    """One measurement row, carrying exactly the keys the real ones carry."""
    height = 100.0 + 10.0 * step
    row: dict[str, object] = {
        "sample": sample,
        "window": window,
        "step": step,
        "band": band,
        "centre": 500.0,
        "position": 500.0,
        "position_drift": 0.0,
        "height": height,
        "area": height * 8.0,
        "n_points": 11,
        "at_edge": False,
        "noise": height / snr,
        "signal_to_noise": snr,
        "height_norm": height_norm,
        "area_norm": height_norm,
        "cross_window": cross_window,
    }
    assert_row_contract(row)
    return row


@pytest.fixture
def rows() -> list[dict[str, object]]:
    """Two samples over a gapped step sequence.

    ``sa`` carries all three bands and has one measurement below ``min_snr``,
    so the hollow-ring marker path is exercised. ``sb`` omits the cross-window
    band entirely, so the all-samples builder's skip path is exercised too.
    """
    built: list[dict[str, object]] = []
    for sample in SAMPLES:
        for index, band in enumerate(BANDS):
            if sample == SAMPLES[1] and band == CROSS_BAND:
                continue
            for step in STEPS:
                weak = sample == SAMPLES[0] and band == BANDS[1] and step == STEPS[1]
                built.append(
                    trend_row(
                        sample,
                        HIGH if band == CROSS_BAND else LOW,
                        step,
                        band,
                        height_norm=1.0 if band == REFERENCE else 0.2 * (index + 1),
                        snr=WEAK_SNR if weak else STRONG_SNR,
                        cross_window=band == CROSS_BAND,
                    )
                )
    return built


def series_for(rows: list[dict[str, object]], sample: str, band: str):
    """The rows for one sample and band, in the order the builders draw them."""
    return sorted(
        (r for r in rows if r["sample"] == sample and r["band"] == band),
        key=lambda r: int(r["step"]),
    )


def reference_lines(axes):
    """The ``axhline(1.0)`` guide, identified by its data rather than position.

    It spans the axes in x, so its x-data is [0, 1] in axes coordinates, which
    no series can be confused with given the step values this fixture uses.
    """
    return [
        line
        for line in axes.lines
        if list(line.get_xdata()) == [0, 1] and list(line.get_ydata()) == [1.0, 1.0]
    ]


def labelled_lines(axes):
    """The lines carrying a legend label: one per drawn series.

    ``len(axes.lines)`` is not the series count. It also includes the
    ``axhline(1.0)`` guide and, for every band holding a sub-``min_snr`` point,
    a second unlabelled line of hollow ring markers.
    """
    return [line for line in axes.lines if not line.get_label().startswith("_")]


def test_agg_backend_is_already_forced_by_importing_plotting() -> None:
    """Asserted, not re-established: ``plotting.py`` sets it at import time."""
    assert matplotlib.get_backend().lower() == "agg"


# ===========================================================================
# build_sample_band_trends
# ===========================================================================


def test_build_sample_band_trends_draws_one_labelled_series_per_band(
    rows: list[dict[str, object]],
) -> None:
    sample = SAMPLES[0]
    figure = build_sample_band_trends(rows, sample, REFERENCE, MIN_SIGNAL_TO_NOISE)

    assert len(figure.axes) == 1
    axes = figure.axes[0]

    mine = [r for r in rows if r["sample"] == sample]
    bands = sorted({str(r["band"]) for r in mine})
    weak_bands = {
        str(r["band"])
        for r in mine
        if float(r["signal_to_noise"]) < MIN_SIGNAL_TO_NOISE
    }
    assert weak_bands, "the fixture must contain a weak measurement"

    assert len(labelled_lines(axes)) == len(bands)
    assert len(reference_lines(axes)) == 1
    # series + one hollow-marker line per weak band + the axhline guide
    assert len(axes.lines) == len(bands) + len(weak_bands) + 1

    expected_labels = set()
    for band in bands:
        if band == REFERENCE:
            expected_labels.add(f"{band} (reference)")
        elif any(r["cross_window"] for r in series_for(rows, sample, band)):
            expected_labels.add(f"{band} *")
        else:
            expected_labels.add(band)
    assert {line.get_label() for line in labelled_lines(axes)} == expected_labels


def test_build_sample_band_trends_draws_exactly_the_rows_it_was_given(
    rows: list[dict[str, object]],
) -> None:
    """The tripwire in spirit: drawn x and y are the input, untransformed."""
    sample = SAMPLES[0]
    figure = build_sample_band_trends(rows, sample, REFERENCE, MIN_SIGNAL_TO_NOISE)
    axes = figure.axes[0]

    by_label = {line.get_label(): line for line in labelled_lines(axes)}
    for band in sorted({str(r["band"]) for r in rows if r["sample"] == sample}):
        series = series_for(rows, sample, band)
        label = next(name for name in by_label if name.split(" ")[0] == band)
        line = by_label[label]
        assert np.array_equal(
            np.asarray(line.get_xdata(), dtype=float),
            np.asarray([int(r["step"]) for r in series], dtype=float),
        )
        assert np.array_equal(
            np.asarray(line.get_ydata(), dtype=float),
            np.asarray([r["height_norm"] for r in series], dtype=float),
        )

    # The gap in the step sequence is a gap, not a re-indexed run of points.
    assert sorted(axes.get_xticks()) == sorted(STEPS)
    assert list(reference_lines(axes)[0].get_ydata()) == [1.0, 1.0]


def test_build_sample_band_trends_rejects_a_sample_with_no_measurements(
    rows: list[dict[str, object]],
) -> None:
    with pytest.raises(ValueError, match="no measurements for sample"):
        build_sample_band_trends(rows, "no_such_sample", REFERENCE, MIN_SIGNAL_TO_NOISE)


# ===========================================================================
# build_all_sample_band_trends
# ===========================================================================


def test_build_all_sample_band_trends_draws_one_panel_per_band(
    rows: list[dict[str, object]],
) -> None:
    figure = build_all_sample_band_trends(rows, REFERENCE, MIN_SIGNAL_TO_NOISE)

    bands = sorted({str(r["band"]) for r in rows})
    columns = min(3, len(bands))
    expected_axes = columns * ((len(bands) + columns - 1) // columns)
    assert len(figure.axes) == expected_axes

    for index, band in enumerate(bands):
        axes = figure.axes[index]
        drawn = [s for s in SAMPLES if series_for(rows, s, band)]
        assert len(labelled_lines(axes)) == len(drawn)
        assert len(reference_lines(axes)) == 1
        # No weak markers in this builder, so the count is exact.
        assert len(axes.lines) == len(drawn) + 1
        assert {line.get_label() for line in labelled_lines(axes)} == set(drawn)
        expected_title = f"{band} *" if band == CROSS_BAND else band
        assert axes.get_title() == expected_title

    # One sample is absent from the cross-window band, and that panel shows it.
    sparse = figure.axes[bands.index(CROSS_BAND)]
    assert len(labelled_lines(sparse)) == 1


def test_all_samples_legend_is_harvested_from_the_first_panel_only(
    rows: list[dict[str, object]],
) -> None:
    """Characterisation of a latent bug. Asserted as-is, not fixed.

    The figure legend comes from ``grid[0][0]`` alone - the first band in
    alphabetical order. A sample absent from that one band is missing from the
    legend of the whole figure even though it is drawn in every other panel.
    The real dataset does not trigger it, because every sample there carries
    every band; a future experiment measuring a band in only some samples would.
    """
    bands = sorted({str(r["band"]) for r in rows})
    first = bands[0]
    # Drop one sample from the first panel only, leaving it drawn elsewhere.
    dropped = SAMPLES[1]
    thinned = [
        r for r in rows if not (r["sample"] == dropped and r["band"] == first)
    ]
    assert any(r["sample"] == dropped for r in thinned)

    figure = build_all_sample_band_trends(thinned, REFERENCE, MIN_SIGNAL_TO_NOISE)
    entries = [text.get_text() for text in figure.legends[0].get_texts()]

    assert dropped not in entries
    assert entries == [SAMPLES[0]]
    # It is nonetheless drawn: the omission is in the legend, not the data.
    other = figure.axes[1]
    assert series_for(thinned, dropped, bands[1])
    assert dropped in {line.get_label() for line in labelled_lines(other)}


def test_build_all_sample_band_trends_draws_exactly_the_rows_it_was_given(
    rows: list[dict[str, object]],
) -> None:
    figure = build_all_sample_band_trends(rows, REFERENCE, MIN_SIGNAL_TO_NOISE)
    bands = sorted({str(r["band"]) for r in rows})

    for index, band in enumerate(bands):
        axes = figure.axes[index]
        by_label = {line.get_label(): line for line in labelled_lines(axes)}
        for sample, line in by_label.items():
            series = series_for(rows, sample, band)
            assert series
            assert np.array_equal(
                np.asarray(line.get_xdata(), dtype=float),
                np.asarray([int(r["step"]) for r in series], dtype=float),
            )
            assert np.array_equal(
                np.asarray(line.get_ydata(), dtype=float),
                np.asarray([r["height_norm"] for r in series], dtype=float),
            )


# ===========================================================================
# plot_sample_band_trends / plot_all_sample_band_trends
# ===========================================================================


def test_plot_sample_band_trends_writes_the_path_it_was_given_and_closes_up(
    rows: list[dict[str, object]], tmp_path: Path
) -> None:
    sample = SAMPLES[0]
    # The filename is composed by quantify_experiment, not by this function; it
    # writes wherever it is pointed.
    target = tmp_path / "figures" / "exp" / f"{sample}_bands.png"
    assert not target.parent.exists()

    written = plot_sample_band_trends(
        rows, sample, REFERENCE, target, MIN_SIGNAL_TO_NOISE
    )

    assert written == target
    assert target.is_file()
    assert target.read_bytes()[:8] == PNG_MAGIC
    assert plt.get_fignums() == []
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == [target]


def test_plot_all_sample_band_trends_writes_the_path_it_was_given_and_closes_up(
    rows: list[dict[str, object]], tmp_path: Path
) -> None:
    target = tmp_path / "figures" / "exp" / "bands_all_samples.png"
    assert not target.parent.exists()

    written = plot_all_sample_band_trends(rows, REFERENCE, target, MIN_SIGNAL_TO_NOISE)

    assert written == target
    assert target.is_file()
    assert target.read_bytes()[:8] == PNG_MAGIC
    assert plt.get_fignums() == []
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == [target]


def test_the_saved_figure_holds_the_same_series_as_the_built_one(
    rows: list[dict[str, object]], tmp_path: Path
) -> None:
    """The wrappers only persist: they add no transform of their own."""
    sample = SAMPLES[0]
    built = build_sample_band_trends(rows, sample, REFERENCE, MIN_SIGNAL_TO_NOISE)
    expected = {
        line.get_label(): (
            np.asarray(line.get_xdata(), dtype=float).tolist(),
            np.asarray(line.get_ydata(), dtype=float).tolist(),
        )
        for line in labelled_lines(built.axes[0])
    }
    plt.close(built)

    target = tmp_path / f"{sample}_bands.png"
    plot_sample_band_trends(rows, sample, REFERENCE, target, MIN_SIGNAL_TO_NOISE)
    assert target.is_file()

    again = build_sample_band_trends(rows, sample, REFERENCE, MIN_SIGNAL_TO_NOISE)
    assert {
        line.get_label(): (
            np.asarray(line.get_xdata(), dtype=float).tolist(),
            np.asarray(line.get_ydata(), dtype=float).tolist(),
        )
        for line in labelled_lines(again.axes[0])
    } == expected
