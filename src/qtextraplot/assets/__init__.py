"""Assets."""

from __future__ import annotations

from pathlib import Path

from koyo.system import get_module_path

# from napari._qt.qt_resources import STYLES as NAPARI_STYLES
from napari.resources import ICONS as NAPARI_ICONS
from qtextra.assets import update_icons, update_styles, update_icon_mapping

HERE = Path(get_module_path("qtextraplot.assets", "__init__.py")).parent.resolve()


ICONS_PATH = HERE / "icons"
ICONS_PATH.mkdir(exist_ok=True)
ICONS = {x.stem: str(x) for x in ICONS_PATH.iterdir() if x.suffix == ".svg"}
ICONS.update(NAPARI_ICONS)
update_icons(ICONS)

STYLES_PATH = HERE / "stylesheets"
STYLES_PATH.mkdir(exist_ok=True)
STYLES = {x.stem: str(x) for x in STYLES_PATH.iterdir() if x.suffix == ".qss"}
# STYLES.update(NAPARI_STYLES)
update_styles(STYLES)


update_icon_mapping(
    {
        "new_surface": "ei.star",
        "new_labels": "fa5s.tag",
        "ndisplay_off": "ph.square",
        "ndisplay_on": "ph.cube",
        "roll": "mdi6.rotate-right-variant",
        "transpose": "ri.t-box-line",
        "grid_off": "mdi6.grid-off",
        "grid_on": "mdi6.grid",
        "line": "ph.line-segment-fill",
        "path": "mdi.chart-line-variant",
        "vertex_insert": "mdi.map-marker-plus",
        "vertex_remove": "mdi.map-marker-minus",
        "vertex_select": "mdi.map-marker-check",
        "grid": "mdi.grid",
        "layers": "fa5s.layer-group",
        "rectangle": "ph.rectangle-bold",
        "ellipse": "mdi6.ellipse-outline",
        "polygon": "mdi.pentagon-outline",
    },
    key="qtextraplot",
)


def load_assets() -> None:
    """Load assets."""
