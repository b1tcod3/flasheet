"""
JoinedDataView: Vista especializada para mostrar resultados de cruces de datos
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QGroupBox, QTextEdit, QPushButton, QMessageBox,
                                QDialog, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal

from app.widgets.data_view import DataView
from core.join.models import JoinResult, JoinMetadata
from core.join.join_history import JoinHistoryEntry


class JoinedDataView(DataView):
    """
    Vista especializada para mostrar resultados de operaciones de cruce.
    Hereda de DataView y añade información específica del join.

    Es una vista pura: no contiene lógica de negocio.
    Las acciones del usuario se emiten como señales para que el
    coordinador las maneje.
    """

    new_join_requested = Signal()
    export_requested = Signal(str)
    history_requested = Signal()
    history_entry_selected = Signal(str)
    history_export_requested = Signal(str)
    history_clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.join_metadata: JoinMetadata | None = None
        self.left_dataset_name: str = ""
        self.right_dataset_name: str = ""

        self.metadata_text: QTextEdit
        self.export_btn: QPushButton
        self.new_join_btn: QPushButton
        self.history_btn: QPushButton
        self.help_btn: QPushButton

        self.add_join_metadata_section()

    def add_join_metadata_section(self) -> None:
        main_layout = self.layout()
        metadata_group = self.create_join_metadata_section()
        main_layout.insertWidget(0, metadata_group)
        main_layout.update()
        self.update()

    def create_join_metadata_section(self) -> QGroupBox:
        metadata_group = QGroupBox("\U0001f4ca Metadatos del Cruce")
        metadata_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #27ae60;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                padding-bottom: 8px;
                background-color: #f8fff9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #27ae60;
            }
        """)

        layout = QVBoxLayout(metadata_group)

        self.metadata_text = QTextEdit()
        self.metadata_text.setMaximumHeight(100)
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
                font-family: monospace;
                font-size: 10px;
                color: #1e293b;
            }
        """)
        layout.addWidget(self.metadata_text)

        buttons_layout = QHBoxLayout()

        self.export_btn = QPushButton("\U0001f4be Exportar Resultados")
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_btn.setEnabled(False)
        buttons_layout.addWidget(self.export_btn)

        self.new_join_btn = QPushButton("\U0001f504 Nuevo Cruce")
        self.new_join_btn.clicked.connect(self.new_join_requested.emit)
        buttons_layout.addWidget(self.new_join_btn)

        self.history_btn = QPushButton("\U0001f4cb Historial")
        self.history_btn.clicked.connect(self.history_requested.emit)
        buttons_layout.addWidget(self.history_btn)

        self.help_btn = QPushButton("\u2753 Ayuda")
        self.help_btn.clicked.connect(self.show_help)
        buttons_layout.addWidget(self.help_btn)

        layout.addLayout(buttons_layout)

        return metadata_group

    def set_join_result(self, result: JoinResult, left_name: str = "", right_name: str = "") -> None:
        self.join_metadata = result.metadata
        self.left_dataset_name = left_name or "Dataset Izquierdo"
        self.right_dataset_name = right_name or "Dataset Derecho"

        super().set_data(result.data)
        self.update_join_metadata_display()
        self.export_btn.setEnabled(True)

    def update_join_metadata_display(self) -> None:
        if self.join_metadata is None:
            self.metadata_text.setPlainText("No hay información de join disponible")
            return

        metadata = self.join_metadata
        info_lines = []

        join_type_names = {
            'inner': 'Inner Join',
            'left': 'Left Join',
            'right': 'Right Join',
            'cross': 'Cross Join'
        }

        info_lines.append(f"Tipo: {join_type_names.get(metadata.join_type.value, metadata.join_type.value)}")
        info_lines.append(f"Datasets: {self.left_dataset_name} + {self.right_dataset_name}")
        info_lines.append(f"Columnas join: {', '.join(metadata.join_keys)}")
        info_lines.append(f"Resultado: {metadata.result_rows:,} filas × {len(self.original_df.columns) if self.original_df is not None else '?'} columnas")
        info_lines.append(f"Tiempo procesamiento: {metadata.processing_time_seconds:.2f} segundos")
        info_lines.append(f"Memoria usada: {metadata.memory_usage_mb:.1f} MB")
        info_lines.append("")

        info_lines.append("Estadísticas:")
        info_lines.append(f"• Coincidencias: {metadata.matched_rows:,}")
        info_lines.append(f"• Solo izquierdo: {metadata.left_only_rows:,}")
        info_lines.append(f"• Solo derecho: {metadata.right_only_rows:,}")
        info_lines.append(f"• Total original izquierdo: {metadata.left_rows:,}")
        info_lines.append(f"• Total original derecho: {metadata.right_rows:,}")

        if metadata.left_rows > 0:
            left_match_pct = (metadata.matched_rows / metadata.left_rows) * 100
            info_lines.append(f"• Cobertura izquierdo: {left_match_pct:.1f}%")

        if metadata.right_rows > 0:
            right_match_pct = (metadata.matched_rows / metadata.right_rows) * 100
            info_lines.append(f"• Cobertura derecho: {right_match_pct:.1f}%")

        self.metadata_text.setPlainText('\n'.join(info_lines))

    def _on_export_clicked(self) -> None:
        if self.original_df is None:
            QMessageBox.warning(self, "Error", "No hay datos para exportar")
            return
        self.export_requested.emit(self.original_df)

    def show_history(self) -> None:
        self.history_requested.emit()

    def populate_history(self, entries: list[JoinHistoryEntry]) -> None:
        if not entries:
            QMessageBox.information(self, "Historial", "No hay operaciones de cruce registradas.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Historial de Operaciones de Cruce")
        dialog.setModal(True)
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        layout.addWidget(list_widget)

        details_label = QLabel("Detalles de la operación seleccionada:")
        layout.addWidget(details_label)

        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(150)
        layout.addWidget(details_text)

        buttons_layout = QHBoxLayout()

        export_btn = QPushButton("Exportar Historial")
        export_btn.clicked.connect(lambda: self.history_export_requested.emit(
            "historial_cruce.json"))
        buttons_layout.addWidget(export_btn)

        clear_btn = QPushButton("Limpiar Historial")
        clear_btn.clicked.connect(lambda: self._on_clear_history(dialog))
        buttons_layout.addWidget(clear_btn)

        buttons_layout.addStretch()

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        for entry in entries:
            item_text = f"{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {entry.join_type.value} - {entry.left_dataset_name} + {entry.right_dataset_name}"
            if not entry.success:
                item_text += " (ERROR)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            list_widget.addItem(item)

        def on_item_selected() -> None:
            current_item = list_widget.currentItem()
            if current_item:
                entry_id = current_item.data(Qt.ItemDataRole.UserRole)
                self._show_entry_details(entries, entry_id, details_text)

        list_widget.itemSelectionChanged.connect(on_item_selected)

        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)

        dialog.exec()

    @staticmethod
    def _show_entry_details(entries: list[JoinHistoryEntry], entry_id: str,
                            details_text: QTextEdit) -> None:
        entry = next((e for e in entries if e.entry_id == entry_id), None)
        if entry is None:
            return

        details = f"""
