"""Example showing how to use the napari image backend."""

from __future__ import annotations

import sys

import numpy as np
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot._napari import NapariImageView


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("qtextraplot napari backend")
    layout = QVBoxLayout(window)

    view = NapariImageView(window, add_toolbars=True, add_dims=True)
    layout.addWidget(view.widget)

    x = np.linspace(-2.0, 2.0, 256)
    xx, yy = np.meshgrid(x, x)
    image = np.sin(xx**2 + yy**2) * np.exp(-0.5 * (xx**2 + yy**2))
    mask = (xx**2 + yy**2) < 1.0

    view.plot(image, name="Signal", colormap="viridis")
    view.add_image_mask(mask.astype(np.uint8), name="Mask", opacity=0.35, editable=False)

    window.resize(900, 700)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
