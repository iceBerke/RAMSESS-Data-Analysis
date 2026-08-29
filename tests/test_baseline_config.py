"""Baseline parameter resolution: precedence, per-window overrides, validation.

Config files are written under ``tmp_path``. No real experiment folder is read.
Window labels are supplied by the caller, so nothing here or in the module under
test assumes a particular set of labels.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ramsess.io import WINDOW_ORDER
from ramsess.report import (
    BASELINE_CONFIG_NAME,
    DEFAULT_BASELINE,
    SOURCE_CONFIG,
    SOURCE_DEFAULT,
    WINDOWS_KEY,
    load_baseline_config,
    print_baseline_config,
    resolve_baseline_config,
)

WINDOWS = {"low", "high"}


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    experiment = tmp_path / "exp"
    experiment.mkdir()
    return experiment


def write_config(folder: Path, payload) -> Path:
    path = folder / BASELINE_CONFIG_NAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- precedence ------------------------------------------------------------


def test_defaults_when_nothing_is_supplied(folder: Path) -> None:
    values, sources = resolve_baseline_config(folder, WINDOWS)
    assert set(values) == WINDOWS
    for label in WINDOWS:
        assert values[label] == DEFAULT_BASELINE
        assert set(sources[label].values()) == {SOURCE_DEFAULT}


def test_top_level_config_beats_defaults(folder: Path) -> None:
    write_config(folder, {"lam": 5e4, "p": 0.02, "n_iter": 4})
    values, sources = resolve_baseline_config(folder, WINDOWS)
    for label in WINDOWS:
        assert values[label] == {"lam": 5e4, "p": 0.02, "n_iter": 4}
        assert set(sources[label].values()) == {SOURCE_CONFIG}


def test_per_window_override_beats_top_level(folder: Path) -> None:
    write_config(
        folder, {"lam": 1e6, "p": 0.01, "n_iter": 10, WINDOWS_KEY: {"high": {"lam": 1e8}}}
    )
    values, sources = resolve_baseline_config(folder, WINDOWS)
    assert values["high"]["lam"] == 1e8
    assert values["low"]["lam"] == 1e6
    assert sources["high"]["lam"] == f"{BASELINE_CONFIG_NAME} {WINDOWS_KEY}.high"
    assert sources["low"]["lam"] == SOURCE_CONFIG


def test_per_window_override_is_per_parameter(folder: Path) -> None:
    """Overriding lam for one window leaves p and n_iter to the lower sources."""
    write_config(folder, {"lam": 1e6, WINDOWS_KEY: {"high": {"lam": 1e8}}})
    values, sources = resolve_baseline_config(folder, WINDOWS)
    assert values["high"] == {"lam": 1e8, "p": DEFAULT_BASELINE["p"], "n_iter": DEFAULT_BASELINE["n_iter"]}
    assert sources["high"]["p"] == SOURCE_DEFAULT
    assert sources["high"]["n_iter"] == SOURCE_DEFAULT
    assert sources["high"]["lam"] == f"{BASELINE_CONFIG_NAME} {WINDOWS_KEY}.high"


def test_window_absent_from_the_block_falls_back_to_top_level(folder: Path) -> None:
    write_config(folder, {"lam": 1e6, WINDOWS_KEY: {"high": {"lam": 1e8}}})
    values, sources = resolve_baseline_config(folder, WINDOWS)
    assert values["low"]["lam"] == 1e6
    assert sources["low"]["lam"] == SOURCE_CONFIG


def test_cli_flag_beats_per_window_config(folder: Path) -> None:
    write_config(folder, {"lam": 1e6, WINDOWS_KEY: {"high": {"lam": 1e8}}})
    values, sources = resolve_baseline_config(folder, WINDOWS, lam=7.0)
    assert values["high"]["lam"] == 7.0
    assert values["low"]["lam"] == 7.0


def test_cli_override_of_a_per_window_value_is_announced(folder: Path) -> None:
    """A global flag silently beating a per-window setting would be a trap."""
    write_config(folder, {"lam": 1e6, WINDOWS_KEY: {"high": {"lam": 1e8}}})
    _, sources = resolve_baseline_config(folder, WINDOWS, lam=7.0)
    assert "--baseline-lam" in sources["high"]["lam"]
    assert "overrides" in sources["high"]["lam"]
    assert f"{WINDOWS_KEY}.high" in sources["high"]["lam"]
    assert "100000000.0" in sources["high"]["lam"]
    assert "1000000.0" in sources["low"]["lam"]


def test_flags_beat_top_level_config(folder: Path) -> None:
    write_config(folder, {"lam": 5e4, "p": 0.02, "n_iter": 4})
    values, sources = resolve_baseline_config(folder, WINDOWS, lam=1.0, p=0.3, n_iter=2)
    for label in WINDOWS:
        assert values[label] == {"lam": 1.0, "p": 0.3, "n_iter": 2}
        assert all("--baseline-" in origin for origin in sources[label].values())


def test_resolution_is_per_parameter(folder: Path) -> None:
    write_config(folder, {"p": 0.02})
    values, sources = resolve_baseline_config(folder, WINDOWS, lam=7.0)
    for label in WINDOWS:
        assert values[label] == {"lam": 7.0, "p": 0.02, "n_iter": DEFAULT_BASELINE["n_iter"]}
        assert "--baseline-lam" in sources[label]["lam"]
        assert sources[label]["p"] == SOURCE_CONFIG
        assert sources[label]["n_iter"] == SOURCE_DEFAULT


def test_absent_config_is_not_an_error(folder: Path) -> None:
    assert load_baseline_config(folder, WINDOWS) == ({}, {})


def test_only_requested_windows_are_resolved(folder: Path) -> None:
    values, _ = resolve_baseline_config(folder, {"low"})
    assert set(values) == {"low"}


def test_arbitrary_window_labels_are_supported(folder: Path) -> None:
    """Nothing in the resolver assumes low and high."""
    write_config(folder, {"lam": 1e6, WINDOWS_KEY: {"mid": {"lam": 3.0}}})
    values, _ = resolve_baseline_config(folder, {"mid", "far"})
    assert values["mid"]["lam"] == 3.0
    assert values["far"]["lam"] == 1e6


# --- validation ------------------------------------------------------------


def test_malformed_json_raises(folder: Path) -> None:
    (folder / BASELINE_CONFIG_NAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        resolve_baseline_config(folder, WINDOWS)


def test_non_object_json_raises(folder: Path) -> None:
    write_config(folder, [1, 2, 3])
    with pytest.raises(ValueError, match="expected a JSON object"):
        resolve_baseline_config(folder, WINDOWS)


def test_unknown_top_level_key_raises_in_baseline_config(folder: Path) -> None:
    write_config(folder, {"lam": 1e5, "smoothness": 3})
    with pytest.raises(ValueError, match="unknown key"):
        resolve_baseline_config(folder, WINDOWS)


def test_unknown_window_key_raises_naming_it(folder: Path) -> None:
    write_config(folder, {WINDOWS_KEY: {"mid": {"lam": 1e8}}})
    with pytest.raises(ValueError) as excinfo:
        resolve_baseline_config(folder, WINDOWS)
    message = str(excinfo.value)
    assert "'mid'" in message
    assert "high" in message and "low" in message


def test_unknown_key_inside_a_window_block_raises(folder: Path) -> None:
    write_config(folder, {WINDOWS_KEY: {"high": {"lam": 1e8, "wobble": 2}}})
    with pytest.raises(ValueError, match="wobble"):
        resolve_baseline_config(folder, WINDOWS)


def test_non_object_windows_block_raises(folder: Path) -> None:
    write_config(folder, {WINDOWS_KEY: [1, 2]})
    with pytest.raises(ValueError, match=f"'{WINDOWS_KEY}' must be a JSON object"):
        resolve_baseline_config(folder, WINDOWS)


def test_non_object_window_entry_raises(folder: Path) -> None:
    write_config(folder, {WINDOWS_KEY: {"high": 1e8}})
    with pytest.raises(ValueError, match="must be a JSON object"):
        resolve_baseline_config(folder, WINDOWS)


@pytest.mark.parametrize("bad_p", [0, 1, -0.5, 2.0])
def test_out_of_range_p_in_config_raises(folder: Path, bad_p) -> None:
    write_config(folder, {"p": bad_p})
    with pytest.raises(ValueError, match="p must be strictly between 0 and 1"):
        resolve_baseline_config(folder, WINDOWS)


@pytest.mark.parametrize("bad_iter", [0, -3, 2.5])
def test_out_of_range_n_iter_in_config_raises(folder: Path, bad_iter) -> None:
    write_config(folder, {"n_iter": bad_iter})
    with pytest.raises(ValueError, match="n_iter must be an integer of at least 1"):
        resolve_baseline_config(folder, WINDOWS)


@pytest.mark.parametrize("bad_lam", [0, -1.0])
def test_out_of_range_lam_in_config_raises(folder: Path, bad_lam) -> None:
    write_config(folder, {"lam": bad_lam})
    with pytest.raises(ValueError, match="lam must be greater than 0"):
        resolve_baseline_config(folder, WINDOWS)


def test_out_of_range_per_window_value_raises_naming_the_window(folder: Path) -> None:
    write_config(folder, {WINDOWS_KEY: {"high": {"p": 5.0}}})
    with pytest.raises(ValueError) as excinfo:
        resolve_baseline_config(folder, WINDOWS)
    assert f"{WINDOWS_KEY}.high" in str(excinfo.value)


def test_non_numeric_value_raises(folder: Path) -> None:
    write_config(folder, {"lam": "big"})
    with pytest.raises(ValueError, match="must be a number"):
        resolve_baseline_config(folder, WINDOWS)


def test_bad_config_never_falls_back_silently(folder: Path) -> None:
    write_config(folder, {"p": 5.0})
    with pytest.raises(ValueError):
        resolve_baseline_config(folder, WINDOWS)


def test_out_of_range_flag_raises(folder: Path) -> None:
    with pytest.raises(ValueError, match="p must be strictly"):
        resolve_baseline_config(folder, WINDOWS, p=1.5)


# --- the notice ------------------------------------------------------------


def test_fallback_notice_is_printed_and_names_the_values(folder: Path, capsys) -> None:
    values, sources = resolve_baseline_config(folder, WINDOWS)
    print_baseline_config(values, sources)
    out = capsys.readouterr().out
    assert "NOTE" in out
    assert SOURCE_DEFAULT in out
    for label in WINDOWS:
        assert label in out
        for key in ("lam", "p", "n_iter"):
            assert f"{label}.{key}" in out


def test_no_fallback_notice_when_everything_is_supplied(folder: Path, capsys) -> None:
    write_config(folder, {"lam": 5e4, "p": 0.02, "n_iter": 4})
    values, sources = resolve_baseline_config(folder, WINDOWS)
    print_baseline_config(values, sources)
    out = capsys.readouterr().out
    assert "NOTE" not in out
    assert BASELINE_CONFIG_NAME in out


def test_notice_names_the_per_window_origin(folder: Path, capsys) -> None:
    """A run using a different lam per window must say so explicitly."""
    write_config(
        folder, {"lam": 1e6, "p": 0.01, "n_iter": 10, WINDOWS_KEY: {"high": {"lam": 1e8}}}
    )
    values, sources = resolve_baseline_config(folder, WINDOWS)
    print_baseline_config(values, sources)
    out = capsys.readouterr().out
    assert f"{WINDOWS_KEY}.high" in out
    assert "100000000.0" in out
    assert "1000000.0" in out


def test_notice_reports_a_cli_override_of_a_window_value(folder: Path, capsys) -> None:
    write_config(folder, {"lam": 1e6, WINDOWS_KEY: {"high": {"lam": 1e8}}})
    values, sources = resolve_baseline_config(folder, WINDOWS, lam=7.0)
    print_baseline_config(values, sources)
    out = capsys.readouterr().out
    assert "overrides" in out
    assert "--baseline-lam" in out


def test_baseline_parameters_print_in_physical_window_order(folder: Path, capsys) -> None:
    """Low before high, matching every other window ordering in the codebase.

    Asserts POSITION. The tests above check that each label and each source
    appears, and would pass in any order; this is the one that pins the order.
    Alphabetical sorting puts 'high' first. Nothing here names a window: the
    expected order is read from WINDOW_ORDER.

    print_baseline_config cannot use window_sort_key, because the resolver it
    is fed by accepts arbitrary labels - see
    test_arbitrary_window_labels_are_supported. It uses
    window_display_order_key, which orders known labels physically and never
    raises on the rest.
    """
    values, sources = resolve_baseline_config(folder, set(WINDOW_ORDER))
    print_baseline_config(values, sources)
    lines = capsys.readouterr().out.split("\n")

    positions = []
    for window in WINDOW_ORDER:
        found = [i for i, line in enumerate(lines) if line == f"  {window}:"]
        assert len(found) == 1, f"expected exactly one heading for {window!r}, got {found}"
        positions.append(found[0])

    assert positions == sorted(positions), (
        f"baseline-parameter blocks are out of physical order: "
        f"{list(zip(WINDOW_ORDER, positions))}. WINDOW_ORDER is {WINDOW_ORDER}, "
        f"so {WINDOW_ORDER[0]!r} must print before {WINDOW_ORDER[1]!r}."
    )


def test_every_source_is_named_on_stdout(folder: Path, capsys) -> None:
    write_config(folder, {"p": 0.02})
    values, sources = resolve_baseline_config(folder, WINDOWS, lam=9.0)
    print_baseline_config(values, sources)
    out = capsys.readouterr().out
    assert "--baseline-lam" in out
    assert SOURCE_CONFIG in out
    assert SOURCE_DEFAULT in out
