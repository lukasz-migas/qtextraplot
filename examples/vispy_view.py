"""Example showing how to use the VisPy backend."""

from __future__ import annotations

import sys

import numpy as np
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot.vispy import ViewVispyLine, ViewVispyScatter


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    x = np.linspace(0.0, 12.0, 300)
    window = QWidget()
    layout = QVBoxLayout(window)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(12)

    line_view = ViewVispyLine(None, x_label="x", y_label="y")
    line_view.plot(x, np.sin(x), color=(0.0, 0.0, 0.0))
    line_view.add_line(x, 0.5 * np.cos(2 * x), gid="secondary", color=(1.0, 0.0, 0.0))
    line_view.add_vline(4.0, gid="cursor")
    line_view.add_hline(0.0)
    layout.addWidget(line_view.widget)

    scatter_view = ViewVispyScatter(None, x_label="x", y_label="y")
    scatter_view.plot(x[::10], np.sin(x[::10]), face_color="#00AAFF", edge_color="#004466", size=8)
    layout.addWidget(scatter_view.widget)

    window.setWindowTitle("qtextraplot vispy backend")
    window.resize(900, 1000)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
