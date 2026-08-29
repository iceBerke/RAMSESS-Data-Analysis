"""Window ranges are derived from the files, never assumed."""

from __future__ import annotations

from conftest import shift_wave, vary
from ramsess.io import group_spectra, load_experiment
from ramsess.report import (
    HARD,
    MODE_TOLERANCE,
    SOFT,
    collect_warnings,
    derive_window_ranges,
    hard_failures,
)


def derive(raw_root, experiment: str = "exp"):
    return derive_window_ranges(load_experiment(raw_root, experiment))


def test_ranges_match_the_files(make_experiment, low_lines, high_lines) -> None:
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_high_0.txt": vary(high_lines, 0),
            "s_high_irr1.txt": vary(high_lines, 1),
            "s_high_irr2.txt": vary(high_lines, 2),
        }
    )
    ranges, trusted, observations = derive(raw)

    expected_low = (
        float(low_lines[0].split()[0]),
        float(low_lines[-1].split()[0]),
    )
    assert ranges["low"] == expected_low
    assert trusted == {"low": True, "high": True}
    assert observations == []


def test_derivation_follows_a_shifted_grating(make_experiment, low_lines, high_lines) -> None:
    """A different grating must not produce a single false failure."""
    shift = -100.0
    raw = make_experiment(
        {
            "s_low_0.txt": vary(shift_wave(low_lines, shift), 0),
            "s_low_irr1.txt": vary(shift_wave(low_lines, shift), 1),
            "s_low_irr2.txt": vary(shift_wave(low_lines, shift), 2),
            "s_high_0.txt": vary(shift_wave(high_lines, shift), 0),
            "s_high_irr1.txt": vary(shift_wave(high_lines, shift), 1),
            "s_high_irr2.txt": vary(shift_wave(high_lines, shift), 2),
        }
    )
    ranges, trusted, _ = derive(raw)
    assert ranges["low"][0] == float(low_lines[0].split()[0]) + shift
    assert all(trusted.values())

    spectra = load_experiment(raw, "exp")
    assert hard_failures(collect_warnings(spectra, group_spectra(spectra))) == []


def test_tie_break_prefers_the_majority_exact_pair(
    make_experiment, low_lines, high_lines
) -> None:
    """One low-precision export must not become the representative range.

    Both candidates sit inside MODE_TOLERANCE of each other, so cluster size
    ties; the winner must be the pair the majority of files share exactly.
    """
    odd = shift_wave(low_lines, 0.004)
    raw = make_experiment(
        {
            "s_low_0.txt": vary(odd, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_low_irr3.txt": vary(low_lines, 3),
            "s_high_0.txt": vary(high_lines, 0),
            "s_high_irr1.txt": vary(high_lines, 1),
            "s_high_irr2.txt": vary(high_lines, 2),
        }
    )
    ranges, trusted, _ = derive(raw)
    majority = (float(low_lines[0].split()[0]), float(low_lines[-1].split()[0]))
    assert ranges["low"] == majority
    assert abs(ranges["low"][0] - float(odd[0].split()[0])) < MODE_TOLERANCE
    assert trusted["low"] is True


def test_too_few_files_skips_the_per_file_check(
    make_experiment, low_lines, high_lines
) -> None:
    """With two files the label is untrusted, so no file is flagged against it."""
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_high_0.txt": vary(high_lines, 0),
            # Wildly off, but the label has too few files to judge it.
            "s_high_irr1.txt": vary(shift_wave(high_lines, 5000.0), 1),
        }
    )
    ranges, trusted, observations = derive(raw)
    assert trusted["high"] is False
    assert trusted["low"] is True
    assert any(sev == SOFT and "high" in msg for sev, msg in observations)

    spectra = load_experiment(raw, "exp")
    findings = collect_warnings(spectra, group_spectra(spectra))
    assert not any("s_high_irr1.txt: wave range" in msg for _, msg in findings)


def test_no_majority_skips_the_per_file_check(make_experiment, low_lines, high_lines) -> None:
    """Four files, no cluster holding more than half, so the label is untrusted."""
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_high_0.txt": vary(high_lines, 0),
            "s_high_irr1.txt": vary(shift_wave(high_lines, 100.0), 1),
            "s_high_irr2.txt": vary(shift_wave(high_lines, 200.0), 2),
            "s_high_irr3.txt": vary(shift_wave(high_lines, 300.0), 3),
        }
    )
    _, trusted, observations = derive(raw)
    assert trusted["high"] is False
    assert any("no majority wave range" in msg for _, msg in observations)


def test_disjointness_fires_even_for_a_skipped_label(
    make_experiment, low_lines
) -> None:
    """The backstop must run regardless of whether a label had enough files.

    'high' has only two files so its per-file check is skipped, but its range
    still overlaps 'low' and that is a hard failure.
    """
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_high_0.txt": vary(low_lines, 3),
            "s_high_irr1.txt": vary(low_lines, 4),
        }
    )
    _, trusted, _ = derive(raw)
    assert trusted["high"] is False

    spectra = load_experiment(raw, "exp")
    findings = collect_warnings(spectra, group_spectra(spectra))
    overlap = [(sev, msg) for sev, msg in findings if "window ranges overlap" in msg]
    assert len(overlap) == 1
    assert overlap[0][0] == HARD
    assert overlap[0][1] in hard_failures(findings)


def test_disjoint_ranges_produce_no_overlap_finding(
    make_experiment, low_lines, high_lines
) -> None:
    raw = make_experiment(
        {
            "s_low_0.txt": vary(low_lines, 0),
            "s_low_irr1.txt": vary(low_lines, 1),
            "s_low_irr2.txt": vary(low_lines, 2),
            "s_high_0.txt": vary(high_lines, 0),
            "s_high_irr1.txt": vary(high_lines, 1),
            "s_high_irr2.txt": vary(high_lines, 2),
        }
    )
    spectra = load_experiment(raw, "exp")
    findings = collect_warnings(spectra, group_spectra(spectra))
    assert not any("window ranges overlap" in msg for _, msg in findings)
