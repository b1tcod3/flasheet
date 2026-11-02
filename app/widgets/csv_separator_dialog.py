"""
Diálogo de Selección de Separador CSV para Flash View Sheet
Permite al usuario elegir el delimitador al importar archivos CSV/TSV.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
                                QDialogButtonBox, QWidget)


class CSVSeparatorDialog(QDialog):
    """Diálogo modal para seleccionar el separador de un archivo CSV/TSV."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Opciones de importación")
        self.setModal(True)
        self.resize(300, 120)

        self.setStyleSheet("""
            QDialog { background-color: white; }
            QLabel { color: #374151; font-size: 13px; }
            QComboBox {
                border: 1px solid #d1d5db; border-radius: 6px;
                padding: 6px 10px; background-color: #f9fafb; color: #374151;
                min-width: 150px;
            }
            QPushButton {
                padding: 6px 15px; border-radius: 6px; font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Selecciona el delimitador usado en tu archivo CSV:")
        layout.addWidget(label)

        self.combo_separator = QComboBox()
        self.combo_separator.addItem("Punto y coma (;)", ";")
        self.combo_separator.addItem("Coma (,)", ",")
        self.combo_separator.addItem("Tabulador (Tab)", "\t")
        self.combo_separator.addItem("Barra (|)", "|")
        layout.addWidget(self.combo_separator)

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
            "background-color: #f3f4f6; color: #4b5563; border: 1px solid #d1d5db;"
        )

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_separator(self) -> str:
        """Devuelve el caracter separador seleccionado por el usuario."""
        return self.combo_separator.currentData()
