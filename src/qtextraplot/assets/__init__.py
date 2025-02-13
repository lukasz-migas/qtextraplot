"""Assets."""

from __future__ import annotations

from pathlib import Path

from koyo.system import get_module_path

# from napari._qt.qt_resources import STYLES as NAPARI_STYLES
from napari.resources import ICONS as NAPARI_ICONS
from qtextra.assets import update_icons, update_styles

HERE = Path(get_module_path("qtextraplot.assets", "__init__.py")).parent.resolve()


ICONS_PATH = HERE / "icons"
ICONS_PATH.mkdir(exist_ok=True)
ICONS = {x.stem: str(x) for x in ICONS_PATH.iterdir() if x.suffix == ".svg"}
ICONS.update(NAPARI_ICONS)
update_icons(ICONS, append=True)

STYLES_PATH = HERE / "stylesheets"
STYLES_PATH.mkdir(exist_ok=True)
STYLES = {x.stem: str(x) for x in STYLES_PATH.iterdir() if x.suffix == ".qss"}
# STYLES.update(NAPARI_STYLES)
update_styles(STYLES, append=True)
