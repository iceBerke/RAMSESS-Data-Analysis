"""Text reporting over loaded spectra.

Formats and prints the inventory, the per-group summary and the warnings for one
experiment. Computes nothing that alters the data it is handed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ramsess.io import Spectrum, group_spectra, guard_not_under_raw, window_sort_key

# How far a file's wave range may sit from the modal range for its window label
# before it is treated as a mismatch. 1.0 cm-1 is about 200x the largest genuine
# export discrepancy seen in the data (0.005) and about 500x smaller than the
# gap between the two windows (548), so it separates real mislabels from
# precision noise with three orders of magnitude of headroom either side.
MODE_TOLERANCE = 1.0

# A window label needs at least this many files, and its modal cluster must hold
# more than half of them, before the modal range is trusted enough to check
# individual files against. With one file the mode is trivially itself and the
# check is vacuous; with two disagreeing files there is no majority to believe.
MIN_FILES_FOR_MODE = 3

# A non-zero wave-axis difference below this is an export-precision difference,
# not a genuine axis mismatch.
PRECISION_TOLERANCE = 0.01

# Severity of a check.
#
# HARD means a file is not what its name says: two files with identical content
# hashes, or a wave range outside the window its filename declares. Either one
# silently corrupts every plot drawn from it, which is why these gate --strict
# and refuse plotting unless overridden.
#
# SOFT items are true, accepted facts about the data as it stands: step gaps, a
# sample with no control, a sample in only one window, a file with no header
# line, wave axes differing below the precision threshold. They are always
# reported and never affect an exit code.
HARD = "hard"
SOFT = "soft"

Finding = tuple[str, str]


class HardCheckFailure(Exception):
    """Raised when hard checks fail and the caller has not passed ``force``."""


BASELINE_CONFIG_NAME = "baseline.json"

# Built-in fallback baseline parameters, used only when neither a CLI flag nor a
# baseline.json supplies a value. These are starting values that suited one
# dataset; they are not universal constants and carry no authority for any other
# experiment. Whenever one of them is used it is announced on stdout, so the
# choice is never silent.
DEFAULT_BASELINE = {"lam": 1e5, "p": 0.01, "n_iter": 10}

SOURCE_DEFAULT = "built-in default"
SOURCE_CONFIG = BASELINE_CONFIG_NAME

# Key of the optional per-window override block inside baseline.json. Its own
# keys are whatever window labels the experiment contains; none are built in.
WINDOWS_KEY = "windows"

# Note for anyone adding baseline diagnostics: a band mean taken close to a
# strong peak tracks the peak, not the background, and is therefore useless as a
# baseline anchor. Pick anchor windows well away from known bands, and check
# what a candidate window actually contains before trusting its spread.


def _validated_baseline_value(key: str, value: object, origin: str) -> float | int:
    """Range-check one baseline parameter.

    Args:
        key: Parameter name, one of ``lam``, ``p`` or ``n_iter``.
        value: The proposed value.
        origin: Where it came from, used in the error message.

    Returns:
        The value, as float for ``lam`` and ``p`` and int for ``n_iter``.

    Raises:
        ValueError: If the value is the wrong type or out of range.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{origin}: {key} must be a number, got {value!r}")
    if key == "n_iter":
        if int(value) != value or int(value) < 1:
            raise ValueError(f"{origin}: n_iter must be an integer of at least 1, got {value!r}")
        return int(value)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{origin}: {key} must be finite, got {value!r}")
    if key == "p" and not 0.0 < number < 1.0:
        raise ValueError(f"{origin}: p must be strictly between 0 and 1, got {value!r}")
    if key == "lam" and number <= 0.0:
        raise ValueError(f"{origin}: lam must be greater than 0, got {value!r}")
    return number


