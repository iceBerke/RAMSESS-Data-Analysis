"""Figure logic for spectra overlays.

All matplotlib work lives here. Intensities are drawn as raw counts: nothing in
this module smooths, baseline-corrects, normalises or rescales the data.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

# Deliberate global side effect at import time. The backend must be chosen
# before pyplot is imported, so this cannot be deferred into a function.
# Importing this module fixes the process backend to the non-interactive Agg,
# which needs no display and lets figures be written from a plain script.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from ramsess.analysis import correct_baseline  # noqa: E402
from ramsess.io import WINDOW_ORDER, Spectrum, window_sort_key  # noqa: E402

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


def build_sample_overlay(
    spectra: list[Spectrum],
    logy: bool = False,
    baseline_params: dict[str, dict[str, float | int]] | None = None,
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

    Returns:
        The open figure.

    Raises:
        ValueError: If ``spectra`` is empty, holds more than one sample, carries
            an unknown window label, or if the tripwire finds that any drawn
            line no longer matches the data it should.
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

    Returns:
        The path written.

    Raises:
        ValueError: Anything :func:`build_sample_overlay` raises.
    """
    figure = build_sample_overlay(spectra, logy=logy, baseline_params=baseline_params)
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
