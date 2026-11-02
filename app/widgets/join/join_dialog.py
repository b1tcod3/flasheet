"""
JoinDialog: Diálogo para configurar operaciones de cruce de datos
"""

import logging
import traceback

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                  QGroupBox, QComboBox, QPushButton, QFormLayout,
                                  QMessageBox, QWidget, QRadioButton, QButtonGroup,
                                  QCheckBox, QLineEdit, QFileDialog, QTableWidget,
                                  QTableWidgetItem, QProgressDialog, QTabWidget, QListWidget,
                                  QListWidgetItem, QSplitter, QAbstractButton, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.services.task_thread import stop_thread
import pandas as pd
from pathlib import Path

from core.data_handler import cargar_datos
from core.join.models import JoinConfig, JoinType
from core.join.exceptions import JoinValidationError
from app.services.join_service import JoinService, JoinWorkerThread, compute_result_columns
from typing import cast

logger = logging.getLogger(__name__)

class JoinDialog(QDialog):
    """
    Diálogo modal para configurar operaciones de cruce de datos
    """

    # Señales
    join_completed = Signal(object, str)  # JoinResult, right_file_path
    join_cancelled = Signal()

    def __init__(self, left_df: pd.DataFrame, parent: QWidget | None = None,
                 join_service: JoinService | None = None) -> None:
        super().__init__(parent)
        self.left_df = left_df
        self.right_df: pd.DataFrame | None = None
        self.right_file_path: Path | None = None
        self.join_service = join_service or JoinService()
        self._worker: JoinWorkerThread | None = None
        self._progress_dialog: QProgressDialog | None = None

        self.right_info_label: QLabel
        self.join_type_group: QButtonGroup
        self.left_key_combo: QComboBox
        self.right_key_combo: QComboBox
        self.left_suffix_edit: QLineEdit
        self.right_suffix_edit: QLineEdit
        self.validate_check: QCheckBox
        self.indicator_check: QCheckBox
        self.sort_check: QCheckBox
        self.select_columns_check: QCheckBox
        self.available_columns_list: QListWidget
        self.add_column_btn: QPushButton
        self.remove_column_btn: QPushButton
        self.select_all_btn: QPushButton
        self.clear_selection_btn: QPushButton
        self.selected_columns_list: QListWidget
        self.preview_stats_label: QLabel
        self.preview_table: QTableWidget
        self.update_preview_btn: QPushButton
        self.validate_btn: QPushButton
        self.execute_btn: QPushButton
        self.cancel_btn: QPushButton

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        """Configurar la interfaz del diálogo"""
        self.setWindowTitle("Configurar Cruce de Datos")
        self.resize(900, 700)
        self.setModal(True)

        main_layout = QVBoxLayout(self)

        # Título
        title_label = QLabel("Configurar Cruce de Datos")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                background-color: #27ae60;
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        main_layout.addWidget(title_label)

        # Crear widget de pestañas
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Pestaña de configuración
        self.create_configuration_tab()

        # Pestaña de vista previa
        self.create_preview_tab()

        # Botones de acción (siempre visibles, fuera de las pestañas)
        self.create_button_panel(main_layout)

    def create_configuration_tab(self) -> None:
        """Crear pestaña de configuración"""
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        # Dataset izquierdo (pre-cargado)
        self.create_left_dataset_group(config_layout)

        # Dataset derecho
        self.create_right_dataset_group(config_layout)

        # Configuración del join
        self.create_join_config_group(config_layout)

        # Opciones avanzadas
        self.create_advanced_options_group(config_layout)

        self.tab_widget.addTab(config_widget, "⚙️ Configuración")

    def create_preview_tab(self) -> None:
        """Crear pestaña de vista previa"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Selección de columnas
        self.create_column_selection_group(preview_layout)

        # Preview
        self.create_preview_group(preview_layout)

        self.tab_widget.addTab(preview_widget, "👁️ Vista Previa")

    def create_left_dataset_group(self, layout: QVBoxLayout) -> None:
        """Crear grupo para dataset izquierdo"""
        group = QGroupBox("Dataset Izquierdo")
        group_layout = QVBoxLayout(group)

        info = f"📄 Datos principales\n{self.left_df.shape[0]} filas × {self.left_df.shape[1]} columnas"
        info_label = QLabel(info)
        info_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        group_layout.addWidget(info_label)

        layout.addWidget(group)

    def create_right_dataset_group(self, layout: QVBoxLayout) -> None:
        """Crear grupo para dataset derecho"""
        group = QGroupBox("Dataset Derecho")
        group_layout = QVBoxLayout(group)

        # Botón para cargar
        load_btn = QPushButton("📁 Cargar Dataset Derecho")
        load_btn.clicked.connect(self.load_right_dataset)
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        group_layout.addWidget(load_btn)

        # Información del dataset derecho
        self.right_info_label = QLabel("No se ha cargado dataset derecho")
        self.right_info_label.setStyleSheet("color: #7f8c8d;")
        group_layout.addWidget(self.right_info_label)

        layout.addWidget(group)

    def create_join_config_group(self, layout: QVBoxLayout) -> None:
        """Crear grupo de configuración del join"""
        group = QGroupBox("Configuración del Join")
        group_layout = QVBoxLayout(group)

        # Tipo de join
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo de Join:"))

        self.join_type_group = QButtonGroup(self)
        join_types = [
            ("Inner Join", JoinType.INNER),
            ("Left Join", JoinType.LEFT),
            ("Right Join", JoinType.RIGHT),
            ("Outer Join", JoinType.OUTER),
            ("Cross Join", JoinType.CROSS)
        ]

        for name, join_type in join_types:
            radio = QRadioButton(name)
            radio.setProperty("join_type", join_type)
            if join_type == JoinType.LEFT:  # Default
                radio.setChecked(True)
            self.join_type_group.addButton(radio)
            type_layout.addWidget(radio)

        type_layout.addStretch()
        group_layout.addLayout(type_layout)

        # Columnas para join
        columns_group = QGroupBox("Columnas para Join")
        columns_layout = QFormLayout(columns_group)

        self.left_key_combo = QComboBox()
        self.left_key_combo.setEnabled(False)
        columns_layout.addRow("Izquierdo:", self.left_key_combo)

        self.right_key_combo = QComboBox()
        self.right_key_combo.setEnabled(False)
        columns_layout.addRow("Derecho:", self.right_key_combo)

        # Botón añadir columna
        add_btn = QPushButton("+ Añadir columna")
        add_btn.clicked.connect(self.add_join_column)
        columns_layout.addRow("", add_btn)

        group_layout.addWidget(columns_group)

        layout.addWidget(group)

    def create_advanced_options_group(self, layout: QVBoxLayout) -> None:
        """Crear grupo de opciones avanzadas"""
        group = QGroupBox("Opciones Avanzadas")
        group_layout = QFormLayout(group)

        # Sufijos
        self.left_suffix_edit = QLineEdit("_left")
        self.right_suffix_edit = QLineEdit("_right")
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("Izquierdo:"))
        suffix_layout.addWidget(self.left_suffix_edit)
        suffix_layout.addWidget(QLabel("Derecho:"))
        suffix_layout.addWidget(self.right_suffix_edit)
        group_layout.addRow("Sufijos:", suffix_layout)

        # Checkboxes
        self.validate_check = QCheckBox("Validar integridad referencial")
        self.validate_check.setChecked(True)
        group_layout.addRow("", self.validate_check)

        self.indicator_check = QCheckBox("Añadir columna indicador (_merge)")
        group_layout.addRow("", self.indicator_check)

        self.sort_check = QCheckBox("Ordenar resultados")
        self.sort_check.setChecked(True)
        group_layout.addRow("", self.sort_check)

        layout.addWidget(group)

    def create_column_selection_group(self, layout: QVBoxLayout) -> None:
        """Crear grupo de selección de columnas"""
        group = QGroupBox("Selección de Columnas (Opcional)")
        group_layout = QVBoxLayout(group)

        # Checkbox para habilitar selección de columnas
        self.select_columns_check = QCheckBox("Seleccionar columnas específicas para el resultado")
        self.select_columns_check.setChecked(False)
        self.select_columns_check.checkStateChanged.connect(self.on_column_selection_changed)
        group_layout.addWidget(self.select_columns_check)

        # Splitter para listas de columnas disponibles y seleccionadas
        splitter = QSplitter()

        # Lista de columnas disponibles
        available_group = QGroupBox("Columnas Disponibles")
        available_layout = QVBoxLayout(available_group)
        self.available_columns_list = QListWidget()
        self.available_columns_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        available_layout.addWidget(self.available_columns_list)
        splitter.addWidget(available_group)

        # Botones de control
        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()

        self.add_column_btn = QPushButton("➡️ Añadir")
        self.add_column_btn.clicked.connect(self.add_selected_columns)
        self.add_column_btn.setEnabled(False)
        buttons_layout.addWidget(self.add_column_btn)

        self.remove_column_btn = QPushButton("⬅️ Quitar")
        self.remove_column_btn.clicked.connect(self.remove_selected_columns)
        self.remove_column_btn.setEnabled(False)
        buttons_layout.addWidget(self.remove_column_btn)

        self.select_all_btn = QPushButton("Seleccionar Todas")
        self.select_all_btn.clicked.connect(self.select_all_columns)
        self.select_all_btn.setEnabled(False)
        buttons_layout.addWidget(self.select_all_btn)

        self.clear_selection_btn = QPushButton("Limpiar Selección")
        self.clear_selection_btn.clicked.connect(self.clear_column_selection)
        self.clear_selection_btn.setEnabled(False)
        buttons_layout.addWidget(self.clear_selection_btn)

        buttons_layout.addStretch()
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        splitter.addWidget(buttons_widget)

        # Lista de columnas seleccionadas
        selected_group = QGroupBox("Columnas Seleccionadas")
        selected_layout = QVBoxLayout(selected_group)
        self.selected_columns_list = QListWidget()
        self.selected_columns_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        selected_layout.addWidget(self.selected_columns_list)
        splitter.addWidget(selected_group)

        # Configurar splitter
        splitter.setSizes([200, 100, 200])

        group_layout.addWidget(splitter)

        # Inicialmente deshabilitado
        self.available_columns_list.setEnabled(False)
        self.selected_columns_list.setEnabled(False)

        layout.addWidget(group)

    def create_preview_group(self, layout: QVBoxLayout) -> None:
        """Crear grupo de preview"""
        group = QGroupBox("Preview de Resultados")
        group_layout = QVBoxLayout(group)

        # Estadísticas
        self.preview_stats_label = QLabel("Cargue un dataset derecho para ver preview")
        self.preview_stats_label.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        group_layout.addWidget(self.preview_stats_label)

        # Tabla preview - sin límite de altura para ocupar espacio disponible
        self.preview_table = QTableWidget()
        group_layout.addWidget(self.preview_table)

        # Botón actualizar preview
        update_btn = QPushButton("🔄 Actualizar Preview")
        update_btn.clicked.connect(self.update_preview)
        update_btn.setEnabled(False)
        self.update_preview_btn = update_btn
        group_layout.addWidget(update_btn)

        layout.addWidget(group)

    def create_button_panel(self, layout: QVBoxLayout) -> None:
        """Crear panel de botones"""
        button_layout = QHBoxLayout()

        self.validate_btn = QPushButton("⚠️ Validar")
        self.validate_btn.clicked.connect(self.validate_config)
        self.validate_btn.setEnabled(False)
        button_layout.addWidget(self.validate_btn)

        button_layout.addStretch()

        self.execute_btn = QPushButton("🚀 Ejecutar Join")
        self.execute_btn.clicked.connect(self.execute_join)
        self.execute_btn.setEnabled(False)
        button_layout.addWidget(self.execute_btn)

        self.cancel_btn = QPushButton("❌ Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def setup_connections(self) -> None:
        """Configurar conexiones de señales"""
        # Actualizar UI cuando cambie el tipo de join
        self.join_type_group.buttonClicked.connect(self.on_join_type_changed)

        # Actualizar preview cuando cambien configuraciones
        self.left_key_combo.currentTextChanged.connect(self.update_preview)
        self.right_key_combo.currentTextChanged.connect(self.update_preview)

        # Actualizar columnas disponibles cuando se cambie a la pestaña de preview
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def load_right_dataset(self) -> None:
        """Cargar dataset derecho"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Dataset Derecho",
            "",
            "Archivos de datos (*.csv *.xlsx *.xls *.json *.parquet *.feather *.hdf5 *.sqlite3);;Todos los archivos (*)"
        )

        if file_path:
            try:
                self.right_df = cargar_datos(file_path)
                self.right_file_path = Path(file_path)
                self.right_info_label.setText(
                    f"📄 {self.right_file_path.name}\n{self.right_df.shape[0]} filas × {self.right_df.shape[1]} columnas"
                )
                self.right_info_label.setStyleSheet("color: #2c3e50; font-weight: bold;")

                # Habilitar configuración
                self.enable_join_config(True)
                self.update_column_combos()

                # Actualizar columnas disponibles si la selección está habilitada
                if self.select_columns_check.isChecked():
                    self.update_available_columns()

            except Exception as e:
                logger.error("Error cargando dataset derecho: %s\n%s", e, traceback.format_exc())
                QMessageBox.critical(self, "Error", f"Error cargando archivo: {str(e)}")

    def enable_join_config(self, enabled: bool) -> None:
        """Habilitar/deshabilitar configuración del join"""
        self.left_key_combo.setEnabled(enabled)
        self.right_key_combo.setEnabled(enabled)
        self.validate_btn.setEnabled(enabled)
        self.execute_btn.setEnabled(enabled)
        self.update_preview_btn.setEnabled(enabled)

    def update_column_combos(self) -> None:
        """Actualizar combos de columnas y sugerir matches automáticos"""
        if self.right_df is not None:
            # Columnas del izquierdo
            left_columns = self.left_df.columns.tolist()
            self.left_key_combo.clear()
            self.left_key_combo.addItems(left_columns)

            # Columnas del derecho
            right_columns = self.right_df.columns.tolist()
            self.right_key_combo.clear()
            self.right_key_combo.addItems(right_columns)

            # Buscar columnas con nombres similares para sugerir automáticamente
            self._suggest_matching_columns(left_columns, right_columns)

    def _suggest_matching_columns(self, left_columns: list[str], right_columns: list[str]) -> None:
        """Sugerir automáticamente columnas que podrían hacer match"""
        # Buscar columnas con el mismo nombre (case insensitive)
        suggested_left, suggested_right = self._find_exact_match(left_columns, right_columns)

        # Si no hay match exacto, buscar columnas con "id" o "key"
        if not suggested_left or not suggested_right:
            suggested_left, suggested_right = self._find_key_match(left_columns, right_columns)

        # Seleccionar las columnas sugeridas
        if suggested_left and suggested_right:
            self.left_key_combo.setCurrentText(suggested_left)
            self.right_key_combo.setCurrentText(suggested_right)

    @staticmethod
    def _find_exact_match(left_columns: list[str], right_columns: list[str]) -> tuple[str | None, str | None]:
        for left_col in left_columns:
            for right_col in right_columns:
                if left_col.lower() == right_col.lower():
                    return left_col, right_col
        return None, None

    @staticmethod
    def _find_key_match(left_columns: list[str], right_columns: list[str]) -> tuple[str | None, str | None]:
        id_columns_left = [col for col in left_columns if 'id' in col.lower() or 'key' in col.lower()]
        id_columns_right = [col for col in right_columns if 'id' in col.lower() or 'key' in col.lower()]

        if id_columns_left and id_columns_right:
            return id_columns_left[0], id_columns_right[0]
        return None, None

    def on_join_type_changed(self, button: QAbstractButton) -> None:
        """Manejar cambio de tipo de join"""
        join_type = button.property("join_type")

        # Para cross join, deshabilitar selección de columnas
        if join_type == JoinType.CROSS:
            self.left_key_combo.setEnabled(False)
            self.right_key_combo.setEnabled(False)
        else:
            self.left_key_combo.setEnabled(True)
            self.right_key_combo.setEnabled(True)

        self.update_preview()

    def on_column_selection_changed(self, state: Qt.CheckState) -> None:
        """Manejar cambio en selección de columnas"""
        enabled = state == Qt.CheckState.Checked

        self.available_columns_list.setEnabled(enabled)
        self.selected_columns_list.setEnabled(enabled)
        self.add_column_btn.setEnabled(enabled)
        self.remove_column_btn.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.clear_selection_btn.setEnabled(enabled)

        if enabled:
            self.update_available_columns()
        else:
            self.available_columns_list.clear()
            self.selected_columns_list.clear()

        self.update_preview()

    def on_tab_changed(self, index: int) -> None:
        """Manejar cambio de pestaña"""
        # Si se cambia a la pestaña de preview (índice 1) y hay dataset derecho cargado
        if index == 1 and self.right_df is not None and self.select_columns_check.isChecked():
            self.update_available_columns()

    def update_available_columns(self) -> None:
        """Actualizar lista de columnas disponibles usando cálculo puro.

        Simula los nombres de columna del resultado sin ejecutar el merge.
        """
        if self.right_df is None:
            return

        config = self.get_config()
        if not config:
            return

        try:
            if config.join_type == JoinType.CROSS:
                available_columns = (
                    list(self.left_df.columns)
                    + list(self.right_df.columns)
                )
            else:
                available_columns = compute_result_columns(
                    self.left_df.columns.tolist(),
                    self.right_df.columns.tolist(),
                    config.left_keys,
                    config.right_keys,
                    config.suffixes,
                )
        except Exception as e:
            logger.warning("Error calculando columnas resultado: %s", e)
            available_columns = (
                list(self.left_df.columns) + list(self.right_df.columns)
            )

        self.available_columns_list.clear()
        for col in sorted(available_columns):
            item = QListWidgetItem(col)
            self.available_columns_list.addItem(item)

    def add_selected_columns(self) -> None:
        """Añadir columnas seleccionadas a la lista de seleccionadas"""
        selected_items = self.available_columns_list.selectedItems()
        for item in selected_items:
            # Verificar si ya está en la lista seleccionada
            existing_items = [self.selected_columns_list.item(i).text()
                            for i in range(self.selected_columns_list.count())]
            if item.text() not in existing_items:
                new_item = QListWidgetItem(item.text())
                self.selected_columns_list.addItem(new_item)

        self.update_preview()

    def remove_selected_columns(self) -> None:
        """Quitar columnas seleccionadas de la lista de seleccionadas"""
        selected_items = self.selected_columns_list.selectedItems()
        for item in selected_items:
            row = self.selected_columns_list.row(item)
            self.selected_columns_list.takeItem(row)

        self.update_preview()

    def select_all_columns(self) -> None:
        """Seleccionar todas las columnas disponibles"""
        self.selected_columns_list.clear()
        for i in range(self.available_columns_list.count()):
            item = self.available_columns_list.item(i)
            new_item = QListWidgetItem(item.text())
            self.selected_columns_list.addItem(new_item)

        self.update_preview()

    def clear_column_selection(self) -> None:
        """Limpiar selección de columnas"""
        self.selected_columns_list.clear()
        self.update_preview()

    def add_join_column(self) -> None:
        """Añadir columna adicional para join múltiple"""
        # TODO: Implementar joins múltiples
        QMessageBox.information(self, "Información", "Joins múltiples no implementados aún")

    def update_preview(self) -> None:
        """Actualizar preview de resultados"""
        if self.right_df is None:
            return

        try:
            config = self.get_config()
            if not config:
                return

            # Crear manager temporal para preview
            preview_df = self.join_service.get_preview(self.left_df, self.right_df, config, max_rows=10)

            # Actualizar estadísticas
            estimated_rows = len(preview_df)
            estimated_cols = len(preview_df.columns)
            self.preview_stats_label.setText(
                f"Estimación: {estimated_rows} filas × {estimated_cols} columnas"
            )

            # Actualizar tabla
            self.update_preview_table(preview_df)

        except Exception as e:
            logger.warning("Error en preview: %s\n%s", e, traceback.format_exc())
            self.preview_stats_label.setText(f"Error en preview: {str(e)}")
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)

    def update_preview_table(self, df: pd.DataFrame) -> None:
        """Actualizar tabla de preview"""
        if df.empty:
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return

        self.preview_table.setRowCount(min(len(df), 10))
        self.preview_table.setColumnCount(len(df.columns))
        self.preview_table.setHorizontalHeaderLabels(df.columns.tolist())

        for row in range(min(len(df), 10)):
            for col in range(len(df.columns)):
                value = str(df.iloc[row, col])
                item = QTableWidgetItem(value)
                self.preview_table.setItem(row, col, item)

        self.preview_table.resizeColumnsToContents()

    def get_config(self) -> JoinConfig | None:
        """Obtener configuración actual"""
        if self.right_df is None:
            return None

        # Tipo de join
        selected_button = self.join_type_group.checkedButton()
        if not selected_button:
            return None
        join_type = selected_button.property("join_type")

        # Columnas de join
        left_keys = [self.left_key_combo.currentText()] if self.left_key_combo.currentText() else []
        right_keys = [self.right_key_combo.currentText()] if self.right_key_combo.currentText() else []

        # Para cross join, no se necesitan keys
        if join_type == JoinType.CROSS:
            left_keys = []
            right_keys = []

        # Columnas a incluir
        include_columns = []
        if self.select_columns_check.isChecked():
            include_columns = [self.selected_columns_list.item(i).text()
                             for i in range(self.selected_columns_list.count())]

        return JoinConfig(
            left_keys=left_keys,
            right_keys=right_keys,
            join_type=join_type,
            suffixes=(self.left_suffix_edit.text(), self.right_suffix_edit.text()),
            validate_integrity=self.validate_check.isChecked(),
            sort_results=self.sort_check.isChecked(),
            indicator=self.indicator_check.isChecked(),
            include_columns=include_columns
        )

    def validate_config(self) -> None:
        """Validar configuración"""
        if self.right_df is None:
            QMessageBox.warning(self, "Error", "Debe cargar un dataset derecho primero")
            return

        config = self.get_config()
        if not config:
            QMessageBox.warning(self, "Error", "Configuración incompleta")
            return

        try:
            validation = self.join_service.validate_config(self.left_df, self.right_df, config)

            if validation.is_valid:
                QMessageBox.information(self, "Validación Exitosa",
                                      "La configuración es válida")
            else:
                errors_text = "\n".join(validation.errors)
                warnings_text = "\n".join(validation.warnings) if validation.warnings else ""

                message = f"Errores:\n{errors_text}"
                if warnings_text:
                    message += f"\n\nAdvertencias:\n{warnings_text}"

                QMessageBox.warning(self, "Errores de Validación", message)

        except JoinValidationError as e:
            logger.warning("Error de validación: %s", e)
            QMessageBox.critical(self, "Error de Validación", str(e))
        except Exception as e:
            logger.error("Error inesperado en validación: %s\n%s", e, traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Error inesperado: {str(e)}")

    def execute_join(self) -> None:
        """Ejecutar el join en un hilo separado para no bloquear la UI."""
        if self.right_df is None:
            QMessageBox.warning(self, "Error", "Debe cargar un dataset derecho primero")
            return

        config = self.get_config()
        if not config:
            QMessageBox.warning(self, "Error", "Configuración incompleta")
            return

        # Advertir sobre cross joins grandes
        if config.join_type == JoinType.CROSS:
            estimated_rows = len(self.left_df) * len(self.right_df)
            if estimated_rows > 1_000_000:
                reply = QMessageBox.question(
                    self, "Cross Join grande",
                    f"El cross join generará ~{estimated_rows:,} filas.\n"
                    "¿Desea continuar?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

        # Validar antes de lanzar el hilo
        validation = self.join_service.validate_config(
            self.left_df, self.right_df, config
        )
        if validation.warnings:
            warning_msg = "Advertencias detectadas:\n" + "\n".join(
                validation.warnings
            )
            warning_msg += "\n\n¿Desea continuar de todos modos?"
            reply = QMessageBox.question(
                self,
                "Advertencias de Configuración",
                warning_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Deshabilitar botones
        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("Procesando...")
        self.cancel_btn.setEnabled(False)

        # Crear barra de progreso
        self._progress_dialog = QProgressDialog(
            "Ejecutando operación de cruce...", "Cancelar", 0, 100, self
        )
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.setAutoReset(False)
        self._progress_dialog.setValue(0)
        self._progress_dialog.canceled.connect(self._cancel_worker)
        self._progress_dialog.show()

        # Lanzar worker
        self._worker = JoinWorkerThread(
            self.join_service, self.left_df, self.right_df, config
        )
        self._worker.progress_updated.connect(self._on_join_progress)
        self._worker.finished.connect(self._on_join_finished)
        self._worker.error_occurred.connect(self._on_join_error)
        self._worker.start()

    def _cancel_worker(self) -> None:
        """Cancelar el hilo de ejecución."""
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
            stop_thread(self._worker, timeout_ms=3000)
        self._restore_buttons()

    def _on_join_progress(self, percent: int) -> None:
        """Actualizar barra de progreso."""
        if self._progress_dialog and not self._progress_dialog.wasCanceled():
            self._progress_dialog.setValue(percent)

    def _on_join_finished(self, result: object) -> None:
        """Manejar resultado exitoso del join."""
        from core.join.models import JoinResult

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        self._restore_buttons()
        self._worker = None

        join_result: JoinResult = cast(JoinResult, result)
        if join_result.success:
            self.join_completed.emit(
                join_result,
                str(self.right_file_path) if self.right_file_path else "",
            )
            QMessageBox.information(
                self,
                "Éxito",
                f"Join completado exitosamente\n"
                f"Resultado: {join_result.metadata.result_rows} filas "
                f"× {len(join_result.data.columns)} columnas\n"
                f"Tiempo: {join_result.metadata.processing_time_seconds:.2f} segundos",
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Error", join_result.error_message)

    def _on_join_error(self, error_message: str) -> None:
        """Manejar error del hilo de ejecución."""
        logger.error("Error en JoinWorkerThread: %s", error_message)
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        self._restore_buttons()
        self._worker = None
        QMessageBox.critical(self, "Error", f"Error inesperado: {error_message}")

    def _restore_buttons(self) -> None:
        """Restaurar estado de botones tras ejecución."""
        self.execute_btn.setEnabled(True)
        self.execute_btn.setText("🚀 Ejecutar Join")
        self.cancel_btn.setEnabled(True)

    def reject(self) -> None:
        """Cancelar operación y limpiar recursos."""
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
            self._worker.wait(2000)
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None
        self.join_cancelled.emit()
        super().reject()