def load_baseline_config(
    experiment_folder: Path, windows: Iterable[str]
) -> tuple[dict[str, float | int], dict[str, dict[str, float | int]]]:
    """Read ``baseline.json`` from an experiment folder, if it is there.

    The optional ``windows`` block carries per-window overrides. Its keys are
    whatever window labels the experiment actually contains; no label is
    built in here.

    Args:
        experiment_folder: The folder holding the experiment's ``.txt`` files.
        windows: The window labels present in the experiment, which are the only
            keys the ``windows`` block may use.

    Returns:
        ``(top_level, per_window)``, both empty if the file is absent.

    Raises:
        ValueError: If the file exists but is not readable JSON, is not an
            object, carries an unknown key at either level, names a window the
            experiment does not contain, or holds an out-of-range value. A
            malformed config is never silently ignored.
    """
    path = experiment_folder / BASELINE_CONFIG_NAME
    if not path.is_file():
        return {}, {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{path}: expected a JSON object, got {type(parsed).__name__}")

    allowed = set(DEFAULT_BASELINE) | {WINDOWS_KEY}
    unknown = sorted(set(parsed) - allowed)
    if unknown:
        raise ValueError(
            f"{path}: unknown key(s) {', '.join(unknown)}; "
            f"expected any of {', '.join(sorted(allowed))}"
        )

    top_level = {
        key: _validated_baseline_value(key, parsed[key], str(path))
        for key in parsed
        if key != WINDOWS_KEY
    }

    per_window: dict[str, dict[str, float | int]] = {}
    block = parsed.get(WINDOWS_KEY)
    if block is not None:
        if not isinstance(block, dict):
            raise ValueError(
                f"{path}: '{WINDOWS_KEY}' must be a JSON object, got {type(block).__name__}"
            )
        valid = sorted(set(windows))
        for label, overrides in block.items():
            if label not in valid:
                raise ValueError(
                    f"{path}: '{WINDOWS_KEY}' names window {label!r}, which this "
                    f"experiment does not contain; valid labels: {', '.join(valid)}"
                )
            if not isinstance(overrides, dict):
                raise ValueError(
                    f"{path}: {WINDOWS_KEY}.{label} must be a JSON object, "
                    f"got {type(overrides).__name__}"
                )
            bad = sorted(set(overrides) - set(DEFAULT_BASELINE))
            if bad:
                raise ValueError(
                    f"{path}: unknown key(s) {', '.join(bad)} under {WINDOWS_KEY}.{label}; "
                    f"expected any of {', '.join(sorted(DEFAULT_BASELINE))}"
                )
            per_window[label] = {
                key: _validated_baseline_value(
                    key, overrides[key], f"{path} ({WINDOWS_KEY}.{label})"
                )
                for key in overrides
            }
    return top_level, per_window


def resolve_baseline_config(
    experiment_folder: Path,
    windows: Iterable[str],
    lam: float | None = None,
    p: float | None = None,
    n_iter: int | None = None,
) -> tuple[dict[str, dict[str, float | int]], dict[str, dict[str, str]]]:
    """Resolve baseline parameters for every window, per parameter.

    Precedence for each parameter of each window independently, most specific
    first: a CLI flag, then ``windows.<label>`` in ``baseline.json``, then the
    top level of ``baseline.json``, then the built-in default. Overriding one
    parameter leaves the others to the lower sources.

    Different windows can genuinely need different smoothness, because their
    backgrounds differ in kind: a flat background under a narrow line is not the
    same problem as a broad hump under a broad band envelope.

    Args:
        experiment_folder: The folder holding the experiment's ``.txt`` files.
        windows: The window labels present in the experiment.
        lam: Value from ``--baseline-lam``, or None. A flag applies to every
            window, so it also overrides per-window config.
        p: Value from ``--baseline-p``, or None.
        n_iter: Value from ``--baseline-n-iter``, or None.

    Returns:
        ``(values, sources)``, both keyed by window label then parameter name.

    Raises:
        ValueError: If a flag value is out of range, or ``baseline.json`` is
            malformed.
    """
    labels = sorted(set(windows))
    top_level, per_window = load_baseline_config(experiment_folder, labels)
    from_flags = {"lam": lam, "p": p, "n_iter": n_iter}

    values: dict[str, dict[str, float | int]] = {}
    sources: dict[str, dict[str, str]] = {}
    for label in labels:
        overrides = per_window.get(label, {})
        values[label] = {}
        sources[label] = {}
        for key in ("lam", "p", "n_iter"):
            flag = f"--baseline-{key.replace('_', '-')}"
            if from_flags[key] is not None:
                values[label][key] = _validated_baseline_value(key, from_flags[key], flag)
                # A global flag beating a per-window setting is easy to miss, so
                # the notice names both values rather than just the winner.
                if key in overrides:
                    sources[label][key] = (
                        f"{flag} (overrides {WINDOWS_KEY}.{label} "
                        f"{key}={overrides[key]!r} from {BASELINE_CONFIG_NAME})"
                    )
                elif key in top_level:
                    sources[label][key] = (
                        f"{flag} (overrides {key}={top_level[key]!r} "
                        f"from {BASELINE_CONFIG_NAME})"
                    )
                else:
                    sources[label][key] = flag
            elif key in overrides:
                values[label][key] = overrides[key]
                sources[label][key] = f"{BASELINE_CONFIG_NAME} {WINDOWS_KEY}.{label}"
            elif key in top_level:
                values[label][key] = top_level[key]
                sources[label][key] = SOURCE_CONFIG
            else:
                values[label][key] = DEFAULT_BASELINE[key]
                sources[label][key] = SOURCE_DEFAULT
    return values, sources


def print_baseline_config(
    values: dict[str, dict[str, float | int]], sources: dict[str, dict[str, str]]
) -> None:
    """Announce the resolved baseline parameters, per window, and their origin."""
    print("baseline parameters:")
    fallen_back: list[str] = []
    for label in sorted(values):
        print(f"  {label}:")
        for key in ("lam", "p", "n_iter"):
            print(f"    {key} = {values[label][key]!r}   from {sources[label][key]}")
            if sources[label][key] == SOURCE_DEFAULT:
                fallen_back.append(f"{label}.{key}={values[label][key]!r}")
    if fallen_back:
        print(
            f"  NOTE: no value supplied for {', '.join(fallen_back)}; using built-in "
            f"defaults. These suited one dataset and are not tuned for this one. "
            f"Set them in {BASELINE_CONFIG_NAME} or on the command line."
        )


BANDS_CONFIG_NAME = "bands.json"

# Below this the band height is comparable to the local noise and the measured
# trend is not worth believing. Flagged, never dropped: the number is still
# reported, marked so nobody reads it as solid.
MIN_SIGNAL_TO_NOISE = 10.0

# A located peak this far from its configured centre means the configuration no
# longer describes the band, whether because it shifted or because the search
# window is catching a neighbour.
MAX_POSITION_DRIFT = 5.0


@dataclass(frozen=True)
class BandSpec:
    """One configured band."""

    name: str
    centre: float
    half_width: float
    window: str


def load_bands_config(
    experiment_folder: Path, window_ranges: Mapping[str, tuple[float, float]]
) -> tuple[str, dict[str, BandSpec], dict[str, tuple[float, float]]]:
    """Read and validate ``bands.json`` from an experiment folder.

    Band names are arbitrary strings; nothing about any particular band is built
    in here.

    Every search window and noise region is checked against the data that is
    actually there, so a centre that no spectrum can measure fails here rather
    than at measurement time, before anything has been written.

    Args:
        experiment_folder: The folder holding the experiment's ``.txt`` files.
        window_ranges: The wave range every file of each window label shares,
            from :func:`common_window_ranges`. Its keys are the window labels
            present in the experiment, and are the only ones the config may
            name. Not the modal ranges: see that function for why.

    Returns:
        ``(reference_name, bands, noise_regions)``. ``noise_regions`` is empty
        for any window that configures none.

    Raises:
        FileNotFoundError: If the file is absent, naming the expected path.
        ValueError: If it is malformed, names an unknown window, omits or
            misnames the reference, defines overlapping search windows within
            one spectral window, places a search window or noise region outside
            the measured range of its window, or gives a bad noise region.
    """
    path = experiment_folder / BANDS_CONFIG_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"no band configuration found; expected {path}. "
            f"Create it to describe which bands to measure."
        )
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{path}: expected a JSON object, got {type(parsed).__name__}")

    allowed_top = {"reference", "bands", "noise_regions"}
    unknown = sorted(set(parsed) - allowed_top)
    if unknown:
        raise ValueError(
            f"{path}: unknown key(s) {', '.join(unknown)}; "
            f"expected any of {', '.join(sorted(allowed_top))}"
        )
    for required in ("reference", "bands"):
        if required not in parsed:
            raise ValueError(f"{path}: missing required key {required!r}")

    raw_bands = parsed["bands"]
    if not isinstance(raw_bands, dict) or not raw_bands:
        raise ValueError(f"{path}: 'bands' must be a non-empty JSON object")

    valid_windows = sorted(window_ranges)
    bands: dict[str, BandSpec] = {}
    for name, spec in raw_bands.items():
        where = f"{path} (bands.{name})"
        if not isinstance(spec, dict):
            raise ValueError(f"{where}: must be a JSON object, got {type(spec).__name__}")
        missing = sorted({"centre", "half_width", "window"} - set(spec))
        if missing:
            raise ValueError(f"{where}: missing key(s) {', '.join(missing)}")
        extra = sorted(set(spec) - {"centre", "half_width", "window"})
        if extra:
            raise ValueError(f"{where}: unknown key(s) {', '.join(extra)}")
        if spec["window"] not in valid_windows:
            raise ValueError(
                f"{where}: window {spec['window']!r} is not present in this experiment; "
                f"valid labels: {', '.join(valid_windows)}"
            )
        for key in ("centre", "half_width"):
            value = spec[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{where}: {key} must be a number, got {value!r}")
            if not math.isfinite(float(value)):
                raise ValueError(f"{where}: {key} must be finite, got {value!r}")
        if float(spec["half_width"]) <= 0:
            raise ValueError(
                f"{where}: half_width must be greater than 0, got {spec['half_width']!r}"
            )
        bands[name] = BandSpec(
            name=name,
            centre=float(spec["centre"]),
            half_width=float(spec["half_width"]),
            window=spec["window"],
        )

    reference = parsed["reference"]
    if not isinstance(reference, str):
        raise ValueError(f"{path}: 'reference' must be a string, got {reference!r}")
    if reference not in bands:
        raise ValueError(
            f"{path}: reference {reference!r} is not defined in 'bands'; "
            f"defined bands: {', '.join(sorted(bands))}"
        )

    # Two bands in one spectral window whose search windows intersect would
    # compete for the same maximum, so the pairing of name to peak stops being
    # meaningful. Bands in different windows can never conflict.
    ordered = sorted(bands.values(), key=lambda b: (b.window, b.centre))
    for first, second in zip(ordered, ordered[1:]):
        if first.window != second.window:
            continue
        if first.centre + first.half_width >= second.centre - second.half_width:
            raise ValueError(
                f"{path}: search windows for {first.name!r} "
                f"[{first.centre - first.half_width:.3f}, "
                f"{first.centre + first.half_width:.3f}] and {second.name!r} "
                f"[{second.centre - second.half_width:.3f}, "
                f"{second.centre + second.half_width:.3f}] overlap in window "
                f"{first.window!r}"
            )

    # Checked here rather than left to measure_band, which raises the same kind
    # of error but only once quantify has begun writing. Failing during config
    # loading means nothing has been written yet, and the message can name the
    # file and the band, neither of which measure_band can see. The late check
    # stays where it is as defence in depth for callers that bypass this one.
    for band in ordered:
        data_low, data_high = window_ranges[band.window]
        low, high = band.centre - band.half_width, band.centre + band.half_width
        if low < data_low or high > data_high:
            raise ValueError(
                f"{path} (bands.{band.name}): search window [{low:.3f}, {high:.3f}] "
                f"falls outside the measured range of window {band.window!r}, "
                f"[{data_low:.3f}, {data_high:.3f}]"
            )

    noise_regions: dict[str, tuple[float, float]] = {}
    raw_regions = parsed.get("noise_regions")
    if raw_regions is not None:
        if not isinstance(raw_regions, dict):
            raise ValueError(
                f"{path}: 'noise_regions' must be a JSON object, "
                f"got {type(raw_regions).__name__}"
            )
        for label, region in raw_regions.items():
            where = f"{path} (noise_regions.{label})"
            if label not in valid_windows:
                raise ValueError(
                    f"{where}: window {label!r} is not present in this experiment; "
                    f"valid labels: {', '.join(valid_windows)}"
                )
            if (
                not isinstance(region, list)
                or len(region) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in region)
            ):
                raise ValueError(f"{where}: expected a [low, high] pair of numbers")
            low, high = float(region[0]), float(region[1])
            if not low < high:
                raise ValueError(f"{where}: expected low < high, got [{low}, {high}]")
            # Same exposure as a band search window, and the same fix:
            # estimate_noise would otherwise catch this only at measurement.
            data_low, data_high = window_ranges[label]
            if low < data_low or high > data_high:
                raise ValueError(
                    f"{where}: noise region [{low:.3f}, {high:.3f}] falls outside "
                    f"the measured range of window {label!r}, "
                    f"[{data_low:.3f}, {data_high:.3f}]"
                )
            noise_regions[label] = (low, high)

    return reference, bands, noise_regions


