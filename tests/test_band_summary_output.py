"""Characterisation of ``print_band_summary``'s output as it stands today.

This file pins the summary table exactly as ``report.py`` prints it right now -
every column width, every flag character, every section heading and the order
they appear in. It records current behaviour; it does not endorse it. The
misalignment test below asserts a formatting bug on purpose.

**Pending item 3 reworks this table, and is expected to break these tests.** A
failure here after that work is the intended signal, not a regression: read the
diff, confirm the new output is what was wanted, and update the expected block.
Never adjust an assertion here to make a red test green without that decision.

Split out of ``test_quantify_experiment.py``, which covers the orchestration
around this function. Nothing here touches the filesystem.
"""

from __future__ import annotations

import pytest

from conftest import assert_row_contract
from ramsess.io import WINDOW_ORDER
from ramsess.report import (
    MAX_POSITION_DRIFT,
    MIN_SIGNAL_TO_NOISE,
    print_band_summary,
)

LOW, HIGH = WINDOW_ORDER

# Deliberately strict. The expected block below restates the field widths and
# wording from report.py rather than importing them, which is the whole point of
# a characterisation test: pending item 3 reworks this table, and when it does
# these tests must fail loudly and show the old text against the new.
#
# No value is typed twice. Every name, number and flag is read back off the rows
# the fixture built, so nothing here encodes a fact about the real dataset.

SUMMARY_SAMPLES = ("alpha", "beta")
SUMMARY_BANDS = ("ref_band", "peak_two", "peak_high")
SUMMARY_REFERENCE = SUMMARY_BANDS[0]
CROSS_BAND = SUMMARY_BANDS[2]
WEAK_SNR = MIN_SIGNAL_TO_NOISE / 2.0
STRONG_SNR = MIN_SIGNAL_TO_NOISE * 5.0
BIG_DRIFT = MAX_POSITION_DRIFT + 2.0


def build_summary_row(
    sample: str,
    window: str,
    step: int,
    band: str,
    *,
    position: float,
    drift: float,
    height: float,
    area: float,
    snr: float | None,
    at_edge: bool,
    height_norm: float | None,
    cross_window: bool,
) -> dict[str, object]:
    """One measurement row, carrying exactly the keys the real ones carry."""
    row: dict[str, object] = {
        "sample": sample,
        "window": window,
        "step": step,
        "band": band,
        "centre": position - drift,
        "position": position,
        "position_drift": drift,
        "height": height,
        "area": area,
        "n_points": 11,
        "at_edge": at_edge,
        "noise": None if snr is None else height / snr,
        "signal_to_noise": snr,
        "height_norm": height_norm,
        "area_norm": height_norm,
        "cross_window": cross_window,
    }
    # Pins the row contract to the CSV columns, the same check the pipeline
    # tests in test_quantify_experiment.py make against real rows.
    assert_row_contract(row)
    return row


@pytest.fixture
def summary_rows() -> list[dict[str, object]]:
    """A row set reaching every branch of print_band_summary.

    One sample with two steps and one band measured at only one of them, one
    controls-only sample, a weak measurement, an edge measurement, a drifted
    reference and a cross-window band.
    """
    a, b = SUMMARY_SAMPLES
    reference, second, cross = SUMMARY_BANDS
    return [
        build_summary_row(
            a, LOW, 0, reference, position=500.0, drift=0.0, height=1000.0,
            area=9000.0, snr=STRONG_SNR, at_edge=False, height_norm=1.0,
            cross_window=False,
        ),
        build_summary_row(
            a, LOW, 0, second, position=600.0, drift=0.0, height=500.0,
            area=4000.0, snr=STRONG_SNR, at_edge=False, height_norm=0.5,
            cross_window=False,
        ),
        build_summary_row(
            a, HIGH, 0, cross, position=2900.0, drift=0.0, height=300.0,
            area=2000.0, snr=STRONG_SNR, at_edge=True, height_norm=0.3,
            cross_window=True,
        ),
        build_summary_row(
            a, LOW, 2, reference, position=500.0, drift=0.0, height=900.0,
            area=8000.0, snr=STRONG_SNR, at_edge=False, height_norm=1.0,
            cross_window=False,
        ),
        build_summary_row(
            a, LOW, 2, second, position=601.0, drift=1.0, height=400.0,
            area=3000.0, snr=WEAK_SNR, at_edge=False, height_norm=0.4444,
            cross_window=False,
        ),
        build_summary_row(
            b, LOW, 0, reference, position=507.0, drift=BIG_DRIFT, height=800.0,
            area=7000.0, snr=STRONG_SNR, at_edge=False, height_norm=1.0,
            cross_window=False,
        ),
        build_summary_row(
            b, LOW, 0, second, position=600.0, drift=0.0, height=200.0,
            area=1500.0, snr=STRONG_SNR, at_edge=False, height_norm=0.25,
            cross_window=False,
        ),
        build_summary_row(
            b, HIGH, 0, cross, position=2900.0, drift=0.0, height=160.0,
            area=1100.0, snr=STRONG_SNR, at_edge=False, height_norm=0.2,
            cross_window=True,
        ),
    ]


