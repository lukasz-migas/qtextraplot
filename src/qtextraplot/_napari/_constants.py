"""Base constants."""

import sys
from collections import OrderedDict

from napari.layers.base._base_constants import Blending
from napari.layers.labels._labels_constants import LabelColorMode, LabelsRendering
from napari.utils.compat import StrEnum

BACKSPACE = "delete" if sys.platform == "darwin" else "backspace"
BLENDING_TRANSLATIONS = OrderedDict(
    [
        (Blending.TRANSLUCENT, "Translucent"),
        (Blending.TRANSLUCENT_NO_DEPTH, "Translucent (no depth)"),
        (Blending.ADDITIVE, "Additive"),
        (Blending.OPAQUE, "Opaque"),
        (Blending.MINIMUM, "Minimum"),
    ]
)


RENDER_MODE_TRANSLATIONS = OrderedDict(
    [
        (LabelsRendering.TRANSLUCENT, "Translucent"),
        (LabelsRendering.ISO_CATEGORICAL, "Iso-categorical"),
    ]
)

LABEL_COLOR_MODE_TRANSLATIONS = OrderedDict(
    [
        (LabelColorMode.AUTO, "auto"),
        (LabelColorMode.DIRECT, "direct"),
    ]
)


class Symbol(StrEnum):
    """Symbol: Valid symbol/marker types for the Points layer.
    The string method returns the valid vispy string.

    """

    ARROW = "arrow"
    CLOBBER = "clobber"
    CROSS = "cross"
    DIAMOND = "diamond"
    DISC = "disc"
    HBAR = "hbar"
    RING = "ring"
    SQUARE = "square"
    STAR = "star"
    TAILED_ARROW = "tailed_arrow"
    TRIANGLE_DOWN = "triangle_down"
    TRIANGLE_UP = "triangle_up"
    VBAR = "vbar"
    X = "x"

    def __str__(self):
        """String representation: The string method returns the
        valid vispy symbol string for the Markers visual.
        """
        return self.value


# Mapping of symbol alias names to the deduplicated name
SYMBOL_ALIAS = {
    "o": Symbol.DISC,
    "*": Symbol.STAR,
    "+": Symbol.CROSS,
    "-": Symbol.HBAR,
    "->": Symbol.TAILED_ARROW,
    ">": Symbol.ARROW,
    "^": Symbol.TRIANGLE_UP,
    "v": Symbol.TRIANGLE_DOWN,
    "s": Symbol.SQUARE,
    "|": Symbol.VBAR,
}

SYMBOL_TRANSLATION = OrderedDict(
    [
        (Symbol.ARROW, "arrow"),
        (Symbol.CLOBBER, "clobber"),
        (Symbol.CROSS, "cross"),
        (Symbol.DIAMOND, "diamond"),
        (Symbol.DISC, "disc"),
        (Symbol.HBAR, "hbar"),
        (Symbol.RING, "ring"),
        (Symbol.SQUARE, "square"),
        (Symbol.STAR, "star"),
        (Symbol.TAILED_ARROW, "tailed arrow"),
        (Symbol.TRIANGLE_DOWN, "triangle down"),
        (Symbol.TRIANGLE_UP, "triangle up"),
        (Symbol.VBAR, "vbar"),
        (Symbol.X, "x"),
    ]
)
