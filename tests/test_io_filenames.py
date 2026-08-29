"""Filename parsing: what is accepted, and that everything else fails loudly."""

from __future__ import annotations

from pathlib import Path

import pytest

from ramsess.io import parse_filename

ACCEPTED = [
    ("a_low_0.txt", ("a", "low", 0)),
    ("a_high_irr1.txt", ("a", "high", 1)),
    ("a_high_irr9.txt", ("a", "high", 9)),
    ("a_high_irr10.txt", ("a", "high", 10)),
    ("a_high_irr123.txt", ("a", "high", 123)),
    ("my_sample_2_low_irr7.txt", ("my_sample_2", "low", 7)),
]

REJECTED = [
    "a_LOW_0.txt",
    "a_High_irr1.txt",
    "a_mid_0.txt",
    "a_low_irr0.txt",
    "a_low_irr01.txt",
    "a_low_irrX.txt",
    "a_low.txt",
    "alow0.txt",
    "_low_0.txt",
]


@pytest.mark.parametrize("name,expected", ACCEPTED)
def test_accepts_valid_filenames(name: str, expected: tuple[str, str, int]) -> None:
    assert parse_filename(Path(name)) == expected


def test_multi_digit_steps_are_not_truncated() -> None:
    """irr10 and irr123 must not be read by a single-digit pattern."""
    assert parse_filename(Path("s_low_irr10.txt"))[2] == 10
    assert parse_filename(Path("s_low_irr123.txt"))[2] == 123


def test_sample_is_split_from_the_right() -> None:
    """The sample part may contain underscores and even a window-like word."""
    assert parse_filename(Path("low_high_low_irr2.txt")) == ("low_high", "low", 2)


@pytest.mark.parametrize("name", REJECTED)
def test_rejects_invalid_filenames(name: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        parse_filename(Path(name))
    assert name in str(excinfo.value), "the error must name the offending file"


def test_rejection_message_states_what_was_expected() -> None:
    with pytest.raises(ValueError, match="low.*high"):
        parse_filename(Path("a_mid_0.txt"))
    with pytest.raises(ValueError, match="positive integer"):
        parse_filename(Path("a_low_irr0.txt"))
