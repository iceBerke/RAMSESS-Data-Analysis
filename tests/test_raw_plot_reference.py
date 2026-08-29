"""The raw plot path is settled; this guards it against silent change.

Structural assertions over the figure, not a hash of the PNG bytes. Bytes are
in fact stable in this environment, but a byte hash breaks on any matplotlib,
freetype or libpng upgrade and reports only that a hash changed - it cannot say
whether a line moved, an axis rescaled or a font shifted. A test everyone learns
to ignore is worse than none, so this asserts the things that would actually
matter and that a hash could not localise.

This is one of exactly two test modules that read ``data/raw/`` (the other being
``test_cli_output.py``). It does so deliberately: the reference output it guards
is the six real overlay figures, and a synthetic fixture would guard something
else. It reads only; it writes nothing anywhere.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pytest

from ramsess.io import load_experiment
from ramsess.plotting import (
    CONTROL_COLOR,
    CONTROL_LINESTYLE,
    DPI,
    X_LABEL,
    Y_LABEL,
    build_sample_overlay,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
EXPERIMENT = "irradiation_sara"

# The reference structure of the six raw overlays, as built today.
# sample -> (panels, data lines per panel, break-mark artists per panel)
REFERENCE_STRUCTURE = {
    "ech1": (2, [1, 1], [1, 1]),
    "ech2": (2, [7, 7], [1, 1]),
    "ech3": (2, [6, 6], [1, 1]),
    "ech4": (2, [7, 7], [1, 1]),
    "ech5": (2, [1, 1], [1, 1]),
    "ech6": (2, [1, 1], [1, 1]),
}

# Axis limits are display settings and may legitimately be retuned, but not by
# accident, so they are pinned too. Tolerance is loose enough to absorb float
# formatting, tight enough that a rescale fails.
REFERENCE_YLIM = {
    "ech1": [(0.0, 90980.851), (3176.9196, 8932.183)],
    "ech2": [(0.0, 165644.076), (1729.2567, 35997.3598)],
    "ech3": [(0.0, 160426.1267), (3982.0056, 39039.2043)],
    "ech4": [(1683.857, 121789.2256), (436.4252, 246769.4068)],
    "ech5": [(0.0, 105540.8969), (3138.0323, 10107.0141)],
    "ech6": [(15930.0844, 38179.5953), (48750.4771, 234912.1439)],
}

# Pinned per sample rather than shared: ech4's low-window control is the
# low-precision export, so its wave axis starts 0.0004 cm-1 lower than the
# others and its panel limits genuinely differ. Collapsing that into one shared
# tolerance would hide a real property of the data.
REFERENCE_XLIM = {
    "ech1": [(120.76395924999998, 1906.0286437500001), (2316.4688601, 3559.6490599)],
    "ech2": [(120.76395924999998, 1906.0286437500001), (2316.4688601, 3559.6490599)],
    "ech3": [(120.76395924999998, 1906.0286437500001), (2316.4688601, 3559.6490599)],
    "ech4": [(120.76358755, 1906.02866145), (2316.4688601, 3559.6490599)],
    "ech5": [(120.76395924999998, 1906.0286437500001), (2316.4688601, 3559.6490599)],
    "ech6": [(120.76395924999998, 1906.0286437500001), (2316.4688601, 3559.6490599)],
}


@pytest.fixture(scope="module")
def by_sample() -> dict[str, list]:
    """The real experiment, grouped by sample. Read-only."""
    grouped: dict[str, list] = {}
    for spectrum in load_experiment(RAW_ROOT, EXPERIMENT):
        grouped.setdefault(spectrum.sample, []).append(spectrum)
    return grouped


def data_lines(axes):
    return [line for line in axes.lines if line.get_linestyle() != "None"]


def break_marks(axes):
    return [line for line in axes.lines if line.get_linestyle() == "None"]


def test_every_reference_sample_is_present(by_sample) -> None:
    assert set(by_sample) == set(REFERENCE_STRUCTURE)


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_panel_and_line_counts_are_unchanged(by_sample, sample: str) -> None:
    panels, per_panel, marks = REFERENCE_STRUCTURE[sample]
    figure = build_sample_overlay(by_sample[sample])
    try:
        assert len(figure.axes) == panels
        assert [len(data_lines(ax)) for ax in figure.axes] == per_panel
        assert [len(break_marks(ax)) for ax in figure.axes] == marks
    finally:
        plt.close(figure)


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_every_line_still_carries_the_raw_file_data(by_sample, sample: str) -> None:
    """The strongest of these assertions: drawn values are the file contents."""
    figure = build_sample_overlay(by_sample[sample])
    try:
        for index, window in enumerate(("low", "high")):
            source = sorted(
                (s for s in by_sample[sample] if s.window == window),
                key=lambda s: s.step,
            )
            drawn = data_lines(figure.axes[index])
            assert len(drawn) == len(source)
            for line, spectrum in zip(drawn, source):
                assert np.array_equal(line.get_xdata(), spectrum.wave)
                assert np.array_equal(line.get_ydata(), spectrum.intensity)
    finally:
        plt.close(figure)


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_axis_limits_are_unchanged(by_sample, sample: str) -> None:
    figure = build_sample_overlay(by_sample[sample])
    try:
        for index, axes in enumerate(figure.axes):
            assert axes.get_xlim() == pytest.approx(
                REFERENCE_XLIM[sample][index], rel=1e-9
            )
            assert axes.get_ylim() == pytest.approx(
                REFERENCE_YLIM[sample][index], rel=1e-6
            )
    finally:
        plt.close(figure)


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_panel_widths_stay_proportional_to_window_span(by_sample, sample: str) -> None:
    figure = build_sample_overlay(by_sample[sample])
    try:
        spans = []
        for window in ("low", "high"):
            group = [s for s in by_sample[sample] if s.window == window]
            spans.append(
                max(float(s.wave.max()) for s in group)
                - min(float(s.wave.min()) for s in group)
            )
        widths = [ax.get_position().width for ax in figure.axes]
        assert spans[0] / widths[0] == pytest.approx(spans[1] / widths[1], rel=1e-9)
    finally:
        plt.close(figure)


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_broken_axis_and_labels_are_unchanged(by_sample, sample: str) -> None:
    figure = build_sample_overlay(by_sample[sample])
    try:
        left, right = figure.axes
        assert left.spines["right"].get_visible() is False
        assert right.spines["left"].get_visible() is False
        assert right.yaxis.get_ticks_position() == "right"
        assert not left.get_shared_y_axes().joined(left, right)
        assert left.get_ylabel() == Y_LABEL
        assert [ax.get_xlabel() for ax in figure.axes] == [X_LABEL, X_LABEL]
    finally:
        plt.close(figure)


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_control_is_black_dashed_and_each_panel_has_its_own_legend(
    by_sample, sample: str
) -> None:
    figure = build_sample_overlay(by_sample[sample])
    try:
        assert figure.legends == [], "legends belong to the panels, not the figure"
        for index, window in enumerate(("low", "high")):
            steps = sorted(
                s.step for s in by_sample[sample] if s.window == window
            )
            legend = figure.axes[index].get_legend()
            labels = [text.get_text() for text in legend.get_texts()]
            expected = ["control" if s == 0 else f"irr{s}" for s in steps]
            assert labels == expected
            control = data_lines(figure.axes[index])[0]
            assert control.get_color() == CONTROL_COLOR
            assert control.get_linestyle() == CONTROL_LINESTYLE
    finally:
        plt.close(figure)


# --- the figures actually on disk ------------------------------------------
#
# The structural assertions above build figures in memory. They would all pass
# with every PNG in figures/ log-scaled, stale or deleted, which is exactly the
# defect that prompted these tests. These compare the real file against a
# reference rendered here and now.
#
# Rendering the reference rather than pinning a hash means both sides are drawn
# by the same matplotlib at test time, so a dependency upgrade moves them
# together and the test does not go stale. A pinned hash would break on the next
# matplotlib, freetype or libpng release and report only that a hash changed.
#
# The skip guards below were written when figures/ was gitignored in full, so
# "a fresh clone has none" was the reason they existed. That reasoning is now
# stale for the six {sample}_overlay.png references: they are tracked, so a
# fresh clone has them and these guards no longer fire on a normal run. They are
# kept for the case they still cover - someone who has deleted figures/ locally.
# The guard in the log-figure test below is a different matter and is live: log
# figures remain gitignored build output.

FIGURES_DIR = PROJECT_ROOT / "figures" / EXPERIMENT
REGENERATE = (
    f".venv\\Scripts\\python.exe main.py plot --experiment {EXPERIMENT}"
)
REGENERATE_LOG = (
    f".venv\\Scripts\\python.exe main.py plot --experiment {EXPERIMENT} --logy"
)


def reference_png(sample: str) -> Path:
    return FIGURES_DIR / f"{sample}_overlay.png"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory, by_sample) -> dict[str, Path]:
    """Render each sample's raw overlay freshly, for comparison against disk."""
    out = tmp_path_factory.mktemp("reference")
    paths = {}
    for sample in sorted(REFERENCE_STRUCTURE):
        figure = build_sample_overlay(by_sample[sample])
        try:
            target = out / f"{sample}_overlay.png"
            figure.savefig(target, dpi=DPI, bbox_inches="tight")
            paths[sample] = target
        finally:
            plt.close(figure)
    return paths


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_reference_figure_exists_on_disk(sample: str) -> None:
    path = reference_png(sample)
    if not FIGURES_DIR.is_dir():
        pytest.skip(f"figures/ not generated; run:  {REGENERATE}")
    assert path.is_file(), f"{path.name} is missing; regenerate with:  {REGENERATE}"
    assert path.stat().st_size > 0


