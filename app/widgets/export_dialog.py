"""
Diálogo de selección de formato de exportación.

Concentra la UI de exportación (formato, título del diálogo y filtro de
archivo) que antes vivía repartida en el coordinador.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ExportFormat(Enum):
    """Formato de exportación con sus metadatos de UI."""

    XLSX = ('Excel (.xlsx)', 'Guardar como Excel', 'Archivos Excel (*.xlsx)', False)
    CSV = ('CSV (.csv)', 'Guardar como CSV', 'Archivos CSV (*.csv)', False)
    PDF = ('PDF (.pdf)', 'Guardar como PDF', 'Archivos PDF (*.pdf)', False)
    SQLITE = ('SQLite (.db)', 'Guardar como SQLite', 'Bases de Datos SQLite (*.db)', True)

    def __init__(
        self,
        label: str,
        dialog_title: str,
        file_filter: str,
        needs_table_name: bool,
    ) -> None:
        self.label = label
        self.dialog_title = dialog_title
        self.file_filter = file_filter
        self.needs_table_name = needs_table_name

    @classmethod
    def from_label(cls, label: str) -> 'ExportFormat':
        """Buscar un formato por la etiqueta mostrada en el combo."""
        for export_format in cls:
            if export_format.label == label:
                return export_format
        raise ValueError(f"Formato de exportación desconocido: {label}")


class ExportDialog(QDialog):
    """Diálogo modal para elegir el formato de exportación."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar Datos")
        self.setModal(True)

        layout = QVBoxLayout(self)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([export_format.label for export_format in ExportFormat])
        self.format_combo.setCurrentText(ExportFormat.XLSX.label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        export_btn = QPushButton("Exportar")
        export_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(export_btn)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    @property
    def selected_format(self) -> ExportFormat:
        return ExportFormat.from_label(self.format_combo.currentText())

    @classmethod
    def ask(cls, parent: QWidget | None = None) -> ExportFormat | None:
        """Mostrar el diálogo y devolver el formato elegido (o None)."""
        dialog = cls(parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_format


def prompt_table_name(parent: QWidget) -> str | None:
    """Pedir el nombre de la tabla para exportar a SQLite."""
    name, ok = QInputDialog.getText(
        parent, "Nombre de la tabla", "Ingresa el nombre de la tabla:"
    )
    if not ok or not name:
        return None
    return name
