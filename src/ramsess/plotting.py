"""Figure logic for spectra overlays.

All matplotlib work lives here. Intensities are drawn as raw counts: nothing in
this module smooths, baseline-corrects, normalises or rescales the data.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib
import numpy as np

# Deliberate global side effect at import time. The backend must be chosen
# before pyplot is imported, so this cannot be deferred into a function.
# Importing this module fixes the process backend to the non-interactive Agg,
# which needs no display and lets figures be written from a plain script.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.transforms import blended_transform_factory  # noqa: E402

from ramsess.analysis import correct_baseline  # noqa: E402
from ramsess.io import WINDOW_ORDER, Spectrum, window_sort_key  # noqa: E402

if TYPE_CHECKING:
    # Only for the annotation parameter's type. Imported under TYPE_CHECKING so
    # that importing this module does not pull report.py in at runtime: report
    # imports plotting lazily to keep matplotlib off the inspect path, and a
    # module-level import back the other way would undo half of that.
    from ramsess.report import BandSpec

CONTROL_STEP = 0
CONTROL_COLOR = "black"
CONTROL_LINESTYLE = "--"
IRRADIATION_COLORMAP = "viridis"

FIGURE_SIZE = (11.0, 5.5)
PANEL_GAP = 0.05
LINE_WIDTH = 0.9
DPI = 200

BASELINE_FIT_COLOR = "tab:red"
CORRECTED_COLOR = "tab:blue"
DIAGNOSTIC_WIDTH = 11.0
DIAGNOSTIC_ROW_HEIGHT = 1.6

X_LABEL = "Raman shift (cm-1)"
Y_LABEL = "Intensity (counts)"

# Point size of a band label. Labels are rotated upright, so this sets their
# horizontal footprint far more than their vertical one.
ANNOTATION_FONT_SIZE = 12
# Width of the vertical rule dropped from a label to the axis.
ANNOTATION_RULE_WIDTH = 0.6
# Rule transparency, so a rule crossing a trace does not read as data.
ANNOTATION_RULE_ALPHA = 0.45
# Near-black for the label, so it carries to the back of a room. Not black: the
# control step is drawn in black and a label should not read as a trace.
ANNOTATION_TEXT_COLOR = "0.15"
# The rule stays grey, and keeps its own alpha on top. Separate from the text
# colour so the label can be darkened without the rule following it.
ANNOTATION_RULE_COLOR = "0.35"
# Below every data trace, whose default zorder is 2, and above the axes patch.
ANNOTATION_ZORDER = 0.5
# Vertical gap between stacked label rows, and below the lowest row, as a
# multiple of the measured label line height so it scales with the font.
ANNOTATION_ROW_GAP = 0.35
# Gap between the top of the panel and the first row, in the same units.
ANNOTATION_TOP_PAD = 0.35
# How far apart two labels in one row must sit, as a multiple of their measured
# half-extents. Above 1.0 so they are separated rather than merely touching.
# Dimensionless on purpose: the spacing itself comes from the renderer.
ANNOTATION_MIN_CLEARANCE = 1.15
# Gap between the foot of a label and the top of its own rule, in the same units
# as the two above. Below ANNOTATION_ROW_GAP, which is what keeps every rule top
# inside the reserved band and so strictly above the traces.
ANNOTATION_RULE_CLEARANCE = 0.25


def _spectra_by_window(spectra: list[Spectrum]) -> dict[str, list[Spectrum]]:
    """Split spectra by window, each list sorted by step ascending.

    Raises:
        ValueError: If a spectrum carries a window label that is not a known
            window.
    """
    by_window: dict[str, list[Spectrum]] = {}
    for spectrum in spectra:
        window_sort_key(spectrum.window)
        by_window.setdefault(spectrum.window, []).append(spectrum)
    for group in by_window.values():
        group.sort(key=lambda s: s.step)
    return by_window


def _style_for_step(step: int, min_step: int, max_step: int) -> tuple[object, str]:
    """Return the ``(colour, linestyle)`` for one irradiation step.

    The control is black and dashed. Irradiation steps take their colour from
    viridis, positioned by the actual step value normalised over the sample's
    own minimum and maximum step, so the same step number gets the same colour
    in every sample even where the sequence has gaps.

    When a sample's minimum and maximum step are equal the normalisation would
    divide by zero. That happens for a controls-only sample, which is nothing
    but a control, so it is drawn exactly like one: black and dashed.
    """
    if step == CONTROL_STEP or max_step == min_step:
        return CONTROL_COLOR, CONTROL_LINESTYLE
    position = (step - min_step) / (max_step - min_step)
    return matplotlib.colormaps[IRRADIATION_COLORMAP](position), "-"


def _step_label(step: int) -> str:
    """Return the legend label for a step."""
    return "control" if step == CONTROL_STEP else f"irr{step}"


def _assert_drawn_data_is_raw(drawn: list[tuple[Line2D, Spectrum]]) -> None:
    """Check that every drawn line still holds the exact file contents.

    Axis limits, colours, scales and legends are display settings and may change
    freely. The plotted values may not: they must always be the exact contents
    of the file. This assertion is the tripwire that proves it, and it runs on
    every plot call rather than only under test.

    Args:
        drawn: Each plotted line paired with the spectrum it was drawn from.

    Raises:
        ValueError: If any line's x or y data differs from the raw arrays.
    """
    for line, spectrum in drawn:
        if not np.array_equal(line.get_xdata(), spectrum.wave):
            raise ValueError(
                f"plotted wave data differs from the file for sample {spectrum.sample!r}, "
                f"window {spectrum.window!r}, step {spectrum.step} ({spectrum.path.name})"
            )
        if not np.array_equal(line.get_ydata(), spectrum.intensity):
            raise ValueError(
                f"plotted intensity data differs from the file for sample {spectrum.sample!r}, "
                f"window {spectrum.window!r}, step {spectrum.step} ({spectrum.path.name})"
            )


def _assert_drawn_data_is_corrected(
    drawn: list[tuple[Line2D, Spectrum, np.ndarray, np.ndarray]],
) -> None:
    """Check corrected lines against the correction, and the correction itself.

    Under baseline correction the drawn values are legitimately not the file
    contents, so the raw tripwire cannot apply. The guarantee is kept in two
    parts instead: every drawn line must equal the corrected array exactly, and
    corrected plus fitted baseline must reconstruct the raw file contents to
    within floating point tolerance. Together those prove the correction was a
    pure subtraction and that nothing else touched the values.

    The tolerance is scaled to the data, because intensities here run to six
    figures and a fixed absolute epsilon would be stricter than a float64
    round trip.

    Args:
        drawn: Each plotted line with its spectrum, corrected array and baseline.

    Raises:
        ValueError: If a line does not match its corrected array, or if the
            correction does not reconstruct the raw data.
    """
    for line, spectrum, corrected, baseline in drawn:
        where = (
            f"sample {spectrum.sample!r}, window {spectrum.window!r}, "
            f"step {spectrum.step} ({spectrum.path.name})"
        )
        if not np.array_equal(line.get_xdata(), spectrum.wave):
            raise ValueError(f"plotted wave data differs from the file for {where}")
        if not np.array_equal(line.get_ydata(), corrected):
            raise ValueError(f"plotted intensity data differs from the correction for {where}")
        scale = float(np.max(np.abs(spectrum.intensity))) or 1.0
        if not np.allclose(corrected + baseline, spectrum.intensity, rtol=0.0, atol=1e-9 * scale):
            residual = float(np.max(np.abs(corrected + baseline - spectrum.intensity)))
            raise ValueError(
                f"baseline correction does not reconstruct the raw data for {where}: "
                f"max residual {residual:.6g}"
            )


def _params_label(
    baseline_params: dict[str, dict[str, float | int]], windows: list[str]
) -> str:
    """Summarise the baseline parameters used, naming windows when they differ.

    Args:
        baseline_params: Parameters keyed by window label.
        windows: The window labels drawn, in display order.

    Returns:
        A single description when every window used the same parameters, or one
        per window when they differ, so a figure never hides that its panels
        were corrected differently.
    """

    def described(params: dict[str, float | int]) -> str:
        return f"lam={params['lam']:g}, p={params['p']:g}, n_iter={params['n_iter']}"

    used = [baseline_params[w] for w in windows]
    if all(params == used[0] for params in used):
        return described(used[0])
    return "; ".join(f"{w}: {described(baseline_params[w])}" for w in windows)


def _draw_break_marks(left_axes: plt.Axes, right_axes: plt.Axes) -> None:
    """Draw the diagonal axis-break marks on the facing edges of two panels."""
    marker = dict(
        marker=[(-1, -0.5), (1, 0.5)],
        markersize=10,
        linestyle="none",
        color="black",
        markeredgecolor="black",
        markeredgewidth=1,
        clip_on=False,
    )
    left_axes.plot([1, 1], [0, 1], transform=left_axes.transAxes, **marker)
    right_axes.plot([0, 0], [0, 1], transform=right_axes.transAxes, **marker)


def _raise_top_excluding_band(
    panel: plt.Axes,
    drawn: list[tuple[np.ndarray, np.ndarray]],
    exclude: BandSpec,
    logy: bool,
) -> float:
    """Recompute one panel's upper limit with a band's search window ignored.

    A band tens of times taller than its neighbours sets the panel's limit and
    flattens everything else against the floor. Dropping its search window from
    the limit calculation scales the panel to the rest of the data instead. The
    band is still drawn in full; it simply runs off the top, and the title says
    so.

    Only the upper limit moves. The lower one is left exactly as the caller left
    it, including the clamp that pulls a negative autoscale margin up to zero,
    because a corrected panel's floor is a separate question from its ceiling.

    The margin matches what autoscale would have applied, taken from
    ``axes.ymargin`` rather than assumed, so an excluded panel is scaled the way
    an ordinary one is. On a log axis that margin is applied in log space, which
    is where matplotlib applies it.

    Args:
        panel: The panel to rescale. Must already hold its drawn data.
        drawn: ``(wave, values)`` for every line drawn on this panel.
        exclude: The band whose search window is left out of the calculation.
            Supplied by the caller: nothing here knows any band's position.
        logy: Whether the panel is on a log y-scale.

    Returns:
        The new upper limit.

    Raises:
        ValueError: If masking the band's window leaves no data to scale to, or
            leaves nothing above the panel's floor - which happens when the
            excluded band held all the signal there was, and would otherwise
            produce an inverted or degenerate axis.
    """
    low, high = exclude.centre - exclude.half_width, exclude.centre + exclude.half_width
    lowest, highest = np.inf, -np.inf
    for wave, values in drawn:
        keep = (wave < low) | (wave > high)
        if not keep.any():
            continue
        lowest = min(lowest, float(values[keep].min()))
        highest = max(highest, float(values[keep].max()))
    if not (np.isfinite(lowest) and np.isfinite(highest)):
        raise ValueError(
            f"excluding the search window [{low:.3f}, {high:.3f}] of band "
            f"{exclude.name!r} leaves no data to scale the panel to"
        )

    bottom, _ = panel.get_ylim()
    margin = plt.rcParams["axes.ymargin"]
    if logy:
        # The masked minimum is data and may be zero or negative even though a
        # log panel's reported floor never is; fall back to the floor then.
        floor = lowest if lowest > 0.0 else bottom
        with np.errstate(invalid="ignore"):
            span = float(np.log10(highest)) - float(np.log10(floor))
            top = float(10.0 ** (np.log10(highest) + margin * span))
    else:
        top = highest + margin * (highest - lowest)

    # One guard for three ways this can go wrong, all of them reachable: the
    # remaining data can sit entirely below the panel's floor, which would
    # invert the axis; it can be non-positive on a log panel, which makes the
    # arithmetic above NaN; and NaN fails this comparison too. Drawing an
    # inverted or degenerate panel would be worse than refusing, because it
    # still looks like a figure.
    if not top > bottom:
        raise ValueError(
            f"excluding the search window [{low:.3f}, {high:.3f}] of band "
            f"{exclude.name!r} leaves nothing above the panel's floor of "
            f"{bottom:.6g}: the remaining data peaks at {highest:.6g}"
        )
    panel.set_ylim(bottom, top)
    return top


def _annotate_band_centres(
    figure: plt.Figure,
    panel: plt.Axes,
    window: str,
    bands: dict[str, BandSpec],
    logy: bool,
) -> list[list[str]]:
    """Label every configured band of one window along the top of one panel.

    Each label is the band's configured centre, rotated upright and anchored to
    the top of the panel, never to the peak it names. That is deliberate: a
    panel whose tallest band is tens of times the others would otherwise crowd
    every small label into the floor of the figure, and how legible a label is
    would depend on how tall its band happened to be. A rule drops from each
    label to the axis, stopping below the label's own foot so it never runs
    through the text it belongs to.

    Where two labels in a row would touch, the second drops to the row below.
    The spacing that decides this is measured from the rendered text, never
    assumed, because it depends on the font, the label strings and the panel's
    drawn width, none of which this module may hardcode.

    The panel's top limit is then raised to hold the rows used, so the labels
    sit above the traces rather than inside them. The bottom limit is left
    exactly as it was, because a corrected panel's floor is legitimately below
    zero and anchoring to zero would move the data. Any legend the caller
    already put on the panel is confined to the data region below the reserved
    band, so it cannot settle on top of the labels.

    Args:
        figure: The figure the panel belongs to, for its renderer.
        panel: The panel to annotate.
        window: That panel's window label. Only bands configured for it are
            drawn; a band belonging to the other window is not this panel's.
        bands: The configured bands, exactly as ``load_bands_config`` returns
            them.
        logy: Whether the panel is on a log y-scale, which changes how the top
            limit has to be raised.

    Returns:
        The band names placed, one list per row, top row first. Empty when the
        panel has no configured band.

    Raises:
        ValueError: If the rows needed would fill the whole panel, leaving no
            room for the data. Refusing is the only honest outcome: the figure
            cannot both hold the labels and show the spectra.
    """
    selected = sorted(
        (spec for spec in bands.values() if spec.window == window),
        key=lambda spec: spec.centre,
    )
    if not selected:
        return []

    renderer = figure.canvas.get_renderer()
    # x in data units so a label tracks its centre, y in axes fractions so it
    # tracks the top of the panel rather than a value.
    blended = blended_transform_factory(panel.transData, panel.transAxes)

    def label(spec: BandSpec, y: float):
        # The label is the configured centre, not the band name. A rotated
        # label's height is the length of its text, and that height is what the
        # reserved band is made of, so a short label buys back panel height that
        # a smaller font cannot. The centre comes from the caller's spec; no
        # position is written here. `:g` drops the point from a whole number.
        return panel.text(
            spec.centre,
            y,
            f"{spec.centre:g}",
            transform=blended,
            rotation=90,
            fontsize=ANNOTATION_FONT_SIZE,
            color=ANNOTATION_TEXT_COLOR,
            horizontalalignment="center",
            verticalalignment="top",
            zorder=ANNOTATION_ZORDER,
        )

    # Measure each label exactly as it will be drawn, then discard the probe.
    # Rotated upright, a label's width is its line height and its height is the
    # length of its text, so both numbers come from the renderer.
    widths: list[float] = []
    heights: list[float] = []
    for spec in selected:
        probe = label(spec, 1.0)
        box = probe.get_window_extent(renderer=renderer)
        widths.append(float(box.width))
        heights.append(float(box.height))
        probe.remove()

    centres_px = [float(panel.transData.transform((spec.centre, 0.0))[0]) for spec in selected]

    # Rows are filled top down. A label goes in the topmost row where it clears
    # the label already placed there; the panel is walked left to right, so that
    # is always the rightmost one in the row.
    rows: list[list[int]] = []
    occupied: list[tuple[float, float]] = []
    for index in range(len(selected)):
        half = widths[index] / 2.0
        target = None
        for row, (last_centre, last_half) in enumerate(occupied):
            needed = ANNOTATION_MIN_CLEARANCE * (last_half + half)
            if centres_px[index] - last_centre >= needed:
                target = row
                break
        if target is None:
            rows.append([])
            occupied.append((0.0, 0.0))
            target = len(rows) - 1
        rows[target].append(index)
        occupied[target] = (centres_px[index], half)

    line_height = max(widths)
    gap = ANNOTATION_ROW_GAP * line_height
    row_heights = [max(heights[index] for index in row) for row in rows]
    # Pad above the first row, each row, and a gap under every row so the lowest
    # label clears the traces.
    reserved = ANNOTATION_TOP_PAD * line_height + sum(row_heights) + gap * len(rows)

    panel_height = float(panel.get_window_extent(renderer=renderer).height)
    fraction = reserved / panel_height
    if fraction >= 1.0:
        raise ValueError(
            f"band labels for window {window!r} need {reserved:.0f} of the panel's "
            f"{panel_height:.0f} pixels, leaving no room for the data: "
            f"{len(selected)} band(s) over {len(rows)} row(s)"
        )

    # Raise the top so the reserved band is empty, compressing what is already
    # drawn into the rest. The bottom never moves.
    bottom, top = panel.get_ylim()
    if logy:
        low, high = float(np.log10(bottom)), float(np.log10(top))
        panel.set_ylim(bottom, float(10.0 ** (low + (high - low) / (1.0 - fraction))))
    else:
        panel.set_ylim(bottom, bottom + (top - bottom) / (1.0 - fraction))

    # Keep the legend out of the band just reserved. Its placement is still
    # chosen by loc="best", but searched only over the data region: "best"
    # scores candidates against the data, and the reserved band is empty of data
    # by construction, so without this it reads as the emptiest part of the
    # panel and the legend lands on top of the labels. Guarded because nothing
    # in this function's contract says the caller made a legend.
    legend = panel.get_legend()
    if legend is not None:
        legend.set_bbox_to_anchor(
            (0.0, 0.0, 1.0, 1.0 - fraction), transform=panel.transAxes
        )

    # Labels and rules are placed together, because a rule has to stop below the
    # foot of its own label and where that foot sits depends on the label's row.
    # ymin/ymax are axes fractions, so this needs no unit conversion and behaves
    # the same on a log axis. The top stays inside the reserved band, and so
    # above every trace, because the clearance is smaller than the row gap.
    cursor = ANNOTATION_TOP_PAD * line_height
    for row, indices in enumerate(rows):
        y = 1.0 - cursor / panel_height
        for index in indices:
            spec = selected[index]
            label(spec, y)
            foot = y - (heights[index] + ANNOTATION_RULE_CLEARANCE * line_height) / panel_height
            panel.axvline(
                spec.centre,
                ymax=foot,
                color=ANNOTATION_RULE_COLOR,
                linewidth=ANNOTATION_RULE_WIDTH,
                alpha=ANNOTATION_RULE_ALPHA,
                zorder=ANNOTATION_ZORDER,
            )
        cursor += row_heights[row] + gap

    return [[selected[index].name for index in row] for row in rows]


def build_sample_overlay(
    spectra: list[Spectrum],
    logy: bool = False,
    baseline_params: dict[str, dict[str, float | int]] | None = None,
    bands: dict[str, BandSpec] | None = None,
    exclude_from_scale: BandSpec | None = None,
) -> plt.Figure:
    """Build the broken-axis overlay figure for one sample.

    The low window is drawn in the left panel and the high window in the right,
    with panel widths proportional to each window's measured wave span so that
    cm-1 per inch matches across the break. The two panels autoscale their y
    axes independently, because within a sample one window's maximum can be an
    order of magnitude above the other's. A sample present in only one window is
    drawn as a single ordinary panel with no break marks.

    The tripwire runs before the figure is returned. Nothing is saved and the
    figure is left open: the caller owns it and must close it.

    Args:
        spectra: Every spectrum for one sample, any windows, any steps.
        logy: Put both panels on a log y-scale.
        baseline_params: ``lam``, ``p`` and ``n_iter`` keyed by window label,
            so each window may be corrected with its own smoothness. When given,
            the baseline-corrected values are drawn instead of the raw ones and
            the title says so. When None the raw file contents are drawn.
        bands: The configured bands, exactly as ``load_bands_config`` returns
            them. When given, each panel is labelled with the bands configured
            for its window. When None nothing is drawn and no limit is changed,
            so the figure is bit for bit what it has always been.
        exclude_from_scale: A band whose search window is left out of the upper
            limit calculation, on the one panel whose window is that band's. The
            band is still drawn and runs off the top, and the title says which
            band it was. Which band this is comes from the caller; nothing here
            knows any band's position. When None no limit is changed.

    Returns:
        The open figure.

    Raises:
        ValueError: If ``spectra`` is empty, holds more than one sample, carries
            an unknown window label, if the labels would fill a whole panel, or
            if the tripwire finds that any drawn line no longer matches the data
            it should.
    """
    if not spectra:
        raise ValueError("no spectra given")
    samples = {s.sample for s in spectra}
    if len(samples) != 1:
        raise ValueError(f"expected spectra for exactly one sample, got {sorted(samples)}")
    sample = spectra[0].sample
    experiment = spectra[0].experiment

    by_window = _spectra_by_window(spectra)
    windows = [w for w in WINDOW_ORDER if w in by_window]

    spans = [
        max(float(s.wave.max()) for s in by_window[w])
        - min(float(s.wave.min()) for s in by_window[w])
        for w in windows
    ]

    steps = [s.step for s in spectra]
    min_step, max_step = min(steps), max(steps)

    figure, axes_list = plt.subplots(
        1,
        len(windows),
        figsize=FIGURE_SIZE,
        squeeze=False,
        gridspec_kw={"width_ratios": spans, "wspace": PANEL_GAP},
    )
    axes = list(axes_list[0])

    # Each line is paired with its spectrum as it is drawn. Re-deriving the
    # mapping from panel.lines at save time would depend on draw order and on
    # filtering out the break-mark artists, and a tripwire that can silently
    # mis-pair is worse than no tripwire at all.
    drawn: list[tuple[Line2D, Spectrum]] = []
    drawn_corrected: list[tuple[Line2D, Spectrum, np.ndarray, np.ndarray]] = []

    for window, panel in zip(windows, axes):
        panel_steps = []
        panel_values: list[tuple[np.ndarray, np.ndarray]] = []
        for spectrum in by_window[window]:
            colour, linestyle = _style_for_step(spectrum.step, min_step, max_step)
            if baseline_params is None:
                values = spectrum.intensity
            else:
                values, fitted = correct_baseline(
                    spectrum, **baseline_params[spectrum.window]
                )
            (line,) = panel.plot(
                spectrum.wave,
                values,
                color=colour,
                linestyle=linestyle,
                linewidth=LINE_WIDTH,
            )
            if baseline_params is None:
                drawn.append((line, spectrum))
            else:
                drawn_corrected.append((line, spectrum, values, fitted))
            panel_steps.append(spectrum.step)
            panel_values.append((spectrum.wave, values))
        panel.set_xlabel(X_LABEL)

        if logy:
            panel.set_yscale("log")
        else:
            # Intensities are photon counts and cannot be negative, so the
            # autoscale margin dipping below zero is meaningless space. Clamp it
            # away, but ONLY when autoscale actually went negative. Forcing every
            # panel to start at zero would add a large empty band under samples
            # whose baseline sits well above it - ech6's low window spans
            # 16941-37168 and would lose nearly half its height. Keep conditional.
            bottom, top = panel.get_ylim()
            if bottom < 0:
                panel.set_ylim(bottom=0, top=top)

        # After the scale and the clamp, so it composes with both: set_yscale
        # re-autoscales and would undo a limit set before it. Before the legend
        # and the labels, because loc="best" and the reserved band are both
        # measured against the panel this leaves behind.
        if exclude_from_scale is not None and window == exclude_from_scale.window:
            _raise_top_excluding_band(panel, panel_values, exclude_from_scale, logy)

        # One legend per panel, listing only the steps drawn in that panel: a
        # sample can be missing a step in one window but not the other.
        handles = [
            Line2D([], [], color=colour, linestyle=linestyle, linewidth=LINE_WIDTH)
            for colour, linestyle in (
                _style_for_step(step, min_step, max_step) for step in sorted(set(panel_steps))
            )
        ]
        panel.legend(
            handles,
            [_step_label(step) for step in sorted(set(panel_steps))],
            loc="best",
            frameon=True,
            title="step",
        )

        # Last, so the labels are measured against the panel's final limits and
        # the reserved band is added on top of the clamp above, not before it.
        if bands is not None:
            _annotate_band_centres(figure, panel, window, bands, logy)

    axes[0].set_ylabel(Y_LABEL)

    if len(axes) == 2:
        left, right = axes
        left.spines["right"].set_visible(False)
        right.spines["left"].set_visible(False)
        # The left spine of the right panel is hidden, so its tick labels move
        # to the right spine rather than sitting inside the break.
        right.yaxis.tick_right()
        right.yaxis.set_label_position("right")
        _draw_break_marks(left, right)

    title = f"{sample} - {experiment}"
    if len(windows) == 1:
        title = f"{title} ({windows[0]} window only)"
    if baseline_params is not None:
        # Stated on the figure itself so a corrected plot can never be mistaken
        # for a raw one once it is out of the directory it was written to.
        title = f"{title} - BASELINE CORRECTED ({_params_label(baseline_params, windows)})"
    if exclude_from_scale is not None:
        # Said on the figure for the same reason. An excluded band can run many
        # panel-heights past the top edge, and a reader who cannot see its peak
        # has no other way to know it was left out of the scale. The band name
        # goes in the title, never in the filename.
        title = (
            f"{title} - y-SCALE EXCLUDES {exclude_from_scale.name} "
            f"({exclude_from_scale.window} panel; its peak runs off the top)"
        )
    figure.suptitle(title)

    if baseline_params is None:
        _assert_drawn_data_is_raw(drawn)
    else:
        _assert_drawn_data_is_corrected(drawn_corrected)
    return figure


def build_baseline_diagnostic(
    spectra: list[Spectrum], baseline_params: dict[str, dict[str, float | int]]
) -> plt.Figure:
    """Build the fit-inspection figure for one sample in one window.

    One row per step in ascending order, two columns: the raw spectrum with the
    fitted baseline drawn over it on the left, the corrected result on the
    right. This is the figure used to judge whether the fit is eating real peaks
    or leaving curvature behind.

    Both tripwires apply: raw lines are checked against the file, corrected
    lines against the correction, and the reconstruction identity is checked
    once per spectrum.

    Args:
        spectra: Every spectrum for one sample in one window.
        baseline_params: ``lam``, ``p`` and ``n_iter`` keyed by window label.

    Returns:
        The open figure. The caller owns it and must close it.

    Raises:
        ValueError: If ``spectra`` is empty, spans more than one sample or
            window, or if a tripwire fires.
    """
    if not spectra:
        raise ValueError("no spectra given")
    samples = {s.sample for s in spectra}
    windows = {s.window for s in spectra}
    if len(samples) != 1 or len(windows) != 1:
        raise ValueError(
            f"expected one sample in one window, got samples {sorted(samples)} "
            f"and windows {sorted(windows)}"
        )
    ordered = sorted(spectra, key=lambda s: s.step)
    sample = ordered[0].sample
    window = ordered[0].window
    experiment = ordered[0].experiment

    figure, axes_grid = plt.subplots(
        len(ordered),
        2,
        figsize=(DIAGNOSTIC_WIDTH, DIAGNOSTIC_ROW_HEIGHT * len(ordered)),
        squeeze=False,
        sharex=True,
    )

    drawn_raw: list[tuple[Line2D, Spectrum]] = []
    drawn_corrected: list[tuple[Line2D, Spectrum, np.ndarray, np.ndarray]] = []

    for row, spectrum in enumerate(ordered):
        corrected, fitted = correct_baseline(spectrum, **baseline_params[window])
        left, right = axes_grid[row]

        (raw_line,) = left.plot(
            spectrum.wave, spectrum.intensity, color="black", linewidth=LINE_WIDTH, label="raw"
        )
        drawn_raw.append((raw_line, spectrum))
        left.plot(
            spectrum.wave,
            fitted,
            color=BASELINE_FIT_COLOR,
            linewidth=LINE_WIDTH * 1.4,
            label="fitted baseline",
        )
        left.set_ylabel(_step_label(spectrum.step))

        (corrected_line,) = right.plot(
            spectrum.wave, corrected, color=CORRECTED_COLOR, linewidth=LINE_WIDTH,
            label="corrected",
        )
        drawn_corrected.append((corrected_line, spectrum, corrected, fitted))
        right.axhline(0.0, color="grey", linewidth=0.6, linestyle=":")

        if row == 0:
            left.set_title("raw with fitted baseline")
            right.set_title("corrected")
            left.legend(loc="best", frameon=True)

    for axes in axes_grid[-1]:
        axes.set_xlabel(X_LABEL)

    figure.suptitle(
        f"{sample} {window} - {experiment} - baseline check "
        f"({_params_label(baseline_params, [window])})"
    )

    _assert_drawn_data_is_raw(drawn_raw)
    _assert_drawn_data_is_corrected(drawn_corrected)
    return figure


def build_sample_band_trends(
    rows: list[dict[str, object]], sample: str, reference: str, min_snr: float
) -> plt.Figure:
    """Plot normalised band intensity against irradiation step for one sample.

    Steps are placed at their actual value, so a gap in the sequence shows as a
    gap. Cross-window bands and low signal-to-noise points are marked, because a
    weak measurement must never be presented as though it were a solid one.

    Args:
        rows: Measurement rows for the whole experiment.
        sample: The sample to draw.
        reference: Name of the reference band, flat at 1.0 by construction.
        min_snr: Below this a point is drawn hollow and called out in the legend.

    Returns:
        The open figure. The caller owns it and must close it.

    Raises:
        ValueError: If no rows match ``sample``.
    """
    mine = [r for r in rows if r["sample"] == sample]
    if not mine:
        raise ValueError(f"no measurements for sample {sample!r}")

    bands = sorted({str(r["band"]) for r in mine})
    colours = matplotlib.colormaps["tab10"]
    figure, axes = plt.subplots(figsize=FIGURE_SIZE)

    any_weak = False
    for index, band in enumerate(bands):
        series = sorted(
            (r for r in mine if r["band"] == band), key=lambda r: int(r["step"])
        )
        steps = [int(r["step"]) for r in series]
        values = [r["height_norm"] for r in series]
        cross = any(bool(r["cross_window"]) for r in series)
        label = f"{band} *" if cross else band
        if band == reference:
            label = f"{band} (reference)"
        colour = colours(index % 10)
        axes.plot(
            steps,
            values,
            marker="o",
            markersize=4,
            linewidth=LINE_WIDTH * 1.6,
            linestyle="--" if cross else "-",
            color=colour,
            label=label,
        )
        weak_steps = [
            s
            for s, r in zip(steps, series)
            if r["signal_to_noise"] is not None and float(r["signal_to_noise"]) < min_snr
        ]
        if weak_steps:
            any_weak = True
            weak_values = [
                v
                for v, r in zip(values, series)
                if r["signal_to_noise"] is not None and float(r["signal_to_noise"]) < min_snr
            ]
            axes.plot(
                weak_steps,
                weak_values,
                marker="o",
                markersize=10,
                linestyle="none",
                markerfacecolor="none",
                markeredgecolor=colour,
                markeredgewidth=1.6,
            )

    axes.axhline(1.0, color="grey", linewidth=0.6, linestyle=":")
    axes.set_xlabel("irradiation step")
    axes.set_ylabel(f"band height / {reference}")
    axes.set_xticks(sorted({int(r["step"]) for r in mine}))
    subtitle = "  dashed + * = cross-window normalisation"
    if any_weak:
        subtitle += f";  hollow ring = SNR < {min_snr:g}"
    axes.set_title(f"{sample} - normalised band intensity\n{subtitle}", fontsize=10)
    axes.legend(loc="best", frameon=True, fontsize=8)
    figure.tight_layout()
    return figure


def build_all_sample_band_trends(
    rows: list[dict[str, object]], reference: str, min_snr: float
) -> plt.Figure:
    """One panel per band, every sample overlaid, so a shared trend is visible."""
    bands = sorted({str(r["band"]) for r in rows})
    samples = sorted({str(r["sample"]) for r in rows})
    columns = min(3, len(bands))
    rows_count = (len(bands) + columns - 1) // columns
    figure, grid = plt.subplots(
        rows_count,
        columns,
        figsize=(4.0 * columns, 3.0 * rows_count),
        squeeze=False,
        sharex=True,
    )
    colours = matplotlib.colormaps["tab10"]

    for index, band in enumerate(bands):
        axes = grid[index // columns][index % columns]
        cross = any(bool(r["cross_window"]) for r in rows if r["band"] == band)
        for position, sample in enumerate(samples):
            series = sorted(
                (r for r in rows if r["band"] == band and r["sample"] == sample),
                key=lambda r: int(r["step"]),
            )
            if not series:
                continue
            axes.plot(
                [int(r["step"]) for r in series],
                [r["height_norm"] for r in series],
                marker="o",
                markersize=3,
                linewidth=LINE_WIDTH * 1.4,
                color=colours(position % 10),
                label=sample,
            )
        axes.axhline(1.0, color="grey", linewidth=0.6, linestyle=":")
        axes.set_title(f"{band} *" if cross else band, fontsize=9)
        axes.tick_params(labelsize=8)
    for index in range(len(bands), rows_count * columns):
        grid[index // columns][index % columns].set_visible(False)
    for axes in grid[-1]:
        if axes.get_visible():
            axes.set_xlabel("irradiation step", fontsize=8)
    grid[0][0].set_ylabel(f"height / {reference}", fontsize=8)
    handles, labels = grid[0][0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8)
    figure.suptitle(
        f"normalised band intensity, all samples  (* = cross-window normalisation)",
        fontsize=11,
    )
    figure.tight_layout()
    return figure


def plot_sample_band_trends(
    rows: list[dict[str, object]],
    sample: str,
    reference: str,
    output_path: Path,
    min_snr: float,
) -> Path:
    """Build and save the per-sample band trend figure."""
    return _save(build_sample_band_trends(rows, sample, reference, min_snr), output_path)


def plot_all_sample_band_trends(
    rows: list[dict[str, object]], reference: str, output_path: Path, min_snr: float
) -> Path:
    """Build and save the all-samples band trend figure."""
    return _save(build_all_sample_band_trends(rows, reference, min_snr), output_path)


def _save(figure: plt.Figure, output_path: Path) -> Path:
    """Write a figure and close it, whatever happens."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    finally:
        plt.close(figure)
    return output_path


