"""Example showing how to use the napari-plot line backend."""

from __future__ import annotations

import sys

import numpy as np
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot._napari import NapariLineView
from qtextra.config import THEMES


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("qtextraplot napari_plot backend")
    layout = QVBoxLayout(window)

    view = NapariLineView(window, x_label="Time", y_label="Amplitude", add_toolbars=True, allow_tools=True)
    layout.addWidget(view.widget)

    x = np.linspace(0.0, 20.0, 500)
    y = np.sin(x) + 0.2 * np.cos(4 * x)

    view.plot(x, y, name="Signal", reset_x=True, reset_y=True)
    view.add_scatter(x[::25], y[::25], name="Samples", symbol="disc", size=8)
    view.add_inf_line(5.0, orientation="vertical", color=(1.0, 0.4, 0.1, 1.0), name="Reference")
    view.add_centroids(np.array([2.5, 7.5, 12.5]), np.array([0.8, -0.4, 0.5]), name="Peaks", width=6)

    window.resize(900, 500)
    window.show()
    THEMES.apply(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
