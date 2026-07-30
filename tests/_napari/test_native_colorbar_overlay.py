"""Tests for the guarded Napari native colorbar overlay."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("napari", reason="napari is not installed")
pytest.importorskip("vispy", reason="vispy is not installed")

from napari._vispy.utils.visual import overlay_to_visual
from napari.components.overlays import ColorBarOverlay as NapariColorBarOverlay
from vispy.visuals.axis import Ticker

from qtextraplot._napari._vispy import register_vispy_overlays
from qtextraplot._napari._vispy.overlays.color_bar_mpl import VispyColorbarOverlay
from qtextraplot._napari.components.overlays.color_bar import (
    ColorBarOverlay as QtextraColorBarOverlay,
)
from qtextraplot._napari.image._vispy import register_vispy_overlays as register_image_vispy_overlays
from qtextraplot._napari.image._vispy.color_bar import (
    _SafeColorBarTicker,
    _SafeVispyColorBarOverlay,
)


class _IdentityTransform:
    """Return input coordinates unchanged."""

    @staticmethod
    def map(values: np.ndarray) -> np.ndarray:
        return np.asarray(values, dtype=float)


def _axis() -> SimpleNamespace:
    """Return the minimum axis interface required by VisPy's ticker."""
    return SimpleNamespace(
        pos=np.asarray([[0.0, 1.0], [0.0, 0.0]]),
        _vec=np.asarray([0.0, -1.0]),
        tick_direction=np.asarray([1.0, 0.0]),
        minor_tick_length=2.5,
        major_tick_length=5.0,
        tick_label_margin=4.0,
        axis_label_margin=35.0,
        transforms=SimpleNamespace(get_transform=lambda *_args: _IdentityTransform()),
    )


def test_safe_colorbar_ticker_handles_minor_ticks_without_major_ticks() -> None:
    """An empty major-tick set should produce empty geometry without raising."""
    ticker = _SafeColorBarTicker(_axis())

    tick_positions, tick_label_positions, _axis_label_position, _anchors = ticker._get_tick_positions(
        np.empty(0),
        np.asarray([0.2, 0.4, 0.6, 0.8]),
    )

    assert tick_positions.shape == (0, 2)
    assert tick_label_positions.shape == (0, 2)


def test_safe_colorbar_ticker_preserves_normal_tick_positions() -> None:
    """Normal major/minor tick geometry should remain identical to VisPy's."""
    major = np.asarray([0.0, 0.5, 1.0])
    minor = np.asarray([0.25, 0.75])

    expected = Ticker(_axis())._get_tick_positions(major, minor)
    actual = _SafeColorBarTicker(_axis())._get_tick_positions(major, minor)

    for actual_array, expected_array in zip(actual[:3], expected[:3], strict=True):
        np.testing.assert_allclose(actual_array, expected_array)
    assert actual[3] == expected[3]


def test_native_colorbar_registration_keeps_qtextraplot_colorbar() -> None:
    """Only Napari's native colorbar should use the guarded visual."""
    register_vispy_overlays()
    register_image_vispy_overlays()

    assert overlay_to_visual[NapariColorBarOverlay] is _SafeVispyColorBarOverlay
    assert overlay_to_visual[QtextraColorBarOverlay] is VispyColorbarOverlay
