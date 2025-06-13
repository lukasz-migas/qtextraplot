"""Enums."""

import typing as ty

from qtextraplot._napari.image.components.viewer_model import Viewer as ImageViewer

try:
    from qtextraplot._napari.line.components.viewer_model import Viewer as LineViewer
except ImportError:
    LineViewer = None


if LineViewer is None:
    ViewerType = ty.Union[LineViewer, ImageViewer]
else:
    ViewerType = ImageViewer
