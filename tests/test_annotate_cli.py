"""The ``--annotate`` gate in ``main.py``: what it loads, and when it refuses.

The one thing ``--annotate`` adds to the ``plot`` path is a dependency on
``bands.json``, which ``plot`` has never had. Two halves of that have to hold and
neither is visible from the figure files, so they are tested here rather than in
``test_output_filenames.py``:

* plain ``plot`` still reads no configuration at all, so an experiment without a
  ``bands.json`` keeps working exactly as before;
* ``--annotate`` without one fails, naming the file it expected.

``main.RAW_ROOT`` and ``main.FIGURES_ROOT`` are redirected to ``tmp_path``, so
this exercises the real dispatch without going near the repository's own trees.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import spectrum_lines, write_spectrum_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# main.py lives at the project root, which pytest does not put on the path -
# conftest adds src/ only, and test_cli_output.py reaches main.py by subprocess
# instead. This module needs it importable so its roots can be redirected.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as cli  # noqa: E402

EXPERIMENT = "exp"
BANDS_CONFIG = {
    "reference": "a",
    "bands": {
        "a": {"centre": 210.0, "half_width": 3.0, "window": "low"},
        "b": {"centre": 2410.0, "half_width": 3.0, "window": "high"},
    },
}


@pytest.fixture
def cli_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One sample in both windows under tmp_path, with main.py pointed at it."""
    raw_root = tmp_path / "raw"
    folder = raw_root / EXPERIMENT
    write_spectrum_file(folder / "s_low_0.txt", spectrum_lines(n=8, start=200.0, stepsize=2.5))
    write_spectrum_file(
        folder / "s_high_0.txt", spectrum_lines(n=8, start=2400.0, stepsize=2.0, base=5000.0)
    )
    monkeypatch.setattr(cli, "RAW_ROOT", raw_root)
    monkeypatch.setattr(cli, "FIGURES_ROOT", tmp_path / "figures")
    return tmp_path


def figures(root: Path) -> set[str]:
    """Every figure written, by name. Recursive: they live one per sample now."""
    return {path.name for path in (root / "figures" / EXPERIMENT).rglob("*.png")}


def test_plain_plot_still_works_without_a_bands_config(cli_roots: Path) -> None:
    """The dependency --annotate adds must not leak onto the default path."""
    assert not (cli_roots / "raw" / EXPERIMENT / "bands.json").exists()
    assert cli.main(["plot", "--experiment", EXPERIMENT]) == 0
    assert figures(cli_roots) == {"s_overlay.png"}


def test_annotate_without_a_bands_config_fails_naming_the_path(
    cli_roots: Path, capsys: pytest.CaptureFixture
) -> None:
    assert not (cli_roots / "raw" / EXPERIMENT / "bands.json").exists()
    assert cli.main(["plot", "--experiment", EXPERIMENT, "--annotate"]) == 1

    error = capsys.readouterr().err
    assert "--annotate" in error
    assert str(cli_roots / "raw" / EXPERIMENT / "bands.json") in error, (
        f"the error must name the file it expected; got: {error!r}"
    )
    assert not (cli_roots / "figures").exists(), "a refused run must draw nothing"


def test_annotate_with_a_bands_config_writes_only_the_annotated_figure(
    cli_roots: Path,
) -> None:
    (cli_roots / "raw" / EXPERIMENT / "bands.json").write_text(
        json.dumps(BANDS_CONFIG), encoding="utf-8"
    )
    assert cli.main(["plot", "--experiment", EXPERIMENT, "--annotate"]) == 0
    assert figures(cli_roots) == {"s_overlay_annotated.png"}
