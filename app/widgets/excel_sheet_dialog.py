"""
Diálogo de Selección de Hoja Excel para Flash View Sheet
Permite al usuario elegir qué pestaña/hoja cargar de un archivo Excel.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
                                QDialogButtonBox, QWidget)
import pandas as pd


class ExcelSheetDialog(QDialog):
    """Diálogo modal para seleccionar la hoja de un archivo Excel."""

    def __init__(self, filepath: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Seleccionar hoja")
        self.setModal(True)
        self.resize(350, 120)

        self.setStyleSheet("""
            QDialog { background-color: #343b48; }
            QLabel { color: #374151; font-size: 13px; }
            QComboBox {
                border: 1px solid #2c313a; border-radius: 6px;
                padding: 6px 10px; background-color: #21252b; color: #374151;
                min-width: 150px;
            }
            QPushButton {
                padding: 6px 15px; border-radius: 6px; font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Selecciona la hoja que deseas abrir:")
        layout.addWidget(label)

        self.combo_sheet = QComboBox()
        self._sheet_names: list[str] = []
        self._load_sheet_names(filepath)
        layout.addWidget(self.combo_sheet)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Aceptar")
        ok_btn.setStyleSheet(
            "background-color: #4f46e5; color: white; border: none;"
        )

        cancel_btn = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Cancelar")
        cancel_btn.setStyleSheet(
            "background-color: #21252b; color: #717e95; border: 1px solid #2c313a;"
        )

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _load_sheet_names(self, filepath: str) -> None:
        """Leer nombres de hojas del archivo Excel."""
        try:
            xf = pd.ExcelFile(filepath)
            self._sheet_names = xf.sheet_names
            xf.close()
        except Exception:
            self._sheet_names = ["Sheet1"]

        for name in self._sheet_names:
            self.combo_sheet.addItem(name, name)

    def get_sheet_name(self) -> str:
        """Devuelve el nombre de la hoja seleccionada."""
        return self.combo_sheet.currentData()
