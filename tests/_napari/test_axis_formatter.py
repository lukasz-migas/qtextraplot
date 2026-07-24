"""Tests for Vispy axis label formatting."""

from __future__ import annotations

import math

import pytest

from qtextraplot._napari.line._vispy.overrides.axis import tick_formatter


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (-0.0, "0"),
        (400, "400"),
        (999.9, "999.9"),
        (1_000, "1k"),
        (-1_250, "-1.25k"),
        (1_000_000, "1M"),
        (1_000_000_000, "1B"),
        (1_000_000_000_000, "1T"),
        (1_000_000_000_000_000, "1e+15"),
        (0.00001, "1e-05"),
    ],
)
def test_tick_formatter_uses_expected_notation(value: float, expected: str) -> None:
    assert tick_formatter(value) == expected


def test_tick_formatter_keeps_hundreds_on_the_same_scale() -> None:
    labels = [tick_formatter(value, tick_spacing=100) for value in range(0, 500, 100)]

    assert labels == ["0", "100", "200", "300", "400"]


def test_tick_formatter_distinguishes_nearby_values() -> None:
    values = (0.1675, 0.16875, 0.17, 0.17125)
    labels = [tick_formatter(value, tick_spacing=0.00125) for value in values]

    assert labels == ["0.1675", "0.1688", "0.17", "0.1713"]
    assert len(labels) == len(set(labels))


def test_tick_formatter_adds_precision_for_narrow_ranges() -> None:
    labels = [tick_formatter(value, tick_spacing=0.000001) for value in (0.17, 0.170001, 0.170002)]

    assert labels == ["0.17", "0.170001", "0.170002"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [(math.inf, "inf"), (-math.inf, "-inf"), (math.nan, "nan")],
)
def test_tick_formatter_handles_non_finite_values(value: float, expected: str) -> None:
    assert tick_formatter(value) == expected
