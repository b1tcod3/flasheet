#!/usr/bin/env python3
"""
Flash View Sheet - Visor de Datos Tabulares
Punto de entrada principal de la aplicación
"""

import sys
import traceback
from pathlib import Path
from types import TracebackType
from typing import Callable, cast

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.resources import get_asset_path
from app.shell import ShellWindow
from app.shell.side_bar import SideBar
from app.theme import apply_theme, current_theme, toggle_theme
from app.view_manager import ViewRegistry

from core.join.join_history import JoinHistory

# Importar servicios y gestores
from app.services import DataService, ExportService, PivotService, CleaningService, JoinService
from app.services.recent_files_service import RecentFilesService
from app.view_manager import ViewCoordinator

# Importar coordinador de aplicación
from app.app_coordinator import AppCoordinator

APP_TITLE = 'Flash View Sheet'
APP_SUBTITLE = 'Visor de datos tabulares · Excel, CSV, SQL'

PAGE_INFO: dict[int, tuple[str, str]] = {
    ViewRegistry.VIEW_MAIN: ('Inicio', 'Abre un archivo o arrástralo sobre la ventana'),
    ViewRegistry.VIEW_DATA: ('Datos', 'Vista tabular con búsqueda, filtros y paginación'),
    ViewRegistry.VIEW_JOIN: ('Cruzar datos', 'Resultado del cruce con otro dataset'),
    ViewRegistry.VIEW_PIVOT: ('Tablas pivote', 'Resumen automático categórica × numérica'),
    ViewRegistry.VIEW_PROFILING: ('Perfil de datos', 'Tipos, nulos y cardinalidad por columna'),
    ViewRegistry.VIEW_VISUALIZER: ('Visualizador', 'Gráficos exploratorios rápidos'),
}


