"""Colorbar overlay rendering tests."""

from __future__ import annotations

import typing as ty

import matplotlib as mpl
from matplotlib.text import Text

from qtextraplot._napari._vispy.overlays.color_bar import ColorBar
from qtextraplot._napari.components.overlays.color_bar import ColorBarOverlay


def test_legacy_percentage_colorbar_renders_percent_ticks(monkeypatch) -> None:
    """Three-element colorbar items should retain percentage tick labels."""
    ticklabels: list[list[str]] = []
    monkeypatch.setattr(
        mpl.colorbar.Colorbar,
        "set_ticklabels",
        lambda _self, labels: ticklabels.append(list(labels)),
    )
    visual = ColorBar()
    visual.colorbar_data = (("viridis", "Ion", (0.0, 100.0)),)

    image = visual._draw_colorbar()

    assert image is not None
    assert ticklabels == [["0.0%", "100.0%"]]


def test_absolute_colorbar_renders_numeric_ticks_and_unit(monkeypatch) -> None:
    """Four-element colorbar items should show absolute limits and a unit label."""
    ticklabels: list[list[str]] = []
    labels: list[str] = []
    original_text = mpl.axes.Axes.text

    def _capture_text(
        self: mpl.axes.Axes,
        x: float,
        y: float,
        text: str,
        *args: ty.Any,
        **kwargs: ty.Any,
    ) -> Text:
        labels.append(str(text))
        return original_text(self, x, y, text, *args, **kwargs)

    monkeypatch.setattr(
        mpl.colorbar.Colorbar,
        "set_ticklabels",
        lambda _self, values: ticklabels.append(list(values)),
    )
    monkeypatch.setattr(mpl.axes.Axes, "text", _capture_text)
    payload = (("viridis", "Ion", (1.25, 9.5), "uM"),)
    overlay = ColorBarOverlay(data=payload)
    visual = ColorBar()
    visual.colorbar_data = overlay.data

    image = visual._draw_colorbar()

    assert image is not None
    assert ticklabels == [["1.25", "9.5"]]
    assert "Ion" in labels
    assert "uM" in labels
