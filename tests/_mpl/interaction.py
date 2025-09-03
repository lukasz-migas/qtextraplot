"""Test interaction"""

import numpy as np

from qtextraplot._mpl.interaction import ExtractEvent, Polygon


class TestPolygon:
    @staticmethod
    def test_init():
        poly = Polygon()
        # add point
        poly.add_point(0, 1)
        assert poly.n_points == 1

        # should not allow duplicates
        poly.add_point(0, 1)
        assert poly.n_points == 1
        poly.add_point(0, 3)
        assert poly.n_points == 2

        # remove point
        poly.remove_last()
        assert poly.n_points == 1

        # remove specific point
        poly.remove_point(0, 1)
        assert poly.n_points == 0

    @staticmethod
    def test_get_poly_mpl():
        poly = Polygon()
        poly.add_point(0, 1)
        poly.add_point(1, 2)
        poly.add_point(3, 3)
        assert poly.n_points == 3

        xy = poly.get_polygon_mpl()
        assert isinstance(xy, np.ndarray)
        assert xy.shape[0] == 3
        assert xy.shape[1] == 2

        xmin, xmax, ymin, ymax = poly.get_zoom_rect()
        assert xmin == 0
        assert xmax == 3
        assert ymin == 1
        assert ymax == 3


class TestExtractEvent:
    @staticmethod
    def test_rect():
        _xmin, _xmax, _ymin, _ymax, _width, _height = 0, 10, 5, 13, 10, 8
        event = ExtractEvent("rect", _xmin, _xmax, _ymin, _ymax)
        assert event.xmin == _xmin
        assert event.xmax == _xmax
        assert event.ymin == _ymin
        assert event.ymax == _ymax
        assert event.width == _width
        assert event.height == _height

        xmin, xmax = event.get_x_range()
        assert xmin == _xmin, xmax == _xmax
        ymin, ymax = event.get_y_range()
        assert ymin == _ymin, ymax == _ymax
        xmin, xmax, width, height = event.get_rect()
        assert xmin == _xmin, xmax == _xmax
        assert width == _width, height == _height

        xmin, xmax, ymin, ymax = event.unpack()
        assert xmin == _xmin, xmax == _xmax
        assert ymin == _ymin, ymax == _ymax

        xmin, ymin, ymax, xmax = event.unpack_rect()
        assert xmin == _xmin, xmax == _xmax
        assert ymin == _ymin, ymax == _ymax

        label = event.get_x_with_width_label(1)
        assert isinstance(label, str)
