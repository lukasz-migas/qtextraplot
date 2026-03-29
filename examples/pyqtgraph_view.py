"""Example showing how to use the pyqtgraph backend."""

from __future__ import annotations

import sys

import numpy as np
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication, QTabWidget

from qtextraplot._pyqtgraph import ViewPyQtGraphImage, ViewPyQtGraphLine, ViewPyQtGraphScatter


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    tabs = QTabWidget()
    tabs.setWindowTitle("qtextraplot pyqtgraph backend")

    x = np.linspace(0.0, 10.0, 300)
    line_view = ViewPyQtGraphLine(tabs, x_label="x", y_label="y", title="Line plot")
    line_view.plot(x, np.sin(x), color="c")
    line_view.add_line(x, 0.5 * np.cos(2 * x), gid="secondary", color="m")
    line_view.add_vline(3.0, gid="cursor")
    line_view.add_hline(0.0)
    line_view.show_patch(4.0, -1.0, 1.5, 2.0, obj_name="roi", color=(255, 255, 0, 80))
    tabs.addTab(line_view.widget, "Line")

    scatter_view = ViewPyQtGraphScatter(tabs, x_label="x", y_label="y", title="Scatter plot")
    scatter_x = np.linspace(0.0, 1.0, 40)
    scatter_view.plot(scatter_x, scatter_x**2, color="y", size=9)
    scatter_view.add_vline(0.5, gid="x=0.5")
    tabs.addTab(scatter_view.widget, "Scatter")

    image_view = ViewPyQtGraphImage(tabs, title="Image plot")
    grid = np.linspace(-3.0, 3.0, 256)
    xx, yy = np.meshgrid(grid, grid)
    image = np.cos(xx) * np.sin(yy) * np.exp(-0.15 * (xx**2 + yy**2))
    image_view.plot(image)
    image_view.add_vline(128, gid="midline")
    tabs.addTab(image_view.widget, "Image")

    tabs.resize(1000, 700)
    tabs.show()
    THEMES.apply(tabs)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