Tipo: {entry.config.join_type.value if entry.config else 'N/A'}
Datasets: {entry.left_dataset_name} + {entry.right_dataset_name}
Columnas join: {', '.join(entry.config.left_keys + entry.config.right_keys) if entry.config else 'N/A'}
Resultado: {entry.result_metadata.get('result_rows', 'N/A')} filas
Tiempo: {entry.result_metadata.get('processing_time', 'N/A'):.2f}s
Memoria: {entry.result_metadata.get('memory_usage', 'N/A'):.1f} MB
Éxito: {'Sí' if entry.success else 'No'}
"""
        if entry.error_message:
            details += f"\nError: {entry.error_message}"

        details_text.setPlainText(details.strip())

    def _on_clear_history(self, dialog: QDialog) -> None:
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de que desea limpiar todo el historial de operaciones de cruce?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_clear_requested.emit()
            QMessageBox.information(self, "Éxito", "Historial limpiado.")
            dialog.accept()

    def show_help(self) -> None:
        help_text = """
        AYUDA: Vista de Datos Cruzados

        Esta vista muestra los resultados de una operación de cruce (join) entre dos datasets.

        TIPOS DE JOIN:
        • Inner Join: Solo filas con coincidencias en ambas tablas
        • Left Join: Todas las filas del dataset izquierdo + coincidencias del derecho
        • Right Join: Todas las filas del dataset derecho + coincidencias del izquierdo
        • Cross Join: Producto cartesiano de ambas tablas

        METADATOS MOSTRADOS:
        • Información del tipo de join realizado
        • Estadísticas de coincidencias y pérdidas
        • Tiempo y memoria utilizados
        • Cobertura de datos

        FUNCIONALIDADES:
        • Filtrado y búsqueda en resultados
        • Paginación para datasets grandes
        • Exportación de resultados
        • Historial de operaciones

        Para más información, consulte la documentación completa.
        """

        QMessageBox.information(self, "Ayuda - Datos Cruzados", help_text)

    def get_join_info(self) -> dict:
        if self.join_metadata is None:
            return {}

        return {
            'join_type': self.join_metadata.join_type.value,
            'left_dataset': self.left_dataset_name,
            'right_dataset': self.right_dataset_name,
            'join_keys': self.join_metadata.join_keys,
            'result_rows': self.join_metadata.result_rows,
            'matched_rows': self.join_metadata.matched_rows,
            'processing_time': self.join_metadata.processing_time_seconds,
            'memory_usage': self.join_metadata.memory_usage_mb,
            'timestamp': self.join_metadata.timestamp.isoformat()
        }
