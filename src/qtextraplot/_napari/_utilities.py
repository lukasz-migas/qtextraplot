"""Utilities."""

from functools import lru_cache

from qtpy.QtCore import QPoint, QSize, Qt
from qtpy.QtGui import QPainter, QPen, QPixmap


@lru_cache(maxsize=2)
def get_font_for_os() -> str:
    """Get a font that supports unicode characters."""
    from koyo.system import IS_LINUX, IS_MAC, IS_WIN
    from vispy.util.fonts import list_fonts

    fonts = list_fonts()
    if IS_WIN:
        font = "Segoe UI"
        alt_font = "Calibri"
    elif IS_MAC:
        font = alt_font = "Helvetica"
    elif IS_LINUX:
        font = "DejaVu Sans"
        alt_font = "Liberation Sans"
    else:
        font = alt_font = "DejaVu Sans"
    if font not in fonts:
        font = alt_font
    if font not in fonts:
        font = "OpenSans"
    return font


@lru_cache(maxsize=64)
def crosshair_pixmap():
    """Create a cross cursor with white/black hollow square pixmap in the middle.
    For use as points cursor.
    """
    size = 25

    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)

    # Base measures
    width = 1
    center = 3  # Must be odd!
    rect_size = center + 2 * width
    square = rect_size + width * 4

    pen = QPen(Qt.GlobalColor.white, 1)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)

    # # Horizontal rectangle
    painter.drawRect(0, (size - rect_size) // 2, size - 1, rect_size - 1)

    # Vertical rectangle
    painter.drawRect((size - rect_size) // 2, 0, rect_size - 1, size - 1)

    # Square
    painter.drawRect((size - square) // 2, (size - square) // 2, square - 1, square - 1)

    pen = QPen(Qt.GlobalColor.black, 2)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)

    # # Square
    painter.drawRect(
        (size - square) // 2 + 2,
        (size - square) // 2 + 2,
        square - 4,
        square - 4,
    )

    pen = QPen(Qt.GlobalColor.black, 3)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)

    # # # Horizontal lines
    mid_vpoint = QPoint(2, size // 2)
    painter.drawLine(mid_vpoint, QPoint(((size - center) // 2) - center + 1, size // 2))
    mid_vpoint = QPoint(size - 3, size // 2)
    painter.drawLine(mid_vpoint, QPoint(((size - center) // 2) + center + 1, size // 2))

    # # # Vertical lines
    mid_hpoint = QPoint(size // 2, 2)
    painter.drawLine(QPoint(size // 2, ((size - center) // 2) - center + 1), mid_hpoint)
    mid_hpoint = QPoint(size // 2, size - 3)
    painter.drawLine(QPoint(size // 2, ((size - center) // 2) + center + 1), mid_hpoint)

    painter.end()
    return pixmap
