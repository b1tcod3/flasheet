"""
Diálogo de selección y previsualización de una plantilla Excel.
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


class ExcelTemplateDialog(QDialog):
    """Diálogo para seleccionar y validar plantilla Excel"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.template_path: str = ""
        self.selected_sheet: str = ""
        self.available_sheets: list[str] = []
        self.setWindowTitle("Seleccionar Plantilla Excel")
        self.resize(700, 500)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        file_group = QGroupBox("Archivo de Plantilla")
        file_layout = QFormLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_layout.addRow("Ruta:", self.file_path_edit)

        button_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Explorar...")
        self.browse_btn.clicked.connect(self.browse_for_template)
        button_layout.addWidget(self.browse_btn)
        button_layout.addStretch()
        file_layout.addRow("", button_layout)

        layout.addWidget(file_group)

        info_group = QGroupBox("Información del Archivo")
        info_layout = QFormLayout(info_group)

        self.info_label = QLabel("No hay archivo seleccionado")
        self.info_label.setWordWrap(True)
        info_layout.addRow("Estado:", self.info_label)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.currentTextChanged.connect(self.on_sheet_changed)
        info_layout.addRow("Hoja:", self.sheet_combo)

        layout.addWidget(info_group)

        preview_group = QGroupBox("Vista Previa de la Plantilla")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget(0, 0)
        self.preview_table.setMaximumHeight(200)
        self.preview_table.setAlternatingRowColors(True)
        preview_layout.addWidget(self.preview_table)

        layout.addWidget(preview_group)

        buttons = QHBoxLayout()
        self.ok_btn = QPushButton("Aceptar")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.ok_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

    def browse_for_template(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Plantilla Excel", "",
            "Excel Files (*.xlsx *.xlsm);;All Files (*)"
        )
        if file_path:
            self.load_template(file_path)

    def load_template(self, file_path: str) -> None:
        try:
            if not file_path.lower().endswith(('.xlsx', '.xlsm')):
                self.info_label.setText("Error: El archivo debe ser .xlsx o .xlsm")
                return

            workbook = openpyxl.load_workbook(file_path, data_only=False)
            self.available_sheets = workbook.sheetnames
            workbook.close()

            self.template_path = file_path
            self.file_path_edit.setText(file_path)

            file_size = Path(file_path).stat().st_size
            self.info_label.setText(
                f"Archivo válido — Tamaño: {file_size / 1024:.1f}KB — "
                f"Hojas: {len(self.available_sheets)}"
            )

            self.sheet_combo.clear()
            self.sheet_combo.addItems(self.available_sheets)
            self.sheet_combo.setEnabled(True)
            self.selected_sheet = self.available_sheets[0] if self.available_sheets else ""

            self.show_preview()

        except Exception as e:
            self.info_label.setText(f"Error al cargar plantilla: {e}")
            self.template_path = ""
            self.file_path_edit.clear()
            self.sheet_combo.setEnabled(False)
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)

    def show_preview(self) -> None:
        try:
            if not self.template_path:
                return
            workbook = openpyxl.load_workbook(self.template_path, data_only=True)
            sheet = workbook[self.selected_sheet] if self.selected_sheet else workbook.active

            max_rows = min(10, sheet.max_row or 0)
            max_cols = min(10, sheet.max_column or 0)

            self.preview_table.setRowCount(max_rows)
            self.preview_table.setColumnCount(max_cols)

            for row in range(max_rows):
                for col in range(max_cols):
                    cell_value = sheet.cell(row + 1, col + 1).value
                    if cell_value is not None:
                        self.preview_table.setItem(row, col, QTableWidgetItem(str(cell_value)))

            workbook.close()
        except Exception:
            pass

    def on_sheet_changed(self, sheet_name: str) -> None:
        self.selected_sheet = sheet_name
        if self.template_path:
            self.show_preview()

    def get_template_info(self) -> tuple[str, str, list[str]]:
        return self.template_path, self.selected_sheet, self.available_sheets


# ──────────────────────────────────────────────────────────────────────
# FilePreviewDialog
# ──────────────────────────────────────────────────────────────────────
