"""No flag combination can overwrite another's output.

The exact property, which is stronger than "every combination gets its own
name": **the same path always means the same bytes**. Two combinations may share
a filename only when what they draw is provably identical - the diagnostic
figure takes no ``logy`` and does not depend on the ``baseline`` flag, so those
runs produce the same file. Any combination whose content differs must land on a
different path.

Everything is written to ``tmp_path``. The project's ``figures/`` tree is never
touched.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from conftest import vary
from ramsess.io import load_experiment
from ramsess.report import LOG_SCALE_SUFFIX, write_sample_overlays

BASELINE = {
    "low": {"lam": 1e6, "p": 0.01, "n_iter": 10},
    "high": {"lam": 1e8, "p": 0.01, "n_iter": 10},
}
COMBINATIONS = list(itertools.product([False, True], repeat=3))  # baseline, diagnostic, logy


def peaked(start: float, spacing: float, n: int, peak_at: int, base: float) -> list[str]:
    """A spectrum with a strong peak, so log-scaled panels have positive data."""
    lines, wave = [], start
    for i in range(n):
        wave += spacing * (1.0 + 0.1 * (i % 3))
        lines.append(f"{wave:.6f}\t{base + (base * 20.0 if i == peak_at else 0.0):.6f}")
    return lines


def build_experiment(root: Path) -> Path:
    """Write one sample, both windows, three steps, under ``root``."""
    from conftest import write_spectrum_file

    folder = root / "raw" / "exp"
    folder.mkdir(parents=True, exist_ok=True)
    for index, step in enumerate(("0", "irr1", "irr2")):
        write_spectrum_file(
            folder / f"s_low_{step}.txt",
            vary(peaked(200.0, 2.5, 40, 20, 1000.0), index),
        )
        write_spectrum_file(
            folder / f"s_high_{step}.txt",
            vary(peaked(2400.0, 2.0, 40, 20, 5000.0), index),
        )
    return root / "raw"


def run(spectra, root: Path, baseline: bool, diagnostic: bool, logy: bool):
    """Run one flag combination into its own output root, return {name: bytes}."""
    import contextlib
    import io as _io

    with contextlib.redirect_stdout(_io.StringIO()):
        written = write_sample_overlays(
            "exp",
            spectra,
            root,
            logy=logy,
            baseline=baseline,
            diagnostic=diagnostic,
            baseline_params=BASELINE if (baseline or diagnostic) else None,
        )
    return {path.name: path.read_bytes() for path in written}


@pytest.fixture(scope="module")
def spectra(tmp_path_factory):
    """One sample, both windows, three steps. Module-scoped: built once."""
    return load_experiment(build_experiment(tmp_path_factory.mktemp("combos")), "exp")


@pytest.fixture(scope="module")
def all_runs(spectra, tmp_path_factory):
    """Every combination, each into an isolated directory so none can clobber.

    Module-scoped because rendering eight combinations is the slow part of this
    module; running it once per test would multiply that by the test count for
    no extra coverage.
    """
    root = tmp_path_factory.mktemp("runs")
    return {
        (baseline, diagnostic, logy): run(
            spectra,
            root / f"out_{int(baseline)}{int(diagnostic)}{int(logy)}",
            baseline,
            diagnostic,
            logy,
        )
        for baseline, diagnostic, logy in COMBINATIONS
    }


def test_same_filename_always_means_identical_bytes(all_runs) -> None:
    """The core guarantee. A shared name must never mean different content."""
    by_name: dict[str, list[tuple[tuple[bool, bool, bool], bytes]]] = {}
    for combination, outputs in all_runs.items():
        for name, payload in outputs.items():
            by_name.setdefault(name, []).append((combination, payload))

    for name, entries in sorted(by_name.items()):
        first_combination, first_payload = entries[0]
        for combination, payload in entries[1:]:
            assert payload == first_payload, (
                f"{name} differs between {first_combination} and {combination}: "
                f"one flag combination would overwrite the other's output"
            )


def test_differing_content_always_gets_a_different_path(all_runs) -> None:
    """The converse: no two runs produce different bytes under one name."""
    payload_to_names: dict[bytes, set[str]] = {}
    for outputs in all_runs.values():
        for name, payload in outputs.items():
            payload_to_names.setdefault(payload, set()).add(name)
    for names in payload_to_names.values():
        assert len(names) == 1, f"identical content written under several names: {names}"


def test_log_and_linear_overlays_are_separate_files(all_runs) -> None:
    linear = all_runs[(False, False, False)]
    log = all_runs[(False, False, True)]
    assert set(linear) == {"s_overlay.png"}
    assert set(log) == {f"s_overlay{LOG_SCALE_SUFFIX}.png"}
    assert set(linear).isdisjoint(log), "a log run must not land on the raw filename"


def test_log_and_linear_baseline_overlays_are_separate_files(all_runs) -> None:
    linear = all_runs[(True, False, False)]
    log = all_runs[(True, False, True)]
    assert set(linear) == {"s_overlay_baseline.png"}
    assert set(log) == {f"s_overlay_baseline{LOG_SCALE_SUFFIX}.png"}
    assert set(linear).isdisjoint(log)


def test_the_raw_filename_is_produced_only_by_the_raw_combination(all_runs) -> None:
    """The six reference figures may only ever be written by plain plot."""
    producers = [
        combination
        for combination, outputs in all_runs.items()
        if "s_overlay.png" in outputs
    ]
    assert producers == [(False, False, False)]


def test_diagnostic_filenames_carry_no_scale_suffix(all_runs) -> None:
    """logy does not reach the diagnostic figure, so it must not appear in its name."""
    for combination, outputs in all_runs.items():
        for name in outputs:
            if "baseline_check" in name:
                assert LOG_SCALE_SUFFIX not in name


def test_logy_is_a_no_op_for_the_diagnostic_figure(all_runs) -> None:
    """Documented behaviour: --logy changes nothing about the diagnostic."""
    without = {k: v for k, v in all_runs[(False, True, False)].items() if "check" in k}
    with_logy = {k: v for k, v in all_runs[(False, True, True)].items() if "check" in k}
    assert without and with_logy
    assert without == with_logy


def test_every_combination_writes_something(all_runs) -> None:
    for combination, outputs in all_runs.items():
        assert outputs, f"{combination} produced no output at all"


def test_a_baseline_run_never_writes_the_raw_figure(spectra, tmp_path) -> None:
    """Running every combination into one shared directory, raw survives intact."""
    shared = tmp_path / "shared"
    raw_bytes = run(spectra, shared, False, False, False)["s_overlay.png"]
    for baseline, diagnostic, logy in COMBINATIONS:
        if not baseline and not diagnostic and not logy:
            continue
        run(spectra, shared, baseline, diagnostic, logy)
    survivor = (shared / "exp" / "s_overlay.png").read_bytes()
    assert survivor == raw_bytes, "another combination overwrote the raw figure"
