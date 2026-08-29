"""Shared fixtures and helpers for the whole suite.

Holds three kinds of thing:

* **Synthetic experiment building** - ``spectrum_lines``, ``vary``,
  ``shift_wave``, ``write_spectrum_file``, the ``make_experiment`` factory and
  the ``low_lines`` / ``high_lines`` pairs. Everything is written under
  ``tmp_path``.
* **Shared contracts** - ``assert_row_contract``, the one piece the two
  measurement-row builders share, and ``tree_snapshot``.
* **Two autouse guards applied to every test in the suite** -
  ``repository_untouched``, which fails any test that modifies ``data/`` or
  ``figures/``, and ``close_figures``, which closes any figure a test leaves
  open.

No test writes ``data/`` or ``figures/``; ``repository_untouched`` now enforces
that rather than leaving it to convention. Exactly two read them, and both only
read:

1. ``test_cli_output.py`` runs the real ``main.py`` in a subprocess against the
   real ``data/raw/``, comparing ``inspect`` stdout to the golden fixture. The
   one non-``inspect`` invocation names a sample that does not exist, which is
   rejected before anything is drawn.
2. ``test_raw_plot_reference.py`` reads the six reference PNGs in
   ``figures/irradiation_sara/`` with ``imread`` and compares them against
   figures it renders into ``tmp_path``. It writes nothing to ``figures/`` and
   skips when that tree has not been generated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Must stay below the sys.path insertion above: ramsess is not importable until
# src/ is on the path. Keep this import to ramsess.report and nothing that pulls
# matplotlib - report.py imports plotting lazily on purpose, so that the inspect
# path never has the process backend fixed on its behalf, and importing pyplot
# here would defeat that.
from ramsess.report import BANDS_CSV_COLUMNS  # noqa: E402

HEADER = "#Wave\t\t#Intensity"


def spectrum_lines(
    n: int = 8, start: float = 200.0, stepsize: float = 2.5, base: float = 1000.0
) -> list[str]:
    """Return ``n`` data lines on a deliberately non-uniform wave axis."""
    lines = []
    wave = start
    for i in range(n):
        # Uneven spacing, matching the real instrument, so nothing can pass by
        # assuming a constant step.
        wave += stepsize * (1.0 + 0.1 * (i % 3))
        lines.append(f"{wave:.6f}\t{base + i * 10:.6f}")
    return lines


def vary(lines: list[str], delta: float) -> list[str]:
    """Offset every intensity by ``delta``, leaving the wave axis untouched.

    Used to give each file distinct contents so the duplicate-hash check does
    not fire in tests that are about something else.
    """
    out = []
    for line in lines:
        wave, intensity = line.split()
        out.append(f"{wave}\t{float(intensity) + delta:.6f}")
    return out


def shift_wave(lines: list[str], delta: float) -> list[str]:
    """Offset every wave value by ``delta``, leaving intensities untouched."""
    out = []
    for line in lines:
        wave, intensity = line.split()
        out.append(f"{float(wave) + delta:.6f}\t{intensity}")
    return out


def write_spectrum_file(
    path: Path, lines: list[str] | None = None, header: bool = True
) -> Path:
    """Write one spectrum file with CRLF endings.

    Uses ``write_bytes`` deliberately: ``write_text`` applies newline
    translation on Windows, turning an explicit ``\\r\\n`` into ``\\r\\r\\n``
    and silently adding a blank line to every fixture.
    """
    body = spectrum_lines() if lines is None else lines
    out = ([HEADER] if header else []) + body
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\r\n".join(out) + "\r\n").encode("utf-8"))
    return path


@pytest.fixture
def make_experiment(tmp_path: Path):
    """Return a factory building a synthetic experiment under ``tmp_path``.

    The factory takes a mapping of filename to either None (default contents),
    a list of data lines, or a ``(lines, header)`` pair. It returns the raw root
    so the result can be passed straight to ``load_experiment``.
    """

    def factory(files: dict[str, object], experiment: str = "exp") -> Path:
        raw_root = tmp_path / "raw"
        folder = raw_root / experiment
        folder.mkdir(parents=True, exist_ok=True)
        for name, spec in files.items():
            if spec is None:
                write_spectrum_file(folder / name)
            elif isinstance(spec, tuple):
                lines, header = spec
                write_spectrum_file(folder / name, lines, header=header)
            else:
                write_spectrum_file(folder / name, spec)  # type: ignore[arg-type]
        return raw_root

    return factory


@pytest.fixture
def low_lines() -> list[str]:
    """Data lines sitting in a low-like window."""
    return spectrum_lines(n=8, start=200.0, stepsize=2.5)


@pytest.fixture
def high_lines() -> list[str]:
    """Data lines sitting in a high-like window, disjoint from ``low_lines``."""
    return spectrum_lines(n=8, start=2400.0, stepsize=2.0, base=5000.0)


def assert_row_contract(row: dict[str, object]) -> None:
    """Assert one measurement row carries exactly the keys the real ones carry.

    The single shared piece of the two row builders. Each test file keeps its
    own builder, because they invent different data for different purposes, but
    both must produce the same key set - the one every consumer reads: the CSV
    writer, the summary printer and both trend builders.
    """
    assert set(row) == set(BANDS_CSV_COLUMNS)


def tree_snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Map every file under ``root`` to its size and modification time."""
    if not root.is_dir():
        return {}
    return {
        str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(autouse=True)
def repository_untouched():
    """Fail if anything in the repository's data/ or figures/ trees changes.

    Autouse and global: every test in the suite is guarded, not only the ones
    that obviously write. Tests own their output roots under ``tmp_path``; the
    real trees are read-only for the whole suite, and ``data/raw/`` is read-only
    for the whole project.
    """
    watched = [PROJECT_ROOT / "data", PROJECT_ROOT / "figures"]
    before = {str(root): tree_snapshot(root) for root in watched}
    yield
    for root in watched:
        assert tree_snapshot(root) == before[str(root)], (
            f"a test modified {root}, which is outside tmp_path. Derived data "
            f"and figures belong under the roots the test itself owns."
        )


@pytest.fixture(autouse=True)
def close_figures():
    """Close every figure a test opened, whatever the test did.

    Imported lazily inside the fixture rather than at module scope: pyplot must
    not be imported before ``ramsess.plotting`` has chosen the Agg backend, and
    a conftest-level import would run first for the whole suite.
    """
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
