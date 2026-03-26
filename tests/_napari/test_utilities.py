"""Tests for napari utility functions."""

from __future__ import annotations

import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")

from qtpy.QtCore import QSize  # noqa: E402
from qtpy.QtGui import QPixmap  # noqa: E402

from qtextraplot._napari._utilities import crosshair_pixmap  # noqa: E402


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