def _group_key(key: tuple[str, str]) -> tuple[str, int]:
    """Sort key putting groups in sample order, then low window before high."""
    sample, window = key
    return sample, window_sort_key(window)


def axis_difference(group: list[Spectrum]) -> tuple[bool, float | None]:
    """Compare the wave axes within a group against its first member.

    Args:
        group: Spectra sharing a ``(sample, window)`` key.

    Returns:
        ``(comparable, max_abs_difference)``. ``comparable`` is False when the
        spectra differ in length, in which case the difference is None.
    """
    reference = group[0].wave
    if any(s.wave.shape != reference.shape for s in group):
        return False, None
    worst = 0.0
    for spectrum in group[1:]:
        worst = max(worst, float(np.max(np.abs(spectrum.wave - reference))))
    return True, worst


def content_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's raw bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _modal_range(
    ranges: list[tuple[float, float]], tolerance: float
) -> tuple[tuple[float, float], int]:
    """Return the most widely shared ``(min, max)`` pair and how many files match.

    A candidate matches a file when both ends agree to within ``tolerance``.
    Ties are broken toward the pair that occurs most often exactly, so a
    low-precision export cannot become the representative for a label whose
    other files agree on a fuller-precision value.

    Args:
        ranges: One ``(min, max)`` pair per file carrying a window label.
        tolerance: Half-width, in cm-1, of the cluster around a candidate.

    Returns:
        ``(modal_range, cluster_size)``.
    """
    best: tuple[tuple[float, float], int] | None = None
    best_score = (-1, -1)
    for candidate in sorted(set(ranges)):
        cluster = sum(
            1
            for low, high in ranges
            if abs(low - candidate[0]) <= tolerance and abs(high - candidate[1]) <= tolerance
        )
        score = (cluster, ranges.count(candidate))
        if score > best_score:
            best, best_score = (candidate, cluster), score
    assert best is not None
    return best


