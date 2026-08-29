"""End-to-end CLI behaviour: stdout against a golden file, and exit codes.

This is the one test module that touches the real dataset. It runs the real
command in a subprocess so genuine process exit codes are exercised, including
argparse's 2, which an in-process call cannot produce without catching
SystemExit. It only ever runs ``inspect``, which writes nothing, so ``figures/``
is never touched.

The golden fixture is generated from verified output. Regenerate it only when
the output is deliberately changed, never to make a failing test pass:

    .venv\\Scripts\\python.exe main.py inspect --experiment irradiation_sara \\
        > tests/fixtures/inspect_irradiation_sara.txt
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "inspect_irradiation_sara.txt"
EXPERIMENT = "irradiation_sara"


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run main.py in a subprocess from the project root."""
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_inspect_stdout_matches_the_golden_fixture() -> None:
    result = run_cli("inspect", "--experiment", EXPERIMENT)
    assert result.returncode == 0
    expected = GOLDEN.read_text(encoding="utf-8")
    assert result.stdout == expected, (
        "inspect output drifted from tests/fixtures/inspect_irradiation_sara.txt. "
        "Regenerate the fixture only if this change was deliberate."
    )


def test_strict_does_not_change_stdout() -> None:
    plain = run_cli("inspect", "--experiment", EXPERIMENT)
    strict = run_cli("inspect", "--experiment", EXPERIMENT, "--strict")
    assert strict.stdout == plain.stdout


def test_inspect_writes_nothing_to_stderr() -> None:
    assert run_cli("inspect", "--experiment", EXPERIMENT).stderr == ""


@pytest.mark.parametrize(
    "args,expected_code",
    [
        (("inspect", "--experiment", EXPERIMENT), 0),
        (("inspect", "--experiment", EXPERIMENT, "--strict"), 0),
        (("inspect",), 1),
        (("plot",), 1),
        (("inspect", "--experiment", "no_such_experiment"), 1),
        (("plot", "--experiment", EXPERIMENT, "--sample", "no_such_sample"), 1),
        ((), 2),
    ],
)
def test_exit_codes(args: tuple[str, ...], expected_code: int) -> None:
    assert run_cli(*args).returncode == expected_code


def test_missing_experiment_lists_available_experiments_on_stderr() -> None:
    result = run_cli("inspect")
    assert result.returncode == 1
    assert "no --experiment given" in result.stderr
    assert EXPERIMENT in result.stderr
    assert result.stdout == ""


def test_unknown_experiment_names_it_on_stderr() -> None:
    result = run_cli("inspect", "--experiment", "no_such_experiment")
    assert result.returncode == 1
    assert "no_such_experiment" in result.stderr


def test_unknown_sample_names_the_available_samples() -> None:
    result = run_cli("plot", "--experiment", EXPERIMENT, "--sample", "no_such_sample")
    assert result.returncode == 1
    assert "no_such_sample" in result.stderr
    assert "ech1" in result.stderr


def test_no_subcommand_is_an_argparse_usage_error() -> None:
    result = run_cli()
    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_unknown_flag_is_rejected() -> None:
    assert run_cli("inspect", "--experiment", EXPERIMENT, "--force").returncode == 2
    assert run_cli("plot", "--experiment", EXPERIMENT, "--strict").returncode == 2
