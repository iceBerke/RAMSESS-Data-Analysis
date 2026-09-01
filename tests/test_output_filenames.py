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
from ramsess.report import (
    ANNOTATED_SUFFIX,
    LOG_SCALE_SUFFIX,
    REFERENCE_EXCLUDED_SUFFIX,
    BandSpec,
    write_sample_overlays,
)

BASELINE = {
    "low": {"lam": 1e6, "p": 0.01, "n_iter": 10},
    "high": {"lam": 1e8, "p": 0.01, "n_iter": 10},
}

# Bands inside the synthetic windows built below. Two of the low ones sit close
# enough together to need a second label row, so the annotated runs exercise the
# row-stacking path rather than only the easy case.
BANDS = {
    "a": BandSpec(name="a", centre=230.0, half_width=5.0, window="low"),
    "b": BandSpec(name="b", centre=240.0, half_width=5.0, window="low"),
    "c": BandSpec(name="c", centre=290.0, half_width=5.0, window="low"),
    "d": BandSpec(name="d", centre=2420.0, half_width=5.0, window="high"),
    "e": BandSpec(name="e", centre=2470.0, half_width=5.0, window="high"),
    # `peaked` puts its one tall peak at 257.75 in the low window. This band
    # sits on it and is the reference, so excluding it genuinely lowers the low
    # panel's limit - otherwise every exclusion run would be a silent no-op and
    # the tests below would pass without exercising anything.
    "ref": BandSpec(name="ref", centre=257.75, half_width=5.0, window="low"),
}
REFERENCE = "ref"

# baseline, diagnostic, logy, annotate, exclude_reference
COMBINATIONS = list(itertools.product([False, True], repeat=5))


def peaked(start: float, spacing: float, n: int, peaks: dict[int, float], base: float):
    """A spectrum with peaks at named sample indices, over a flat baseline.

    More than one peak matters for the exclusion runs: baseline correction
    flattens everything that is not a peak to about zero, so a spectrum whose
    only peak is the excluded one leaves nothing positive behind and the
    exclusion correctly refuses to scale to it.
    """
    lines, wave = [], start
    for i in range(n):
        wave += spacing * (1.0 + 0.1 * (i % 3))
        lines.append(f"{wave:.6f}\t{base * (1.0 + peaks.get(i, 0.0)):.6f}")
    return lines


def build_experiment(root: Path) -> Path:
    """Write one sample, both windows, three steps, under ``root``."""
    from conftest import write_spectrum_file

    folder = root / "raw" / "exp"
    folder.mkdir(parents=True, exist_ok=True)
    for index, step in enumerate(("0", "irr1", "irr2")):
        write_spectrum_file(
            folder / f"s_low_{step}.txt",
            # index 20 is wave 257.750, inside the reference band; index 32 is
            # 290.750, inside band "c" and left standing when the reference goes.
            vary(peaked(200.0, 2.5, 40, {20: 20.0, 32: 4.0}, 1000.0), index),
        )
        write_spectrum_file(
            folder / f"s_high_{step}.txt",
            vary(peaked(2400.0, 2.0, 40, {20: 20.0}, 5000.0), index),
        )
    return root / "raw"


def run(
    spectra,
    root: Path,
    baseline: bool,
    diagnostic: bool,
    logy: bool,
    annotate: bool,
    exclude_reference: bool,
):
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
            annotate=annotate,
            bands=BANDS if (annotate or exclude_reference) else None,
            reference=REFERENCE if exclude_reference else None,
            exclude_reference=exclude_reference,
        )
    return {path.name: path.read_bytes() for path in written}


@pytest.fixture(scope="module")
def spectra(tmp_path_factory):
    """One sample, both windows, three steps. Module-scoped: built once."""
    return load_experiment(build_experiment(tmp_path_factory.mktemp("combos")), "exp")


