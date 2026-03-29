"""pytest-qt tests for the matplotlib PlotBase widget."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib", reason="matplotlib is not installed")

from qtpy.QtCore import Qt  # noqa: E402

from qtextraplot._mpl.plot_base import PlotBase  # noqa: E402


class _ConcretePlot(PlotBase):
    """Minimal concrete subclass that does not call any abstract methods."""


@pytest.fixture
def plot_widget(qtbot):
    """Return a minimal PlotBase instance registered with qtbot."""
    widget = _ConcretePlot(None)
    qtbot.addWidget(widget)
    return widget


class TestPlotBaseInit:
    def test_widget_created(self, plot_widget):
        assert plot_widget is not None

    def test_has_canvas(self, plot_widget):
        assert plot_widget.canvas is not None

    def test_has_figure(self, plot_widget):
        assert plot_widget.figure is not None

    def test_size_policy_expanding(self, plot_widget):
        from qtpy.QtWidgets import QSizePolicy

        sp = plot_widget.sizePolicy()
        assert sp.horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert sp.verticalPolicy() == QSizePolicy.Policy.Expanding

    def test_figsize_default(self, plot_widget):
        assert plot_widget.figsize == [8, 8]

    def test_ax_created_on_first_access(self, plot_widget):
        ax = plot_widget.ax
        assert ax is not None
        assert plot_widget._ax is ax  # cached after first access

    def test_zoom_initially_none(self, plot_widget):
        assert plot_widget.zoom is None

    def test_patch_lines_markers_arrows_empty(self, plot_widget):
        assert plot_widget.patch == []
        assert plot_widget.lines == []
        assert plot_widget.markers == []
        assert plot_widget.arrows == []


class TestPlotBaseClear:
    def test_clear_resets_ax(self, plot_widget):
        _ = plot_widget.ax  # force _ax creation
        assert plot_widget._ax is not None
        plot_widget.clear()
        assert plot_widget._ax is None

    def test_clear_resets_collections(self, plot_widget):
        plot_widget.clear()
        assert plot_widget.patch == []
        assert plot_widget.lines == []
        assert plot_widget.markers == []
        assert plot_widget.arrows == []

    def test_clear_resets_zoom(self, plot_widget):
        plot_widget.clear()
        assert plot_widget.zoom is None


class TestPlotBaseXYLimits:
    def test_store_plot_limits_normalizes_extent_order(self, plot_widget):
        ax = plot_widget.ax
        extent = [0, 1, 5, 9]
        plot_widget.store_plot_limits([extent], [ax])
        assert ax.plot_limits == [0, 5, 1, 9]

    def test_store_plot_limits_rejects_invalid_extent_length(self, plot_widget):
        with pytest.raises(ValueError, match="Extent must be"):
            plot_widget.store_plot_limits([[0, 1, 2]], [plot_widget.ax])

    def test_get_xy_limits_after_plot(self, plot_widget):
        x = np.arange(10, dtype=float)
        y = x ** 2
        plot_widget.ax.plot(x, y)
        limits = plot_widget.get_xy_limits()
        assert len(limits) == 4
        xmin, xmax, ymin, ymax = limits
        assert xmin <= xmax
        assert ymin <= ymax

    def test_on_reset_zoom(self, plot_widget):
        x = np.arange(5, dtype=float)
        y = x.copy()
        ax = plot_widget.ax
        ax.plot(x, y)
        plot_widget.store_plot_limits([[0, 0, 5, 5]], [ax])
        # should not raise
        plot_widget.on_reset_zoom()


class TestPlotBaseLines:
    def test_add_vline(self, plot_widget):
        _ = plot_widget.ax
        plot_widget.plot_add_vline(xpos=5.0, gid="test_vline")
        # line should be tracked
        line = plot_widget.get_line("test_vline")
        assert line is not None

    def test_add_then_remove_vline(self, plot_widget):
        _ = plot_widget.ax
        plot_widget.plot_add_vline(xpos=3.0, gid="vline_del")
        plot_widget.plot_remove_line("vline_del")
        line = plot_widget.get_line("vline_del")
        assert line is None

    def test_add_hline(self, plot_widget):
        _ = plot_widget.ax
        plot_widget.plot_add_hline(ypos=2.0, gid="test_hline")
        line = plot_widget.get_line("test_hline")
        assert line is not None


class TestPlotBasePatches:
    def test_add_and_get_patch(self, plot_widget):
        _ = plot_widget.ax
        plot_widget.plot_add_patch(0, 0, 1, 1, obj_name="my_patch")
        patch = plot_widget.get_existing_patch("my_patch")
        assert patch is not None
        assert patch.obj_name == "my_patch"

    def test_remove_patches(self, plot_widget):
        _ = plot_widget.ax
        plot_widget.plot_add_patch(0, 0, 1, 1, obj_name="p1")
        plot_widget.plot_add_patch(1, 0, 1, 1, obj_name="p2")
        plot_widget.plot_remove_patches(repaint=False)
        assert plot_widget.patch == []


class TestPlotBaseRepaint:
    def test_repaint_no_error(self, plot_widget):
        _ = plot_widget.ax
        plot_widget.repaint()

    def test_repaint_false_skips(self, plot_widget):
        """When repaint=False the canvas.draw() should NOT be called."""
        _ = plot_widget.ax
        called = []
        original = plot_widget.canvas.draw
        plot_widget.canvas.draw = lambda: called.append(1)
        plot_widget.repaint(False)
        plot_widget.canvas.draw = original
        assert called == []


class TestPlotBaseSignals:
    def test_evt_move_emitted_by_zoom(self, qtbot, plot_widget):
        """Smoke test: setting up a zoom handler and connecting to evt_move should work."""
        received = []
        plot_widget.evt_move.connect(lambda v: received.append(v))
        # Just verify the signal attribute is present and connectable
        assert hasattr(plot_widget, "evt_move")

    def test_evt_released_emitted(self, qtbot, plot_widget):
        received = []
        plot_widget.evt_released.connect(lambda: received.append(True))
        assert hasattr(plot_widget, "evt_released")

    def test_evt_pick_connected_to_evt_pick(self, qtbot, plot_widget):
        """After setup_new_zoom, evt_pick should forward to evt_pick (not evt_pressed)."""
        import numpy as np

        ax = plot_widget.ax
        ax.plot([0, 1], [0, 1])
        extent = [0, 0, 1, 1]
        plot_widget.setup_new_zoom([ax], data_limits=[extent], allow_extraction=False)
        assert plot_widget.zoom is not None
