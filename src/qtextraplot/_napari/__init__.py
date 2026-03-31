"""Init."""

import contextlib
import sys

try:
    import napari
except ImportError:
    raise ImportError(
        "Failed to import optional dependency 'napari'. "
        f"Current interpreter: {sys.executable}. "
        "Install it in this environment with 'pip install napari' or use the same interpreter where napari is already"
        " installed.",
    ) from None

with contextlib.suppress(ImportError, TypeError):
    import napari_plot
    # raise ImportError("please install napari using 'pip install napari-plot'") from None


# Monkey patch icons
import napari.resources._icons

import qtextraplot._napari._register
from qtextraplot.assets import ICONS

# overwrite napari list of icons
# This is required because we've added several new layer types that have custom icons associated with them.
napari.resources._icons.ICONS.update(ICONS)


from qtextraplot._napari.image.wrapper import NapariImageView

with contextlib.suppress(ImportError):
    from qtextraplot._napari.line.wrapper import NapariLineView
