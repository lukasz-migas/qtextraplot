"""pytest-qt tests for the vispy BasePlot / PlotLine / PlotScatter widgets."""

from __future__ import annotations

import numpy as np
import pytest

vispy = pytest.importorskip("vispy", reason="vispy is not installed")

from qtextraplot._vispy.base import PlotLine, PlotScatter  # noqa: E402
from qtextraplot._vispy.models.extents import Extents  # noqa: E402


# ---------------------------------------------------------------------------
# Extents
# ---------------------------------------------------------------------------


class TestExtents:
    def test_add_range_and_get_xy(self):
        ext = Extents()
        ext.add_range(0.0, 10.0, -1.0, 5.0)
        xmin, xmax, ymin, ymax = ext.get_xy()
        assert xmin == 0.0
        assert xmax == 10.0
        assert ymin == -1.0
        assert ymax == 5.0

    def test_reset_clears_lists(self):
        ext = Extents()
        ext.add_range(0.0, 1.0, 0.0, 1.0)
        ext.reset()
        assert ext.x == []
        assert ext.y == []

    def test_multiple_ranges_expand_correctly(self):
        ext = Extents()
        ext.add_range(0.0, 5.0, 0.0, 3.0)
        ext.add_range(2.0, 8.0, -2.0, 7.0)
        xmin, xmax, ymin, ymax = ext.get_xy()
        assert xmin == 0.0
        assert xmax == 8.0
        assert ymin == -2.0
        assert ymax == 7.0

    def test_get_x_and_get_y(self):
        ext = Extents()
        ext.add_range(1.0, 9.0, 2.0, 6.0)
        assert ext.get_x() == (1.0, 9.0)
        assert ext.get_y() == (2.0, 6.0)


# ---------------------------------------------------------------------------
# PlotLine (needs a QApplication; qtbot ensures one exists)
# ---------------------------------------------------------------------------


@pytest.fixture
def line_plot(qtbot):
    """Return a PlotLine with a native Qt widget registered with qtbot."""
    plot = PlotLine(parent=None, facecolor="white")
    qtbot.addWidget(plot.native)
    return plot


class TestPlotLine:
    def test_instantiation(self, line_plot):
        assert line_plot is not None

    def test_node_initially_none(self, line_plot):
        assert line_plot.node is None

    def test_plot_1d_creates_node(self, line_plot):
        x = np.linspace(0, 10, 50)
        y = np.sin(x)
        line_plot.plot_1d(x, y)
        assert line_plot.node is not None

    def test_plot_1d_sets_extents(self, line_plot):
        x = np.linspace(0, 5, 20)
        y = np.ones_like(x) * 3.0
        line_plot.plot_1d(x, y)
        xmin, xmax, ymin, ymax = line_plot.get_xy_limits()
        assert xmin == pytest.approx(0.0, abs=1e-3)
        assert xmax == pytest.approx(5.0, abs=1e-3)

    def test_clear_removes_node(self, line_plot):
        x = np.linspace(0, 1, 10)
        line_plot.plot_1d(x, x)
        line_plot.clear()
        assert line_plot.node is None

    def test_clear_resets_extents(self, line_plot):
        x = np.linspace(0, 10, 10)
        line_plot.plot_1d(x, x)
        line_plot.clear()
        assert line_plot._extents.x == []

    def test_plot_1d_add(self, line_plot):
        x = np.arange(5, dtype=float)
        y = x * 2
        line_plot.plot_1d_add(x, y, gid="extra")
        assert "extra" in line_plot.nodes

    def test_plot_1d_remove(self, line_plot):
        x = np.arange(5, dtype=float)
        line_plot.plot_1d_add(x, x, gid="to_remove")
        line_plot.plot_1d_remove("to_remove")
        assert "to_remove" not in line_plot.nodes

    def test_add_vline(self, line_plot):
        line_plot.plot_add_vline(xpos=2.5, gid="v1")
        assert "v1" in line_plot.nodes

    def test_add_hline(self, line_plot):
        line_plot.plot_add_hline(ypos=1.0, gid="h1")
        assert "h1" in line_plot.nodes

    def test_remove_line_by_gid(self, line_plot):
        line_plot.plot_add_vline(xpos=1.0, gid="del_me")
        line_plot.plot_remove_line("del_me")
        assert "del_me" not in line_plot.nodes

    def test_clear_detaches_extra_nodes(self, line_plot):
        x = np.arange(5, dtype=float)
        line_plot.plot_1d_add(x, x, gid="n1")
        line_plot.plot_1d_add(x, x * 2, gid="n2")
        line_plot.clear()
        assert line_plot.nodes == {}

    def test_repaint_no_error(self, line_plot):
        line_plot.repaint()


# ---------------------------------------------------------------------------
# PlotScatter
# ---------------------------------------------------------------------------


@pytest.fixture
def scatter_plot(qtbot):
    plot = PlotScatter(parent=None, facecolor="white")
    qtbot.addWidget(plot.native)
    return plot


class TestPlotScatter:
    def test_instantiation(self, scatter_plot):
        assert scatter_plot is not None

    def test_node_initially_none(self, scatter_plot):
        assert scatter_plot.node is None

    def test_marker_data_kwargs_omits_scaling_when_unsupported(self, scatter_plot):
        class _Node:
            def set_data(self, pos=None, size=10.0):
                return pos, size

        scatter_plot.node = _Node()
        kwargs = scatter_plot._marker_data_kwargs(symbol="square", size=3)
        assert kwargs == {"symbol": "square", "size": 3}

    def test_ensure_marker_node_initializes_once(self, scatter_plot):
        node = scatter_plot._ensure_marker_node()
        assert node is scatter_plot.node
        assert scatter_plot._ensure_marker_node() is node

    def test_set_marker_data_initializes_node(self, scatter_plot):
        x = np.array([0.0, 1.0])
        y = np.array([1.0, 2.0])
        scatter_plot._set_marker_data(
            x,
            y,
            zorder=7,
            face_color="#00FF00",
            edge_color="#000000",
            size=4,
        )
        assert scatter_plot.node is not None
        assert scatter_plot.node.order == 7

    def test_plot_scatter_creates_node(self, scatter_plot):
        x = np.random.rand(20)
        y = np.random.rand(20)
        scatter_plot.plot_scatter(x, y)
        assert scatter_plot.node is not None

    def test_update_scatter(self, scatter_plot):
        x = np.random.rand(10)
        y = np.random.rand(10)
        scatter_plot.plot_scatter(x, y)
        x2 = np.random.rand(10)
        y2 = np.random.rand(10)
        scatter_plot.update_scatter(x2, y2)  # should not raise

    def test_clear(self, scatter_plot):
        x = np.random.rand(5)
        scatter_plot.plot_scatter(x, x)
        scatter_plot.clear()
        assert scatter_plot.node is None
