"""Characterisation tests for ``quantify_experiment``.

These lock in CURRENT behaviour so that the pending changes to quantification
surface as failures rather than as silent drift. Where the behaviour recorded
here looks wrong it is still asserted exactly as it stands: nothing in this file
endorses what it pins, and every such case is called out in a comment.

``tests/test_quantify.py`` covers the components of quantification - config
validation, the write guard, export, normalisation. This file covers the
function that orchestrates them, which nothing else calls.
``tests/test_band_summary_output.py`` covers ``print_band_summary``, which this
function calls last.

Every experiment is synthetic and lives under ``tmp_path``. Nothing here reads
or writes the project's ``data/`` or ``figures/`` trees, and the autouse
``repository_untouched`` fixture in ``conftest.py`` proves it rather than
asserting it in prose.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
import numpy as np
import pytest

from conftest import tree_snapshot, write_spectrum_file
from ramsess.io import WINDOW_ORDER, load_experiment
from ramsess.report import (
    BANDS_CONFIG_NAME,
    BANDS_CSV_COLUMNS,
    BASELINE_CONFIG_NAME,
    DERIVED_HEADER,
    MIN_SIGNAL_TO_NOISE,
    quantify_experiment,
    resolve_baseline_config,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOW, HIGH = WINDOW_ORDER

EXPERIMENT = "synthetic"

# --- fixture geometry ------------------------------------------------------
#
# These describe the synthetic data this file invents. They are not facts about
# any real experiment, and no assertion below restates them: every expected
# value is read back out of the fixture or off the loaded wave axis, exactly as
# test_quantify.py::valid_config already does.

N_POINTS = 90
AXIS = {
    #        start,  spacing,  base intensity
    LOW: (200.0, 2.5, 1000.0),
    HIGH: (2400.0, 2.0, 5000.0),
}
# Indices, on the axis above, where a peak is planted and where a band is
# therefore configured. Coupling the two means the located position lands on the
# configured centre by construction, so the drift flag stays quiet unless a test
# wants it.
PEAK_INDICES = {LOW: (18, 54), HIGH: (45,)}
BAND_NAMES = {LOW: ("alpha_band", "beta_band"), HIGH: ("gamma_band",)}
REFERENCE = BAND_NAMES[LOW][0]
# Half-width expressed in points, converted to wave units off the real axis.
HALF_WIDTH_POINTS = 4
# A featureless stretch, clear of every planted peak.
NOISE_INDICES = (72, 84)

PEAK_HEIGHT = 900.0
# A small deterministic ripple, so the noise estimate is a real positive number
# instead of the degenerate zero a perfectly flat baseline would give.
RIPPLE = 2.0

BASELINE_PAYLOAD = {
    "lam": 1e6,
    "p": 0.01,
    "n_iter": 10,
    "windows": {HIGH: {"lam": 1e8}},
}


# --- building a synthetic experiment ---------------------------------------


def spectrum_body(window: str, delta: float) -> list[str]:
    """One spectrum in ``window``: flat, rippled, with a peak at each index."""
    start, spacing, base = AXIS[window]
    peaks = set(PEAK_INDICES[window])
    lines, wave = [], start
    for i in range(N_POINTS):
        wave += spacing * (1.0 + 0.1 * (i % 3))
        value = base + delta + RIPPLE * ((i % 5) - 2)
        if i in peaks:
            value += PEAK_HEIGHT
        lines.append(f"{wave:.6f}\t{value:.6f}")
    return lines


def step_name(step: int) -> str:
    """Filename step token: ``0`` for the control, ``irr<N>`` otherwise."""
    return "0" if step == 0 else f"irr{step}"


def build_experiment(tmp_path: Path, layout: dict[str, dict[str, list[int]]]) -> Path:
    """Write a synthetic experiment and return its raw root.

    Args:
        tmp_path: The test's temporary directory.
        layout: ``{sample: {window: [steps]}}``. A sample may omit a window and
            a step sequence may have gaps; both are things the real data does.

    Returns:
        The raw root, ready to hand to ``load_experiment``.
    """
    raw_root = tmp_path / "raw"
    folder = raw_root / EXPERIMENT
    folder.mkdir(parents=True, exist_ok=True)
    # Every file gets a distinct intensity offset, so no two share a content
    # hash and the duplicate-content hard check stays out of the way.
    delta = 0.0
    for sample in sorted(layout):
        for window in sorted(layout[sample], key=WINDOW_ORDER.index):
            for step in sorted(layout[sample][window]):
                delta += 1.0
                write_spectrum_file(
                    folder / f"{sample}_{window}_{step_name(step)}.txt",
                    spectrum_body(window, delta),
                )
    return raw_root


def axis_for(raw_root: Path, window: str) -> np.ndarray:
    """Return the wave axis actually loaded for ``window``."""
    for spectrum in load_experiment(raw_root, EXPERIMENT):
        if spectrum.window == window:
            return spectrum.wave
    raise AssertionError(f"the fixture wrote no {window!r} spectra")


def write_configs(raw_root: Path, *, noise: bool = True) -> dict[str, object]:
    """Write ``bands.json`` and ``baseline.json``, derived off the real axis.

    Band centres and half-widths are read from the loaded wave arrays rather
    than written as literals, so the configuration cannot drift away from the
    data it describes.

    Returns:
        The ``bands.json`` payload, for tests that need to know what was asked.
    """
    folder = raw_root / EXPERIMENT
    present = {s.window for s in load_experiment(raw_root, EXPERIMENT)}
    windows = [w for w in WINDOW_ORDER if w in present]
    bands: dict[str, dict[str, object]] = {}
    regions: dict[str, list[float]] = {}
    for window in windows:
        wave = axis_for(raw_root, window)
        half_width = float(wave[HALF_WIDTH_POINTS] - wave[0])
        for name, index in zip(BAND_NAMES[window], PEAK_INDICES[window]):
            bands[name] = {
                "centre": float(wave[index]),
                "half_width": half_width,
                "window": window,
            }
        low_index, high_index = NOISE_INDICES
        regions[window] = [float(wave[low_index]), float(wave[high_index])]

    payload: dict[str, object] = {"reference": REFERENCE, "bands": bands}
    if noise:
        payload["noise_regions"] = regions
    (folder / BANDS_CONFIG_NAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (folder / BASELINE_CONFIG_NAME).write_text(
        json.dumps(BASELINE_PAYLOAD, indent=2), encoding="utf-8"
    )
    return payload


def run_quantify(
    raw_root: Path, out_root: Path, sample: str | None = None, force: bool = False
) -> list[dict[str, object]]:
    """Drive ``quantify_experiment`` exactly as ``main.py`` does.

    The baseline parameters are resolved through ``resolve_baseline_config``
    rather than invented here, mirroring ``main.py:106``, so the fixture's
    ``baseline.json`` genuinely determines what the correction uses.
    """
    spectra = load_experiment(raw_root, EXPERIMENT)
    values, sources = resolve_baseline_config(
        raw_root / EXPERIMENT, {s.window for s in spectra}
    )
    return quantify_experiment(
        EXPERIMENT,
        spectra,
        raw_root,
        out_root / "derived",
        out_root / "figures",
        values,
        sources,
        sample=sample,
        force=force,
    )


@pytest.fixture
def one_sample_both_windows(tmp_path: Path) -> Path:
    """The ordinary case: one sample, both windows, a control and two steps."""
    raw_root = build_experiment(tmp_path, {"sa": {LOW: [0, 1, 2], HIGH: [0, 1, 2]}})
    write_configs(raw_root)
    return raw_root


# ===========================================================================
# B1 - quantify_experiment, happy path
# ===========================================================================


def test_agg_backend_is_already_forced_by_importing_plotting() -> None:
    """The backend is fixed at import time; no test needs to set it.

    ``plotting.py`` calls ``matplotlib.use("Agg")`` before pyplot is imported,
    which is a documented, deliberate global side effect. Asserting it here
    verifies the guarantee without duplicating the mechanism.
    """
    import ramsess.plotting  # noqa: F401  - imported for its backend side effect

    assert matplotlib.get_backend().lower() == "agg"


def test_return_value_has_one_row_per_band_per_spectrum(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    raw_root = one_sample_both_windows
    rows = run_quantify(raw_root, tmp_path / "out")
    capsys.readouterr()

    spectra = load_experiment(raw_root, EXPERIMENT)
    bands_per_window = {w: len(BAND_NAMES[w]) for w in WINDOW_ORDER}
    expected = sum(bands_per_window[s.window] for s in spectra)
    assert len(rows) == expected

    # The row contract. Every consumer - the CSV writer, the summary printer and
    # both trend builders - reads these keys and nothing else.
    for row in rows:
        assert set(row) == set(BANDS_CSV_COLUMNS)

    assert {str(r["sample"]) for r in rows} == {s.sample for s in spectra}
    assert {int(r["step"]) for r in rows} == {s.step for s in spectra}
    assert {str(r["band"]) for r in rows} == set(BAND_NAMES[LOW]) | set(BAND_NAMES[HIGH])


def test_reference_normalises_to_one_and_cross_window_marks_the_other_window(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    rows = run_quantify(one_sample_both_windows, tmp_path / "out")
    capsys.readouterr()

    reference_window = next(w for w in WINDOW_ORDER if REFERENCE in BAND_NAMES[w])
    for row in rows:
        if row["band"] == REFERENCE:
            assert row["height_norm"] == 1.0
            assert row["area_norm"] == 1.0
        assert bool(row["cross_window"]) is (row["window"] != reference_window)


def test_measured_position_lands_on_the_configured_centre(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    """The fixture plants each peak at its band's centre, so drift is zero.

    This is the fixture checking itself: if it drifted, every flag assertion
    below would be measuring the fixture rather than the code.
    """
    rows = run_quantify(one_sample_both_windows, tmp_path / "out")
    capsys.readouterr()
    for row in rows:
        assert row["position"] == row["centre"]
        assert row["position_drift"] == 0.0
        assert row["at_edge"] is False
        assert float(row["signal_to_noise"]) > MIN_SIGNAL_TO_NOISE


def test_derived_spectra_are_written_with_the_expected_header_and_row_count(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    raw_root = one_sample_both_windows
    out_root = tmp_path / "out"
    run_quantify(raw_root, out_root)
    capsys.readouterr()

    spectra = load_experiment(raw_root, EXPERIMENT)
    derived = out_root / "derived" / EXPERIMENT
    for spectrum in spectra:
        path = derived / (
            f"{spectrum.sample}_{spectrum.window}_{spectrum.step}_corrected.txt"
        )
        assert path.is_file()
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == DERIVED_HEADER
        assert len(lines) == int(spectrum.wave.size) + 1
        for line in lines[1:]:
            assert len(line.split("\t")) == 3

    written = sorted(derived.glob("*_corrected.txt"))
    assert len(written) == len(spectra)


def test_derived_columns_still_reconstruct_the_raw_spectrum(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    """corrected + fitted baseline == raw, read back off the file on disk."""
    raw_root = one_sample_both_windows
    out_root = tmp_path / "out"
    run_quantify(raw_root, out_root)
    capsys.readouterr()

    derived = out_root / "derived" / EXPERIMENT
    for spectrum in load_experiment(raw_root, EXPERIMENT):
        table = np.loadtxt(
            derived
            / f"{spectrum.sample}_{spectrum.window}_{spectrum.step}_corrected.txt",
            comments="#",
            dtype=np.float64,
        )
        scale = float(np.max(np.abs(spectrum.intensity)))
        assert np.allclose(table[:, 0], spectrum.wave)
        assert np.max(np.abs(table[:, 1] + table[:, 2] - spectrum.intensity)) <= 1e-6 * scale


def test_provenance_records_every_source_file_and_names_baseline_json(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    """The parameters came from the fixture's baseline.json, and it says so."""
    raw_root = one_sample_both_windows
    out_root = tmp_path / "out"
    run_quantify(raw_root, out_root)
    capsys.readouterr()

    path = out_root / "derived" / EXPERIMENT / "provenance.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {
        "experiment",
        "generated_utc",
        "baseline_parameters",
        "source_files",
    }
    assert payload["experiment"] == EXPERIMENT

    spectra = load_experiment(raw_root, EXPERIMENT)
    assert len(payload["source_files"]) == len(spectra)
    assert {entry["name"] for entry in payload["source_files"]} == {
        s.path.name for s in spectra
    }
    for entry in payload["source_files"]:
        assert set(entry) == {"name", "sample", "window", "step", "sha256", "n_points"}
        assert len(entry["sha256"]) == 64

    recorded = payload["baseline_parameters"]
    assert set(recorded) == {s.window for s in spectra}
    for window, parameters in recorded.items():
        assert set(parameters) == {"lam", "p", "n_iter"}
        for key, entry in parameters.items():
            # Nothing fell back to a built-in default: baseline.json supplied
            # every value, which is what makes the fixture's file load-bearing.
            assert BASELINE_CONFIG_NAME in entry["source"]
    # The per-window override in the fixture beat the top level, for that window
    # and that parameter only.
    assert recorded[HIGH]["lam"]["value"] == BASELINE_PAYLOAD["windows"][HIGH]["lam"]
    assert recorded[LOW]["lam"]["value"] == BASELINE_PAYLOAD["lam"]


