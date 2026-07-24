"""Axis label formatting helpers."""

from __future__ import annotations

import math

_MIN_SIGNIFICANT_DIGITS = 4
_MAX_SIGNIFICANT_DIGITS = 15
_SI_SCALES = (
    (1e12, "T"),
    (1e9, "B"),
    (1e6, "M"),
    (1e3, "k"),
)


def _scale_for_value(value: float) -> tuple[float, str]:
    """Return the SI scale and suffix for a finite value."""
    magnitude = abs(value)
    if magnitude >= 1e15:
        return 1.0, ""
    for scale, suffix in _SI_SCALES:
        if magnitude >= scale:
            return scale, suffix
    return 1.0, ""


def _precision_for_spacing(value: float, tick_spacing: float | None) -> int:
    """Return enough significant digits to distinguish adjacent ticks."""
    if tick_spacing is None:
        return _MIN_SIGNIFICANT_DIGITS

    spacing = abs(float(tick_spacing))
    if not math.isfinite(spacing) or spacing == 0:
        return _MIN_SIGNIFICANT_DIGITS

    value_exponent = math.floor(math.log10(abs(value)))
    spacing_exponent = math.floor(math.log10(spacing))
    precision = max(_MIN_SIGNIFICANT_DIGITS, value_exponent - spacing_exponent + 2)
    return min(precision, _MAX_SIGNIFICANT_DIGITS)


def tick_formatter(value: float, *, tick_spacing: float | None = None) -> str:
    """Format a tick value using compact SI notation.

    Parameters
    ----------
    value : float
        Tick value to format.
    tick_spacing : float, optional
        Distance between adjacent major ticks. When supplied, additional
        precision is retained so that nearby tick labels remain distinct.

    Returns
    -------
    str
        Formatted tick label.
    """
    value = float(value)
    if value == 0:
        return "0"
    if not math.isfinite(value):
        return f"{value:g}"

    scale, suffix = _scale_for_value(value)
    scaled_value = value / scale
    scaled_spacing = None if tick_spacing is None else float(tick_spacing) / scale
    precision = _precision_for_spacing(scaled_value, scaled_spacing)
    return f"{scaled_value:.{precision}g}{suffix}"
