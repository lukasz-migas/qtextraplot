"""Example showing the standalone colorbar widget above a napari canvas."""

from __future__ import annotations

import sys

import numpy as np
from napari.layers import Image
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot.napari import NapariImageView, QtNapariImageColorbarWidget


def make_signal(shape: tuple[int, int], center: tuple[float, float], width: float) -> np.ndarray:
    """Create a smooth synthetic image for the example."""
    y = np.linspace(-1.0, 1.0, shape[0])
    x = np.linspace(-1.0, 1.0, shape[1])
    xx, yy = np.meshgrid(x, y)
    distance = ((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / width
    signal = np.exp(-distance)
    signal += 0.18 * np.exp(-((xx + 0.25) ** 2 + (yy - 0.3) ** 2) / (width * 0.35))
    return signal / np.nanmax(signal)


class ColorbarCanvasExample(QWidget):
    """Napari canvas with an externally managed colorbar overlay."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("qtextraplot napari colorbar widget")
        self._dynamic_layer: Image | None = None

        self.view = NapariImageView(self, add_toolbars=True, add_dims=False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view.widget)

        self._add_layers()
        self.colorbar_panel = QtNapariImageColorbarWidget(
            self.view.viewer,
            self,
            title="Image colorbars",
            size_preset="medium",
        )
        self.colorbar_panel.raise_()

        self._schedule_layer_list_demo()

    def resizeEvent(self, event) -> None:
        """Keep the colorbar panel hovering above the canvas."""
        super().resizeEvent(event)
        if not hasattr(self, "colorbar_panel"):
            return
        width = min(760, max(320, self.width() - 32))
        self.colorbar_panel.setGeometry(16, 16, width, self.colorbar_panel.sizeHint().height())

    def _add_layers(self) -> None:
        shape = (256, 256)
        layers = [
            ("703.5724 m/z +/- 21.3 ppm", "magenta", make_signal(shape, (-0.35, -0.2), 0.18)),
            ("734.5666 m/z +/- 20.4 ppm", "blue", make_signal(shape, (0.2, 0.05), 0.14)),
            ("762.5639 m/z +/- 19.2 ppm", "green", make_signal(shape, (0.05, 0.35), 0.2)),
        ]

        self.layers: list[Image] = []
        for index, (name, colormap, data) in enumerate(layers):
            selected_min = 0.3 if index else 0.5
            selected_max = 1.0 / (2.8 if index != 1 else 2.0)
            layer = self.view.add_image(
                data,
                name=name,
                colormap=colormap,
                blending="additive",
                keep_auto_contrast=False,
            )
            layer.contrast_limits_range = (0.0, 1.0)
            layer.contrast_limits = (selected_min * selected_max, selected_max)
            self.layers.append(layer)

    def _schedule_layer_list_demo(self) -> None:
        pass
        # QTimer.singleShot(1200, self._add_dynamic_layer)
        # QTimer.singleShot(3200, self._remove_dynamic_layer)

    def _add_dynamic_layer(self) -> None:
        data = make_signal((256, 256), (0.42, -0.35), 0.1)
        self._dynamic_layer = self.view.add_image(
            data,
            name="Dynamic 780.5912 m/z +/- 18.8 ppm",
            colormap="yellow",
            blending="additive",
            keep_auto_contrast=False,
        )
        self._dynamic_layer.contrast_limits_range = (0.0, 1.0)
        self._dynamic_layer.contrast_limits = (0.15, 0.45)

    def _remove_dynamic_layer(self) -> None:
        if self._dynamic_layer is not None and self._dynamic_layer in self.view.viewer.layers:
            self.view.viewer.layers.remove(self._dynamic_layer)
            self._dynamic_layer = None


def main() -> int:
    """Run the example application."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = ColorbarCanvasExample()
    window.resize(980, 720)
    window.show()
    THEMES.apply(window)
    window.colorbar_panel.raise_()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
