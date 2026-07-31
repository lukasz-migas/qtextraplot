"""Tests for napari utility functions."""

from __future__ import annotations

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")

from napari.layers import Image  # noqa: E402
from qtpy.QtCore import QSize  # noqa: E402
from qtpy.QtGui import QPixmap  # noqa: E402

from qtextraplot._napari._utilities import (  # noqa: E402
    crosshair_pixmap,
    set_layer_spatial_calibration,
)


def test_set_layer_spatial_calibration() -> None:
    """Spatial calibration should update layer units and scale."""
    layer = Image(np.zeros((4, 4)))

    set_layer_spatial_calibration([layer], unit="um", pixel_size=2.5)

    assert all(str(unit) == "micrometer" for unit in layer.units)
    np.testing.assert_array_equal(layer.scale, (2.5, 2.5))


def test_set_layer_spatial_calibration_to_pixels() -> None:
    """Pixel calibration should restore pixel units and unit scale."""
    layer = Image(np.zeros((4, 4)), scale=(2.5, 2.5), units=("um", "um"))

    set_layer_spatial_calibration([layer], unit=None, pixel_size=1.0)

    assert all(str(unit) == "pixel" for unit in layer.units)
    np.testing.assert_array_equal(layer.scale, (1.0, 1.0))


def test_set_layer_spatial_calibration_without_layers() -> None:
    """An empty layer collection should be a safe no-op."""
    set_layer_spatial_calibration([], unit="um", pixel_size=2.5)


class TestCrosshairPixmap:
    def test_returns_pixmap(self, qtbot):
        pixmap = crosshair_pixmap()
        assert isinstance(pixmap, QPixmap)

    def test_pixmap_not_null(self, qtbot):
        pixmap = crosshair_pixmap()
        assert not pixmap.isNull()

    def test_pixmap_is_square_25x25(self, qtbot):
        pixmap = crosshair_pixmap()
        assert pixmap.size() == QSize(25, 25)

    def test_lru_cache_returns_same_object(self, qtbot):
        p1 = crosshair_pixmap()
        p2 = crosshair_pixmap()
        assert p1 is p2