def find(rows: list[dict[str, object]], sample: str, step: int, band: str):
    """The one row matching this coordinate, or None if it was not measured."""
    matches = [
        r for r in rows if r["sample"] == sample and r["step"] == step and r["band"] == band
    ]
    assert len(matches) <= 1
    return matches[0] if matches else None


def test_print_band_summary_renders_the_current_table_exactly(
    summary_rows: list[dict[str, object]], capsys
) -> None:
    print_band_summary(summary_rows, SUMMARY_REFERENCE)
    captured = capsys.readouterr()
    assert captured.err == ""

    a, b = SUMMARY_SAMPLES
    reference, second, cross = SUMMARY_BANDS
    ordered_bands = sorted(SUMMARY_BANDS)
    weak = find(summary_rows, a, 2, second)
    edged = find(summary_rows, a, 0, cross)
    drifted = find(summary_rows, b, 0, reference)

    expected: list[str] = ["", "== reference band =="]
    expected.append(f"  {reference}: absolute height and area per sample and step")
    expected.append(
        f"    {'sample':8s} {'step':>5s} {'height':>14s} {'area':>16s} {'position':>10s}"
    )
    for sample, step in ((a, 0), (a, 2), (b, 0)):
        row = find(summary_rows, sample, step, reference)
        label = "control" if step == 0 else f"irr{step}"
        expected.append(
            f"    {row['sample']:8s} {label:>5s} {row['height']:14.1f} "
            f"{row['area']:16.1f} {row['position']:10.2f}"
        )

    expected.extend(["", "== normalised band heights =="])
    for sample in SUMMARY_SAMPLES:
        steps = sorted({int(r["step"]) for r in summary_rows if r["sample"] == sample})
        expected.append(f"  {sample}:")
        expected.append(
            "    "
            + "band".ljust(16)
            + "".join(f"{('c' if s == 0 else f'i{s}'):>9s}" for s in steps)
        )
        for band in ordered_bands:
            cells = ""
            for step in steps:
                row = find(summary_rows, sample, step, band)
                if row is None:
                    cells += f"{'-':>9s}"
                    continue
                mark = ""
                if row["at_edge"]:
                    mark = "E"
                elif float(row["signal_to_noise"]) < MIN_SIGNAL_TO_NOISE:
                    mark = "~"
                cells += f"{row['height_norm']:8.4f}{mark}"
            flag = " *" if band == cross else "  "
            expected.append(f"    {band:16s}" + cells + flag)

    expected.extend(["", "== flags =="])
    expected.append(
        f"  '~' signal-to-noise below {MIN_SIGNAL_TO_NOISE:g}, "
        f"'E' peak on the search-window edge, '*' cross-window normalisation"
    )
    expected.append(f"  measurements below SNR {MIN_SIGNAL_TO_NOISE:g}: 1 of {len(summary_rows)}")
    expected.append(
        f"    {weak['sample']} {weak['band']} step {weak['step']}: "
        f"SNR {weak['signal_to_noise']:.1f} (height {weak['height']:.1f}, "
        f"noise {weak['noise']:.1f})"
    )
    expected.append("  peaks on a search-window edge: 1")
    expected.append(
        f"    {edged['sample']} {edged['band']} step {edged['step']}: "
        f"position {edged['position']:.2f} vs centre {edged['centre']:.2f}"
    )
    expected.append(
        f"  bands whose located position moved more than "
        f"{MAX_POSITION_DRIFT:g} cm-1 from the configured centre:"
    )
    expected.append(
        f"    {drifted['sample']} {drifted['band']}: 1 step(s), drift "
        f"{drifted['position_drift']:+.2f} to {drifted['position_drift']:+.2f} cm-1"
    )
    cross_rows = [r for r in summary_rows if r["cross_window"]]
    expected.append(
        f"  CROSS-WINDOW NORMALISATION: {len(cross_rows)} measurement(s) in window(s) "
        f"{HIGH} were normalised to reference {SUMMARY_REFERENCE!r}, which "
        f"lies in a different spectral window."
    )
    expected.append(
        "    Low and high are separate sequential sweeps, so this assumes both "
        "shared the same collection efficiency. That assumption is plausible "
        "here but untested. Treat those ratios accordingly."
    )

    assert captured.out == "\n".join(expected) + "\n"


