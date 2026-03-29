"""Example showing how to use the pyqtgraph backend."""

from __future__ import annotations

import sys

import numpy as np
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication

from qtextraplot.pyqtgraph import ViewPyQtGraphCanvas


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    view = ViewPyQtGraphCanvas(None, x_label="x", y_label="y", title="Universal pyqtgraph canvas")

    x = np.linspace(0.0, 10.0, 300)
    view.plot(x, np.sin(x), gid="signal", color="black")
    view.add_line(x, 0.5 * np.cos(2 * x), gid="secondary", color="green")
    view.scatter(x[::12], np.sin(x[::12]), gid="samples", color="magenta", size=9)

    grid = np.linspace(-3.0, 3.0, 256)
    xx, yy = np.meshgrid(grid, grid)
    image = np.cos(xx) * np.sin(yy) * np.exp(-0.15 * (xx**2 + yy**2))
    view.imshow(image, gid="heatmap", opacity=0.45)

    view.add_vline(3.0, gid="cursor")
    view.add_hline(0.0)
    view.add_infline(pos=7.0, angle=90, gid="limit", color="pink")
    view.show_patch(4.0, -1.0, 1.5, 2.0, obj_name="roi", color=(255, 255, 0, 80))

    view.widget.resize(1000, 700)
    view.widget.show()
    THEMES.apply(view.widget)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
