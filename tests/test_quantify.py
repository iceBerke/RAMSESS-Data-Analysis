"""bands.json validation, the raw-write guard, export and normalisation.

Synthetic experiments under ``tmp_path`` throughout. Nothing here reads or
writes the project's ``data/`` or ``figures/`` trees.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import spectrum_lines, vary, write_spectrum_file
from ramsess.io import guard_not_under_raw, load_experiment
from ramsess.report import (
    BANDS_CONFIG_NAME,
    common_window_ranges,
    load_bands_config,
    measure_all_bands,
    write_bands_csv,
    write_derived_spectra,
    write_provenance,
)

PARAMS = {
    "low": {"lam": 1e6, "p": 0.01, "n_iter": 10},
    "high": {"lam": 1e8, "p": 0.01, "n_iter": 10},
}


def peaky(start: float, spacing: float, n: int, centre_index: int, base: float) -> list[str]:
    """A flat spectrum with one triangular peak, on a non-uniform axis."""
    lines, wave = [], start
    for i in range(n):
        wave += spacing * (1.0 + 0.1 * (i % 3))
        value = base + (900.0 if i == centre_index else 0.0)
        lines.append(f"{wave:.6f}\t{value:.6f}")
    return lines


@pytest.fixture
def experiment(tmp_path: Path) -> Path:
    """One sample, both windows, three steps, with a peak in each window."""
    raw = tmp_path / "raw"
    folder = raw / "exp"
    folder.mkdir(parents=True)
    for step in ("0", "irr1", "irr2"):
        write_spectrum_file(
            folder / f"s_low_{step}.txt", peaky(200.0, 2.5, 60, 30, 1000.0)
        )
        write_spectrum_file(
            folder / f"s_high_{step}.txt", peaky(2400.0, 2.0, 60, 30, 5000.0)
        )
    return raw


def band_config(folder: Path, payload) -> Path:
    path = folder / BANDS_CONFIG_NAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def spectra_bounds(raw: Path, window: str) -> tuple[float, float]:
    group = [s for s in load_experiment(raw, "exp") if s.window == window]
    return float(group[0].wave.min()), float(group[0].wave.max())


def window_ranges(raw: Path) -> dict[str, tuple[float, float]]:
    """What ``load_bands_config`` now takes: the range every file shares.

    Derived at runtime from the files the fixture wrote, never written out as
    literals, so a change to the fixture's axis cannot leave the configuration
    describing data that is not there.
    """
    return common_window_ranges(load_experiment(raw, "exp"))


@pytest.fixture
def valid_config(experiment: Path):
    low_lo, low_hi = spectra_bounds(experiment, "low")
    high_lo, high_hi = spectra_bounds(experiment, "high")
    centre_low = (low_lo + low_hi) / 2
    centre_high = (high_lo + high_hi) / 2
    return {
        "reference": "ref",
        "bands": {
            "ref": {"centre": centre_low, "half_width": 20.0, "window": "low"},
            "other": {"centre": centre_high, "half_width": 20.0, "window": "high"},
        },
    }


# --- the raw-write guard ---------------------------------------------------


def test_guard_raises_for_a_path_under_raw(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    with pytest.raises(ValueError, match="refusing to write inside the raw data root"):
        guard_not_under_raw(raw / "exp" / "out.txt", raw)


def test_guard_raises_for_the_raw_root_itself(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    with pytest.raises(ValueError, match="refusing to write"):
        guard_not_under_raw(raw, raw)


def test_guard_names_the_offending_path(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    with pytest.raises(ValueError) as excinfo:
        guard_not_under_raw(raw / "exp" / "sneaky.json", raw)
    assert "sneaky.json" in str(excinfo.value)


def test_guard_allows_a_sibling_path(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    target = tmp_path / "derived" / "out.txt"
    assert guard_not_under_raw(target, raw) == target


def test_export_refuses_a_derived_root_inside_raw(experiment: Path) -> None:
    spectra = load_experiment(experiment, "exp")
    with pytest.raises(ValueError, match="refusing to write inside the raw data root"):
        write_derived_spectra("exp", spectra, experiment / "sneaky", experiment, PARAMS)


# --- derived export --------------------------------------------------------


def test_derived_files_reconstruct_the_raw_spectra(experiment: Path, tmp_path: Path) -> None:
    spectra = load_experiment(experiment, "exp")
    written, worst = write_derived_spectra(
        "exp", spectra, tmp_path / "derived", experiment, PARAMS
    )
    assert len(written) == len(spectra)
    assert worst < 1e-6

    by_name = {s.path.stem: s for s in spectra}
    for path in written:
        table = np.loadtxt(path, comments="#", dtype=np.float64)
        assert table.shape[1] == 3, "wave, corrected, baseline"
        stem = path.stem.replace("_corrected", "")
        sample, window, step = stem.rsplit("_", 2)
        key = f"{sample}_{window}_{'0' if step == '0' else 'irr' + step}"
        source = by_name[key]
        assert np.allclose(table[:, 0], source.wave, rtol=0, atol=1e-5)
        residual = np.max(np.abs(table[:, 1] + table[:, 2] - source.intensity))
        assert residual < 1e-6 * float(np.max(np.abs(source.intensity)))


def test_derived_files_carry_a_self_documenting_header(
    experiment: Path, tmp_path: Path
) -> None:
    spectra = load_experiment(experiment, "exp")
    written, _ = write_derived_spectra(
        "exp", spectra, tmp_path / "derived", experiment, PARAMS
    )
    header = written[0].read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("#")
    for token in ("wave", "corrected", "baseline"):
        assert token in header


def test_provenance_records_parameters_hashes_and_time(
    experiment: Path, tmp_path: Path
) -> None:
    spectra = load_experiment(experiment, "exp")
    sources = {w: {k: "baseline.json" for k in PARAMS[w]} for w in PARAMS}
    path = write_provenance(
        "exp", spectra, tmp_path / "derived", experiment, PARAMS, sources
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["experiment"] == "exp"
    assert payload["generated_utc"].endswith("+00:00")
    assert payload["baseline_parameters"]["low"]["lam"]["value"] == 1e6
    assert payload["baseline_parameters"]["low"]["lam"]["source"] == "baseline.json"
    assert len(payload["source_files"]) == len(spectra)
    assert all(len(entry["sha256"]) == 64 for entry in payload["source_files"])


# --- bands.json validation -------------------------------------------------


def test_absent_bands_config_raises_naming_the_path(experiment: Path) -> None:
    with pytest.raises(FileNotFoundError, match=BANDS_CONFIG_NAME):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_valid_config_loads(experiment: Path, valid_config) -> None:
    band_config(experiment / "exp", valid_config)
    reference, bands, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    assert reference == "ref"
    assert set(bands) == {"ref", "other"}
    assert bands["other"].window == "high"
    assert regions == {}


def test_missing_reference_key_raises(experiment: Path, valid_config) -> None:
    del valid_config["reference"]
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="missing required key 'reference'"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_reference_not_in_bands_raises(experiment: Path, valid_config) -> None:
    valid_config["reference"] = "absent"
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="reference 'absent' is not defined"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_unknown_window_raises_naming_it(experiment: Path, valid_config) -> None:
    valid_config["bands"]["other"]["window"] = "middle"
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError) as excinfo:
        load_bands_config(experiment / "exp", window_ranges(experiment))
    message = str(excinfo.value)
    assert "'middle'" in message and "low" in message and "high" in message


def test_overlapping_search_windows_raise(experiment: Path, valid_config) -> None:
    centre = valid_config["bands"]["ref"]["centre"]
    valid_config["bands"]["neighbour"] = {
        "centre": centre + 10.0,
        "half_width": 20.0,
        "window": "low",
    }
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="overlap in window 'low'"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_bands_in_different_windows_never_overlap(experiment: Path, valid_config) -> None:
    """Identical widths in different windows: not a conflict.

    The overlap check is per spectral window, so two bands may sit at the same
    offset within their own windows without competing for a maximum. Both are
    placed at their own window's centre, so each is genuinely measurable and the
    only thing under test is the overlap rule.
    """
    valid_config["bands"]["other"]["half_width"] = valid_config["bands"]["ref"][
        "half_width"
    ]
    band_config(experiment / "exp", valid_config)
    reference, bands, _ = load_bands_config(experiment / "exp", window_ranges(experiment))
    assert set(bands) == {"ref", "other"}
    assert bands["ref"].window != bands["other"].window
    assert bands["ref"].half_width == bands["other"].half_width


def test_out_of_range_search_window_raises_during_config_loading(
    experiment: Path, valid_config
) -> None:
    """Caught while reading the config, before any caller can write anything.

    The same condition is checked again inside measure_band, which stays as
    defence in depth for callers that build a BandSpec without going through
    this function. Through this function it is now unreachable.
    """
    low_lo, low_hi = spectra_bounds(experiment, "low")
    outside = low_lo - (low_hi - low_lo)
    valid_config["bands"]["ref"]["centre"] = outside
    band_config(experiment / "exp", valid_config)

    with pytest.raises(ValueError) as excinfo:
        load_bands_config(experiment / "exp", window_ranges(experiment))

    message = str(excinfo.value)
    assert BANDS_CONFIG_NAME in message
    assert "bands.ref" in message
    assert "'low'" in message
    assert f"[{low_lo:.3f}, {low_hi:.3f}]" in message
    assert "falls outside the measured range" in message


@pytest.mark.parametrize("half_width", [0, -3])
def test_non_positive_half_width_raises(experiment: Path, valid_config, half_width) -> None:
    valid_config["bands"]["ref"]["half_width"] = half_width
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="half_width must be greater than 0"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_unknown_top_level_key_raises(experiment: Path, valid_config) -> None:
    valid_config["extra"] = 1
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="unknown key"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_unknown_key_in_a_band_raises(experiment: Path, valid_config) -> None:
    valid_config["bands"]["ref"]["colour"] = "red"
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="unknown key\\(s\\) colour"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_noise_region_is_optional_and_validated(experiment: Path, valid_config) -> None:
    # Derived from the axis the fixture actually wrote, so the region cannot
    # drift outside the data and start failing the range check for a reason
    # this test is not about.
    low_lo, low_hi = spectra_bounds(experiment, "low")
    span = low_hi - low_lo
    low, high = low_lo + span * 0.6, low_lo + span * 0.9
    valid_config["noise_regions"] = {"low": [low, high]}
    band_config(experiment / "exp", valid_config)
    _, _, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    assert regions == {"low": (low, high)}


def test_noise_region_outside_the_data_raises_during_config_loading(
    experiment: Path, valid_config
) -> None:
    """Same exposure as a band, so the same early check."""
    low_lo, low_hi = spectra_bounds(experiment, "low")
    valid_config["noise_regions"] = {"low": [low_lo, low_hi + (low_hi - low_lo)]}
    band_config(experiment / "exp", valid_config)

    with pytest.raises(ValueError) as excinfo:
        load_bands_config(experiment / "exp", window_ranges(experiment))

    message = str(excinfo.value)
    assert "noise_regions.low" in message
    assert "falls outside the measured range" in message
    assert f"[{low_lo:.3f}, {low_hi:.3f}]" in message


def test_noise_region_for_an_unknown_window_raises(experiment: Path, valid_config) -> None:
    valid_config["noise_regions"] = {"middle": [300, 400]}
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="'middle'"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


def test_malformed_noise_region_raises(experiment: Path, valid_config) -> None:
    valid_config["noise_regions"] = {"low": [400, 300]}
    band_config(experiment / "exp", valid_config)
    with pytest.raises(ValueError, match="expected low < high"):
        load_bands_config(experiment / "exp", window_ranges(experiment))


# --- normalisation and the cross-window flag -------------------------------


def test_reference_normalises_to_exactly_one(experiment: Path, valid_config) -> None:
    band_config(experiment / "exp", valid_config)
    reference, bands, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    rows = measure_all_bands(load_experiment(experiment, "exp"), bands, reference, regions, PARAMS)
    for row in (r for r in rows if r["band"] == "ref"):
        assert row["height_norm"] == pytest.approx(1.0)
        assert row["area_norm"] == pytest.approx(1.0)


def test_normalisation_divides_by_the_reference(experiment: Path, valid_config) -> None:
    band_config(experiment / "exp", valid_config)
    reference, bands, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    rows = measure_all_bands(load_experiment(experiment, "exp"), bands, reference, regions, PARAMS)
    for step in (0, 1, 2):
        ref = next(r for r in rows if r["band"] == "ref" and r["step"] == step)
        other = next(r for r in rows if r["band"] == "other" and r["step"] == step)
        assert other["height_norm"] == pytest.approx(other["height"] / ref["height"])
        assert other["area_norm"] == pytest.approx(other["area"] / ref["area"])


def test_cross_window_flag_is_set_for_exactly_the_other_window(
    experiment: Path, valid_config
) -> None:
    band_config(experiment / "exp", valid_config)
    reference, bands, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    rows = measure_all_bands(load_experiment(experiment, "exp"), bands, reference, regions, PARAMS)
    for row in rows:
        expected = row["window"] != bands[reference].window
        assert row["cross_window"] is expected
    assert any(r["cross_window"] for r in rows), "the fixture must exercise both cases"
    assert any(not r["cross_window"] for r in rows)


def test_signal_to_noise_present_only_when_a_region_is_configured(
    experiment: Path, valid_config
) -> None:
    band_config(experiment / "exp", valid_config)
    reference, bands, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    spectra = load_experiment(experiment, "exp")
    without = measure_all_bands(spectra, bands, reference, regions, PARAMS)
    assert all(r["signal_to_noise"] is None for r in without)

    low_lo, low_hi = spectra_bounds(experiment, "low")
    with_region = measure_all_bands(
        spectra, bands, reference, {"low": (low_lo + 1, low_lo + 40)}, PARAMS
    )
    assert any(r["signal_to_noise"] is not None for r in with_region if r["window"] == "low")
    assert all(r["signal_to_noise"] is None for r in with_region if r["window"] == "high")


# --- the csv ---------------------------------------------------------------


def test_bands_csv_has_one_row_per_measurement_with_the_flags(
    experiment: Path, valid_config, tmp_path: Path
) -> None:
    band_config(experiment / "exp", valid_config)
    reference, bands, regions = load_bands_config(experiment / "exp", window_ranges(experiment))
    rows = measure_all_bands(load_experiment(experiment, "exp"), bands, reference, regions, PARAMS)
    path = write_bands_csv("exp", rows, tmp_path / "derived", experiment)

    with path.open(encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == len(rows)
    for column in (
        "sample", "window", "step", "band", "centre", "position", "height", "area",
        "at_edge", "signal_to_noise", "height_norm", "area_norm", "cross_window",
    ):
        assert column in written[0]