def derive_window_ranges(
    spectra: list[Spectrum],
) -> tuple[dict[str, tuple[float, float]], dict[str, bool], list[Finding]]:
    """Derive each window label's wave range from the files themselves.

    Nothing about the spectrometer is assumed: the range for a label is the
    ``(min, max)`` pair shared by the largest number of files carrying that
    label, within :data:`MODE_TOLERANCE`.

    This is strictly weaker than hardcoded literals against one failure mode: if
    most files carrying a label were mislabelled, they would define the mode and
    the correct minority would be flagged instead. The inter-label disjointness
    check in :func:`collect_warnings` is the backstop for that case, which is
    why it runs unconditionally.

    Args:
        spectra: Every spectrum in the experiment.

    Returns:
        ``(ranges, trusted, observations)`` where ``ranges`` maps each label to
        its modal range, ``trusted`` says whether that label had enough agreeing
        files to check individual files against, and ``observations`` holds the
        soft notes for labels that did not.
    """
    by_label: dict[str, list[tuple[float, float]]] = {}
    for spectrum in spectra:
        by_label.setdefault(spectrum.window, []).append(
            (float(spectrum.wave.min()), float(spectrum.wave.max()))
        )

    ranges: dict[str, tuple[float, float]] = {}
    trusted: dict[str, bool] = {}
    observations: list[Finding] = []
    for label in sorted(by_label, key=window_sort_key):
        found = by_label[label]
        modal, cluster = _modal_range(found, MODE_TOLERANCE)
        ranges[label] = modal
        if len(found) < MIN_FILES_FOR_MODE:
            trusted[label] = False
            observations.append(
                (
                    SOFT,
                    f"{label}: only {len(found)} file(s) carry this window label, fewer than "
                    f"{MIN_FILES_FOR_MODE} - wave range check skipped for this label",
                )
            )
        elif cluster * 2 <= len(found):
            trusted[label] = False
            observations.append(
                (
                    SOFT,
                    f"{label}: no majority wave range among {len(found)} files "
                    f"(largest cluster {cluster}) - wave range check skipped for this label",
                )
            )
        else:
            trusted[label] = True
    return ranges, trusted, observations


def common_window_ranges(spectra: list[Spectrum]) -> dict[str, tuple[float, float]]:
    """Return the wave range every file carrying a window label shares.

    Deliberately not :func:`derive_window_ranges`, and not a variant of it: the
    two answer different questions and must not be confused.
    :func:`derive_window_ranges` returns the *modal* range - what a typical file
    with this label looks like - which is the right basis for spotting one
    mislabelled file against its peers.

    This returns the *intersection*: the widest span that every file with the
    label can actually measure. That is the only sound bound for a band search
    window, because :func:`~ramsess.bands.measure_band` checks each spectrum
    against its own axis. A band inside the modal range but outside one narrow
    outlier would pass configuration and then fail at measurement, which is the
    late failure the bound exists to prevent.

    Args:
        spectra: Every spectrum in the experiment.

    Returns:
        ``{label: (highest minimum, lowest maximum)}``, one entry per label
        present. A label whose files disagree yields a narrower span than any
        modal range would, which is the intended conservatism.
    """
    ranges: dict[str, tuple[float, float]] = {}
    for spectrum in spectra:
        low, high = float(spectrum.wave.min()), float(spectrum.wave.max())
        if spectrum.window in ranges:
            have_low, have_high = ranges[spectrum.window]
            ranges[spectrum.window] = (max(have_low, low), min(have_high, high))
        else:
            ranges[spectrum.window] = (low, high)
    return ranges


def print_spectra(spectra: list[Spectrum]) -> None:
    """Print one line per spectrum."""
    print("== spectra ==")
    header = (
        f"{'filename':28s} {'sample':10s} {'window':6s} {'step':>4s} {'n':>5s} "
        f"{'wave_min':>11s} {'wave_max':>11s} {'int_min':>13s} {'int_max':>13s}"
    )
    print(header)
    for s in spectra:
        print(
            f"{s.path.name:28s} {s.sample:10s} {s.window:6s} {s.step:4d} {s.wave.size:5d} "
            f"{s.wave.min():11.4f} {s.wave.max():11.4f} "
            f"{s.intensity.min():13.4f} {s.intensity.max():13.4f}"
        )


def print_groups(groups: dict[tuple[str, str], list[Spectrum]]) -> None:
    """Print a per-(sample, window) summary."""
    print("\n== groups ==")
    for key in sorted(groups, key=_group_key):
        group = groups[key]
        steps = [s.step for s in group]
        comparable, worst = axis_difference(group)
        if not comparable:
            axis = "axes NOT comparable (differing lengths)"
        elif worst == 0.0:
            axis = "axes identical (max diff 0)"
        elif worst < PRECISION_TOLERANCE:
            axis = f"axes agree to export precision (max diff {worst:.6g})"
        else:
            axis = f"axes DIFFER (max diff {worst:.6g})"
        print(f"  {key[0]:10s} {key[1]:5s} steps={steps}  {axis}")


