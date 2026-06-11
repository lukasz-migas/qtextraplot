"""Example showing canvas legend overlays on the napari-plot line backend."""

from __future__ import annotations

import sys

import numpy as np
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot.napari_plot import NapariLineView


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("qtextraplot napari-plot legend overlay")
    layout = QVBoxLayout(window)

    view = NapariLineView(window, x_label="Time", y_label="Amplitude", add_toolbars=True, allow_tools=True)
    layout.addWidget(view.widget)

    x = np.linspace(0.0, 20.0, 500)
    y = np.sin(x) + 0.25 * np.cos(3.0 * x)
    sample_indices = np.arange(20, x.size, 45)

    view.plot(x, y, name="Signal", color="#4dd2ff", reset_x=True, reset_y=True)
    view.add_scatter(
        x[sample_indices],
        y[sample_indices],
        name="Samples",
        face_color="#ffcc4d",
        border_color="#ffffff",
        symbol="square",
        size=9,
    )
    view.add_centroids(
        x[[70, 185, 320, 430]],
        y[[70, 185, 320, 430]],
        name="Detected peaks",
        color="#ff4d8d",
        orientation="vertical",
        width=6,
    )
    view.viewer.add_points(
        np.column_stack((x[[120, 270, 390]], y[[120, 270, 390]] + 0.35)),
        name="Annotations",
        face_color=["#b3ff66", "#b3ff66", "#8c66ff"],
        border_color="#111111",
        symbol=["disc", "disc", "triangle_up"],
        size=14,
    )

    view.set_legend_from_layers(
        visible=True,
        sync=True,
        position="top_right",
        font_size=10,
        marker_size=12,
        background_color=(0.0, 0.0, 0.0, 0.65),
    )

    window.resize(900, 500)
    window.show()
    THEMES.apply(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