def test_reference_table_columns_misalign_on_control_rows(
    summary_rows: list[dict[str, object]], capsys
) -> None:
    """Characterisation of a formatting wart. Asserted as-is, not fixed.

    The step column is formatted ``{label:>5s}`` but the control label is
    ``control``, seven characters. It overflows the field and shifts height,
    area and position two columns right on control rows only, so the header no
    longer sits above its data. Pending item 3 reworks this table; when it does,
    this test is the one that says the old layout is gone.
    """
    print_band_summary(summary_rows, SUMMARY_REFERENCE)
    lines = capsys.readouterr().out.split("\n")

    a = SUMMARY_SAMPLES[0]
    control_row = find(summary_rows, a, 0, SUMMARY_REFERENCE)
    irradiated_row = find(summary_rows, a, 2, SUMMARY_REFERENCE)
    header = next(line for line in lines if line.lstrip().startswith("sample"))
    control = next(line for line in lines if "control" in line)
    irradiated = next(line for line in lines if f"irr{irradiated_row['step']}" in line)

    def right_edge(line: str, text: str) -> int:
        return line.index(text) + len(text)

    header_edge = right_edge(header, "height")
    # The step field is five wide. "irr2" fits, so that row's height value lands
    # exactly under the header.
    assert right_edge(irradiated, f"{irradiated_row['height']:.1f}") == header_edge
    # "control" is seven characters and overflows the field, pushing height,
    # area and position right by exactly the overflow on control rows only.
    overflow = len("control") - 5
    assert overflow == 2
    assert right_edge(control, f"{control_row['height']:.1f}") == header_edge + overflow


def test_without_noise_regions_the_summary_says_no_snr_was_computed(capsys) -> None:
    rows = [
        build_summary_row(
            SUMMARY_SAMPLES[0], LOW, 0, SUMMARY_REFERENCE, position=500.0, drift=0.0,
            height=1000.0, area=9000.0, snr=None, at_edge=False, height_norm=1.0,
            cross_window=False,
        )
    ]
    print_band_summary(rows, SUMMARY_REFERENCE)
    out = capsys.readouterr().out

    assert (
        "  no noise_regions configured in bands.json, so no signal-to-noise "
        "was computed and no weak-band flagging was possible" in out
    )
    assert "measurements below SNR" not in out
    assert "CROSS-WINDOW NORMALISATION" not in out
    assert "peaks on a search-window edge" not in out


def test_a_missing_normalised_value_renders_as_the_same_dash_as_a_missing_row(
    capsys,
) -> None:
    """None height_norm and an absent measurement are indistinguishable.

    Both print the same right-aligned '-'. This is the reporting half of the
    missing-reference-window behaviour covered in test_quantify_experiment.py,
    and pending item 3 will have to decide whether the two cases should still
    look alike.
    """
    sample = SUMMARY_SAMPLES[0]
    reference, second, _ = SUMMARY_BANDS
    rows = [
        build_summary_row(
            sample, LOW, 0, reference, position=500.0, drift=0.0, height=1000.0,
            area=9000.0, snr=STRONG_SNR, at_edge=False, height_norm=1.0,
            cross_window=False,
        ),
        build_summary_row(
            sample, LOW, 0, second, position=600.0, drift=0.0, height=500.0,
            area=4000.0, snr=STRONG_SNR, at_edge=False, height_norm=None,
            cross_window=False,
        ),
    ]
    print_band_summary(rows, reference)
    lines = capsys.readouterr().out.split("\n")

    band_line = next(line for line in lines if line.strip().startswith(second))
    assert band_line == f"    {second:16s}" + f"{'-':>9s}" + "  "
