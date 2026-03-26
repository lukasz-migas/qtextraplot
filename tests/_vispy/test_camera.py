"""pytest tests for the BoxZoomCamera and BoxZoomCameraMixin."""

from __future__ import annotations

import pytest

vispy = pytest.importorskip("vispy", reason="vispy is not installed")

from qtextraplot._vispy.camera import BoxZoomCamera, round_to_half, to_rect  # noqa: E402
from qtextraplot._vispy.base import PlotLine  # noqa: E402


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestToRect:
    def test_symmetric_box(self):
        left, right, bottom, top = to_rect((5, 5), 4, 6)
        assert left == 3
        assert right == 7
        assert bottom == 2
        assert top == 8


class TestRoundToHalf:
    def test_rounds_correctly(self):
        result = round_to_half(0.6, 1.4)
        assert list(result) == pytest.approx([0.5, 1.5])

    def test_zero(self):
        assert list(round_to_half(0.0)) == pytest.approx([0.0])


# ---------------------------------------------------------------------------
# BoxZoomCamera requires a parent vispy scene which PlotLine sets up
# ---------------------------------------------------------------------------


@pytest.fixture
def camera(qtbot):
    """Provide a BoxZoomCamera attached to a real PlotLine camera."""
    plot = PlotLine(parent=None, facecolor="white")
    qtbot.addWidget(plot.native)
    return plot.view.camera


class TestBoxZoomCameraExtents:
    def test_set_extents_stores_rect(self, camera):
        camera.set_extents(0, 100, 0, 200)
        assert camera._extents is not None
        assert camera._extents.left == 0
        assert camera._extents.right == 100
        assert camera._extents.bottom == 0
        assert camera._extents.top == 200

    def test_extent_property(self, camera):
        camera.set_extents(1, 9, 2, 8)
        camera.simple_zoom(1, 9, 2, 8)
        left, right, bottom, top = camera.extent
        assert left == pytest.approx(1, abs=0.1)
        assert right == pytest.approx(9, abs=0.1)

    def test_check_zoom_limit_clamps(self, camera):
        from vispy.geometry import Rect

        camera.set_extents(0, 10, 0, 10)
        rect = Rect()
        rect.left = -5  # outside lower bound
        rect.right = 15  # outside upper bound
        rect.bottom = -3
        rect.top = 12
        clamped = camera._check_zoom_limit(rect)
        assert clamped.left == 0
        assert clamped.right == 10
        assert clamped.bottom == 0
        assert clamped.top == 10

    def test_check_range_swaps_if_inverted(self, camera):
        x0, x1, y0, y1 = camera._check_range(8, 2, 7, 3)
        assert x0 < x1
        assert y0 < y1

    def test_callbacks_setter_wraps_scalars(self, camera):
        called = []
        camera.callbacks = {"ZOOM": lambda e: called.append(e)}
        # After the setter, each value should be wrapped in a list
        assert isinstance(camera._callbacks["ZOOM"], list)

    def test_reset_polygon(self, camera):
        from qtextraplot.utils.interaction import Polygon

        camera.reset_polygon()
        assert isinstance(camera.polygon, Polygon)
        assert camera.roi_shape == "rect"
        assert camera.lock is False
