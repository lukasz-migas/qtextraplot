"""Compatibility helpers for Napari's native colorbar overlay."""

from __future__ import annotations

import typing as ty

import numpy as np
from napari._vispy.overlays.colorbar import VispyColorBarOverlay
from vispy.visuals.axis import Ticker


class _SafeColorBarTicker(Ticker):
    """Avoid VisPy's invalid tick slice when there are no major ticks."""

    def _get_tick_positions(
        self,
        major_tick_fractions: np.ndarray,
        minor_tick_fractions: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, ty.Sequence[str]]:
        if len(major_tick_fractions) == 0:
            minor_tick_fractions = np.empty(0, dtype=float)
        return super()._get_tick_positions(major_tick_fractions, minor_tick_fractions)


class _SafeVispyColorBarOverlay(VispyColorBarOverlay):
    """Use the guarded ticker for Napari's native per-layer colorbars."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        super().__init__(*args, **kwargs)
        self.node.ticks.ticker = _SafeColorBarTicker(self.node.ticks)
