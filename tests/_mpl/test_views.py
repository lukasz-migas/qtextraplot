"""Tests for MPL view wrappers."""

from __future__ import annotations

import numpy as np

from qtextraplot.mpl import ViewMplLine


def test_mpl_line_view_plot_update_and_reset(qtbot):
    view = ViewMplLine(None)
    qtbot.addWidget(view.widget)

    x = np.linspace(0, 1, 20)
    y = np.cos(x)
    view.plot(x, y, color="k")
    view.update(x, y + 1)
    view.add_vline(0.5, gid="marker")

    assert view.figure.get_line("marker") is not None

    view.reset()

    assert np.array_equal(view._data["x"], x)
    assert np.array_equal(view._data["y"], y + 1)


def test_mpl_line_view_imshow_caches_image(qtbot):
    view = ViewMplLine(None)
    qtbot.addWidget(view.widget)

    image = np.arange(16).reshape(4, 4)
    view.imshow(image)

    assert np.array_equal(view._data["image"], image)
