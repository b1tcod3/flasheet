"""
Diálogo principal de exportación separada con plantillas Excel.
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

from core.data_handler import (
    ExcelTemplateSplitter, ExportSeparatedConfig, ValidationResult
)

from .column_mapping import ColumnMappingWidget
from .file_preview import FilePreviewDialog


class ExportSeparatedDialog(QDialog):
    """
    Diálogo compacto de configuración de exportación separada.
    Panel dividido (QSplitter): configuración a la izquierda, mapeo a la derecha.
    """

    configuration_changed = Signal()
    validation_updated = Signal(bool, str)

    def __init__(self, dataframe: pd.DataFrame, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df = dataframe
        self.config: ExportSeparatedConfig | None = None
        self.validation_result: ValidationResult | None = None
        self._template_path: str = ""
        self._template_ext: str = ".xlsx"
        self._dest_path: Path | None = None

        self.setWindowTitle("Configurar Exportación Separada")
        self.setMinimumSize(900, 560)
        self.resize(1000, 600)

        self._setup_ui()
        self._setup_connections()
        self._initialize_data()

    # ── UI ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 8, 10, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Panel izquierdo: Configuración ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(6)

        # Configuración principal
        cfg_group = QGroupBox("Configuración Principal")
        cfg_grid = QGridLayout(cfg_group)
        cfg_grid.setSpacing(4)

        cfg_grid.addWidget(QLabel("Columna:"), 0, 0)
        self.column_combo = QComboBox()
        cfg_grid.addWidget(self.column_combo, 0, 1)

        self.include_nulls_check = QCheckBox("Incluir nulos")
        cfg_grid.addWidget(self.include_nulls_check, 0, 2)

        cfg_grid.addWidget(QLabel("Plantilla:"), 1, 0)
        tpl_row = QHBoxLayout()
        self.template_path_label = QLabel("Ninguna")
        self.template_path_label.setStyleSheet("color: #717e95; font-style: italic;")
        tpl_row.addWidget(self.template_path_label, 1)
        self.select_template_btn = QPushButton("Examinar…")
        self.select_template_btn.setFixedWidth(90)
        tpl_row.addWidget(self.select_template_btn)
        cfg_grid.addLayout(tpl_row, 1, 1, 1, 2)

        cfg_grid.addWidget(QLabel("Hoja / Celda:"), 2, 0)
        sheet_cell_row = QHBoxLayout()
        self.sheet_combo = QComboBox()
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.setMinimumWidth(100)
        sheet_cell_row.addWidget(self.sheet_combo)
        self.start_cell_combo = QComboBox()
        self.start_cell_combo.setEditable(True)
        self.start_cell_combo.addItems(["A1", "A2", "A5", "B1", "B2"])
        self.start_cell_combo.setFixedWidth(80)
        sheet_cell_row.addWidget(self.start_cell_combo)
        sheet_cell_row.addStretch()
        cfg_grid.addLayout(sheet_cell_row, 2, 1, 1, 2)

        left_layout.addWidget(cfg_group)

        # Salida y archivos
        out_group = QGroupBox("Salida y Archivos")
        out_grid = QGridLayout(out_group)
        out_grid.setSpacing(4)

        out_grid.addWidget(QLabel("Destino:"), 0, 0)
        dest_row = QHBoxLayout()
        self.dest_folder_label = QLabel("Sin seleccionar")
        self.dest_folder_label.setStyleSheet("color: #717e95; font-style: italic;")
        dest_row.addWidget(self.dest_folder_label, 1)
        self.select_folder_btn = QPushButton("Cambiar…")
        self.select_folder_btn.setFixedWidth(90)
        dest_row.addWidget(self.select_folder_btn)
        out_grid.addLayout(dest_row, 0, 1)

        out_grid.addWidget(QLabel("Nombre:"), 1, 0)
        name_row = QHBoxLayout()
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setPlaceholderText("{valor}_{fecha}.xlsx")
        self.filename_template_edit.setText("{valor}_{fecha}.xlsx")
        name_row.addWidget(self.filename_template_edit, 1)
        name_row.addWidget(QLabel("({valor}, {fecha}, {contador})"))
        out_grid.addLayout(name_row, 1, 1)

        out_grid.addWidget(QLabel("Duplicados:"), 2, 0)
        self.handle_duplicates_combo = QComboBox()
        self.handle_duplicates_combo.addItems([
            "Sobrescribir", "Numerar automáticamente", "Ignorar"
        ])
        out_grid.addWidget(self.handle_duplicates_combo, 2, 1)

        left_layout.addWidget(out_group)

        # Preview lado a lado
        prev_group = QGroupBox("Previsualización")
        prev_layout = QHBoxLayout(prev_group)
        prev_layout.setSpacing(4)

        val_col = QVBoxLayout()
        val_col.addWidget(QLabel("Valores:"))
        self.values_preview = QListWidget()
        self.values_preview.setMaximumHeight(100)
        val_col.addWidget(self.values_preview)
        prev_layout.addLayout(val_col)

        name_col = QVBoxLayout()
        name_col.addWidget(QLabel("Nombres generados:"))
        self.filenames_preview = QListWidget()
        self.filenames_preview.setMaximumHeight(100)
        name_col.addWidget(self.filenames_preview)
        prev_layout.addLayout(name_col)

        left_layout.addWidget(prev_group)
        left_layout.addStretch()

        # ── Panel derecho: Mapeo ──
        right = QGroupBox("Mapeo de Columnas (DataFrame → Excel)")
        right_layout = QVBoxLayout(right)
        self.mapping_widget = ColumnMappingWidget()
        right_layout.addWidget(self.mapping_widget)

        # ── Ensamblar splitter ──
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([480, 520])
        root.addWidget(splitter, 1)

        # ── Barra de validación + botones ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(4)
        root.addWidget(self.progress_bar)

        bottom = QHBoxLayout()
        self.validation_label = QLabel("Configuración incompleta")
        self.validation_label.setStyleSheet("color: #d97706; font-weight: bold;")
        bottom.addWidget(self.validation_label)
        bottom.addStretch()

        self.preview_btn = QPushButton("Vista Previa")
        self.preview_btn.setEnabled(False)
        bottom.addWidget(self.preview_btn)

        self.cancel_btn = QPushButton("Cancelar")
        bottom.addWidget(self.cancel_btn)

        self.export_btn = QPushButton("Exportar")
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet(
            "QPushButton { background-color: #bd93f9; color: white; "
            "border: none; border-radius: 6px; padding: 6px 18px; font-weight: 600; }"
            "QPushButton:hover { background-color: #ff79c6; }"
            "QPushButton:disabled { background-color: #717e95; }"
        )
        bottom.addWidget(self.export_btn)

        root.addLayout(bottom)

    # ── Conexiones ──────────────────────────────────────────────────

    def _setup_connections(self) -> None:
        self.column_combo.currentTextChanged.connect(self.on_column_changed)
        self.filename_template_edit.textChanged.connect(self.on_template_changed)
        self.start_cell_combo.currentTextChanged.connect(self.on_start_cell_changed)
        self.sheet_combo.currentTextChanged.connect(self.on_sheet_changed)
        self.select_template_btn.clicked.connect(self.select_template)
        self.select_folder_btn.clicked.connect(self.select_destination_folder)
        self.cancel_btn.clicked.connect(self.reject)
        self.export_btn.clicked.connect(self._on_export)
        self.preview_btn.clicked.connect(self.show_file_preview)

        self._validation_timer = QTimer()
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(500)
        self._validation_timer.timeout.connect(self.validate_configuration)

    # ── Inicialización ──────────────────────────────────────────────

    def _initialize_data(self) -> None:
        if self.df is None or self.df.empty:
            return
        self.column_combo.addItems(self.df.columns.tolist())
        self.mapping_widget.set_dataframe_columns(self.df.columns.tolist())
        self.mapping_widget.set_excel_columns([chr(65 + i) for i in range(26)])
        self._load_settings()
        self.update_values_preview()
        self.validate_configuration()

    # ── Persistencia con QSettings ──────────────────────────────────

    def _save_settings(self) -> None:
        s = QSettings("FlashSheet", "ExportSeparated")
        s.beginGroup("Config")
        s.setValue("separator_column", self.column_combo.currentText())
        s.setValue("template_path", self._template_path)
        s.setValue("template_ext", self._template_ext)
        s.setValue("start_cell", self.start_cell_combo.currentText())
        s.setValue("file_template", self.filename_template_edit.text())
        s.setValue("handle_duplicates", self.handle_duplicates_combo.currentText())
        s.setValue("output_folder", str(self._dest_path) if self._dest_path else "")
        s.setValue("column_mapping", str(self.mapping_widget.get_mapping()))
        s.endGroup()

    def _load_settings(self) -> None:
        s = QSettings("FlashSheet", "ExportSeparated")
        s.beginGroup("Config")

        col = str(s.value("separator_column", ""))
        if col:
            idx = self.column_combo.findText(col)
            if idx >= 0:
                self.column_combo.setCurrentIndex(idx)

        tpl_path = str(s.value("template_path", ""))
        tpl_ext = str(s.value("template_ext", ".xlsx"))
        if tpl_path and Path(tpl_path).exists():
            self._load_template_settings(tpl_path, tpl_ext)

        cell = str(s.value("start_cell", "A1"))
        idx = self.start_cell_combo.findText(cell)
        if idx >= 0:
            self.start_cell_combo.setCurrentIndex(idx)
        else:
            self.start_cell_combo.setEditText(cell)

        file_tpl = str(s.value("file_template", ""))
        if file_tpl:
            self.filename_template_edit.setText(file_tpl)

        dup = str(s.value("handle_duplicates", ""))
        if dup:
            idx = self.handle_duplicates_combo.findText(dup)
            if idx >= 0:
                self.handle_duplicates_combo.setCurrentIndex(idx)

        output = str(s.value("output_folder", ""))
        if output and Path(output).is_dir():
            self._dest_path = Path(output)
            self.dest_folder_label.setText(self._dest_path.name)
            self.dest_folder_label.setToolTip(str(self._dest_path))
            self.dest_folder_label.setStyleSheet("color: #111827;")

        mapping_str = str(s.value("column_mapping", ""))
        if mapping_str:
            self._load_mapping_settings(mapping_str)

        s.endGroup()

    def _load_template_settings(self, tpl_path: str, tpl_ext: str) -> None:
        self._template_path = tpl_path
        self._template_ext = tpl_ext
        self.template_path_label.setText(Path(tpl_path).name)
        self.template_path_label.setStyleSheet("color: #111827;")
        self.template_path_label.setToolTip(tpl_path)
        try:
            wb = openpyxl.load_workbook(tpl_path, read_only=True)
            self.sheet_combo.blockSignals(True)
            self.sheet_combo.clear()
            self.sheet_combo.addItems(wb.sheetnames)
            self.sheet_combo.setEnabled(True)
            self.sheet_combo.blockSignals(False)
            wb.close()
        except Exception:
            pass

    def _load_mapping_settings(self, mapping_str: str) -> None:
        import ast
        try:
            mapping = ast.literal_eval(mapping_str)
            if isinstance(mapping, dict):
                for df_col, excel_col in mapping.items():
                    for row in range(self.mapping_widget.mapping_table.rowCount()):
                        item = self.mapping_widget.mapping_table.item(row, 0)
                        if item and item.text() == df_col:
                            combo = self.mapping_widget.mapping_table.cellWidget(row, 2)
                            if combo:
                                idx = combo.findText(excel_col)
                                if idx >= 0:
                                    combo.setCurrentIndex(idx)
                            break
        except Exception:
            pass

    # ── Selección de plantilla ──────────────────────────────────────

    def select_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Plantilla Excel", "",
            "Excel (*.xlsx *.xlsm);;Todos (*)"
        )
        if not path:
            return

        try:
            wb = openpyxl.load_workbook(path, read_only=True)
            sheets = wb.sheetnames
            wb.close()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo leer la plantilla:\n{e}")
            return

        self._template_path = path
        self._template_ext = Path(path).suffix.lower()
        name = Path(path).name
        self.template_path_label.setText(name)
        self.template_path_label.setStyleSheet("color: #111827;")
        self.template_path_label.setToolTip(path)

        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(sheets)
        self.sheet_combo.setEnabled(True)
        self.sheet_combo.blockSignals(False)

        # Actualizar extensión en el filename template
        current = self.filename_template_edit.text().strip()
        if current.lower().endswith(('.xlsx', '.xlsm')):
            current = current[:current.rfind('.')] + self._template_ext
        else:
            current += self._template_ext
        self.filename_template_edit.blockSignals(True)
        self.filename_template_edit.setText(current)
        self.filename_template_edit.blockSignals(False)

        self._validation_timer.start()

    # ── Selección de destino ────────────────────────────────────────

    def select_destination_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Destino")
        if not folder:
            return

        self._dest_path = Path(folder)
        self.dest_folder_label.setText(self._dest_path.name)
        self.dest_folder_label.setToolTip(str(self._dest_path))
        self.dest_folder_label.setStyleSheet("color: #111827;")

        self._validation_timer.start()

    # ── Cambios en campos ───────────────────────────────────────────

    def on_column_changed(self, _column: str) -> None:
        self.update_values_preview()
        self.update_filename_preview()
        self._validation_timer.start()

    def on_template_changed(self) -> None:
        self.update_filename_preview()
        self._validation_timer.start()

    def on_start_cell_changed(self, _text: str) -> None:
        self._validation_timer.start()

    def on_sheet_changed(self, _name: str) -> None:
        self._validation_timer.start()

    # ── Previews ────────────────────────────────────────────────────

    def update_values_preview(self) -> None:
        self.values_preview.clear()
        col = self.column_combo.currentText()
        if not col or self.df is None or col not in self.df.columns:
            return

        sample = self.df[col] if len(self.df) < 5000 else self.df[col].sample(5000)
        counts = sample.value_counts().head(15)
        for val, cnt in counts.items():
            if pd.notna(val):
                self.values_preview.addItem(f"  {val}  ({cnt:,})")

        nulls = self.df[col].isnull().sum()
        if nulls > 0:
            self.values_preview.addItem(f"  [Nulos]  ({nulls:,})")

    def update_filename_preview(self) -> None:
        self.filenames_preview.clear()
        col = self.column_combo.currentText()
        template = self.filename_template_edit.text().strip()
        if not col or not template or self.df is None or col not in self.df.columns:
            return

        if not template.lower().endswith(('.xlsx', '.xlsm')):
            template += self._template_ext

        for i, val in enumerate(self.df[col].dropna().unique()[:8]):
            fname = (template
                     .replace("{valor}", str(val))
                     .replace("{fecha}", datetime.now().strftime("%Y-%m-%d"))
                     .replace("{contador}", f"{i + 1:02d}")
                     .replace("{columna_nombre}", col))
            self.filenames_preview.addItem(f"  {fname}")

    # ── Validación ──────────────────────────────────────────────────

    def validate_configuration(self) -> None:
        config = self._build_config(validate=False)
        if config is None:
            self._set_validation(False, "Configuración incompleta")
            return

        try:
            splitter = ExcelTemplateSplitter(self.df, config)
            result = splitter.validate_configuration()
            self.validation_result = result

            if not result.is_valid:
                self._set_validation(False, f"{len(result.errors)} error(es)")
            elif result.warnings:
                self._set_validation(True, f"Válida ({len(result.warnings)} advertencia(s))")
            else:
                self._set_validation(True, "Configuración válida")
        except Exception as e:
            self._set_validation(False, str(e))

    def _set_validation(self, valid: bool, msg: str) -> None:
        color = "#16a34a" if valid else "#d97706"
        icon = "✅" if valid else "⚠️"
        self.validation_label.setText(f"{icon} {msg}")
        self.validation_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.export_btn.setEnabled(valid)
        self.preview_btn.setEnabled(valid)
        self.validation_updated.emit(valid, msg)

    # ── Construcción de config ──────────────────────────────────────

    def _build_config(self, validate: bool = True) -> ExportSeparatedConfig | None:
        col = self.column_combo.currentText()
        if not col:
            return None

        template = self.filename_template_edit.text().strip()
        if not template:
            return None
        if not template.lower().endswith(('.xlsx', '.xlsm')):
            template += self._template_ext

        output = str(self._dest_path) if self._dest_path else ""
        if not output:
            return None

        start_cell = self.start_cell_combo.currentText().strip() or "A1"

        dup_map = {
            "Sobrescribir": "overwrite",
            "Numerar automáticamente": "append",
            "Ignorar": "skip",
        }

        config = ExportSeparatedConfig(
            separator_column=col,
            template_path=self._template_path,
            output_folder=output,
            start_cell=start_cell,
            file_template=template,
            column_mapping=self.mapping_widget.get_mapping(),
            handle_duplicates=dup_map.get(
                self.handle_duplicates_combo.currentText(), "overwrite"
            ),
        )

        if validate:
            try:
                splitter = ExcelTemplateSplitter(self.df, config)
                result = splitter.validate_configuration()
                if not result.is_valid:
                    return None
            except Exception:
                return None

        return config

    # ── Preview de archivos ─────────────────────────────────────────

    def show_file_preview(self) -> None:
        col = self.column_combo.currentText()
        if not col or self.df is None or col not in self.df.columns:
            return

        files_info: list[dict[str, Any]] = []
        for val in self.df[col].dropna().unique():
            group = self.df[self.df[col] == val]
            fname = (self.filename_template_edit.text().strip()
                     .replace("{valor}", str(val))
                     .replace("{fecha}", datetime.now().strftime("%Y-%m-%d")))
            if not fname.lower().endswith(('.xlsx', '.xlsm')):
                fname += self._template_ext
            files_info.append({
                'filename': fname,
                'group': str(val),
                'rows': len(group),
                'size': f"~{len(group) * 0.5:.1f}KB",
                'status': 'Listo'
            })

        FilePreviewDialog(files_info, self).exec()

    # ── Exportar ────────────────────────────────────────────────────

    def _on_export(self) -> None:
        config = self._build_config()
        if config is None:
            QMessageBox.warning(self, "Inválido", "Revise la configuración.")
            return
        self.config = config
        self.accept()

    # ── API pública ─────────────────────────────────────────────────

    def get_configuration(self, validate: bool = True) -> ExportSeparatedConfig | None:
        if self.config is not None and not validate:
            return self.config
        return self._build_config(validate=validate)

    def accept(self) -> None:
        if self.config is None:
            config = self._build_config()
            if config is None:
                QMessageBox.warning(
                    self, "Configuración Inválida",
                    "La configuración actual no es válida. Revise los errores marcados."
                )
                return
            self.config = config
        self._save_settings()
        super().accept()

    # ── Cleanup ─────────────────────────────────────────────────────

    def closeEvent(self, event: Any) -> None:
        self._validation_timer.stop()
        super().closeEvent(event)
