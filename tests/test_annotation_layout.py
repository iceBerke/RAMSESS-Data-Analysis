"""What the band annotation actually draws: rules, label text, and the legend.

The filename tests prove an annotated run writes different bytes under its own
name; they cannot say whether what it drew is right. These assert the three
geometric properties that a reader of the figure depends on, none of which any
other module covers:

* a rule stops below the foot of its own label, so it never runs through the
  text it belongs to - and the foot differs per label, because labels sit in
  different rows and their rendered heights differ;
* a label is the band's configured centre, not its name;
* the legend never settles on top of a label, in any flag combination.

Everything is built in ``tmp_path`` and in memory. Nothing is saved, and the
project's ``figures/`` tree is never touched.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from conftest import vary, write_spectrum_file
from ramsess.io import load_experiment
from ramsess.plotting import build_sample_overlay
from ramsess.report import BandSpec

BASELINE = {
    "low": {"lam": 1e6, "p": 0.01, "n_iter": 10},
    "high": {"lam": 1e8, "p": 0.01, "n_iter": 10},
}

# Names deliberately unlike the centres, so a test asserting the label text can
# tell the two apart. `alpha` and `beta` sit close enough to need a second row,
# which is what makes the per-label rule extent worth asserting at all.
BANDS = {
    "alpha": BandSpec(name="alpha", centre=230.0, half_width=1.5, window="low"),
    "beta": BandSpec(name="beta", centre=234.0, half_width=1.5, window="low"),
    "gamma": BandSpec(name="gamma", centre=290.0, half_width=1.5, window="low"),
    "delta": BandSpec(name="delta", centre=2420.0, half_width=1.5, window="high"),
    "epsilon": BandSpec(name="epsilon", centre=2470.0, half_width=1.5, window="high"),
}
CENTRES = {"230", "234", "290", "2420", "2470"}

COMBINATIONS = [
    (False, False),
    (False, True),
    (True, False),
    (True, True),
]  # baseline, logy


def peaked(start: float, spacing: float, n: int, peak_at: int, base: float) -> list[str]:
    """A spectrum with a strong peak, so log-scaled panels have positive data."""
    lines, wave = [], start
    for i in range(n):
        wave += spacing * (1.0 + 0.1 * (i % 3))
        lines.append(f"{wave:.6f}\t{base + (base * 20.0 if i == peak_at else 0.0):.6f}")
    return lines


@pytest.fixture(scope="module")
def spectra(tmp_path_factory):
    """One sample, both windows, three steps, spanning the configured bands."""
    folder = tmp_path_factory.mktemp("annotated") / "raw" / "exp"
    folder.mkdir(parents=True)
    for index, step in enumerate(("0", "irr1", "irr2")):
        write_spectrum_file(
            folder / f"s_low_{step}.txt", vary(peaked(200.0, 2.5, 40, 20, 1000.0), index)
        )
        write_spectrum_file(
            folder / f"s_high_{step}.txt", vary(peaked(2400.0, 2.0, 40, 20, 5000.0), index)
        )
    return load_experiment(folder.parent, "exp")


def annotation_rules(panel, centres: set[float]):
    """The vertical rules this module drew, told apart from data and break marks.

    A rule is the only two-point vertical line whose x sits on a configured
    centre; a data trace has one point per sample and a break mark is drawn
    with no linestyle.
    """
    found = []
    for line in panel.lines:
        x = line.get_xdata()
        if len(x) == 2 and x[0] == x[1] and float(x[0]) in centres:
            found.append(line)
    return found


def axes_fraction_bottom(text, panel, renderer) -> float:
    """Where a label's foot sits, as a fraction of the panel's height."""
    box = text.get_window_extent(renderer=renderer)
    panel_box = panel.get_window_extent(renderer=renderer)
    return (box.y0 - panel_box.y0) / panel_box.height


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_every_rule_stops_below_its_own_label(spectra, baseline: bool, logy: bool) -> None:
    """F1. A rule through its own label is the defect this rules out."""
    figure = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        bands=BANDS,
    )
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        centres = {spec.centre for spec in BANDS.values()}
        checked = 0
        for panel in figure.axes:
            rules = annotation_rules(panel, centres)
            assert len(rules) == len(panel.texts), "every label needs exactly one rule"
            by_centre = {float(rule.get_xdata()[0]): rule for rule in rules}
            for text in panel.texts:
                centre = float(text.get_position()[0])
                # axvline draws in axes fractions on y, which is the same frame
                # the label's foot is measured in.
                top = float(by_centre[centre].get_ydata()[1])
                foot = axes_fraction_bottom(text, panel, renderer)
                assert top < foot, (
                    f"the rule at {centre:g} reaches {top:.4f} but its label's foot "
                    f"is at {foot:.4f}: the rule runs through its own label"
                )
                checked += 1
        assert checked == len(BANDS), "not every configured band was checked"
    finally:
        plt.close(figure)


def test_more_than_one_row_is_actually_exercised(spectra) -> None:
    """Guards the test above: with one row, a per-label extent proves little."""
    figure = build_sample_overlay(spectra, bands=BANDS)
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        tops = {
            round(text.get_window_extent(renderer=renderer).y1, 1)
            for text in figure.axes[0].texts
        }
        assert len(tops) > 1, (
            "the low panel drew every label in one row, so the per-label rule "
            "extent is untested; move the configured centres closer together"
        )
    finally:
        plt.close(figure)


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_labels_are_the_configured_centre_not_the_band_name(
    spectra, baseline: bool, logy: bool
) -> None:
    """F2. The centre is short, which is what buys back panel height."""
    figure = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        bands=BANDS,
    )
    try:
        drawn = {text.get_text() for panel in figure.axes for text in panel.texts}
        assert drawn == CENTRES
        assert drawn.isdisjoint(BANDS), "a label carries a band name, not its centre"
    finally:
        plt.close(figure)


def test_a_whole_number_centre_carries_no_decimal_point(spectra) -> None:
    """522.0 must read as 522. The centres above are all whole numbers."""
    figure = build_sample_overlay(spectra, bands=BANDS)
    try:
        for panel in figure.axes:
            for text in panel.texts:
                assert "." not in text.get_text(), text.get_text()
    finally:
        plt.close(figure)


@pytest.mark.parametrize("baseline,logy", COMBINATIONS)
def test_no_legend_overlaps_a_label(spectra, baseline: bool, logy: bool) -> None:
    """F3. loc="best" scores against data, and the reserved band holds none.

    Two assertions, because the visible symptom and the invariant are not the
    same thing. Whether a legend inside the reserved band actually lands on a
    label depends on where it sits horizontally, which is luck; that it stays
    out of the band at all is what the fix guarantees. Asserting only the
    symptom would let the fix be removed whenever the luck held.
    """
    figure = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=BASELINE if baseline else None,
        bands=BANDS,
    )
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        for panel in figure.axes:
            legend = panel.get_legend()
            assert legend is not None
            legend_box = legend.get_window_extent(renderer=renderer)

            hit = [
                text.get_text()
                for text in panel.texts
                if text.get_window_extent(renderer=renderer).overlaps(legend_box)
            ]
            assert not hit, f"the legend sits on label(s) {hit}"

            panel_box = panel.get_window_extent(renderer=renderer)
            legend_top = (legend_box.y1 - panel_box.y0) / panel_box.height
            lowest_label = min(
                axes_fraction_bottom(text, panel, renderer) for text in panel.texts
            )
            assert legend_top <= lowest_label, (
                f"the legend reaches {legend_top:.4f} but the lowest label's foot "
                f"is at {lowest_label:.4f}: the legend has entered the reserved band"
            )
    finally:
        plt.close(figure)


def test_annotation_leaves_the_unannotated_figure_alone(spectra) -> None:
    """None of the three fixes may reach a figure built without bands."""
    figure = build_sample_overlay(spectra)
    try:
        for panel in figure.axes:
            assert len(panel.texts) == 0
            assert annotation_rules(panel, {s.centre for s in BANDS.values()}) == []
            legend = panel.get_legend()
            assert legend.get_bbox_to_anchor().bounds == pytest.approx(
                panel.get_window_extent().bounds
            ), "an unannotated legend must still be anchored to the whole panel"
    finally:
        plt.close(figure)
