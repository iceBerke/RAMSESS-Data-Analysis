"""Each check fires with the right severity, and gating acts on HARD only."""

from __future__ import annotations

import pytest

from conftest import shift_wave, spectrum_lines, vary
from ramsess.io import group_spectra, load_experiment
from ramsess.report import (
    HARD,
    SOFT,
    HardCheckFailure,
    collect_warnings,
    hard_failures,
    preflight,
)


def findings_for(raw_root, experiment: str = "exp"):
    """Load an experiment and collect its findings."""
    spectra = load_experiment(raw_root, experiment)
    return spectra, collect_warnings(spectra, group_spectra(spectra))


def severity_of(findings, fragment: str) -> str:
    """Return the severity of the single finding containing ``fragment``."""
    matches = [sev for sev, msg in findings if fragment in msg]
    assert matches, f"no finding matching {fragment!r} in {[m for _, m in findings]}"
    assert len(matches) == 1, f"{fragment!r} matched {len(matches)} findings"
    return matches[0]


def messages(findings) -> list[str]:
    return [msg for _, msg in findings]


@pytest.fixture
def clean_files(low_lines, high_lines):
    """Three distinct low files and three distinct high files, all valid."""
    return {
        "s_low_0.txt": vary(low_lines, 0),
        "s_low_irr1.txt": vary(low_lines, 1),
        "s_low_irr2.txt": vary(low_lines, 2),
        "s_high_0.txt": vary(high_lines, 0),
        "s_high_irr1.txt": vary(high_lines, 1),
        "s_high_irr2.txt": vary(high_lines, 2),
    }


def test_clean_experiment_has_no_findings(make_experiment, clean_files) -> None:
    _, findings = findings_for(make_experiment(clean_files))
    assert findings == [], f"unexpected findings: {messages(findings)}"


# --- SOFT checks -----------------------------------------------------------


def test_step_gap_is_soft(make_experiment, clean_files) -> None:
    files = dict(clean_files)
    files["s_low_irr3.txt"] = files.pop("s_low_irr2.txt")
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s low: gap in step sequence, missing [2]") == SOFT


def test_missing_control_is_soft(make_experiment, clean_files) -> None:
    files = dict(clean_files)
    files["s_low_irr3.txt"] = files.pop("s_low_0.txt")
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s low: no control (step 0)") == SOFT


def test_single_window_sample_is_soft(make_experiment, clean_files) -> None:
    files = {k: v for k, v in clean_files.items() if "_low_" in k}
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s: present in only one window (low)") == SOFT


def test_missing_header_is_soft(make_experiment, clean_files) -> None:
    files = dict(clean_files)
    files["s_low_0.txt"] = (files["s_low_0.txt"], False)
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s_low_0.txt: no '#' header line") == SOFT


def test_sub_threshold_precision_difference_is_soft(make_experiment, clean_files) -> None:
    """A 0.005 shift is the known low-precision export quirk, not a mismatch."""
    files = dict(clean_files)
    files["s_low_irr1.txt"] = shift_wave(files["s_low_irr1.txt"], 0.005)
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s low: wave axes differ by 0.005") == SOFT


def test_too_few_files_for_a_mode_is_soft(make_experiment, low_lines, high_lines) -> None:
    files = {
        "s_low_0.txt": vary(low_lines, 0),
        "s_low_irr1.txt": vary(low_lines, 1),
        "s_low_irr2.txt": vary(low_lines, 2),
        "s_high_0.txt": vary(high_lines, 0),
        "s_high_irr1.txt": vary(high_lines, 1),
    }
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "high: only 2 file(s) carry this window label") == SOFT


# --- HARD checks -----------------------------------------------------------


def test_duplicate_content_is_hard(make_experiment, clean_files) -> None:
    files = dict(clean_files)
    files["s_low_irr2.txt"] = files["s_low_irr1.txt"]
    _, findings = findings_for(make_experiment(files))
    severity = severity_of(findings, "identical file contents")
    assert severity == HARD
    message = next(m for m in messages(findings) if "identical file contents" in m)
    assert "s_low_irr1.txt" in message and "s_low_irr2.txt" in message