def collect_warnings(
    spectra: list[Spectrum], groups: dict[tuple[str, str], list[Spectrum]]
) -> list[Finding]:
    """Gather observations about the experiment, each tagged with a severity.

    Args:
        spectra: All spectra in the experiment.
        groups: The same spectra keyed by ``(sample, window)``.

    Returns:
        ``(severity, message)`` pairs in reporting order, where severity is
        :data:`HARD` or :data:`SOFT`.
    """
    warnings: list[Finding] = []

    for key in sorted(groups, key=_group_key):
        sample, window = key
        steps = [s.step for s in groups[key]]
        irradiation = [n for n in steps if n > 0]
        if irradiation and 0 not in steps:
            warnings.append(
                (
                    SOFT,
                    f"{sample} {window}: no control (step 0) but has irradiation "
                    f"steps {irradiation}",
                )
            )
        if irradiation:
            missing = sorted(set(range(1, max(irradiation) + 1)) - set(irradiation))
            if missing:
                warnings.append(
                    (SOFT, f"{sample} {window}: gap in step sequence, missing {missing}")
                )

    windows_by_sample: dict[str, set[str]] = {}
    for sample, window in groups:
        windows_by_sample.setdefault(sample, set()).add(window)
    for sample in sorted(windows_by_sample):
        present = sorted(windows_by_sample[sample], key=window_sort_key)
        if len(present) < 2:
            warnings.append((SOFT, f"{sample}: present in only one window ({present[0]})"))

    # Differing lengths and an above-threshold mismatch are both HARD: they mean
    # files in the same group disagree about the wave axis, which is the same
    # class of integrity failure as a duplicate or a window mismatch, and neither
    # can be true of correctly acquired data from one instrument. Only the
    # sub-threshold case is SOFT - that is the known ech4 export quirk.
    for key in sorted(groups, key=_group_key):
        comparable, worst = axis_difference(groups[key])
        if not comparable:
            warnings.append((HARD, f"{key[0]} {key[1]}: wave axes have differing lengths"))
        elif worst and worst < PRECISION_TOLERANCE:
            warnings.append(
                (
                    SOFT,
                    f"{key[0]} {key[1]}: wave axes differ by {worst:.6g}, below "
                    f"{PRECISION_TOLERANCE} - export precision difference, not an axis mismatch",
                )
            )
        elif worst:
            warnings.append(
                (HARD, f"{key[0]} {key[1]}: wave axes mismatch, max difference {worst:.6g}")
            )

    for s in spectra:
        if not s.has_header:
            warnings.append((SOFT, f"{s.path.name}: no '#' header line, first line is data"))

    window_ranges, trusted, range_observations = derive_window_ranges(spectra)
    warnings.extend(range_observations)

    # Unconditional: two window labels whose ranges overlap cannot both be right,
    # whatever the file counts. This is the backstop against a wholesale mislabel
    # defining its own mode, so it runs even for labels the mode rule skipped.
    labels = sorted(window_ranges, key=window_sort_key)
    for i, first in enumerate(labels):
        for second in labels[i + 1 :]:
            a_low, a_high = window_ranges[first]
            b_low, b_high = window_ranges[second]
            if a_low <= b_high and b_low <= a_high:
                warnings.append(
                    (
                        HARD,
                        f"window ranges overlap: '{first}' [{a_low:.3f}, {a_high:.3f}] and "
                        f"'{second}' [{b_low:.3f}, {b_high:.3f}] - windows must be disjoint",
                    )
                )

    for s in spectra:
        if not trusted.get(s.window, False):
            continue
        low, high = window_ranges[s.window]
        if s.wave.min() < low - MODE_TOLERANCE or s.wave.max() > high + MODE_TOLERANCE:
            warnings.append(
                (
                    HARD,
                    f"{s.path.name}: wave range [{s.wave.min():.3f}, {s.wave.max():.3f}] falls "
                    f"outside the '{s.window}' window range [{low:.3f}, {high:.3f}] - "
                    f"contents may not match the window in the filename",
                )
            )

    by_hash: dict[str, list[str]] = {}
    for s in spectra:
        by_hash.setdefault(content_hash(s.path), []).append(s.path.name)
    for digest in sorted(by_hash):
        names = sorted(by_hash[digest])
        if len(names) > 1:
            warnings.append(
                (
                    HARD,
                    f"identical file contents: {', '.join(names)} (sha256 {digest[:16]})",
                )
            )

    return warnings


def hard_failures(findings: list[Finding]) -> list[str]:
    """Return the messages of the hard findings only."""
    return [message for severity, message in findings if severity == HARD]


def preflight(
    subcommand: str, experiment: str, spectra: list[Spectrum], force: bool = False
) -> None:
    """Run the hard checks and refuse to continue if any fire.

    Every subcommand that touches data should call this before doing so; one
    call is all the gating a new subcommand needs.

    Args:
        subcommand: Name of the calling subcommand, used in the messages.
        experiment: Name of the experiment folder under the raw data root.
        spectra: Every spectrum loaded from that folder.
        force: Continue anyway after warning loudly.

    Raises:
        HardCheckFailure: If hard checks fail and ``force`` is not set. The
            individual failures are printed to stderr before raising.
    """
    failures = hard_failures(collect_warnings(spectra, group_spectra(spectra)))
    if not failures:
        return
    if not force:
        print(
            f"refusing to {subcommand} {experiment}: {len(failures)} hard check(s) failed",
            file=sys.stderr,
        )
        for message in failures:
            print(f"  {message}", file=sys.stderr)
        print("re-run with --force to continue anyway", file=sys.stderr)
        raise HardCheckFailure(
            f"{len(failures)} hard check(s) failed for experiment {experiment!r}"
        )
    print("!" * 78, file=sys.stderr)
    print(
        f"WARNING: --force overriding {len(failures)} failed hard check(s) in {experiment}.",
        file=sys.stderr,
    )
    print("The figures below may not show the data their filenames claim.", file=sys.stderr)
    for message in failures:
        print(f"  OVERRIDDEN: {message}", file=sys.stderr)
    print("!" * 78, file=sys.stderr)


def print_warnings(findings: list[Finding]) -> None:
    """Print the warnings section."""
    print("\n== warnings ==")
    if not findings:
        print("  none")
        return
    for _, message in findings:
        print(f"  {message}")


def write_sample_overlays(
    experiment: str,
    spectra: list[Spectrum],
    figures_root: Path,
    sample: str | None = None,
    logy: bool = False,
    force: bool = False,
    baseline: bool = False,
    diagnostic: bool = False,
    baseline_params: dict[str, float | int] | None = None,
) -> list[Path]:
    """Write one overlay figure per sample and print a line for each.

    Hard checks run before anything is drawn. If any fire, nothing is written
    unless ``force`` is set, because a hard finding means a file is not what its
    name says and any figure drawn from it would be quietly wrong.

    Args:
        experiment: Name of the experiment folder under the raw data root.
        spectra: Every spectrum loaded from that folder.
        figures_root: Directory holding one subfolder per experiment.
        sample: Restrict output to this sample; None writes every sample.
        logy: Put both panels on a log y-scale.
        force: Draw anyway when hard checks fail, after warning loudly.
        baseline: Write baseline-corrected overlays instead of raw ones.
        diagnostic: Write one fit-inspection figure per sample per window.
        baseline_params: ``lam``, ``p`` and ``n_iter``, required when either
            baseline mode is on.

    Returns:
        The paths written, in sample order.

    Raises:
        HardCheckFailure: If hard checks fail and ``force`` is not set. The
            individual failures are printed to stderr before raising.
        ValueError: If ``sample`` names a sample not present in the experiment,
            or a baseline mode is requested without parameters.
    """
    # Imported here so that the inspect path never pulls in matplotlib and never
    # has the process backend fixed to Agg on its behalf.
    from ramsess.plotting import plot_baseline_diagnostic, plot_sample_overlay

    if (baseline or diagnostic) and baseline_params is None:
        raise ValueError("a baseline mode was requested without baseline parameters")

    preflight("plot", experiment, spectra, force=force)

    by_sample: dict[str, list[Spectrum]] = {}
    for spectrum in spectra:
        by_sample.setdefault(spectrum.sample, []).append(spectrum)

    if sample is not None:
        if sample not in by_sample:
            raise ValueError(
                f"sample {sample!r} not found in experiment {experiment!r}; "
                f"available samples: {', '.join(sorted(by_sample))}"
            )
        wanted = [sample]
    else:
        wanted = sorted(by_sample)

    output_directory = figures_root / experiment

    # Filenames encode every flag that changes what is drawn, so that the same
    # path always means the same bytes and no combination can overwrite
    # another's output. Only `logy` needs encoding: it changes the two overlay
    # figures, and the diagnostic figure does not take it at all. The scheme is
    # computed here from the flags this function already has rather than being
    # injectable - if a caller ever needs to override it, this is the place.
    scale_suffix = LOG_SCALE_SUFFIX if logy else ""

    written: list[Path] = []
    for name in wanted:
        group = by_sample[name]

        # Raw stays the default. A baseline mode writes to its own filenames and
        # never touches the raw figure, so both persist side by side on disk.
        if not baseline and not diagnostic:
            path = plot_sample_overlay(
                group, output_directory / f"{name}_overlay{scale_suffix}.png", logy=logy
            )
            written.append(path)
            print(f"wrote {path}   {_dominance(group)}")

        if baseline:
            path = plot_sample_overlay(
                group,
                output_directory / f"{name}_overlay_baseline{scale_suffix}.png",
                logy=logy,
                baseline_params=baseline_params,
            )
            written.append(path)
            print(f"wrote {path}   baseline corrected   {_dominance(group)}")

        if diagnostic:
            by_window: dict[str, list[Spectrum]] = {}
            for spectrum in group:
                by_window.setdefault(spectrum.window, []).append(spectrum)
            for window in sorted(by_window, key=window_sort_key):
                path = plot_baseline_diagnostic(
                    by_window[window],
                    output_directory / f"{name}_{window}_baseline_check.png",
                    baseline_params,
                )
                written.append(path)
                print(f"wrote {path}   {len(by_window[window])} step(s)")
    return written


