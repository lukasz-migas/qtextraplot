"""Tests for shared utilities."""

from __future__ import annotations

import numpy as np
import pytest

from qtextraplot.utils.colormap import vispy_colormap, vispy_colormaps
from qtextraplot.utils.interaction import ExtractEvent, Polygon, get_center
from qtextraplot.utils.utilities import running_under_pytest
from qtextraplot.utils.views_base import build_wildcard


# ---------------------------------------------------------------------------
# running_under_pytest
# ---------------------------------------------------------------------------


def test_running_under_pytest_returns_true(monkeypatch):
    monkeypatch.setenv("QTEXTRAPLOT_PYTEST", "1")
    assert running_under_pytest() is True


def test_running_under_pytest_returns_false(monkeypatch):
    monkeypatch.delenv("QTEXTRAPLOT_PYTEST", raising=False)
    assert running_under_pytest() is False


# ---------------------------------------------------------------------------
# build_wildcard
# ---------------------------------------------------------------------------


def test_build_wildcard_single_format():
    wildcard = build_wildcard(("png",))
    assert "PNG" in wildcard
    assert "*.png" in wildcard


def test_build_wildcard_multiple_formats():
    wildcard = build_wildcard(("png", "svg"))
    assert ";;" in wildcard


def test_build_wildcard_all_formats():
    formats = ("png", "eps", "jpeg", "tiff", "raw", "ps", "pdf", "svg", "svgz")
    wildcard = build_wildcard(formats)
    for fmt in formats:
        assert fmt in wildcard


# ---------------------------------------------------------------------------
# Polygon
# ---------------------------------------------------------------------------


class TestPolygon:
    def test_initial_state(self):
        poly = Polygon()
        assert poly.n_points == 0
        assert poly.points == []

    def test_add_point(self):
        poly = Polygon()
        poly.add_point(1.0, 2.0)
        assert poly.n_points == 1

    def test_no_duplicate_points(self):
        poly = Polygon()
        poly.add_point(0, 0)
        poly.add_point(0, 0)
        assert poly.n_points == 1

    def test_remove_specific_point(self):
        poly = Polygon()
        poly.add_point(1, 2)
        poly.add_point(3, 4)
        poly.remove_point(1, 2)
        assert poly.n_points == 1
        assert poly.points == [[3, 4]]

    def test_remove_last_point(self):
        poly = Polygon()
        poly.add_point(0, 0)
        poly.add_point(1, 1)
        poly.remove_last()
        assert poly.n_points == 1

    def test_reset(self):
        poly = Polygon()
        poly.add_point(0, 0)
        poly.reset()
        assert poly.n_points == 0

    def test_get_polygon_mpl_shape(self):
        poly = Polygon()
        poly.add_point(0, 1)
        poly.add_point(2, 3)
        arr = poly.get_polygon_mpl()
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (2, 2)

    def test_get_polygon_vispy_shape(self):
        poly = Polygon()
        poly.add_point(0, 1)
        poly.add_point(2, 3)
        arr = poly.get_polygon_vispy()
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (2, 2)

    def test_get_zoom_rect_correct_bounds(self):
        poly = Polygon()
        poly.add_point(1, 2)
        poly.add_point(5, 7)
        poly.add_point(3, 4)
        xmin, xmax, ymin, ymax = poly.get_zoom_rect()
        assert xmin == 1
        assert xmax == 5
        assert ymin == 2
        assert ymax == 7

    def test_evt_n_changed_emitted(self, qtbot):
        poly = Polygon()
        with qtbot.waitSignal(poly.evt_n_changed, timeout=1000):
            poly.add_point(1, 2)


# ---------------------------------------------------------------------------
# ExtractEvent
# ---------------------------------------------------------------------------


class TestExtractEvent:
    def test_basic_attributes(self):
        evt = ExtractEvent("rect", 0, 10, 2, 8)
        assert evt.xmin == 0
        assert evt.xmax == 10
        assert evt.ymin == 2
        assert evt.ymax == 8

    def test_width_and_height(self):
        evt = ExtractEvent("rect", 3, 7, 1, 5)
        assert evt.width == pytest.approx(4.0)
        assert evt.height == pytest.approx(4.0)

    def test_get_x_range(self):
        evt = ExtractEvent("rect", 1, 9, 0, 0)
        assert evt.get_x_range() == (1, 9)

    def test_get_y_range(self):
        evt = ExtractEvent("rect", 0, 0, 3, 11)
        assert evt.get_y_range() == (3, 11)

    def test_get_rect(self):
        evt = ExtractEvent("rect", 2, 6, 1, 4)
        xmin, ymin, width, height = evt.get_rect()
        assert xmin == 2
        assert ymin == 1
        assert width == pytest.approx(4.0)
        assert height == pytest.approx(3.0)

    def test_unpack(self):
        evt = ExtractEvent("rect", 1, 5, 2, 9)
        assert evt.unpack() == (1, 5, 2, 9)

    def test_unpack_as_int(self):
        evt = ExtractEvent("rect", 1.4, 5.6, 2.1, 8.9)
        result = evt.unpack(as_int=True)
        assert all(isinstance(v, int) for v in result)

    def test_unpack_rect(self):
        evt = ExtractEvent("rect", 1, 5, 2, 9)
        xmin, ymin, xmax, ymax = evt.unpack_rect()
        assert xmin == 1
        assert ymin == 2
        assert xmax == 5
        assert ymax == 9

    def test_is_point_true(self):
        evt = ExtractEvent("rect", 1.0, 1.0, 1.0, 1.0)
        assert evt.is_point() is True

    def test_is_point_false(self):
        evt = ExtractEvent("rect", 0, 5, 0, 5)
        assert evt.is_point() is False

    def test_get_zoom_rect_with_pad(self):
        evt = ExtractEvent("rect", 2, 8, 3, 7)
        xmin, xmax, ymin, ymax = evt.get_zoom_rect(pad=1)
        assert xmin == 1
        assert xmax == 9
        assert ymin == 2
        assert ymax == 8

    def test_get_x_with_width_label(self):
        evt = ExtractEvent("rect", 0, 10, 0, 0)
        label = evt.get_x_with_width_label(1)
        assert isinstance(label, str)
        assert "±" in label

    def test_get_line_mask(self):
        evt = ExtractEvent("rect", 2, 6, 0, 0)
        mask = evt.get_line_mask(as_int=True)
        assert list(mask) == [2, 3, 4, 5]


# ---------------------------------------------------------------------------
# get_center
# ---------------------------------------------------------------------------


def test_get_center_symmetric():
    assert get_center(0.0, 10.0) == pytest.approx(5.0)


def test_get_center_negative():
    assert get_center(-4.0, 4.0) == pytest.approx(0.0)


def test_get_center_order_independent():
    assert get_center(10.0, 0.0) == pytest.approx(get_center(0.0, 10.0))


# ---------------------------------------------------------------------------
# vispy colormap helpers (require vispy)
# ---------------------------------------------------------------------------

vispy_pkg = pytest.importorskip("vispy", reason="vispy is not installed")


def test_vispy_colormap_returns_colormap():
    from vispy.color import Colormap

    color = np.array([1.0, 0.0, 0.0, 1.0])
    cmap = vispy_colormap(color)
    assert isinstance(cmap, Colormap)


def test_vispy_colormaps_returns_list():
    color1 = np.array([1.0, 0.0, 0.0, 1.0])
    color2 = np.array([0.0, 1.0, 0.0, 1.0])
    cmaps = vispy_colormaps([color1, color2])
    assert len(cmaps) == 2
