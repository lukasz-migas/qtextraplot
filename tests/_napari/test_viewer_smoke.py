"""Smoke tests for the embedded napari viewers."""

from __future__ import annotations

import numpy as np

from qtextraplot._napari.image.wrapper import NapariImageView


def test_image_view_constructs_and_adds_image(qtbot, _mock_opengl_capabilities) -> None:
    """The image viewer should construct and render a napari 0.8 image layer."""
    view = NapariImageView(
        add_dims=False,
        add_toolbars=False,
        allow_extraction=False,
    )
    qtbot.addWidget(view.widget)

    layer = view.add_image(np.arange(16, dtype=float).reshape(4, 4))

    assert layer in view.viewer.layers
    assert view.widget.canvas._font_info.face == view.widget._overlay_font


def test_extract_shapes_layer_uses_image_scale(qtbot, _mock_opengl_capabilities) -> None:
    """The extraction layer should inherit the image scale with napari 0.8."""
    view = NapariImageView(
        add_dims=False,
        add_toolbars=False,
        allow_extraction=False,
    )
    qtbot.addWidget(view.widget)
    image_layer = view.plot(
        np.arange(16, dtype=float).reshape(4, 4),
        clip=False,
        scale=(2.0, 3.0),
    )

    shapes_layer = view.add_extract_shapes_layer()

    np.testing.assert_array_equal(shapes_layer.scale, image_layer.scale)
