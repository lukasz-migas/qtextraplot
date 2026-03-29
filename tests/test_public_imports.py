"""Public import surface tests."""

from qtextraplot._napari import NapariImageView, NapariLineView
from qtextraplot._pyqtgraph import ViewPyQtGraphImage, ViewPyQtGraphLine, ViewPyQtGraphScatter


def test_public_backend_imports():
    assert NapariImageView is not None
    assert NapariLineView is not None
    assert ViewPyQtGraphLine is not None
    assert ViewPyQtGraphScatter is not None
    assert ViewPyQtGraphImage is not None