def test_axis_mismatch_above_threshold_is_hard(make_experiment, clean_files) -> None:
    files = dict(clean_files)
    files["s_low_irr1.txt"] = shift_wave(files["s_low_irr1.txt"], 0.5)
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s low: wave axes mismatch") == HARD


def test_differing_axis_lengths_is_hard(make_experiment, clean_files) -> None:
    files = dict(clean_files)
    files["s_low_irr1.txt"] = files["s_low_irr1.txt"][:-2]
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s low: wave axes have differing lengths") == HARD


def test_window_content_mismatch_is_hard(make_experiment, low_lines, high_lines) -> None:
    """A file labelled high but carrying low-window data."""
    files = {
        "s_low_0.txt": vary(low_lines, 0),
        "s_low_irr1.txt": vary(low_lines, 1),
        "s_low_irr2.txt": vary(low_lines, 2),
        "s_high_0.txt": vary(high_lines, 0),
        "s_high_irr1.txt": vary(high_lines, 1),
        "s_high_irr2.txt": vary(low_lines, 9),
    }
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "s_high_irr2.txt: wave range") == HARD


def test_overlapping_window_ranges_is_hard(make_experiment, low_lines) -> None:
    """Both labels carry low-window data, so their derived ranges collide."""
    files = {
        "s_low_0.txt": vary(low_lines, 0),
        "s_low_irr1.txt": vary(low_lines, 1),
        "s_low_irr2.txt": vary(low_lines, 2),
        "s_high_0.txt": vary(low_lines, 3),
        "s_high_irr1.txt": vary(low_lines, 4),
        "s_high_irr2.txt": vary(low_lines, 5),
    }
    _, findings = findings_for(make_experiment(files))
    assert severity_of(findings, "window ranges overlap") == HARD


# --- filtering and gating --------------------------------------------------


def test_hard_failures_filters_to_hard_only() -> None:
    findings = [(SOFT, "soft one"), (HARD, "hard one"), (SOFT, "soft two")]
    assert hard_failures(findings) == ["hard one"]


def test_hard_failures_empty_when_all_soft() -> None:
    assert hard_failures([(SOFT, "a"), (SOFT, "b")]) == []


@pytest.fixture
def dirty_spectra(make_experiment, clean_files):
    """An experiment with exactly one hard failure."""
    files = dict(clean_files)
    files["s_low_irr2.txt"] = files["s_low_irr1.txt"]
    return load_experiment(make_experiment(files), "exp")


def test_preflight_raises_on_hard(dirty_spectra, capsys) -> None:
    with pytest.raises(HardCheckFailure):
        preflight("plot", "exp", dirty_spectra, force=False)
    err = capsys.readouterr().err
    assert "refusing to plot exp" in err
    assert "identical file contents" in err
    assert "--force" in err


def test_preflight_uses_the_calling_subcommand_name(dirty_spectra, capsys) -> None:
    with pytest.raises(HardCheckFailure):
        preflight("export", "exp", dirty_spectra)
    assert "refusing to export exp" in capsys.readouterr().err


def test_preflight_returns_with_force(dirty_spectra, capsys) -> None:
    preflight("plot", "exp", dirty_spectra, force=True)
    err = capsys.readouterr().err
    assert "OVERRIDDEN" in err
    assert "!!!" in err


def test_preflight_silent_when_clean(make_experiment, clean_files, capsys) -> None:
    spectra = load_experiment(make_experiment(clean_files), "exp")
    preflight("plot", "exp", spectra)
    assert capsys.readouterr().err == ""


def test_soft_findings_never_gate(make_experiment, clean_files, capsys) -> None:
    """A pile of SOFT findings must not stop preflight."""
    files = dict(clean_files)
    files["s_low_irr3.txt"] = files.pop("s_low_irr2.txt")
    files["s_high_0.txt"] = (files["s_high_0.txt"], False)
    spectra = load_experiment(make_experiment(files), "exp")
    _, findings = findings_for(make_experiment(files))
    assert any(sev == SOFT for sev, _ in findings)
    assert hard_failures(findings) == []
    preflight("plot", "exp", spectra)
    assert capsys.readouterr().err == ""