@pytest.mark.parametrize("sample", sorted(REFERENCE_STRUCTURE))
def test_reference_figure_on_disk_matches_a_fresh_render(
    sample: str, rendered: dict[str, Path]
) -> None:
    """Catches an overwritten, log-scaled or stale file that the in-memory
    assertions above cannot see."""
    path = reference_png(sample)
    if not path.is_file():
        pytest.skip(f"{path.name} not generated; run:  {REGENERATE}")

    on_disk = mpimg.imread(path)
    expected = mpimg.imread(rendered[sample])

    assert on_disk.shape == expected.shape, (
        f"{path.name} has shape {on_disk.shape}, expected {expected.shape}. "
        f"The file on disk is not the raw linear overlay. Regenerate with:  {REGENERATE}"
    )
    assert np.array_equal(on_disk, expected), (
        f"{path.name} differs from a freshly rendered raw overlay - it may have "
        f"been overwritten by another flag combination (--logy writes "
        f"{sample}_overlay_log.png, not this file). Regenerate with:  {REGENERATE}"
    )


def test_no_log_scaled_figure_occupies_a_reference_filename() -> None:
    """--logy must write its own filenames, never the six reference ones.

    Counts the log figures on disk before asserting anything. An earlier version
    put the assertions inside a per-sample ``if stray.is_file()``, which meant
    that with no log figures present the test passed having examined nothing -
    and the log figures are gitignored, so a fresh clone has none. Skipping once,
    for the whole run, makes that state visible instead of silent.
    """
    if not FIGURES_DIR.is_dir():
        pytest.skip(f"figures/ not generated; run:  {REGENERATE}")

    present = [
        (sample, FIGURES_DIR / f"{sample}_overlay_log.png")
        for sample in sorted(REFERENCE_STRUCTURE)
        if (FIGURES_DIR / f"{sample}_overlay_log.png").is_file()
    ]
    if not present:
        pytest.skip(
            f"no {{sample}}_overlay_log.png on disk, so there is nothing to "
            f"check; they are gitignored build output. Generate them with:  "
            f"{REGENERATE_LOG}"
        )

    for sample, stray in present:
        assert stray != reference_png(sample)
        assert not np.array_equal(
            mpimg.imread(stray), mpimg.imread(reference_png(sample))
        ), f"{stray.name} and {sample}_overlay.png hold the same image"


def test_titles_do_not_claim_correction(by_sample) -> None:
    """The raw path must never label itself as corrected."""
    for sample in sorted(REFERENCE_STRUCTURE):
        figure = build_sample_overlay(by_sample[sample])
        try:
            title = figure._suptitle.get_text()
            assert sample in title and EXPERIMENT in title
            assert "BASELINE" not in title.upper()
        finally:
            plt.close(figure)
