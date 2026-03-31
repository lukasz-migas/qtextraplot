"""Public import surface tests."""

import pytest

from qtextraplot.mpl import ViewMplLine
from qtextraplot.napari import NapariImageView
from qtextraplot.napari_plot import NapariLineView
from qtextraplot.pyqtgraph import ViewPyQtGraphImage, ViewPyQtGraphLine, ViewPyQtGraphScatter

vispy = pytest.importorskip("vispy")

from qtextraplot.vispy import PlotLine, PlotScatter, ViewVispyLine, ViewVispyScatter


def test_public_backend_imports():
    assert NapariImageView is not None
    assert NapariLineView is not None
    assert ViewPyQtGraphLine is not None
    assert ViewPyQtGraphScatter is not None
    assert ViewPyQtGraphImage is not None
    assert ViewMplLine is not None
    assert PlotLine is not None
    assert PlotScatter is not None
    assert ViewVispyLine is not None
    assert ViewVispyScatter is not None
