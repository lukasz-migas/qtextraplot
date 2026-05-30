"""Example showing canvas legend overlays on the napari image backend."""

from __future__ import annotations

import sys

import numpy as np
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot.napari import NapariImageView


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("qtextraplot napari legend overlay")
    layout = QVBoxLayout(window)

    view = NapariImageView(window, add_toolbars=True, add_dims=True)
    layout.addWidget(view.widget)

    grid = np.linspace(-3.0, 3.0, 256)
    xx, yy = np.meshgrid(grid, grid)
    image = np.sin(2.2 * xx) * np.cos(1.8 * yy) + np.exp(-0.5 * (xx**2 + yy**2))
    view.plot(image, name="Signal", colormap="magma", clip=False)

    points = np.asarray(
        [
            [72.0, 88.0],
            [104.0, 152.0],
            [150.0, 112.0],
            [182.0, 180.0],
        ],
    )
    point_layer = view.viewer.add_points(
        points,
        name="Objects",
        properties={"label": np.asarray(["cell", "cell", "nucleus", "debris"])},
        face_color=["#ff4d4d", "#ff4d4d", "#4dd2ff", "#ffe066"],
        symbol=["disc", "disc", "diamond", "square"],
        size=16,
    )

    view.set_legend_from_points(
        point_layer,
        name="Object legend",
        position="top_right",
        font_size=11,
        marker_size=12,
        background_color=(0.0, 0.0, 0.0, 0.7),
    )
    view.set_legend(
        [
            {"label": "Intensity", "colormap": "magma"},
            {"label": "Manual note", "marker": "star", "color": "white"},
        ],
        name="Manual legend",
        position="bottom_left",
        font_size=10,
    )

    window.resize(900, 700)
    window.show()
    THEMES.apply(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