def _dominance(spectra: list[Spectrum]) -> str:
    """Describe how one sample's low and high window maxima compare."""
    maxima: dict[str, float] = {}
    for spectrum in spectra:
        peak = float(spectrum.intensity.max())
        maxima[spectrum.window] = max(maxima.get(spectrum.window, peak), peak)
    low, high = maxima.get("low"), maxima.get("high")
    if low is None or high is None:
        present = "low" if low is not None else "high"
        return f"{present} window only, max={maxima[present]:.1f}"
    ratio = low / high
    direction = "low-dominant" if ratio >= 1.0 else "high-dominant"
    return f"low_max={low:.1f} high_max={high:.1f} low/high={ratio:.2f} {direction}"


# Appended to the figures whose content depends on the y-scale, so a log-scaled
# run cannot land on the linear run's filename. The diagnostic figure never
# takes `logy`, so it carries no suffix.
LOG_SCALE_SUFFIX = "_log"

DERIVED_HEADER = (
    "# wave(cm-1)\tcorrected_intensity(counts)\tfitted_baseline(counts)"
    "\t# raw = corrected + fitted_baseline"
)


def write_derived_spectra(
    experiment: str,
    spectra: list[Spectrum],
    derived_root: Path,
    raw_root: Path,
    baseline_params: dict[str, dict[str, float | int]],
) -> tuple[list[Path], float]:
    """Write one corrected-spectrum file per input, then verify by reading back.

    Three columns rather than two so the file documents itself and the raw data
    can be reconstructed by summing columns 2 and 3.

    Args:
        experiment: Name of the experiment folder.
        spectra: Every spectrum to export.
        derived_root: Root of the derived output tree.
        raw_root: The read-only raw root, for the write guard.
        baseline_params: Parameters keyed by window label.

    Returns:
        ``(paths_written, worst_reconstruction_residual)``.

    Raises:
        ValueError: If a target would land under ``raw_root``, or if a written
            file does not reconstruct its raw spectrum on read-back.
    """
    from ramsess.analysis import correct_baseline

    folder = guard_not_under_raw(derived_root / experiment, raw_root)
    folder.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    worst = 0.0
    for spectrum in spectra:
        corrected, baseline = correct_baseline(spectrum, **baseline_params[spectrum.window])
        name = f"{spectrum.sample}_{spectrum.window}_{spectrum.step}_corrected.txt"
        path = guard_not_under_raw(folder / name, raw_root)
        lines = [DERIVED_HEADER]
        for w, c, b in zip(spectrum.wave, corrected, baseline):
            lines.append(f"{w:.6f}\t{c:.6f}\t{b:.6f}")
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        written.append(path)

        # Read back rather than trusting the arrays still in memory: the point
        # is to prove what landed on disk reconstructs the file it came from.
        table = np.loadtxt(path, comments="#", dtype=np.float64)
        scale = float(np.max(np.abs(spectrum.intensity))) or 1.0
        residual = float(np.max(np.abs(table[:, 1] + table[:, 2] - spectrum.intensity)))
        worst = max(worst, residual)
        if residual > 1e-6 * scale:
            raise ValueError(
                f"{path.name}: columns 2 and 3 do not reconstruct the raw spectrum; "
                f"max residual {residual:.6g} against a scale of {scale:.6g}"
            )
    return written, worst


