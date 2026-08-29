"""Reading RAMSESS spectra from disk.

This module only reads and organises data. It never smooths, baseline-corrects,
normalises, despikes, resamples, converts units, sorts or otherwise alters the
numbers it returns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Listed in the physical order of the spectral windows, low before high. Both
# the accepted window labels and their sort order come from this one tuple.
WINDOW_ORDER = ("low", "high")
VALID_WINDOWS = WINDOW_ORDER

_STEP_RE = re.compile(r"^irr([1-9][0-9]*)$")


def guard_not_under_raw(path: Path, raw_root: Path) -> Path:
    """Refuse to hand back a write target that lives under the raw data root.

    Raw files are the experiment. They are the one thing here that cannot be
    regenerated, so no code path may write into them: derived data and figures
    are reproducible from raw plus config, and raw is not reproducible from
    anything. This is a tripwire in the same spirit as the plotting one - it
    catches the mistake at the moment it would happen and names the path.

    It guards the sites that call it, not the whole process; nothing short of
    replacing ``open`` globally could do that. Every write in this codebase goes
    through it, and any new one must too.

    Args:
        path: The intended write target.
        raw_root: The read-only raw data root.

    Returns:
        ``path`` unchanged, so this can wrap a path at the point of use.

    Raises:
        ValueError: If ``path`` is inside ``raw_root``.
    """
    resolved = path.resolve()
    root = raw_root.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError(
            f"refusing to write inside the raw data root: {resolved} is under {root}. "
            f"Raw data is read-only; derived output belongs under data/derived/."
        )
    return path


def window_sort_key(window: str) -> int:
    """Return the sort position of a spectral window, low before high.

    Args:
        window: A window label.

    Returns:
        The window's index in :data:`WINDOW_ORDER`.

    Raises:
        ValueError: If the label is not a known window.
    """
    try:
        return WINDOW_ORDER.index(window)
    except ValueError:
        raise ValueError(
            f"unknown spectral window {window!r}; expected one of {WINDOW_ORDER}"
        ) from None


@dataclass(frozen=True, eq=False)
class Spectrum:
    """One spectrum: one sample, one spectral window, one irradiation step."""

    wave: np.ndarray
    intensity: np.ndarray
    sample: str
    window: str
    step: int
    experiment: str
    path: Path
    has_header: bool


def list_experiments(raw_root: Path) -> list[str]:
    """Return the names of the experiment folders directly under ``raw_root``.

    Args:
        raw_root: Directory holding one subfolder per experiment.

    Returns:
        Sorted subfolder names.

    Raises:
        NotADirectoryError: If ``raw_root`` does not exist or is not a directory.
        ValueError: If ``raw_root`` contains no subfolders.
    """
    if not raw_root.is_dir():
        raise NotADirectoryError(f"raw data root does not exist or is not a directory: {raw_root}")
    names = sorted(p.name for p in raw_root.iterdir() if p.is_dir())
    if not names:
        raise ValueError(f"no experiment subfolders found in {raw_root}")
    return names


def parse_filename(path: Path) -> tuple[str, str, int]:
    """Parse ``<sample>_<window>_<step>.txt`` into its three components.

    The sample part may itself contain underscores, so the stem is split from
    the right. ``0`` denotes the control; ``irr<N>`` denotes irradiation step
    ``N``, a positive integer of any number of digits.

    Args:
        path: Path to a spectrum file. Only the filename is inspected.

    Returns:
        ``(sample, window, step)``.

    Raises:
        ValueError: If the filename does not follow the convention. Never falls
            back to a default and never guesses.
    """
    stem = path.stem
    parts = stem.rsplit("_", 2)
    if len(parts) != 3:
        raise ValueError(
            f"{path.name}: expected a filename of the form "
            f"'<sample>_<window>_<step>.txt' with at least two underscores, got {stem!r}"
        )
    sample, window, step_text = parts

    if not sample:
        raise ValueError(f"{path.name}: expected a non-empty sample name, got {stem!r}")

    if window not in VALID_WINDOWS:
        raise ValueError(
            f"{path.name}: expected window to be exactly 'low' or 'high' (lowercase), "
            f"got {window!r}"
        )

    if step_text == "0":
        step = 0
    else:
        match = _STEP_RE.match(step_text)
        if match is None:
            raise ValueError(
                f"{path.name}: expected step to be '0' or 'irr<N>' with N a positive "
                f"integer without leading zeros, got {step_text!r}"
            )
        step = int(match.group(1))

    return sample, window, step


def load_spectrum(path: Path, experiment: str) -> Spectrum:
    """Read one spectrum file.

    A single leading header line is skipped if, and only if, it starts with
    ``#``; some legacy exports have no header and their first line is data.
    Whether a header was present is recorded on the returned ``Spectrum``. Every
    remaining line must contain exactly two whitespace-separated floats. Values
    are returned in file order, unmodified.

    Args:
        path: File to read.
        experiment: Name of the containing folder under the raw data root.

    Returns:
        The parsed spectrum.

    Raises:
        ValueError: If the file is empty, holds no data lines, or contains a
            malformed line. The message names the file and the 1-based line
            number of the first malformed line. Bad lines are never skipped.
    """
    sample, window, step = parse_filename(path)

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"{path.name}: file is empty")

    has_header = lines[0].lstrip().startswith("#")
    first_data_lineno = 2 if has_header else 1
    body = lines[1:] if has_header else lines

    waves: list[float] = []
    intensities: list[float] = []
    for offset, line in enumerate(body):
        lineno = first_data_lineno + offset
        fields = line.split()
        if len(fields) != 2:
            raise ValueError(
                f"{path.name}: line {lineno}: expected exactly 2 whitespace-separated "
                f"fields, got {len(fields)}: {line!r}"
            )
        try:
            wave_value = float(fields[0])
            intensity_value = float(fields[1])
        except ValueError as exc:
            raise ValueError(
                f"{path.name}: line {lineno}: expected two floats, got {line!r}"
            ) from exc
        waves.append(wave_value)
        intensities.append(intensity_value)

    if not waves:
        raise ValueError(f"{path.name}: no data lines found")

    return Spectrum(
        wave=np.asarray(waves, dtype=np.float64),
        intensity=np.asarray(intensities, dtype=np.float64),
        sample=sample,
        window=window,
        step=step,
        experiment=experiment,
        path=path,
        has_header=has_header,
    )


def load_experiment(raw_root: Path, experiment: str) -> list[Spectrum]:
    """Load every ``.txt`` spectrum in ``raw_root/experiment``.

    Args:
        raw_root: Directory holding one subfolder per experiment.
        experiment: Name of the experiment subfolder.

    Returns:
        Spectra sorted by ``(sample, window, step)``, with ``window`` in the
        physical order low before high and ``step`` compared numerically so
        ``irr10`` follows ``irr9``.

    Raises:
        NotADirectoryError: If the experiment folder does not exist.
        ValueError: If the folder holds no ``.txt`` files, if any filename or
            file body fails to parse, or if a window label is not in
            :data:`WINDOW_ORDER`. A single bad file fails the whole call.
    """
    folder = raw_root / experiment
    if not folder.is_dir():
        raise NotADirectoryError(f"experiment folder does not exist: {folder}")

    paths = sorted(folder.glob("*.txt"))
    if not paths:
        raise ValueError(f"no .txt files found in {folder}")

    spectra = [load_spectrum(path, experiment) for path in paths]
    spectra.sort(key=lambda s: (s.sample, window_sort_key(s.window), s.step))
    return spectra


def group_spectra(spectra: list[Spectrum]) -> dict[tuple[str, str], list[Spectrum]]:
    """Group spectra by ``(sample, window)``.

    Args:
        spectra: Spectra to group.

    Returns:
        Mapping from ``(sample, window)`` to that group's spectra, each group
        sorted by ``step`` ascending.
    """
    groups: dict[tuple[str, str], list[Spectrum]] = {}
    for spectrum in spectra:
        groups.setdefault((spectrum.sample, spectrum.window), []).append(spectrum)
    for group in groups.values():
        group.sort(key=lambda s: s.step)
    return groups
