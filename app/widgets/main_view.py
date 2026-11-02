"""
Vista Principal para Flash View Sheet
Implementa interfaz de carga con Drag & Drop y lista de archivos recientes.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QScrollArea, QProgressBar, QStyle)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from pathlib import Path

from app.resources import get_asset_path

class FileItemWidget(QFrame):
    """Widget personalizado para representar un archivo en la lista de subidas"""
    
    cancel_clicked = Signal(str)
    delete_clicked = Signal(str)

    def __init__(self, filepath: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.filepath = filepath
        self.filename = Path(filepath).name
        self.is_uploading = True
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-bottom: 1px solid #e0e0e0;
                padding: 8px 0px;
                color: #334155;
            }
            QLabel { border: none; color: #334155; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Icono del archivo
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setStyleSheet("background-color: #f0f4f8; border-radius: 4px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(20, 20))
        layout.addWidget(self.icon_label)

        # Contenedor central (Nombre + Progreso)
        center_layout = QVBoxLayout()
        center_layout.setSpacing(2)
        
        self.name_label = QLabel(self.filename)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        center_layout.addWidget(self.name_label)

        # Elementos de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 2px;
            }
        """)
        center_layout.addWidget(self.progress_bar)

        # Textos de progreso (Tamaño y Porcentaje)
        self.progress_text_layout = QHBoxLayout()
        self.size_label = QLabel("Calculando...")
        self.size_label.setStyleSheet("font-size: 11px; color: #888;")
        self.percent_label = QLabel("Cargando... 0%")
        self.percent_label.setStyleSheet("font-size: 11px; color: #4a90e2; font-weight: bold;")
        
        self.progress_text_layout.addWidget(self.size_label)
        self.progress_text_layout.addStretch()
        self.progress_text_layout.addWidget(self.percent_label)
        
        center_layout.addLayout(self.progress_text_layout)
        layout.addLayout(center_layout)

        # Botón de acción (Cancelar / Eliminar)
        self.action_btn = QPushButton()
        self.action_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.action_btn.setFixedSize(24, 24)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #ff4d4f;
                font-size: 14px;
                background-color: transparent;
            }
            QPushButton:hover { background-color: #ffeeee; border-radius: 12px; }
        """)
        self.action_btn.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.action_btn)

    def set_progress(self, loaded_bytes: int, total_bytes: int) -> None:
        """Actualiza el estado de la carga visualmente"""
        if total_bytes > 0:
            percent = int((loaded_bytes / total_bytes) * 100)
            self.progress_bar.setValue(percent)
            
            loaded_mb = loaded_bytes / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            self.size_label.setText(f"{loaded_mb:.1f} MB of {total_mb:.1f} MB")
            self.percent_label.setText(f"Cargando... {percent}%")
            
            if percent >= 100:
                self.set_completed()

    def set_completed(self) -> None:
        """Cambia el widget a su estado de carga finalizada"""
        self.is_uploading = False
        self.progress_bar.hide()
        self.size_label.hide()
        self.percent_label.hide()
        self.action_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

    def set_error(self, message: str = "Error") -> None:
        """Marca el widget como error de carga"""
        self.is_uploading = False
        self.progress_bar.hide()
        self.size_label.hide()
        self.percent_label.setText(message)
        self.percent_label.setStyleSheet("font-size: 11px; color: #ff4d4f; font-weight: bold;")
        self.action_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

    def _on_action_clicked(self) -> None:
        if self.is_uploading:
            self.cancel_clicked.emit(self.filepath)
        else:
            self.delete_clicked.emit(self.filepath)


class RecentFileWidget(QFrame):
    """Widget para un archivo reciente en la lista"""

    clicked = Signal(str)
    remove_clicked = Signal(str)

    def __init__(self, filepath: str, filename: str, relative_time: str,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.filepath = filepath
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-bottom: 1px solid #e0e0e0;
                padding: 6px 0px;
                color: #334155;
            }
            QFrame:hover { background-color: #f5f7fa; }
            QLabel { border: none; color: #334155; }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setFixedSize(28, 28)
        icon_label.setStyleSheet("background-color: #eef5ff; border-radius: 4px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(18, 18))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        text_layout.addWidget(name_lbl)

        time_lbl = QLabel(relative_time)
        time_lbl.setStyleSheet("font-size: 11px; color: #888;")
        text_layout.addWidget(time_lbl)

        layout.addLayout(text_layout, 1)

        remove_btn = QPushButton()
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; }
            QPushButton:hover { background-color: #ffeeee; border-radius: 10px; }
        """)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(filepath))
        layout.addWidget(remove_btn)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)
        super().mousePressEvent(event)