def write_provenance(
    experiment: str,
    spectra: list[Spectrum],
    derived_root: Path,
    raw_root: Path,
    baseline_params: dict[str, dict[str, float | int]],
    baseline_sources: dict[str, dict[str, str]],
) -> Path:
    """Record how the derived files were made, for someone finding them later.

    Args:
        experiment: Name of the experiment folder.
        spectra: Every spectrum that fed the export.
        derived_root: Root of the derived output tree.
        raw_root: The read-only raw root, for the write guard.
        baseline_params: Parameters actually used, keyed by window.
        baseline_sources: Where each of those values came from.

    Returns:
        The path written.
    """
    path = guard_not_under_raw(derived_root / experiment / "provenance.json", raw_root)
    payload = {
        "experiment": experiment,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_parameters": {
            window: {
                key: {"value": values[key], "source": baseline_sources[window][key]}
                for key in sorted(values)
            }
            for window, values in baseline_params.items()
        },
        "source_files": [
            {
                "name": spectrum.path.name,
                "sample": spectrum.sample,
                "window": spectrum.window,
                "step": spectrum.step,
                "sha256": content_hash(spectrum.path),
                "n_points": int(spectrum.wave.size),
            }
            for spectrum in spectra
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def measure_all_bands(
    spectra: list[Spectrum],
    bands: dict[str, BandSpec],
    reference: str,
    noise_regions: dict[str, tuple[float, float]],
    baseline_params: dict[str, dict[str, float | int]],
) -> list[dict[str, object]]:
    """Measure every configured band in every spectrum and normalise.

    Args:
        spectra: Every spectrum in the experiment.
        bands: Configured bands by name.
        reference: Name of the band used for normalisation.
        noise_regions: Featureless region per window, possibly empty.
        baseline_params: Parameters keyed by window label.

    Returns:
        One row per (sample, window, step, band), each a flat mapping.
    """
    from ramsess.analysis import correct_baseline
    from ramsess.bands import estimate_noise, measure_band

    reference_window = bands[reference].window

    corrected: dict[tuple[str, str, int], tuple[Spectrum, np.ndarray]] = {}
    for spectrum in spectra:
        values, _ = correct_baseline(spectrum, **baseline_params[spectrum.window])
        corrected[(spectrum.sample, spectrum.window, spectrum.step)] = (spectrum, values)

    noise: dict[tuple[str, str, int], float | None] = {}
    for key, (spectrum, values) in corrected.items():
        region = noise_regions.get(spectrum.window)
        noise[key] = (
            estimate_noise(spectrum.wave, values, region) if region is not None else None
        )

    rows: list[dict[str, object]] = []
    by_sample_step: dict[tuple[str, int], dict[str, object]] = {}

    # The reference is measured first for every (sample, step), because every
    # other band in that step is normalised against it.
    for name in [reference] + [n for n in sorted(bands) if n != reference]:
        spec = bands[name]
        for (sample, window, step), (spectrum, values) in sorted(corrected.items()):
            if window != spec.window:
                continue
            measurement = measure_band(
                spectrum.wave,
                values,
                spec.centre,
                spec.half_width,
                noise=noise[(sample, window, step)],
            )
            row: dict[str, object] = {
                "sample": sample,
                "window": window,
                "step": step,
                "band": name,
                "centre": spec.centre,
                "position": measurement.position,
                "height": measurement.height,
                "area": measurement.area,
                "n_points": measurement.n_points,
                "at_edge": measurement.at_edge,
                "noise": measurement.noise,
                "signal_to_noise": measurement.signal_to_noise,
                "position_drift": measurement.position - spec.centre,
            }
            if name == reference:
                by_sample_step[(sample, step)] = {
                    "height": measurement.height,
                    "area": measurement.area,
                }
            rows.append(row)

    for row in rows:
        anchor = by_sample_step.get((row["sample"], row["step"]))
        height = anchor["height"] if anchor else None
        area = anchor["area"] if anchor else None
        row["height_norm"] = (
            row["height"] / height if height not in (None, 0.0) else None
        )
        row["area_norm"] = row["area"] / area if area not in (None, 0.0) else None
        # Low and high are separate sequential sweeps. Normalising a band in one
        # against a reference in the other assumes both sweeps shared the same
        # collection efficiency - plausible, untested. Never present such a
        # number without saying so.
        row["cross_window"] = row["window"] != reference_window
    return rows


BANDS_CSV_COLUMNS = [
    "sample",
    "window",
    "step",
    "band",
    "centre",
    "position",
    "position_drift",
    "height",
    "area",
    "n_points",
    "at_edge",
    "noise",
    "signal_to_noise",
    "height_norm",
    "area_norm",
    "cross_window",
]


def write_bands_csv(
    experiment: str, rows: list[dict[str, object]], derived_root: Path, raw_root: Path
) -> Path:
    """Write the per-measurement table."""
    path = guard_not_under_raw(derived_root / experiment / "bands.csv", raw_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BANDS_CSV_COLUMNS)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["sample"], r["step"], r["band"])):
            writer.writerow({key: row.get(key) for key in BANDS_CSV_COLUMNS})
    return path


def print_band_summary(rows: list[dict[str, object]], reference: str) -> None:
    """Print the compact quantification summary."""
    print("\n== reference band ==")
    print(f"  {reference}: absolute height and area per sample and step")
    print(f"    {'sample':8s} {'step':>5s} {'height':>14s} {'area':>16s} {'position':>10s}")
    for row in sorted(
        (r for r in rows if r["band"] == reference), key=lambda r: (r["sample"], r["step"])
    ):
        label = "control" if row["step"] == 0 else f"irr{row['step']}"
        print(
            f"    {row['sample']:8s} {label:>5s} {row['height']:14.1f} "
            f"{row['area']:16.1f} {row['position']:10.2f}"
        )

    print("\n== normalised band heights ==")
    bands = sorted({str(r["band"]) for r in rows})
    samples = sorted({str(r["sample"]) for r in rows})
    for sample in samples:
        steps = sorted({int(r["step"]) for r in rows if r["sample"] == sample})
        print(f"  {sample}:")
        print("    " + "band".ljust(16) + "".join(f"{('c' if s == 0 else f'i{s}'):>9s}" for s in steps))
        for band in bands:
            cells = []
            for step in steps:
                match = [
                    r
                    for r in rows
                    if r["sample"] == sample and r["step"] == step and r["band"] == band
                ]
                if not match:
                    cells.append(f"{'-':>9s}")
                    continue
                row = match[0]
                value = row["height_norm"]
                mark = ""
                if row["at_edge"]:
                    mark = "E"
                elif row["signal_to_noise"] is not None and (
                    row["signal_to_noise"] < MIN_SIGNAL_TO_NOISE
                ):
                    mark = "~"
                cells.append(f"{value:8.4f}{mark}" if value is not None else f"{'-':>9s}")
            flag = " *" if any(
                r["cross_window"] for r in rows if r["band"] == band
            ) else "  "
            print(f"    {band:16s}" + "".join(cells) + flag)

    weak = [r for r in rows if r["signal_to_noise"] is not None and r["signal_to_noise"] < MIN_SIGNAL_TO_NOISE]
    edged = [r for r in rows if r["at_edge"]]
    drifted = [r for r in rows if abs(float(r["position_drift"])) > MAX_POSITION_DRIFT]
    cross = [r for r in rows if r["cross_window"]]
    have_noise = any(r["signal_to_noise"] is not None for r in rows)

    print("\n== flags ==")
    print("  '~' signal-to-noise below "
          f"{MIN_SIGNAL_TO_NOISE:g}, 'E' peak on the search-window edge, "
          "'*' cross-window normalisation")
    if not have_noise:
        print(
            "  no noise_regions configured in bands.json, so no signal-to-noise "
            "was computed and no weak-band flagging was possible"
        )
    else:
        print(f"  measurements below SNR {MIN_SIGNAL_TO_NOISE:g}: {len(weak)} of {len(rows)}")
        for row in sorted(weak, key=lambda r: (r["sample"], r["band"], r["step"]))[:24]:
            print(
                f"    {row['sample']} {row['band']} step {row['step']}: "
                f"SNR {row['signal_to_noise']:.1f} (height {row['height']:.1f}, "
                f"noise {row['noise']:.1f})"
            )
        if len(weak) > 24:
            print(f"    ... and {len(weak) - 24} more, see bands.csv")

    if edged:
        print(f"  peaks on a search-window edge: {len(edged)}")
        for row in sorted(edged, key=lambda r: (r["sample"], r["band"], r["step"]))[:12]:
            print(
                f"    {row['sample']} {row['band']} step {row['step']}: "
                f"position {row['position']:.2f} vs centre {row['centre']:.2f}"
            )

    by_band_sample: dict[tuple[str, str], list[float]] = {}
    for row in drifted:
        by_band_sample.setdefault(
            (str(row["sample"]), str(row["band"])), []
        ).append(float(row["position_drift"]))
    if by_band_sample:
        print(
            f"  bands whose located position moved more than "
            f"{MAX_POSITION_DRIFT:g} cm-1 from the configured centre:"
        )
        for (sample, band), drifts in sorted(by_band_sample.items()):
            print(
                f"    {sample} {band}: {len(drifts)} step(s), drift "
                f"{min(drifts):+.2f} to {max(drifts):+.2f} cm-1"
            )

    if cross:
        windows = sorted({str(r["window"]) for r in cross})
        print(
            f"  CROSS-WINDOW NORMALISATION: {len(cross)} measurement(s) in window(s) "
            f"{', '.join(windows)} were normalised to reference {reference!r}, which "
            f"lies in a different spectral window."
        )
        print(
            "    Low and high are separate sequential sweeps, so this assumes both "
            "shared the same collection efficiency. That assumption is plausible "
            "here but untested. Treat those ratios accordingly."
        )


