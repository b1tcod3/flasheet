"""
Diálogo de Opciones de Carga para Flash View Sheet
Permite configurar opciones como saltar filas y renombrar columnas
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QSpinBox, QPushButton,
                                 QGroupBox, QFormLayout, QDialogButtonBox, QTableWidget,
                                 QTableWidgetItem, QCheckBox, QWidget)

class LoadOptionsDialog(QDialog):
    """
    Diálogo para configurar opciones de carga de datos
    """
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Opciones de Carga")
        self.resize(600, 400)
        self.skip_rows: int = 0
        self.column_names: dict[str, str] = {}
        self.enable_column_visibility: bool = False
        self.setup_ui()
        
    def setup_ui(self) -> None:
        """Configurar la interfaz del diálogo"""
        main_layout = QVBoxLayout(self)
        
        # Grupo: Saltar Filas
        skip_group = QGroupBox("Saltar Filas")
        skip_layout = QFormLayout(skip_group)

        self.skip_spin = QSpinBox()
        self.skip_spin.setMinimum(0)
        self.skip_spin.setMaximum(1000)
        self.skip_spin.setValue(0)
        skip_layout.addRow("Número de filas a saltar (la siguiente se usará como encabezado):", self.skip_spin)
        
        main_layout.addWidget(skip_group)
        
        # Grupo: Renombrar Columnas
        rename_group = QGroupBox("Renombrar Columnas (deja vacío para mantener el nombre original)")
        rename_layout = QVBoxLayout(rename_group)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Nombre Original", "Nuevo Nombre"])
        self.table.horizontalHeader().setStretchLastSection(True)
        rename_layout.addWidget(self.table)
        
        # Botón para añadir fila
        add_row_btn = QPushButton("Añadir Columna")
        add_row_btn.clicked.connect(self.add_row)
        rename_layout.addWidget(add_row_btn)
        
        main_layout.addWidget(rename_group)

        # Grupo: Opciones Adicionales
        additional_group = QGroupBox("Opciones Adicionales")
        additional_layout = QVBoxLayout(additional_group)

        self.column_visibility_checkbox = QCheckBox("Habilitar controles de visibilidad de columnas")
        self.column_visibility_checkbox.setToolTip("Permite mostrar/ocultar columnas después de cargar los datos")
        additional_layout.addWidget(self.column_visibility_checkbox)

        main_layout.addWidget(additional_group)

        # Botones de diálogo
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        
    def add_row(self) -> None:
        """Añadir una fila al table para renombrar columna"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        
    def set_columns(self, columns: list[str]) -> None:
        """Establecer las columnas originales"""
        self.table.setRowCount(0)
        for col in columns:
            self.add_row()
            self.table.item(self.table.rowCount()-1, 0).setText(col)
            
    def get_options(self) -> tuple[int, dict[str, str], bool]:
        """Obtener las opciones configuradas"""
        self.skip_rows = self.skip_spin.value()
        self.column_names = {}
        for row in range(self.table.rowCount()):
            original = self.table.item(row, 0).text().strip()
            new = self.table.item(row, 1).text().strip()
            if original and new:
                self.column_names[original] = new
        self.enable_column_visibility = self.column_visibility_checkbox.isChecked()
        return self.skip_rows, self.column_names, self.enable_column_visibility
