"""Enums."""

import typing as ty

from qtextraplot._napari.image.components.viewer_model import Viewer as ImageViewer

try:
    from napari_plot.viewer import ViewerModel as LineViewer
except ImportError:
    LineViewer = None


ViewerType = ImageViewer if LineViewer is None else ty.Union[ImageViewer, LineViewer]