@pytest.fixture(scope="module")
def all_runs(spectra, tmp_path_factory):
    """Every combination, each into an isolated directory so none can clobber.

    Module-scoped because rendering thirty-two combinations is the slow part of
    this module; running it once per test would multiply that by the test count
    for no extra coverage.
    """
    root = tmp_path_factory.mktemp("runs")
    return {
        (baseline, diagnostic, logy, annotate, exclude): run(
            spectra,
            root / f"out_{int(baseline)}{int(diagnostic)}{int(logy)}{int(annotate)}{int(exclude)}",
            baseline,
            diagnostic,
            logy,
            annotate,
            exclude,
        )
        for baseline, diagnostic, logy, annotate, exclude in COMBINATIONS
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
    linear = all_runs[(False, False, False, False, False)]
    log = all_runs[(False, False, True, False, False)]
    assert set(linear) == {"s_overlay.png"}
    assert set(log) == {f"s_overlay{LOG_SCALE_SUFFIX}.png"}
    assert set(linear).isdisjoint(log), "a log run must not land on the raw filename"


def test_log_and_linear_baseline_overlays_are_separate_files(all_runs) -> None:
    linear = all_runs[(True, False, False, False, False)]
    log = all_runs[(True, False, True, False, False)]
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
    assert producers == [(False, False, False, False, False)]


def test_diagnostic_filenames_carry_no_scale_suffix(all_runs) -> None:
    """logy does not reach the diagnostic figure, so it must not appear in its name."""
    for combination, outputs in all_runs.items():
        for name in outputs:
            if "baseline_check" in name:
                assert LOG_SCALE_SUFFIX not in name


def test_logy_is_a_no_op_for_the_diagnostic_figure(all_runs) -> None:
    """Documented behaviour: --logy changes nothing about the diagnostic."""
    without = {k: v for k, v in all_runs[(False, True, False, False, False)].items() if "check" in k}
    with_logy = {k: v for k, v in all_runs[(False, True, True, False, False)].items() if "check" in k}
    assert without and with_logy
    assert without == with_logy


@pytest.mark.parametrize(
    "baseline,logy,plain_name,annotated_name",
    [
        (False, False, "s_overlay.png", f"s_overlay{ANNOTATED_SUFFIX}.png"),
        (
            False,
            True,
            f"s_overlay{LOG_SCALE_SUFFIX}.png",
            f"s_overlay{ANNOTATED_SUFFIX}{LOG_SCALE_SUFFIX}.png",
        ),
        (
            True,
            False,
            "s_overlay_baseline.png",
            f"s_overlay_baseline{ANNOTATED_SUFFIX}.png",
        ),
        (
            True,
            True,
            f"s_overlay_baseline{LOG_SCALE_SUFFIX}.png",
            f"s_overlay_baseline{ANNOTATED_SUFFIX}{LOG_SCALE_SUFFIX}.png",
        ),
    ],
)
def test_annotating_changes_the_figure_and_its_name(
    all_runs, baseline: bool, logy: bool, plain_name: str, annotated_name: str
) -> None:
    """Annotation must actually draw something, under its own name.

    Both halves matter. A name that changed while the pixels did not would mean
    the flag renamed the output and drew nothing, which no filename test would
    catch on its own.
    """
    plain = all_runs[(baseline, False, logy, False, False)]
    annotated = all_runs[(baseline, False, logy, True, False)]
    assert set(plain) == {plain_name}
    assert set(annotated) == {annotated_name}
    assert annotated[annotated_name] != plain[plain_name], (
        f"{annotated_name} holds the same pixels as {plain_name}: --annotate "
        f"changed the filename but drew no labels"
    )


def test_an_annotated_run_never_writes_an_unannotated_overlay(all_runs) -> None:
    """The six reference overlays must be unreachable from an annotated run."""
    unannotated = {
        "s_overlay.png",
        f"s_overlay{LOG_SCALE_SUFFIX}.png",
        "s_overlay_baseline.png",
        f"s_overlay_baseline{LOG_SCALE_SUFFIX}.png",
    }
    for combination, outputs in all_runs.items():
        if not combination[3]:
            continue
        assert unannotated.isdisjoint(outputs), (
            f"{combination} carries --annotate yet wrote "
            f"{sorted(unannotated & set(outputs))}"
        )


def test_annotation_does_not_reach_the_diagnostic_figure(all_runs) -> None:
    """--annotate takes no effect there, so the bytes must be identical."""
    without = {k: v for k, v in all_runs[(False, True, False, False, False)].items() if "check" in k}
    annotated = {k: v for k, v in all_runs[(False, True, False, True, False)].items() if "check" in k}
    assert without and annotated
    assert without == annotated


@pytest.mark.parametrize(
    "baseline,logy,plain_name,excluded_name",
    [
        (False, False, "s_overlay.png", f"s_overlay{REFERENCE_EXCLUDED_SUFFIX}.png"),
        (
            False,
            True,
            f"s_overlay{LOG_SCALE_SUFFIX}.png",
            f"s_overlay{REFERENCE_EXCLUDED_SUFFIX}{LOG_SCALE_SUFFIX}.png",
        ),
        (
            True,
            False,
            "s_overlay_baseline.png",
            f"s_overlay_baseline{REFERENCE_EXCLUDED_SUFFIX}.png",
        ),
        (
            True,
            True,
            f"s_overlay_baseline{LOG_SCALE_SUFFIX}.png",
            f"s_overlay_baseline{REFERENCE_EXCLUDED_SUFFIX}{LOG_SCALE_SUFFIX}.png",
        ),
    ],
)
def test_excluding_the_reference_changes_the_figure_and_its_name(
    all_runs, baseline: bool, logy: bool, plain_name: str, excluded_name: str
) -> None:
    """The excluded run writes its own name, and different pixels under it.

    This does NOT prove the panel was rescaled: the title also changes, and a
    build that renamed the file and retitled it while rescaling nothing passes
    here. Verified by making the rescale a no-op - every assertion below still
    held. ``tests/test_scale_exclusion.py`` carries the test that fails in that
    case, by checking the excluded band ends up above the panel's limit.
    """
    plain = all_runs[(baseline, False, logy, False, False)]
    excluded = all_runs[(baseline, False, logy, False, True)]
    assert set(plain) == {plain_name}
    assert set(excluded) == {excluded_name}
    assert excluded[excluded_name] != plain[plain_name], (
        f"{excluded_name} holds the same pixels as {plain_name}: the exclusion "
        f"changed the filename but drew nothing differently"
    )


def test_an_excluded_run_never_writes_an_unexcluded_overlay(all_runs) -> None:
    """The six reference overlays must be unreachable from an excluded run."""
    unexcluded = {
        "s_overlay.png",
        f"s_overlay{LOG_SCALE_SUFFIX}.png",
        "s_overlay_baseline.png",
        f"s_overlay_baseline{LOG_SCALE_SUFFIX}.png",
        f"s_overlay{ANNOTATED_SUFFIX}.png",
        f"s_overlay{ANNOTATED_SUFFIX}{LOG_SCALE_SUFFIX}.png",
    }
    for combination, outputs in all_runs.items():
        if not combination[4]:
            continue
        assert unexcluded.isdisjoint(outputs), (
            f"{combination} carries the exclusion yet wrote "
            f"{sorted(unexcluded & set(outputs))}"
        )


def test_the_exclusion_does_not_reach_the_diagnostic_figure(all_runs) -> None:
    """It takes no effect there, so the bytes must be identical."""
    without = {
        k: v for k, v in all_runs[(False, True, False, False, False)].items() if "check" in k
    }
    excluded = {
        k: v for k, v in all_runs[(False, True, False, False, True)].items() if "check" in k
    }
    assert without and excluded
    assert without == excluded


def test_every_combination_writes_something(all_runs) -> None:
    for combination, outputs in all_runs.items():
        assert outputs, f"{combination} produced no output at all"


def test_a_baseline_run_never_writes_the_raw_figure(spectra, tmp_path) -> None:
    """Running every combination into one shared directory, raw survives intact."""
    shared = tmp_path / "shared"
    raw_bytes = run(spectra, shared, False, False, False, False, False)["s_overlay.png"]
    for baseline, diagnostic, logy, annotate, exclude in COMBINATIONS:
        if not any((baseline, diagnostic, logy, annotate, exclude)):
            continue
        run(spectra, shared, baseline, diagnostic, logy, annotate, exclude)
    survivor = (shared / "exp" / "s_overlay.png").read_bytes()
    assert survivor == raw_bytes, "another combination overwrote the raw figure"
