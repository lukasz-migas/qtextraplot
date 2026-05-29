"""Example showing object outline overlays on the napari image backend."""

from __future__ import annotations

import sys

import numpy as np
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot.napari import NapariImageView


def ellipse_outline(
    center: tuple[float, float],
    radius: tuple[float, float],
    n_points: int = 180,
) -> np.ndarray:
    """Create an ellipse outline in image data coordinates."""
    theta = np.linspace(0.0, 2.0 * np.pi, n_points, endpoint=False)
    y = center[0] + radius[0] * np.sin(theta)
    x = center[1] + radius[1] * np.cos(theta)
    return np.column_stack((y, x))


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("qtextraplot napari object outlines")
    layout = QVBoxLayout(window)

    view = NapariImageView(window, add_toolbars=True, add_dims=True)
    layout.addWidget(view.widget)

    grid = np.linspace(-3.0, 3.0, 256)
    xx, yy = np.meshgrid(grid, grid)
    image = np.sin(2.5 * xx) * np.cos(2.5 * yy) + np.exp(-0.7 * (xx**2 + yy**2))
    image_layer = view.plot(image, name="Signal", colormap="viridis", clip=False)

    outline_a = ellipse_outline((78.0, 88.0), (26.0, 40.0))
    outline_b = ellipse_outline((152.0, 165.0), (34.0, 24.0))
    outline_c = np.array(
        [
            [72.0, 178.0],
            [116.0, 206.0],
            [142.0, 184.0],
            [126.0, 138.0],
            [88.0, 136.0],
        ],
    )

    view.set_object_outlines(
        [outline_a, outline_b, outline_c],
        name="Detected objects",
        target_layer=image_layer,
        color=["#ff4d4d", "#4dd2ff", "#ffe066"],
        width=[2.0, 3.0, 2.0],
    )
    view.set_object_outlines(
        ellipse_outline((128.0, 128.0), (62.0, 62.0)),
        name="Reference outline",
        target_layer=image_layer,
        color="white",
        width=1.5,
    )

    window.resize(900, 700)
    window.show()
    THEMES.apply(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