def test_bands_csv_has_the_expected_header_and_one_row_per_measurement(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    out_root = tmp_path / "out"
    rows = run_quantify(one_sample_both_windows, out_root)
    capsys.readouterr()

    path = out_root / "derived" / EXPERIMENT / "bands.csv"
    assert path.is_file()
    with path.open(encoding="utf-8", newline="") as handle:
        table = list(csv.reader(handle))
    assert table[0] == BANDS_CSV_COLUMNS
    assert len(table) - 1 == len(rows)


def test_every_figure_is_written_to_the_expected_path(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    out_root = tmp_path / "out"
    rows = run_quantify(one_sample_both_windows, out_root)
    capsys.readouterr()

    figures = out_root / "figures" / EXPERIMENT
    samples = sorted({str(r["sample"]) for r in rows})
    expected = {f"{name}_bands.png" for name in samples} | {"bands_all_samples.png"}
    assert {p.name for p in figures.iterdir()} == expected
    for path in figures.iterdir():
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_nothing_is_written_outside_the_roots_the_caller_owns(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    """Every artefact lands under tmp_path, and raw is left exactly as found."""
    raw_root = one_sample_both_windows
    out_root = tmp_path / "out"
    before_raw = tree_snapshot(raw_root)

    run_quantify(raw_root, out_root)
    capsys.readouterr()

    assert tree_snapshot(raw_root) == before_raw
    produced = [p for p in out_root.rglob("*") if p.is_file()]
    assert produced
    for path in produced:
        assert path.resolve().is_relative_to(tmp_path.resolve())
    # The repository trees are checked by the autouse repository_untouched
    # fixture, which covers B5 for every test in this file.


def test_stdout_announces_every_file_it_wrote(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    out_root = tmp_path / "out"
    rows = run_quantify(one_sample_both_windows, out_root)
    captured = capsys.readouterr()
    assert captured.err == ""

    derived = out_root / "derived" / EXPERIMENT
    figures = out_root / "figures" / EXPERIMENT
    spectra = load_experiment(one_sample_both_windows, EXPERIMENT)

    assert f"wrote {len(spectra)} corrected spectra to {derived}" in captured.out
    assert "worst reconstruction residual on read-back:" in captured.out
    assert f"wrote {derived / 'provenance.json'}" in captured.out
    assert f"wrote {derived / 'bands.csv'}   {len(rows)} measurement(s)" in captured.out
    for name in sorted({str(r["sample"]) for r in rows}):
        assert f"wrote {figures / f'{name}_bands.png'}" in captured.out
    assert f"wrote {figures / 'bands_all_samples.png'}" in captured.out
    for window in sorted({s.window for s in spectra}):
        assert f"  noise region for {window}: [" in captured.out


def test_without_noise_regions_it_says_so_rather_than_guessing(
    tmp_path: Path, capsys
) -> None:
    raw_root = build_experiment(tmp_path, {"sa": {LOW: [0, 1], HIGH: [0, 1]}})
    write_configs(raw_root, noise=False)
    rows = run_quantify(raw_root, tmp_path / "out")
    captured = capsys.readouterr()

    assert (
        f"  no noise_regions configured in {BANDS_CONFIG_NAME}; "
        f"signal-to-noise will not be computed" in captured.out
    )
    assert all(row["noise"] is None for row in rows)
    assert all(row["signal_to_noise"] is None for row in rows)


def test_noise_region_notices_print_in_physical_window_order(
    one_sample_both_windows: Path, tmp_path: Path, capsys
) -> None:
    """Low before high, like every other window ordering in this codebase.

    Asserts POSITION, not membership. ``test_stdout_announces_every_file_it_wrote``
    already checks each notice appears, and would pass in any order; this is the
    one that pins the order. Alphabetical sorting puts 'high' first, which
    contradicts the rule that windows sort physically and never alphabetically.
    Nothing here names a window: the expected order is read from WINDOW_ORDER.
    """
    run_quantify(one_sample_both_windows, tmp_path / "out")
    lines = capsys.readouterr().out.split("\n")

    positions = []
    for window in WINDOW_ORDER:
        found = [
            i
            for i, line in enumerate(lines)
            if line.startswith(f"  noise region for {window}:")
        ]
        assert len(found) == 1, f"expected exactly one notice for {window!r}, got {found}"
        positions.append(found[0])

    assert positions == sorted(positions), (
        f"noise-region notices are out of physical order: "
        f"{list(zip(WINDOW_ORDER, positions))}. WINDOW_ORDER is {WINDOW_ORDER}, "
        f"so {WINDOW_ORDER[0]!r} must print before {WINDOW_ORDER[1]!r}."
    )


# ===========================================================================
# B2 - quantify_experiment, edge cases
# ===========================================================================


def test_a_gap_in_the_step_sequence_is_measured_not_rejected(
    tmp_path: Path, capsys
) -> None:
    """A missing step in each window, as ech3 has. Soft, so it never gates."""
    present = [0, 1, 3, 4]
    missing = 2
    raw_root = build_experiment(tmp_path, {"sa": {LOW: present, HIGH: present}})
    write_configs(raw_root)

    rows = run_quantify(raw_root, tmp_path / "out")
    capsys.readouterr()

    assert sorted({int(r["step"]) for r in rows}) == present
    assert missing not in {int(r["step"]) for r in rows}
    # The figure still gets written; the gap shows as a gap because steps are
    # placed at their actual value.
    assert (tmp_path / "out" / "figures" / EXPERIMENT / "sa_bands.png").is_file()


def test_a_controls_only_sample_is_measured_as_a_single_point(
    tmp_path: Path, capsys
) -> None:
    raw_root = build_experiment(
        tmp_path,
        {"sa": {LOW: [0], HIGH: [0]}, "sb": {LOW: [0, 1], HIGH: [0, 1]}},
    )
    write_configs(raw_root)

    rows = run_quantify(raw_root, tmp_path / "out")
    capsys.readouterr()

    controls_only = [r for r in rows if r["sample"] == "sa"]
    assert controls_only
    assert {int(r["step"]) for r in controls_only} == {0}
    figures = tmp_path / "out" / "figures" / EXPERIMENT
    assert (figures / "sa_bands.png").is_file()
    # bands_all_samples.png includes the controls-only sample, as a single point.
    assert (figures / "bands_all_samples.png").is_file()


def test_a_sample_missing_the_non_reference_window_simply_has_fewer_rows(
    tmp_path: Path, capsys
) -> None:
    """Case (a) of the one-window sample: nothing else changes.

    The reference lives in the other window, so normalisation is unaffected and
    the sample just contributes no rows for the absent window's bands.
    """
    absent = next(w for w in WINDOW_ORDER if REFERENCE not in BAND_NAMES[w])
    kept = next(w for w in WINDOW_ORDER if w != absent)
    raw_root = build_experiment(
        tmp_path,
        {"sa": {kept: [0, 1]}, "sb": {LOW: [0, 1], HIGH: [0, 1]}},
    )
    write_configs(raw_root)

    rows = run_quantify(raw_root, tmp_path / "out")
    capsys.readouterr()

    mine = [r for r in rows if r["sample"] == "sa"]
    assert mine
    assert {str(r["window"]) for r in mine} == {kept}
    assert {str(r["band"]) for r in mine} == set(BAND_NAMES[kept])
    # Normalisation is untouched: the reference is present for this sample.
    assert all(r["height_norm"] is not None for r in mine)


def test_sample_missing_the_reference_window_normalises_to_none_pending_items_2_and_3(
    tmp_path: Path, capsys
) -> None:
    """Case (b): no reference measurement, so every normalised value is None.

    This is the exact path pending items 2 and 3 will change - making
    ``reference`` optional, and reworking the summary table. Current behaviour:
    no exception, rows are still produced and still written to bands.csv, but
    ``height_norm`` and ``area_norm`` are None for every row of this sample, the
    summary prints '-' in those cells, and the trend figure draws an all-NaN
    series. Asserted as it stands, not endorsed.
    """
    reference_window = next(w for w in WINDOW_ORDER if REFERENCE in BAND_NAMES[w])
    other = next(w for w in WINDOW_ORDER if w != reference_window)
    raw_root = build_experiment(
        tmp_path,
        {"sa": {other: [0, 1]}, "sb": {LOW: [0, 1], HIGH: [0, 1]}},
    )
    write_configs(raw_root)

    out_root = tmp_path / "out"
    rows = run_quantify(raw_root, out_root)
    captured = capsys.readouterr()

    mine = [r for r in rows if r["sample"] == "sa"]
    assert mine
    assert all(r["height_norm"] is None for r in mine)
    assert all(r["area_norm"] is None for r in mine)
    # The raw measurement itself is still real; only the ratio is missing.
    assert all(isinstance(r["height"], float) for r in mine)

    # It is written and drawn regardless, with no warning of its own.
    assert (out_root / "figures" / EXPERIMENT / "sa_bands.png").is_file()
    with (out_root / "derived" / EXPERIMENT / "bands.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        table = {(r["sample"], r["band"], r["step"]): r for r in csv.DictReader(handle)}
    for row in mine:
        stored = table[(str(row["sample"]), str(row["band"]), str(row["step"]))]
        assert stored["height_norm"] == ""
        assert stored["area_norm"] == ""

    # The summary renders the missing ratio as the same '-' it uses for a band
    # that was never measured, so the two cases are indistinguishable on stdout.
    assert "-" in captured.out


def rewrite_bands_config(raw_root: Path, payload: dict[str, object]) -> None:
    """Overwrite the experiment's bands.json with a deliberately bad payload."""
    (raw_root / EXPERIMENT / BANDS_CONFIG_NAME).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def assert_nothing_was_written(out_root: Path) -> None:
    """Assert a failed run left no derived tree and no figures at all.

    Not "no bands.csv" - nothing. Not even the directory. A derived tree that
    exists is one whose measurements completed, so there is no half-finished
    state that could be mistaken for a successful export.
    """
    assert not (out_root / "derived").exists()
    assert not (out_root / "figures").exists()
    assert [p for p in out_root.rglob("*") if p.is_file()] == []


def test_a_band_outside_the_wave_range_fails_before_anything_is_written(
    tmp_path: Path, capsys
) -> None:
    """The guarantee: a bad band centre costs nothing and leaves nothing.

    Caught by ``load_bands_config`` against the range every file of that window
    shares, so the message can name the config file and the band. Even if it
    were not, the export now runs after measurement, so a failure could not
    leave a derived tree behind.
    """
    raw_root = build_experiment(tmp_path, {"sa": {LOW: [0, 1], HIGH: [0, 1]}})
    payload = write_configs(raw_root)

    wave = axis_for(raw_root, LOW)
    low, high = float(wave.min()), float(wave.max())
    beyond = high + (high - low)
    payload["bands"][REFERENCE]["centre"] = beyond
    half_width = payload["bands"][REFERENCE]["half_width"]
    rewrite_bands_config(raw_root, payload)

    out_root = tmp_path / "out"
    with pytest.raises(ValueError) as excinfo:
        run_quantify(raw_root, out_root)
    capsys.readouterr()

    message = str(excinfo.value)
    # All five elements: the config file, the band, the window, the search
    # window asked for, and the range actually available.
    assert BANDS_CONFIG_NAME in message
    assert f"bands.{REFERENCE}" in message
    assert f"{LOW!r}" in message
    assert f"[{beyond - half_width:.3f}, {beyond + half_width:.3f}]" in message
    assert f"[{low:.3f}, {high:.3f}]" in message
    assert "falls outside the measured range" in message

    assert_nothing_was_written(out_root)


def test_a_band_window_holding_too_few_points_fails_before_anything_is_written(
    tmp_path: Path, capsys
) -> None:
    """The case validation cannot catch, which only the ordering fixes.

    A search window fully inside the data range but narrower than
    ``MIN_POINTS`` samples passes every check in ``load_bands_config`` and
    fails inside ``measure_band``. Because measurement now runs before the
    export, that late failure still leaves nothing behind - which is the whole
    point of ordering the writes rather than enumerating the ways config can be
    wrong.
    """
    raw_root = build_experiment(tmp_path, {"sa": {LOW: [0, 1], HIGH: [0, 1]}})
    payload = write_configs(raw_root)

    wave = axis_for(raw_root, LOW)
    # Narrower than one point spacing, so the window spans at most three
    # samples - comfortably under MIN_POINTS - while staying well inside the
    # data range, which is what makes this distinct from the test above.
    payload["bands"][REFERENCE]["half_width"] = float(wave[1] - wave[0]) * 0.9
    rewrite_bands_config(raw_root, payload)

    out_root = tmp_path / "out"
    with pytest.raises(ValueError) as excinfo:
        run_quantify(raw_root, out_root)
    capsys.readouterr()

    message = str(excinfo.value)
    assert "fewer than the minimum" in message
    # Confirms it got past config loading: this is the late check firing, not
    # the early one.
    assert "falls outside the measured range" not in message

    assert_nothing_was_written(out_root)


# ===========================================================================
# ADD-1 - the sample= filter's asymmetric scope
# ===========================================================================


def test_sample_filter_restricts_measurement_but_not_the_export(
    tmp_path: Path, capsys
) -> None:
    """Deliberate and documented, and on the list to revisit. Locked in here.

    ``write_derived_spectra`` and ``write_provenance`` run on the full spectra
    list before the filter is applied, so provenance.json describes the whole
    experiment rather than a partial tree. If that ever changes, this goes red.
    """
    layout = {
        "sa": {LOW: [0, 1], HIGH: [0, 1]},
        "sb": {LOW: [0, 1], HIGH: [0, 1]},
        "sc": {LOW: [0, 1], HIGH: [0, 1]},
    }
    raw_root = build_experiment(tmp_path, layout)
    write_configs(raw_root)
    wanted = sorted(layout)[1]

    out_root = tmp_path / "out"
    rows = run_quantify(raw_root, out_root, sample=wanted)
    capsys.readouterr()

    spectra = load_experiment(raw_root, EXPERIMENT)
    derived = out_root / "derived" / EXPERIMENT

    # (a) corrected spectra exist for every sample, not only the requested one.
    assert len(sorted(derived.glob("*_corrected.txt"))) == len(spectra)
    for sample in sorted(layout):
        assert sorted(derived.glob(f"{sample}_*_corrected.txt"))
    payload = json.loads((derived / "provenance.json").read_text(encoding="utf-8"))
    assert {entry["sample"] for entry in payload["source_files"]} == set(layout)

    # (b) measurement covers only the requested sample.
    assert {str(r["sample"]) for r in rows} == {wanted}
    with (derived / "bands.csv").open(encoding="utf-8", newline="") as handle:
        table = list(csv.DictReader(handle))
    assert {entry["sample"] for entry in table} == {wanted}
    assert len(table) == len(rows)

    # (c) exactly one per-sample figure, plus the all-samples one.
    figures = out_root / "figures" / EXPERIMENT
    assert {p.name for p in figures.iterdir()} == {
        f"{wanted}_bands.png",
        "bands_all_samples.png",
    }


def test_an_unknown_sample_raises_naming_the_available_samples(
    tmp_path: Path, capsys
) -> None:
    layout = {"sa": {LOW: [0], HIGH: [0]}, "sb": {LOW: [0], HIGH: [0]}}
    raw_root = build_experiment(tmp_path, layout)
    write_configs(raw_root)

    with pytest.raises(ValueError) as excinfo:
        run_quantify(raw_root, tmp_path / "out", sample="no_such_sample")
    capsys.readouterr()

    message = str(excinfo.value)
    assert "sample 'no_such_sample' not found in experiment" in message
    assert EXPERIMENT in message
    for sample in sorted(layout):
        assert sample in message


# ===========================================================================
# B5 - the regression, standing alone as well as autouse
# ===========================================================================


def test_quantify_against_tmp_path_writes_nothing_into_the_repository(
    tmp_path: Path, capsys
) -> None:
    """Explicit form of what the autouse fixture enforces everywhere else."""
    raw_root = build_experiment(tmp_path, {"sa": {LOW: [0, 1], HIGH: [0, 1]}})
    write_configs(raw_root)

    watched = [PROJECT_ROOT / "data", PROJECT_ROOT / "figures"]
    before = {str(root): tree_snapshot(root) for root in watched}

    run_quantify(raw_root, tmp_path / "out")
    capsys.readouterr()

    for root in watched:
        assert tree_snapshot(root) == before[str(root)]
    assert not (PROJECT_ROOT / "figures" / EXPERIMENT).exists()
    assert not (PROJECT_ROOT / "data" / "derived" / EXPERIMENT).exists()
