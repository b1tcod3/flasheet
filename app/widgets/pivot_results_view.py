"""
PivotResultsView - Widget para mostrar tablas pivote automáticas en pestañas.
Cada pestaña contiene una tabla QTableView con un DataFrame pivote.
"""

import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                                QTableView, QLabel, QPushButton, QHeaderView,
                                QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.models.pandas_model import VirtualizedPandasModel


class PivotTabWidget(QWidget):
    """Widget individual para una pestaña de pivote."""

    def __init__(self, df: pd.DataFrame, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df = df
        self.title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel(f"{title}  ({len(df)} filas × {len(df.columns)} columnas)")
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: #1e293b; padding: 4px 0;")
        layout.addWidget(header)

        table = QTableView()
        model = VirtualizedPandasModel(df)
        table.setModel(model)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableView {
                background-color: white;
                alternate-background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                gridline-color: #e2e8f0;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                border: none;
                border-bottom: 2px solid #cbd5e1;
                padding: 6px 8px;
                font-weight: bold;
                color: #334155;
            }
        """)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(28)
        layout.addWidget(table)


class PivotResultsView(QWidget):
    """
    Vista que muestra múltiples tablas pivote en un QTabWidget.
    Cada pestaña es una combinación categórica × numérica.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: dict[str, pd.DataFrame] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("background-color: #f8fafc;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        header_layout = QHBoxLayout()

        title = QLabel("Tablas Pivote Automáticas")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        export_btn = QPushButton("ExportarTodo")
        export_btn.setToolTip("Exportar todas las pestañas a Excel")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        export_btn.clicked.connect(self._export_all)
        header_layout.addWidget(export_btn)

        main_layout.addLayout(header_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                background: #f3f4f6;
                color: #334155;
                border: 1px solid #d1d5db;
                border-bottom: none;
                padding: 6px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #2563eb;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #e5e7eb;
            }
        """)
        main_layout.addWidget(self.tab_widget)

        self._empty_label = QLabel("Haz clic en el botón de Pivote en la barra de herramientas\npara generar automáticamente las tablas pivote.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        main_layout.addWidget(self._empty_label)

    def set_pivot_results(self, results: dict[str, pd.DataFrame]) -> None:
        """Recibir resultados de pivote y crear pestañas."""
        self._results = results
        self.tab_widget.clear()

        if not results:
            self._empty_label.setVisible(True)
            self.tab_widget.setVisible(False)
            return

        self._empty_label.setVisible(False)
        self.tab_widget.setVisible(True)

        for name, df in results.items():
            tab = PivotTabWidget(df, name)
            self.tab_widget.addTab(tab, name)

    def get_results(self) -> dict[str, pd.DataFrame]:
        return self._results

    def _export_all(self) -> None:
        """Exportar todas las pestañas a un solo archivo Excel."""
        if not self._results:
            QMessageBox.information(self, "Sin datos", "No hay tablas pivote para exportar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Exportar Tablas Pivote", "Tablas_Pivote.xlsx",
            "Archivos Excel (*.xlsx)"
        )
        if not filepath:
            return

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for name, df in self._results.items():
                    safe_name = name[:31].replace("/", "-").replace("\\", "-")
                    df.to_excel(writer, sheet_name=safe_name, index=True)
            QMessageBox.information(self, "Exportado",
                f"Se exportaron {len(self._results)} tablas a:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exportando: {e}")
