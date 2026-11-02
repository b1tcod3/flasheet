#!/usr/bin/env python3
"""
Flash View Sheet - Visor de Datos Tabulares
Punto de entrada principal de la aplicación
"""

import sys
import traceback
from pathlib import Path
from types import TracebackType

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QDialog

from app.resources import get_asset_path
from app.theme import apply_light_theme

from core.join.join_history import JoinHistory

# Importar servicios y gestores
from app.services import DataService, ExportService, PivotService, CleaningService, JoinService
from app.services.recent_files_service import RecentFilesService
from app.toolbar import ToolbarManager
from app.view_manager import ViewCoordinator

# Importar coordinador de aplicación
from app.app_coordinator import AppCoordinator

# Importar menús
from app.menus.menu_builder import MenuBuilder

class MainWindow(QMainWindow):
    """Ventana principal de la aplicación - Orquestador de componentes"""
    
    # Instance attributes
    data_service: DataService
    export_service: ExportService
    pivot_service: PivotService
    cleaning_service: CleaningService
    toolbar_manager: ToolbarManager
    view_coordinator: ViewCoordinator
    coordinator: AppCoordinator
    join_history: JoinHistory
    recent_files_service: RecentFilesService
    menu_builder: MenuBuilder
    separar_menu: object | None
    datos_menu: object | None
    tabla_pivote_menu: object | None
    
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Flash View Sheet - Visor de Datos Tabulares")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)
        
        # Inicializar servicios
        self._init_services()
        
        # Inicializar gestor de toolbar
        self._init_toolbar()
        
        # Inicializar coordinador de aplicación
        self._init_coordinator()
        
        # Configurar UI
        self._setup_ui()
        self._setup_connections()
        self._load_initial_recent_files()
    
    # ==================== INICIALIZACIÓN ====================
    
    def _init_services(self) -> None:
        """Inicializar servicios centralizados"""
        self.data_service = DataService()
        self.export_service = ExportService()
        self.pivot_service = PivotService()
        self.cleaning_service = CleaningService()
        self.recent_files_service = RecentFilesService()
    
    def _init_toolbar(self) -> None:
        """Inicializar toolbar manager"""
        self.toolbar_manager = ToolbarManager(self)
    
    def _init_coordinator(self) -> None:
        """Inicializar coordinador de aplicación"""
        # 1. Dependencias primero
        self.join_history = JoinHistory()
        self.join_service = JoinService()
        self.view_coordinator = ViewCoordinator(self)
        
        # 2. Inyectar todo en el constructor
        self.coordinator = AppCoordinator(
            parent_window=self,
            data_service=self.data_service,
            export_service=self.export_service,
            pivot_service=self.pivot_service,
            cleaning_service=self.cleaning_service,
            view_coordinator=self.view_coordinator,
            toolbar_manager=self.toolbar_manager,
            join_history=self.join_history,
            recent_files_service=self.recent_files_service,
            join_service=self.join_service
        )
        
        # 3. Conexiones posteriores
        self.toolbar_manager.set_coordinators(self.view_coordinator, self.coordinator)
        self.coordinator.status_message.connect(self.statusBar().showMessage)
    
    def _setup_ui(self) -> None:
        """Configurar la interfaz de usuario"""
        self._setup_central_widget()
        self._create_menu_bar()
        self._add_toolbar()
        self.statusBar().showMessage("Listo para cargar datos")
    
    def _setup_central_widget(self) -> None:
        """Delega la creación del contenedor principal al ViewCoordinator"""
        self.view_coordinator.create_views(self)
        self.setCentralWidget(self.view_coordinator.get_stacked_widget())
    
    def _create_menu_bar(self) -> None:
        """Crear barra de menús"""
        self.menu_builder = MenuBuilder(self, self.coordinator, self.view_coordinator)
        self.menu_builder.build()
        
        refs = self.menu_builder.get_menu_references()
        self.separar_menu = refs.get('separar_menu')
        self.datos_menu = refs.get('datos_menu')
        self.tabla_pivote_menu = refs.get('tabla_pivote_menu')
    
    def _add_toolbar(self) -> None:
        """Añadir toolbar"""
        self.toolbar_manager.create_toolbar()
        toolbar = self.toolbar_manager.get_toolbar()
        if toolbar is not None:
            self.addToolBar(toolbar)
    
    def _setup_connections(self) -> None:
        """Configurar conexiones de señales"""
        main_view = self.view_coordinator.get_main_view()
        data_view = self.view_coordinator.get_data_view()
        joined_view = self.view_coordinator.get_joined_data_view()
        profiling_view = self.view_coordinator.get_profiling_view()
        quick_visualizer_view = self.view_coordinator.get_quick_visualizer_view()
        
        if main_view:
            main_view.load_file_clicked.connect(self.coordinator.solicitar_apertura_archivo)
            main_view.files_dropped.connect(self.coordinator.iniciar_carga_multiple)
            main_view.reload_with_options.connect(self._on_reload_with_options)
            main_view.recent_file_clicked.connect(self.coordinator.on_recent_file_clicked)
            main_view.recent_file_remove.connect(self.coordinator.on_recent_file_remove)
        
        if data_view:
            data_view.filter_applied.connect(self.coordinator.on_filter_applied)
            data_view.filter_cleared.connect(self.coordinator.on_filter_cleared)
        
        if joined_view:
            joined_view.new_join_requested.connect(self.coordinator.abrir_cruzar_datos)
            joined_view.export_requested.connect(self.coordinator.exportar_resultado_join)
            joined_view.history_requested.connect(self.coordinator.abrir_historial)
            joined_view.history_clear_requested.connect(self.coordinator.limpiar_historial_joins)

        if profiling_view:
            profiling_view.visualize_requested.connect(
                self.coordinator.open_visualizer_for_column)

        if quick_visualizer_view:
            quick_visualizer_view.generate_requested.connect(
                self.coordinator.on_visualize_requested)
        
        # Conectar señales de datos del coordinator al ViewCoordinator
        self.coordinator.datos_originales_cargados.connect(
            self.view_coordinator.on_datos_originales_cargados)
        self.coordinator.datos_actualizados.connect(
            self.view_coordinator.on_datos_actualizados)
        
        # Conectar datos_disponibles a menús y toolbar (single source of truth)
        self.coordinator.datos_disponibles.connect(self.menu_builder.set_data_actions_enabled)
        self.coordinator.datos_disponibles.connect(self.toolbar_manager.on_datos_disponibles)
    
    def _load_initial_recent_files(self) -> None:
        """Cargar y mostrar archivos recientes al iniciar"""
        main_view = self.view_coordinator.get_main_view()
        if main_view:
            entries = self.recent_files_service.get_recent()
            main_view.set_recent_files(entries)
    
    # ==================== SEÑALES ====================
    
    def _on_reload_with_options(self, filepath: str, skip_rows: int, column_names: dict[str, str], enable_column_visibility: bool = True) -> None:
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
        self.coordinator.iniciar_carga_archivo(filepath, skip_rows, column_names, enable_column_visibility=enable_column_visibility, separator=separator, sheet_name=sheet_name)
    
    # ==================== EVENTOS ====================
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Manejar cierre de aplicación con limpieza ordenada."""
        # 1. Detener threads y liberar DataFrames grandes
        self.data_service.cleanup()
        self.pivot_service.cleanup()
        
        # 2. Desconectar coordinator y liberar vistas
        self.coordinator.cleanup()
        self.view_coordinator.cleanup()
        
        event.accept()

def _global_exception_handler(exc_type: type[BaseException] | None, exc_value: BaseException | None, exc_traceback: TracebackType | None) -> None:
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
    app.setApplicationDisplayName("Flash View Sheet")

    # Tema claro explícito: no depender de la paleta del sistema operativo
    apply_light_theme(app)

    # Instalar manejador global de errores
    sys.excepthook = _global_exception_handler
    
    # Configurar icono
    logo_path = get_asset_path("logo.png")
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))
    
    # Crear y mostrar ventana
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
