"""Example showing how to use the matplotlib backend."""

from __future__ import annotations

import sys

import numpy as np
from qtpy.QtWidgets import QApplication

from qtextraplot.mpl import ViewMplLine


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    view = ViewMplLine(None, title="qtextraplot mpl backend", x_label="x", y_label="y")
    x = np.linspace(0.0, 10.0, 400)
    y = np.sin(x) + 0.15 * np.cos(3 * x)

    view.plot(x, y, color="k")
    view.add_line(x, 0.5 * np.cos(x), gid="secondary", color="tab:red")
    view.add_vline(2.5, gid="cursor")
    view.add_hline(0.0)

    view.widget.resize(900, 500)
    view.widget.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
