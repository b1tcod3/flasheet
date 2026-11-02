"""
Tabla de mapeo columna de DataFrame -> columna de Excel.
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


class ColumnMappingWidget(QWidget):
    """Widget para gestionar mapeo de columnas DataFrame ↔ Excel"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df_columns: list[str] = []
        self.excel_columns: list[str] = []
        self.mapping: dict[str, str] = {}
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.mapping_table = QTableWidget(0, 4)
        self.mapping_table.setHorizontalHeaderLabels([
            "Columna Data", "→", "Columna Excel", "Vista Previa"
        ])

        header = self.mapping_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.mapping_table.setAlternatingRowColors(True)

        layout.addWidget(self.mapping_table)

        button_layout = QHBoxLayout()
        self.auto_map_btn = QPushButton("Auto-mapear")
        self.add_column_btn = QPushButton("+ Añadir")
        self.remove_column_btn = QPushButton("- Eliminar")

        self.auto_map_btn.clicked.connect(self.auto_map_positional)
        self.add_column_btn.clicked.connect(self.add_mapping_row)
        self.remove_column_btn.clicked.connect(self.remove_selected_rows)

        button_layout.addWidget(self.auto_map_btn)
        button_layout.addWidget(self.add_column_btn)
        button_layout.addWidget(self.remove_column_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def set_dataframe_columns(self, columns: list[str]) -> None:
        self.df_columns = columns
        self.refresh_mapping_table()

    def set_excel_columns(self, columns: list[str]) -> None:
        self.excel_columns = columns
        for row in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(row, 2)
            if combo:
                combo.clear()
                combo.addItems(self.excel_columns)

    def refresh_mapping_table(self) -> None:
        self.mapping_table.setRowCount(len(self.df_columns))
        for row, col_name in enumerate(self.df_columns):
            item = QTableWidgetItem(col_name)
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.mapping_table.setItem(row, 0, item)

            arrow_item = QTableWidgetItem("→")
            arrow_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            arrow_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mapping_table.setItem(row, 1, arrow_item)

            combo = QComboBox()
            combo.addItems(self.excel_columns)
            self.mapping_table.setCellWidget(row, 2, combo)

            preview_item = QTableWidgetItem("Sin datos")
            preview_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.mapping_table.setItem(row, 3, preview_item)

    def auto_map_positional(self) -> None:
        for row in range(min(len(self.df_columns), len(self.excel_columns))):
            combo = self.mapping_table.cellWidget(row, 2)
            if combo:
                combo.setCurrentIndex(row)

    def add_mapping_row(self) -> None:
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
        self.mapping_table.setItem(row, 0, QTableWidgetItem(""))

        arrow_item = QTableWidgetItem("→")
        arrow_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        arrow_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mapping_table.setItem(row, 1, arrow_item)

        combo = QComboBox()
        combo.addItems(self.excel_columns)
        self.mapping_table.setCellWidget(row, 2, combo)
        self.mapping_table.setItem(row, 3, QTableWidgetItem(""))

    def remove_selected_rows(self) -> None:
        selected_rows = sorted(
            [item.row() for item in self.mapping_table.selectedIndexes()],
            reverse=True
        )
        for row in selected_rows:
            self.mapping_table.removeRow(row)

    def get_mapping(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for row in range(self.mapping_table.rowCount()):
            df_col_item = self.mapping_table.item(row, 0)
            combo = self.mapping_table.cellWidget(row, 2)
            if df_col_item and combo:
                df_col = df_col_item.text().strip()
                excel_col = combo.currentText().strip()
                if df_col and excel_col:
                    mapping[df_col] = excel_col
        return mapping


# ──────────────────────────────────────────────────────────────────────
# ExcelTemplateDialog
# ──────────────────────────────────────────────────────────────────────
