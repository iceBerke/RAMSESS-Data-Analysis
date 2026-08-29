"""Loading: ordering, header handling, error reporting, and data fidelity."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from conftest import spectrum_lines, write_spectrum_file
from ramsess.io import group_spectra, load_experiment, load_spectrum, window_sort_key


def test_steps_sort_numerically_not_lexically(make_experiment) -> None:
    """irr10 must follow irr9, not sit between irr1 and irr2."""
    raw = make_experiment(
        {f"s_low_{n}.txt": None for n in ["0", "irr1", "irr2", "irr9", "irr10", "irr123"]}
    )
    steps = [s.step for s in load_experiment(raw, "exp")]
    assert steps == [0, 1, 2, 9, 10, 123]


def test_low_sorts_before_high(make_experiment, low_lines, high_lines) -> None:
    raw = make_experiment(
        {
            "s_high_0.txt": high_lines,
            "s_low_0.txt": low_lines,
            "s_high_irr1.txt": high_lines,
            "s_low_irr1.txt": low_lines,
        }
    )
    assert [(s.window, s.step) for s in load_experiment(raw, "exp")] == [
        ("low", 0),
        ("low", 1),
        ("high", 0),
        ("high", 1),
    ]


def test_window_sort_key_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="mid"):
        window_sort_key("mid")


def test_headed_and_headerless_files_give_the_same_rows(tmp_path: Path) -> None:
    """The header is skipped only when present; no data row may be lost."""
    lines = spectrum_lines(n=12)
    headed = write_spectrum_file(tmp_path / "s_low_0.txt", lines, header=True)
    bare = write_spectrum_file(tmp_path / "s_low_irr1.txt", lines, header=False)

    a = load_spectrum(headed, "exp")
    b = load_spectrum(bare, "exp")

    assert a.has_header is True
    assert b.has_header is False
    assert a.wave.size == b.wave.size == 12
    assert np.array_equal(a.wave, b.wave)
    assert np.array_equal(a.intensity, b.intensity)


def test_malformed_line_number_is_correct_with_header(tmp_path: Path) -> None:
    """Third data line, preceded by a header, is file line 4."""
    lines = spectrum_lines(n=5)
    lines[2] = "abc\t1.0"
    path = write_spectrum_file(tmp_path / "s_low_0.txt", lines, header=True)
    with pytest.raises(ValueError, match=r"line 4: expected two floats"):
        load_spectrum(path, "exp")


def test_malformed_line_number_is_correct_without_header(tmp_path: Path) -> None:
    """The same third data line, with no header, is file line 3."""
    lines = spectrum_lines(n=5)
    lines[2] = "abc\t1.0"
    path = write_spectrum_file(tmp_path / "s_low_0.txt", lines, header=False)
    with pytest.raises(ValueError, match=r"line 3: expected two floats"):
        load_spectrum(path, "exp")


def test_wrong_field_count_raises_naming_the_file(tmp_path: Path) -> None:
    lines = spectrum_lines(n=4)
    lines[1] = "1.0 2.0 3.0"
    path = write_spectrum_file(tmp_path / "s_low_0.txt", lines)
    with pytest.raises(ValueError, match="s_low_0.txt.*line 3.*2 whitespace"):
        load_spectrum(path, "exp")


def test_empty_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "s_low_0.txt"
    path.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        load_spectrum(path, "exp")


def test_header_with_no_data_raises(tmp_path: Path) -> None:
    path = write_spectrum_file(tmp_path / "s_low_0.txt", [], header=True)
    with pytest.raises(ValueError, match="no data lines"):
        load_spectrum(path, "exp")


def test_loaded_arrays_equal_the_file_contents(tmp_path: Path) -> None:
    lines = spectrum_lines(n=6)
    path = write_spectrum_file(tmp_path / "s_low_0.txt", lines)
    spectrum = load_spectrum(path, "exp")

    expected = np.array([[float(x) for x in line.split()] for line in lines])
    assert np.array_equal(spectrum.wave, expected[:, 0])
    assert np.array_equal(spectrum.intensity, expected[:, 1])
    assert spectrum.wave.dtype == np.float64


def test_loader_does_not_reorder_data(tmp_path: Path) -> None:
    """A descending axis must come back descending, not silently sorted."""
    lines = ["300.0\t5.0", "200.0\t6.0", "100.0\t7.0"]
    path = write_spectrum_file(tmp_path / "s_low_0.txt", lines)
    spectrum = load_spectrum(path, "exp")
    assert list(spectrum.wave) == [300.0, 200.0, 100.0]


def test_one_bad_filename_fails_the_whole_experiment(make_experiment) -> None:
    raw = make_experiment({"s_low_0.txt": None, "s_mid_0.txt": None})
    with pytest.raises(ValueError, match="s_mid_0.txt"):
        load_experiment(raw, "exp")


def test_missing_folder_and_empty_folder_raise(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        load_experiment(tmp_path, "absent")
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="no .txt files"):
        load_experiment(tmp_path, "empty")


def test_group_spectra_keys_and_step_order(make_experiment, low_lines, high_lines) -> None:
    raw = make_experiment(
        {
            "s_low_irr2.txt": low_lines,
            "s_low_0.txt": low_lines,
            "s_low_irr10.txt": low_lines,
            "s_high_0.txt": high_lines,
        }
    )
    groups = group_spectra(load_experiment(raw, "exp"))
    assert set(groups) == {("s", "low"), ("s", "high")}
    assert [s.step for s in groups[("s", "low")]] == [0, 2, 10]
