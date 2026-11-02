"""
Diálogos de progreso reutilizables.

Viven en la capa de widgets para que los servicios no dependan de Qt Widgets.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressDialog, QWidget


def create_progress_dialog(
    parent: QWidget | None,
    title: str = "Cargando datos",
    label: str = "Cargando archivo...",
) -> QProgressDialog:
    """Crear un QProgressDialog modal con el estilo común de la app."""
    dialog = QProgressDialog(label, "Cancelar", 0, 100, parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    return dialog