class MainWindow(ShellWindow):
    """Ventana principal: compone el shell con los servicios de la aplicación."""

    def __init__(self) -> None:
        super().__init__(APP_TITLE, APP_SUBTITLE)

        self._init_services()
        self._init_coordinator()
        self._attach_views()
        self._setup_connections()
        self._setup_shortcuts()
        self._load_initial_state()

    # ==================== INICIALIZACIÓN ====================

    def _init_services(self) -> None:
        """Inicializar servicios centralizados"""
        self.data_service = DataService()
        self.export_service = ExportService()
        self.pivot_service = PivotService()
        self.cleaning_service = CleaningService()
        self.recent_files_service = RecentFilesService()

    def _init_coordinator(self) -> None:
        """Inicializar coordinador de aplicación"""
        self.join_history = JoinHistory()
        self.join_service = JoinService()
        self.view_coordinator = ViewCoordinator(self)

        self.coordinator = AppCoordinator(
            parent_window=self,
            data_service=self.data_service,
            export_service=self.export_service,
            pivot_service=self.pivot_service,
            cleaning_service=self.cleaning_service,
            view_coordinator=self.view_coordinator,
            navigation=self.side_bar,
            join_history=self.join_history,
            recent_files_service=self.recent_files_service,
            join_service=self.join_service,
        )
        self.coordinator.status_message.connect(self.set_status)

    def _attach_views(self) -> None:
        """Crear las vistas y colocarlas dentro del área de contenido."""
        self.view_coordinator.create_views(self)
        stacked = self.view_coordinator.get_stacked_widget()
        self.set_pages(stacked)
        self._on_view_changed(ViewRegistry.VIEW_MAIN)

    # ==================== CONEXIONES ====================

    def _setup_connections(self) -> None:
        """Conectar el shell con los coordinadores."""
        # Navegación
        self.side_bar.page_requested.connect(self._on_page_requested)
        self.side_bar.action_requested.connect(self._on_action_requested)
        self.side_bar.toggle_left_requested.connect(self.toggle_left_panel)
        self.side_bar.exit_button.clicked.connect(self.close)

        # Paneles
        self.left_panel.open_file_requested.connect(self.coordinator.solicitar_apertura_archivo)
        self.left_panel.open_folder_requested.connect(self.coordinator.solicitar_carga_carpeta)
        self.left_panel.recent_clicked.connect(self.coordinator.on_recent_file_clicked)

        self.right_panel.theme_toggle_requested.connect(self._toggle_theme)
        self.right_panel.page_size_changed.connect(self._change_page_size)
        self.right_panel.about_requested.connect(self.coordinator.mostrar_acerca_de)

        # Barra de contenido
        self.export_requested.connect(self.coordinator.mostrar_dialogo_exportacion)

        # Cambios de vista iniciados por la app (carga, join, pivote…)
        self.view_coordinator.get_view_switcher().view_changed.connect(self._on_view_changed)

        # Datos: el coordinador avisa y las vistas se actualizan
        self.coordinator.datos_originales_cargados.connect(
            self.view_coordinator.on_datos_originales_cargados)
        self.coordinator.datos_actualizados.connect(
            self.view_coordinator.on_datos_actualizados)
        self.coordinator.datos_disponibles.connect(self._on_data_available)

        data_view = self.view_coordinator.get_data_view()
        if data_view is not None:
            data_view.data_updated.connect(self._on_data_updated)
            data_view.filter_applied.connect(self.coordinator.on_filter_applied)
            data_view.filter_cleared.connect(self.coordinator.on_filter_cleared)

        # Vistas que emiten acciones
        main_view = self.view_coordinator.get_main_view()
        if main_view:
            main_view.load_file_clicked.connect(self.coordinator.solicitar_apertura_archivo)
            main_view.files_dropped.connect(self.coordinator.iniciar_carga_multiple)
            main_view.reload_with_options.connect(self._on_reload_with_options)
            main_view.recent_file_clicked.connect(self.coordinator.on_recent_file_clicked)
            main_view.recent_file_remove.connect(self.coordinator.on_recent_file_remove)

        joined_view = self.view_coordinator.get_joined_data_view()
        if joined_view:
            joined_view.new_join_requested.connect(self.coordinator.abrir_cruzar_datos)
            joined_view.export_requested.connect(self.coordinator.exportar_resultado_join)
            joined_view.history_requested.connect(self.coordinator.abrir_historial)
            joined_view.history_clear_requested.connect(self.coordinator.limpiar_historial_joins)

        profiling_view = self.view_coordinator.get_profiling_view()
        if profiling_view:
            profiling_view.visualize_requested.connect(self.coordinator.open_visualizer_for_column)

        quick_visualizer = self.view_coordinator.get_quick_visualizer_view()
        if quick_visualizer:
            quick_visualizer.generate_requested.connect(self.coordinator.on_visualize_requested)

        self.right_panel.set_theme_name(current_theme())

    def _setup_shortcuts(self) -> None:
        """Atajos equivalentes a los antiguos menús."""
        bindings: list[tuple[str, Callable[[], object]]] = [
            ('Ctrl+O', self.coordinator.solicitar_apertura_archivo),
            ('Ctrl+Shift+O', self.coordinator.solicitar_carga_carpeta),
            ('Ctrl+E', self.coordinator.mostrar_dialogo_exportacion),
            ('Ctrl+Shift+S', self.coordinator.exportar_datos_separados),
            ('Ctrl+L', self.coordinator.ejecutar_limpieza_rapida),
            ('Ctrl+Shift+J', self.coordinator.abrir_cruzar_datos),
            ('Ctrl+Alt+P', self.coordinator.auto_pivot),
            ('Ctrl+1', lambda: self._on_page_requested(ViewRegistry.VIEW_MAIN)),
            ('Ctrl+2', lambda: self._on_page_requested(ViewRegistry.VIEW_DATA)),
            ('Ctrl+3', lambda: self._on_page_requested(ViewRegistry.VIEW_PROFILING)),
            ('Ctrl+4', lambda: self._on_page_requested(ViewRegistry.VIEW_VISUALIZER)),
            ('Ctrl+B', self.toggle_side_bar),
            ('F1', self.coordinator.mostrar_acerca_de),
            ('Ctrl+Q', lambda: self.close()),
        ]

        self._shortcuts = []
        for sequence, handler in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def _load_initial_state(self) -> None:
        """Estado inicial del shell y de los archivos recientes."""
        self.on_datos_disponibles(False)
        self.refresh_recent_files()

    # ==================== NAVEGACIÓN ====================

    def _on_page_requested(self, view_id: int) -> None:
        self.view_coordinator.switch_to(view_id)
        self.left_panel.close_panel()
        self.right_panel.close_panel()
        self.title_bar.settings_btn.setChecked(False)
        self.side_bar.set_left_button_checked(False)

    def _on_view_changed(self, view_id: int) -> None:
        """Sincronizar sidebar y cabecera con la vista activa."""
        self.side_bar.set_active(view_id)
        title, description = PAGE_INFO.get(view_id, (APP_TITLE, ''))
        self.set_page_info(title, description)

    def _on_action_requested(self, action: str) -> None:
        actions: dict[str, Callable[[], object]] = {
            'open': self.coordinator.solicitar_apertura_archivo,
            'folder': self.coordinator.solicitar_carga_carpeta,
            'export': self.coordinator.mostrar_dialogo_exportacion,
            'separate': self.coordinator.exportar_datos_separados,
            'clean': self.coordinator.ejecutar_limpieza_rapida,
        }
        handler = actions.get(action)
        if handler is not None:
            handler()

    # ==================== DATOS ====================

    def _on_data_available(self, available: bool) -> None:
        self.on_datos_disponibles(available)

    def _on_data_updated(self, df: object) -> None:
        shape = getattr(df, 'shape', None)
        if shape is not None:
            self.set_rows_info(f'{shape[0]:,} filas × {shape[1]} columnas')

    def _change_page_size(self, size: int) -> None:
        data_view = self.view_coordinator.get_data_view()
        if data_view is not None:
            data_view.set_page_size(size)

    def refresh_recent_files(self) -> None:
        """Actualizar la lista de recientes en el panel izquierdo y en la vista."""
        entries = self.recent_files_service.get_recent()
        self.left_panel.set_recent_files(entries)
        main_view = self.view_coordinator.get_main_view()
        if main_view:
            main_view.set_recent_files(entries)

    # ==================== TEMA ====================

    def _toggle_theme(self) -> None:
        instance = QApplication.instance()
        if instance is None:
            return
        theme = toggle_theme(cast(QApplication, instance))
        self.right_panel.set_theme_name(theme)
        self.view_coordinator.refresh_theme()

    # ==================== SEÑALES ====================

    def _on_reload_with_options(
        self,
        filepath: str,
        skip_rows: int,
        column_names: dict[str, str],
        enable_column_visibility: bool = True,
    ) -> None:
        """Manejar recarga con opciones"""
        separator = None
        sheet_name = None
        suffix = Path(filepath).suffix.lower()
        if suffix in ('.csv', '.tsv'):
            from app.widgets.csv_separator_dialog import CSVSeparatorDialog

            csv_dialog = CSVSeparatorDialog(self)
            if csv_dialog.exec() == QDialog.DialogCode.Accepted:
                separator = csv_dialog.get_separator()
            else:
                return
        elif suffix in ('.xlsx', '.xls'):
            from app.widgets.excel_sheet_dialog import ExcelSheetDialog

            excel_dialog = ExcelSheetDialog(filepath, self)
            if excel_dialog.exec() == QDialog.DialogCode.Accepted:
                sheet_name = excel_dialog.get_sheet_name()
            else:
                return

        self.coordinator.iniciar_carga_archivo(
            filepath,
            skip_rows,
            column_names,
            enable_column_visibility=enable_column_visibility,
            separator=separator,
            sheet_name=sheet_name,
        )

    # ==================== EVENTOS ====================

    def closeEvent(self, event: QCloseEvent) -> None:
        """Manejar cierre de aplicación con limpieza ordenada."""
        self.data_service.cleanup()
        self.pivot_service.cleanup()
        self.coordinator.cleanup()
        self.view_coordinator.cleanup()
        super().closeEvent(event)


def _global_exception_handler(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_traceback: TracebackType | None,
) -> None:
    """Atrapa errores fatales y muestra un diálogo antes de morir."""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Error fatal:\n{error_msg}", file=sys.stderr)

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Error Crítico")
    msg.setText("Ha ocurrido un error inesperado en la aplicación.")
    msg.setDetailedText(error_msg)
    msg.exec()


class SafeApplication(QApplication):
    """Captura excepciones dentro de slots de Qt y las redirige a sys.excepthook."""

    def notify(self, receiver: QObject, event: QEvent) -> bool:
        try:
            return super().notify(receiver, event)
        except Exception:
            sys.excepthook(*sys.exc_info())
            return False


def main() -> None:
    """Función principal de la aplicación"""
    app = SafeApplication(sys.argv)
    app.setApplicationName("FlashSheet")
    app.setOrganizationName("FlashSheet")
    app.setApplicationDisplayName(APP_TITLE)

    apply_theme(app, 'dark')

    sys.excepthook = _global_exception_handler

    logo_path = get_asset_path("logo.png")
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
