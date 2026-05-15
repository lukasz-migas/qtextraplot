"""Example showing the standalone colorbar widget above a napari canvas."""

from __future__ import annotations

import sys
import typing as ty

import numpy as np
from napari.layers import Image
from napari.utils.colormaps import Colormap
from qtextra.config import THEMES
from qtpy.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget

from qtextraplot._napari import NapariImageView
from qtextraplot.widgets import ColorbarStackItem, QtColorbarStack


def make_signal(shape: tuple[int, int], center: tuple[float, float], width: float) -> np.ndarray:
    """Create a smooth synthetic image for the example."""
    y = np.linspace(-1.0, 1.0, shape[0])
    x = np.linspace(-1.0, 1.0, shape[1])
    xx, yy = np.meshgrid(x, y)
    distance = ((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / width
    signal = np.exp(-distance)
    signal += 0.18 * np.exp(-((xx + 0.25) ** 2 + (yy - 0.3) ** 2) / (width * 0.35))
    return signal / np.nanmax(signal)


def transparent_low_colormap(colormap: Colormap, active: bool) -> Colormap:
    """Return a colormap with optional transparent low values."""
    low_color = [0.0, 0.0, 0.0, 0.0] if active else None
    return colormap.copy(update={"low_color": low_color})


class ColorbarCanvasExample(QWidget):
    """Napari canvas with an externally managed colorbar overlay."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("qtextraplot napari colorbar widget")
        self._base_colormaps: dict[Image, Colormap] = {}

        self.view = NapariImageView(self, add_toolbars=True, add_dims=False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view.widget)

        self.colorbar_panel = QFrame(self)
        self.colorbar_panel.setObjectName("floatingColorbarPanel")
        self.colorbar_panel.setStyleSheet(
            "QFrame#floatingColorbarPanel { background: rgba(0, 0, 0, 180); border-radius: 4px; }",
        )
        panel_layout = QVBoxLayout(self.colorbar_panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        self.colorbar_stack = QtColorbarStack(self.colorbar_panel)
        panel_layout.addWidget(self.colorbar_stack)
        self.colorbar_panel.raise_()

        self._add_layers()
        self._configure_colorbars()

    def resizeEvent(self, event) -> None:
        """Keep the colorbar panel hovering above the canvas."""
        super().resizeEvent(event)
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
        for name, colormap, data in layers:
            layer = self.view.add_image(
                data,
                name=name,
                colormap=colormap,
                blending="additive",
                contrast_limits=(0.0, 1.0),
                keep_auto_contrast=False,
            )
            self._base_colormaps[layer] = layer.colormap
            self.layers.append(layer)

    def _configure_colorbars(self) -> None:
        items = []
        for index, layer in enumerate(self.layers):
            selected_min = 0.3 if index else 0.5
            selected_max = 1.0 / (2.8 if index != 1 else 2.0)
            items.append(
                ColorbarStackItem(
                    label=layer.name,
                    data_range=(0.0, 1.0),
                    limits=(selected_min * selected_max, selected_max),
                    colorbar=self._base_colormaps[layer].colorbar,
                ),
            )

        self.colorbar_stack.set_items(items)
        for layer, widget in zip(self.layers, self.colorbar_stack.widgets, strict=True):
            widget.limitsChanged.connect(
                ty.cast(
                    ty.Callable[[tuple[float, float]], None],
                    lambda limits, layer=layer: self._on_limits_changed(layer, limits),
                ),
            )
            self._on_limits_changed(layer, widget.value())

    def _on_limits_changed(self, layer: Image, limits: tuple[float, float]) -> None:
        """Apply externally managed limits to a napari image layer."""
        layer.contrast_limits = limits
        data_min = float(layer.contrast_limits_range[0])
        active = float(limits[0]) > data_min
        layer.colormap = transparent_low_colormap(self._base_colormaps[layer], active)


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