class MainView(QWidget):
    """
    Vista principal con Drag & Drop y lista de archivos recientes.
    """
    load_file_clicked = Signal()
    files_dropped = Signal(list)  # lista de rutas válidas (multi-archivo)
    reload_with_options = Signal(str, int, dict, bool)
    recent_file_clicked = Signal(str)
    recent_file_remove = Signal(str)
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_file: str | None = None
        self._original_columns: list[str] = []
        self._file_widgets: dict[str, FileItemWidget] = {}
        
        self.setAcceptDrops(True) # Habilitar Drag & Drop en toda la vista
        self.setup_ui()
        
    def setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(40)

        # ==========================================
        # PANEL IZQUIERDO: Zona de Carga (Drag & Drop)
        # ==========================================
        left_panel = QVBoxLayout()
        
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("uploadZone")
        self.drop_zone.setStyleSheet("""
            QFrame#uploadZone {
                border: 2px dashed #4a90e2;
                border-radius: 12px;
                background-color: #f8fbff;
            }
            QFrame#uploadZone:hover {
                background-color: #eef5ff;
            }
        """)
        
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.setSpacing(15)

        # Logo de la aplicación
        logo_label = QLabel()
        logo_path = get_asset_path("logo.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled_pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("Flash Sheet")
            logo_label.setStyleSheet("font-size: 24px; color: #4a90e2; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(logo_label)

        # Flecha de subida
        upload_icon = QLabel("↑")
        upload_icon.setStyleSheet("font-size: 48px; color: #4a90e2; font-weight: bold;")
        upload_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(upload_icon)

        # Botón Browse
        self.load_button = QPushButton("Browse")
        self.load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #357abd; }
        """)
        self.load_button.clicked.connect(self.load_file)
        drop_layout.addWidget(self.load_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Texto informativo
        drop_label = QLabel("drop a file here")
        drop_label.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(drop_label)

        support_label = QLabel("*File supported .csv, .xlsx, .json")
        support_label.setStyleSheet("color: #666; font-size: 12px;")
        support_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(support_label)

        left_panel.addWidget(self.drop_zone)
        main_layout.addLayout(left_panel, stretch=6) # Toma el 60% del ancho

        # ==========================================
        # PANEL DERECHO: Archivos Cargados
        # ==========================================
        right_panel = QVBoxLayout()
        
        title_label = QLabel("Uploaded files")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
        right_panel.addWidget(title_label)

        # Scroll Area para la lista
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.files_container = QWidget()
        self.files_container.setStyleSheet("background: transparent;")
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.files_layout.setContentsMargins(0, 0, 10, 0)
        
        self.scroll_area.setWidget(self.files_container)
        right_panel.addWidget(self.scroll_area)

        self.recent_title_label = QLabel("Archivos Recientes")
        self.recent_title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #333; padding-top: 8px;")
        self.recent_title_label.hide()
        right_panel.addWidget(self.recent_title_label)

        self.recent_scroll_area = QScrollArea()
        self.recent_scroll_area.setWidgetResizable(True)
        self.recent_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.recent_scroll_area.setMaximumHeight(200)
        self.recent_scroll_area.setStyleSheet("background: transparent;")
        self.recent_scroll_area.hide()

        self.recent_container = QWidget()
        self.recent_container.setStyleSheet("background: transparent;")
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.recent_layout.setContentsMargins(0, 0, 10, 0)

        self.recent_scroll_area.setWidget(self.recent_container)
        right_panel.addWidget(self.recent_scroll_area)
        
        # Botón de opciones (ahora reubicado o flotante bajo la lista)
        self.options_button = QPushButton("Opciones del Archivo Actual")
        self.options_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d; color: white; border: none;
                padding: 8px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        self.options_button.clicked.connect(self.show_options)
        self.options_button.hide()
        right_panel.addWidget(self.options_button)

        main_layout.addLayout(right_panel, stretch=4) # Toma el 40% del ancho

    # --- Eventos de Drag & Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_zone.setStyleSheet("""
                QFrame#uploadZone {
                    border: 2px solid #4a90e2; background-color: #eef5ff; border-radius: 12px;
                }
            """)

    def dragLeaveEvent(self, event: QDragLeaveEvent | None = None) -> None:
        self.drop_zone.setStyleSheet("""
            QFrame#uploadZone {
                border: 2px dashed #4a90e2; background-color: #f8fbff; border-radius: 12px;
            }
        """)

    def dropEvent(self, event: QDropEvent) -> None:
        self.dragLeaveEvent()
        urls = event.mimeData().urls()
        if not urls:
            return
        paths = []
        for url in urls:
            filepath = url.toLocalFile()
            if Path(filepath).is_file():
                paths.append(filepath)
        if paths:
            self.files_dropped.emit(paths)

    # --- Lógica de Vistas y Archivos ---
    def load_file(self) -> None:
        self.load_file_clicked.emit()

    def add_file_to_list(self, filepath: str) -> FileItemWidget:
        """Añade un archivo a la lista lateral derecha e inicia su estado 'cargando'"""
        if filepath in self._file_widgets:
            return self._file_widgets[filepath]
            
        widget = FileItemWidget(filepath, self)
        widget.delete_clicked.connect(self.remove_file_from_list)
        widget.cancel_clicked.connect(self.remove_file_from_list)
        
        self.files_layout.addWidget(widget)
        self._file_widgets[filepath] = widget
        self.current_file = filepath
        return widget

    def clear_file_list(self) -> None:
        """Limpia toda la lista de archivos"""
        for widget in self._file_widgets.values():
            self.files_layout.removeWidget(widget)
            widget.deleteLater()
        self._file_widgets.clear()
        self.hide_options_button()

    def update_file_progress(self, filepath: str, loaded: int, total: int) -> None:
        """Permite al Coordinador actualizar la barra de progreso"""
        if filepath in self._file_widgets:
            self._file_widgets[filepath].set_progress(loaded, total)

    def set_file_completed(self, filepath: str) -> None:
        """Marca la carga como terminada"""
        if filepath in self._file_widgets:
            self._file_widgets[filepath].set_completed()
            self.current_file = filepath
            self.show_options_button()

    def set_file_error(self, filepath: str, message: str) -> None:
        """Marca la carga del archivo como fallida con un mensaje de error"""
        if filepath in self._file_widgets:
            self._file_widgets[filepath].set_error(message)

    def remove_file_from_list(self, filepath: str) -> None:
        if filepath in self._file_widgets:
            widget = self._file_widgets.pop(filepath)
            self.files_layout.removeWidget(widget)
            widget.deleteLater()
            
            if self.current_file == filepath:
                self.current_file = None
                self.hide_options_button()

    def set_file_info(self, filepath: str) -> None:
        """Método de retrocompatibilidad con el coordinador actual"""
        self.add_file_to_list(filepath)
        self.set_file_completed(filepath)

    def show_options(self) -> None:
        from app.widgets.load_options_dialog import LoadOptionsDialog
        dialog = LoadOptionsDialog(self)
        if self._original_columns:
            dialog.set_columns(self._original_columns)

        if dialog.exec():
            skip_rows, column_names, enable_column_visibility = dialog.get_options()
            self.reload_with_options.emit(self.current_file, skip_rows, column_names, enable_column_visibility)

    def set_original_columns(self, columns: list[str]) -> None:
        self._original_columns = columns

    def show_options_button(self) -> None:
        self.options_button.show()

    def hide_options_button(self) -> None:
        self.options_button.hide()

    # --- Archivos Recientes ---

    def set_recent_files(self, entries: list[dict]) -> None:
        for _ in range(self.recent_layout.count()):
            child = self.recent_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not entries:
            self.recent_title_label.hide()
            self.recent_scroll_area.hide()
            return

        self.recent_title_label.show()
        self.recent_scroll_area.show()

        for entry in entries:
            widget = RecentFileWidget(
                entry["filepath"],
                entry["filename"],
                entry["relative_time"],
                self,
            )
            widget.clicked.connect(self.recent_file_clicked.emit)
            widget.remove_clicked.connect(self.recent_file_remove.emit)
            self.recent_layout.addWidget(widget)