def quantify_experiment(
    experiment: str,
    spectra: list[Spectrum],
    raw_root: Path,
    derived_root: Path,
    figures_root: Path,
    baseline_params: dict[str, dict[str, float | int]],
    baseline_sources: dict[str, dict[str, str]],
    sample: str | None = None,
    force: bool = False,
) -> list[dict[str, object]]:
    """Measure the configured bands, then export corrected spectra and report.

    Nothing is written until measurement has succeeded. A run that fails leaves
    no derived tree at all, so a tree that exists is always one whose
    measurements completed and can never be mistaken for a successful export.

    Deliberately has no CLI override for the baseline parameters. quantify
    writes derived data, and derived data must be reproducible from raw plus
    config alone; a flag would let someone generate derived files whose
    parameters exist only in their shell history. plot is exploratory and keeps
    the escape hatch, quantify is the record and does not.

    Args:
        experiment: Name of the experiment folder.
        spectra: Every spectrum loaded from it.
        raw_root: The read-only raw root.
        derived_root: Root of the derived output tree.
        figures_root: Root of the figure tree.
        baseline_params: Parameters keyed by window label.
        baseline_sources: Where each of those values came from.
        sample: Restrict measurement and figures to this sample.
        force: Continue when hard checks fail, after warning loudly.

    Returns:
        The measurement rows.

    Raises:
        FileNotFoundError: If ``bands.json`` is absent.
        HardCheckFailure: If hard checks fail and ``force`` is not set.
        ValueError: If configuration or measurement fails.
    """
    from ramsess.plotting import plot_all_sample_band_trends, plot_sample_band_trends

    preflight("quantify", experiment, spectra, force=force)

    window_ranges = common_window_ranges(spectra)
    reference, bands, noise_regions = load_bands_config(
        raw_root / experiment, window_ranges
    )

    if noise_regions:
        # Physical order, low before high, never alphabetical - the same rule
        # every other window ordering in this codebase follows.
        for label in sorted(noise_regions, key=window_sort_key):
            low, high = noise_regions[label]
            print(f"  noise region for {label}: [{low:g}, {high:g}] cm-1")
    else:
        print(
            f"  no noise_regions configured in {BANDS_CONFIG_NAME}; "
            f"signal-to-noise will not be computed"
        )

    wanted = spectra
    if sample is not None:
        available = sorted({s.sample for s in spectra})
        if sample not in available:
            raise ValueError(
                f"sample {sample!r} not found in experiment {experiment!r}; "
                f"available samples: {', '.join(available)}"
            )
        wanted = [s for s in spectra if s.sample == sample]

    # Measurement runs before anything is written. The validation above catches
    # the configuration errors it can name, but not every one: a search window
    # that sits inside the data yet holds too few points still fails here, and
    # so would anything neither check anticipates. Ordering, not enumeration, is
    # what makes the guarantee - a derived tree that exists is a tree whose
    # measurements completed. A failed run leaves nothing behind to be mistaken
    # for a successful export.
    rows = measure_all_bands(wanted, bands, reference, noise_regions, baseline_params)

    written, worst = write_derived_spectra(
        experiment, spectra, derived_root, raw_root, baseline_params
    )
    print(f"wrote {len(written)} corrected spectra to {derived_root / experiment}")
    print(f"  worst reconstruction residual on read-back: {worst:.6g}")
    provenance = write_provenance(
        experiment, spectra, derived_root, raw_root, baseline_params, baseline_sources
    )
    print(f"wrote {provenance}")

    csv_path = write_bands_csv(experiment, rows, derived_root, raw_root)
    print(f"wrote {csv_path}   {len(rows)} measurement(s)")

    output_directory = guard_not_under_raw(figures_root / experiment, raw_root)
    for name in sorted({str(r["sample"]) for r in rows}):
        path = plot_sample_band_trends(
            rows,
            name,
            reference,
            guard_not_under_raw(output_directory / f"{name}_bands.png", raw_root),
            MIN_SIGNAL_TO_NOISE,
        )
        print(f"wrote {path}")
    path = plot_all_sample_band_trends(
        rows,
        reference,
        guard_not_under_raw(output_directory / "bands_all_samples.png", raw_root),
        MIN_SIGNAL_TO_NOISE,
    )
    print(f"wrote {path}")

    print_band_summary(rows, reference)
    return rows


def print_report(experiment: str, spectra: list[Spectrum]) -> list[Finding]:
    """Print the full inspection report for one experiment.

    Args:
        experiment: Name of the experiment folder under the raw data root.
        spectra: Every spectrum loaded from that folder.

    Returns:
        The findings that were printed, so a caller can gate on their severity.
    """
    groups = group_spectra(spectra)
    print(f"experiment: {experiment}   files: {len(spectra)}   groups: {len(groups)}")
    print_spectra(spectra)
    print_groups(groups)
    findings = collect_warnings(spectra, groups)
    print_warnings(findings)
    return findings
