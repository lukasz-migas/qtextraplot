"""Tests for VisPy view wrappers."""

from __future__ import annotations

import numpy as np
import pytest

vispy = pytest.importorskip("vispy", reason="vispy is not installed")

from qtextraplot.vispy import ViewVispyLine, ViewVispyScatter  # noqa: E402


def test_vispy_line_view_caches_and_resets(qtbot):
    view = ViewVispyLine(None)
    qtbot.addWidget(view.widget)

    x = np.linspace(0, 1, 10)
    y = np.sin(x)
    view.plot(x, y, color=(1, 0, 0))
    view.add_line(x, y * 2, gid="extra")
    view.update_line_width(3, gid="extra")

    assert "extra" in view.figure.nodes

    view.reset()

    assert np.array_equal(view._data["x"], x)
    assert np.array_equal(view._data["y"], y)


def test_vispy_line_view_supports_viewbase_annotations(qtbot):
    view = ViewVispyLine(None)
    qtbot.addWidget(view.widget)

    x = np.linspace(0, 1, 10)
    view.plot(x, np.sin(x))
    view.add_vline(0.4, gid="cursor")
    view.add_hline(0.0)

    assert "cursor" in view.figure.nodes
    assert "ax_hline" in view.figure.nodes


def test_vispy_scatter_view_updates_data(qtbot):
    view = ViewVispyScatter(None)
    qtbot.addWidget(view.widget)

    x = np.linspace(0, 1, 5)
    y = x**2
    view.plot(x, y)
    view.update(x, y + 1)

    assert np.array_equal(view._data["x"], x)
    assert np.array_equal(view._data["y"], y + 1)
