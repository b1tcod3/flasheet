"""
Previsualización de los archivos que se van a generar.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QGroupBox, QFormLayout, QGridLayout,
                               QComboBox, QLineEdit, QMessageBox,
                               QListWidget, QCheckBox,
                               QWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QFileDialog,
                               QSplitter, QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer, QSettings
import pandas as pd
import openpyxl
from pathlib import Path
from datetime import datetime
from typing import Any


class FilePreviewDialog(QDialog):
    """Diálogo para vista previa de archivos a generar"""

    def __init__(self, files_info: list[dict[str, Any]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.files_info = files_info
        self.setWindowTitle("Vista Previa de Archivos")
        self.resize(800, 400)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtros:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Todos", "Listos", "Advertencias", "Errores"])
        self.status_filter.currentTextChanged.connect(self.filter_files)
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.files_table = QTableWidget(0, 5)
        self.files_table.setHorizontalHeaderLabels([
            "Nombre de Archivo", "Grupo", "Filas", "Tamaño", "Estado"
        ])
        header = self.files_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.files_table.setAlternatingRowColors(True)
        layout.addWidget(self.files_table)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        buttons = QHBoxLayout()
        self.ok_btn = QPushButton("Aceptar")
        self.ok_btn.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

        self.refresh_table()

    def refresh_table(self) -> None:
        filtered_files = self.get_filtered_files()
        self.files_table.setRowCount(len(filtered_files))

        for row, file_info in enumerate(filtered_files):
            self.files_table.setItem(row, 0, QTableWidgetItem(file_info.get('filename', '')))
            self.files_table.setItem(row, 1, QTableWidgetItem(file_info.get('group', '')))
            self.files_table.setItem(row, 2, QTableWidgetItem(str(file_info.get('rows', 0))))
            self.files_table.setItem(row, 3, QTableWidgetItem(file_info.get('size', '')))

            status_item = QTableWidgetItem(file_info.get('status', ''))
            if file_info.get('status') == 'Listo':
                status_item.setBackground(Qt.GlobalColor.green)
            elif file_info.get('status') == 'Advertencia':
                status_item.setBackground(Qt.GlobalColor.yellow)
            elif file_info.get('status') == 'Error':
                status_item.setBackground(Qt.GlobalColor.red)
            self.files_table.setItem(row, 4, status_item)

        self.update_summary(filtered_files)

    def get_filtered_files(self) -> list[dict[str, Any]]:
        filter_text = self.status_filter.currentText()
        if filter_text == "Todos":
            return self.files_info
        return [f for f in self.files_info if f.get('status') == filter_text]

    def update_summary(self, files: list[dict[str, Any]]) -> None:
        total_files = len(files)
        total_rows = sum(f.get('rows', 0) for f in files)
        self.summary_label.setText(
            f"Resumen: {total_files} archivos — {total_rows} filas totales"
        )

    def filter_files(self) -> None:
        self.refresh_table()


# ──────────────────────────────────────────────────────────────────────
# ExportSeparatedDialog — Vista Compacta
# ──────────────────────────────────────────────────────────────────────