def plot_sample_overlay(
    spectra: list[Spectrum],
    output_path: Path,
    logy: bool = False,
    baseline_params: dict[str, dict[str, float | int]] | None = None,
    bands: dict[str, BandSpec] | None = None,
    exclude_from_scale: BandSpec | None = None,
) -> Path:
    """Draw every step of one sample as a broken-axis overlay and save it.

    Thin wrapper over :func:`build_sample_overlay`: one function builds the
    figure, this one persists it.

    Args:
        spectra: Every spectrum for one sample, any windows, any steps.
        output_path: PNG path to write. Parent directories are created and an
            existing file is overwritten.
        logy: Put both panels on a log y-scale.
        baseline_params: Passed through; None draws raw data.
        bands: Passed through; None draws no band labels.
        exclude_from_scale: Passed through; None changes no limit.

    Returns:
        The path written.

    Raises:
        ValueError: Anything :func:`build_sample_overlay` raises.
    """
    figure = build_sample_overlay(
        spectra,
        logy=logy,
        baseline_params=baseline_params,
        bands=bands,
        exclude_from_scale=exclude_from_scale,
    )
    return _save(figure, output_path)


def plot_baseline_diagnostic(
    spectra: list[Spectrum], output_path: Path, baseline_params: dict[str, dict[str, float | int]]
) -> Path:
    """Build the fit-inspection figure for one sample and window, and save it.

    Args:
        spectra: Every spectrum for one sample in one window.
        output_path: PNG path to write.
        baseline_params: ``lam``, ``p`` and ``n_iter`` keyed by window label.

    Returns:
        The path written.

    Raises:
        ValueError: Anything :func:`build_baseline_diagnostic` raises.
    """
    figure = build_baseline_diagnostic(spectra, baseline_params)
    return _save(figure, output_path)
