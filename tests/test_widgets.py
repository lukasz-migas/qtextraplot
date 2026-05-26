"""Widget tests."""

from __future__ import annotations

from napari.utils.colormaps import AVAILABLE_COLORMAPS

from qtextraplot.widgets import QtColormapButton


def test_colormap_button_updates_preview_and_emits(qtbot) -> None:
    """Colormap button should update the selected colormap and preview icon."""
    button = QtColormapButton(colormap="magma")
    qtbot.addWidget(button)
    emitted: list[str] = []
    button.evt_colormap_changed.connect(emitted.append)

    button.set_colormap("viridis")

    assert button.current_colormap() == "viridis"
    assert emitted == ["viridis"]
    assert not button.icon().isNull()


def test_colormap_button_custom_color_registers_colormap(qtbot) -> None:
    """Custom colors should become selectable napari colormaps."""
    button = QtColormapButton(colormap="magma")
    qtbot.addWidget(button)
    emitted: list[str] = []
    button.evt_colormap_changed.connect(emitted.append)

    button.set_custom_color("#ff0000")

    assert button.current_colormap() == "custom #ff0000"
    assert emitted == ["custom #ff0000"]
    assert "custom #ff0000" in AVAILABLE_COLORMAPS
    assert not button.icon().isNull()


def test_colormap_button_popup_opens_combobox_list(qtbot) -> None:
    """Left-click behavior should show the colormap option list directly."""
    button = QtColormapButton(colormap="magma")
    qtbot.addWidget(button)

    button.show_colormap_popup()

    assert button._popup is not None
    qtbot.waitUntil(lambda: button._popup.combobox.view().isVisible())
