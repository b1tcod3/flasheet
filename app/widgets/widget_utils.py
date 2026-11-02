"""
Utilidades para widgets creados y destruidos en tiempo de ejecución.

Qt mantiene viva una conexión mientras el objeto exista; destruir con `del`
deja punteros colgando. `blockSignals` + `deleteLater` es la forma segura:
corta emisiones pendientes y deja que el event loop libere el objeto.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


def dispose_widget(widget: QWidget | None) -> None:
    """Bloquear señales y programar la destrucción segura de un widget."""
    if widget is None:
        return

    widget.blockSignals(True)
    widget.setParent(None)
    widget.deleteLater()


__all__ = ['dispose_widget']
