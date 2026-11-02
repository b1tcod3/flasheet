"""
Grips de redimensionado para la ventana sin marco.

Se usa `QWindow.startSystemResize()`, que delega en el compositor: funciona
igual en X11 y Wayland y respeta el escalado por pantalla. Reimplementar el
resize a mano con `setGeometry()` (como en la referencia) se rompe con HiDPI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

GRIP_SIZE = 6


class ResizeGrip(QWidget):
    """Banda invisible en un borde de la ventana que inicia el resize."""

    def __init__(self, parent: QWidget, edge: Qt.Edge, cursor: Qt.CursorShape) -> None:
        super().__init__(parent)
        self._edge = edge
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setToolTip('')

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        window = self.window()
        handle = window.windowHandle() if window is not None else None
        if handle is not None and handle.startSystemResize(self._edge):
            event.accept()
            return

        super().mousePressEvent(event)


def create_grips(window: QWidget) -> dict[str, ResizeGrip]:
    """Crear los cuatro grips de borde de una ventana."""
    grips = {
        'left': ResizeGrip(window, Qt.Edge.LeftEdge, Qt.CursorShape.SizeHorCursor),
        'right': ResizeGrip(window, Qt.Edge.RightEdge, Qt.CursorShape.SizeHorCursor),
        'top': ResizeGrip(window, Qt.Edge.TopEdge, Qt.CursorShape.SizeVerCursor),
        'bottom': ResizeGrip(window, Qt.Edge.BottomEdge, Qt.CursorShape.SizeVerCursor),
    }
    for grip in grips.values():
        grip.raise_()
    return grips


def position_grips(window: QWidget, grips: dict[str, ResizeGrip]) -> None:
    """Recolocar los grips en los bordes de la ventana."""
    width = window.width()
    height = window.height()

    grips['left'].setGeometry(0, GRIP_SIZE, GRIP_SIZE, max(0, height - 2 * GRIP_SIZE))
    grips['right'].setGeometry(width - GRIP_SIZE, GRIP_SIZE, GRIP_SIZE, max(0, height - 2 * GRIP_SIZE))
    grips['top'].setGeometry(0, 0, width, GRIP_SIZE)
    grips['bottom'].setGeometry(0, height - GRIP_SIZE, width, GRIP_SIZE)

    for grip in grips.values():
        grip.raise_()


__all__ = ['GRIP_SIZE', 'ResizeGrip', 'create_grips', 'position_grips']
