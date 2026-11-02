"""
Constructor de menús para Flash View Sheet.

Todas las acciones de menú viven como atributos de instancia de esta clase,
eliminando el estado global de MenuActions. La señal datos_disponibles
se conecta directamente al método set_data_actions_enabled().
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar
from .archivo_menu import ArchivoMenu
from .datos_menu import DatosMenu
from .vista_menu import VistaMenu
from app.view_manager.view_registry import ViewRegistry
from typing import Any


class MenuBuilder:
    """
    Builder para crear la barra de menús completa.

    Todas las QAction se crean y gestionan como atributos de instancia.
    Los coordinadores se reciben por constructor para no depender de la
    estructura interna de la ventana principal.
    """

    def __init__(self, parent_window: Any, coordinator: Any, view_coordinator: Any) -> None:
        self.parent_window = parent_window
        self.coordinator = coordinator
        self.view_coordinator = view_coordinator
        self.menu_bar: QMenuBar = QMenuBar()

        # Referencias a menús para actualización posterior
        self.separar_menu: Any | None = None
        self.datos_menu: Any | None = None
        self.tabla_pivote_menu: Any | None = None

        # Acciones — se crean en _create_actions()
        self.abrir_action: QAction
        self.cargar_carpeta_action: QAction
        self.exportar_pdf_action: QAction
        self.exportar_imagen_action: QAction
        self.exportar_xlsx_action: QAction
        self.exportar_csv_action: QAction
        self.exportar_sql_action: QAction
        self.salir_action: QAction

        self.exportar_separado_action: QAction

        self.cruzar_datos_action: QAction

        self.pivot_simple_action: QAction
        self.export_pivot_action: QAction

        self.vista_principal_action: QAction
        self.vista_datos_action: QAction
        self.vista_info_action: QAction
        self.vista_perfil_action: QAction
        self.vista_visualizador_action: QAction
        self.acerca_de_action: QAction

        self.limpieza_rapida_action: QAction

        self._create_actions()

    def _create_actions(self) -> None:
        """Crear todas las acciones como atributos de instancia."""
        p = self.parent_window

        # === Archivo ===
        self.abrir_action = QAction("&Abrir...", p)
        self.abrir_action.setShortcut("Ctrl+O")
        self.abrir_action.setStatusTip("Abrir archivo de datos")

        self.cargar_carpeta_action = QAction("&Cargar Carpeta...", p)
        self.cargar_carpeta_action.setShortcut("Ctrl+Shift+O")
        self.cargar_carpeta_action.setStatusTip("Cargar y consolidar carpeta de archivos Excel")

        self.exportar_pdf_action = QAction("&PDF...", p)
        self.exportar_pdf_action.setShortcut("Ctrl+P")
        self.exportar_pdf_action.setStatusTip("Exportar datos a formato PDF")

        self.exportar_imagen_action = QAction("&Imagen...", p)
        self.exportar_imagen_action.setShortcut("Ctrl+I")
        self.exportar_imagen_action.setStatusTip("Exportar vista actual como imagen")

        self.exportar_xlsx_action = QAction("&XLSX...", p)
        self.exportar_xlsx_action.setShortcut("Ctrl+X")
        self.exportar_xlsx_action.setStatusTip("Exportar datos a formato Excel")

        self.exportar_csv_action = QAction("&CSV...", p)
        self.exportar_csv_action.setShortcut("Ctrl+C")
        self.exportar_csv_action.setStatusTip("Exportar datos a formato CSV")

        self.exportar_sql_action = QAction("&SQL...", p)
        self.exportar_sql_action.setShortcut("Ctrl+S")
        self.exportar_sql_action.setStatusTip("Exportar datos a base de datos SQLite")

        self.salir_action = QAction("&Salir", p)
        self.salir_action.setShortcut("Ctrl+Q")
        self.salir_action.setStatusTip("Cerrar la aplicación")

        # === Separar ===
        self.exportar_separado_action = QAction("&Exportar Datos Separados...", p)
        self.exportar_separado_action.setShortcut("Ctrl+Shift+S")
        self.exportar_separado_action.setStatusTip("Exportar datos separados por columna usando plantillas Excel")
        self.exportar_separado_action.setEnabled(False)

        # === Datos ===
        self.cruzar_datos_action = QAction("&Cruzar Datos...", p)
        self.cruzar_datos_action.setShortcut("Ctrl+Shift+J")
        self.cruzar_datos_action.setStatusTip("Cruzar datos con otro dataset usando operaciones de join")
        self.cruzar_datos_action.setEnabled(False)

        # === Tabla Pivote ===
        self.pivot_simple_action = QAction("&Generar Pivote Automático", p)
        self.pivot_simple_action.setShortcut("Ctrl+Alt+P")
        self.pivot_simple_action.setStatusTip("Generar tablas pivote automáticas para todas las combinaciones")
        self.pivot_simple_action.setEnabled(False)

        self.export_pivot_action = QAction("&Exportar Datos Actuales...", p)
        self.export_pivot_action.setShortcut("Ctrl+Alt+E")
        self.export_pivot_action.setStatusTip("Exportar los datos que se muestran actualmente")
        self.export_pivot_action.setEnabled(False)

        # === Vista ===
        self.vista_principal_action = QAction("&Vista Principal", p)
        self.vista_principal_action.setShortcut("Ctrl+1")
        self.vista_principal_action.setStatusTip("Cambiar a la vista principal")

        self.vista_datos_action = QAction("&Vista de Datos", p)
        self.vista_datos_action.setShortcut("Ctrl+2")
        self.vista_datos_action.setStatusTip("Cambiar a la vista de datos")

        self.vista_info_action = QAction("&Ver Información del dataset", p)
        self.vista_info_action.setStatusTip("Mostrar información del dataset actual")

        self.vista_perfil_action = QAction("&Perfil de Datos", p)
        self.vista_perfil_action.setShortcut("Ctrl+3")
        self.vista_perfil_action.setStatusTip("Mostrar el perfil de datos del dataset")
        self.vista_perfil_action.setEnabled(False)

        self.vista_visualizador_action = QAction("&Visualizador Rápido", p)
        self.vista_visualizador_action.setShortcut("Ctrl+4")
        self.vista_visualizador_action.setStatusTip("Generar gráficos exploratorios rápidos")
        self.vista_visualizador_action.setEnabled(False)

        # === Ayuda ===
        self.acerca_de_action = QAction("&Acerca de...", p)
        self.acerca_de_action.setShortcut("F1")
        self.acerca_de_action.setStatusTip("Mostrar información sobre la aplicación")

        # === Datos ===
        self.limpieza_rapida_action = QAction("Limpieza &Rápida", p)
        self.limpieza_rapida_action.setShortcut("Ctrl+L")
        self.limpieza_rapida_action.setStatusTip("Eliminar nulos, duplicados y espacios en blanco")
        self.limpieza_rapida_action.setEnabled(False)

    # ==================== CONSTRUCCIÓN ====================

    def build(self) -> QMenuBar:
        """Construir la barra de menús completa."""
        self.menu_bar = QMenuBar()

        self._build_archivo_menu()
        self._build_separar_menu()
        self._build_datos_menu()
        self._build_tabla_pivote_menu()
        self._build_vista_menu()
        self._build_ayuda_menu()

        self._connect_actions(self.coordinator, self.view_coordinator)

        return self.menu_bar

    def _build_archivo_menu(self) -> None:
        actions: list[QAction | None] = [
            self.abrir_action,
            self.cargar_carpeta_action,
            None,
            self.exportar_pdf_action,
            self.exportar_imagen_action,
            self.exportar_xlsx_action,
            self.exportar_csv_action,
            self.exportar_sql_action,
            None,
            self.salir_action,
        ]
        ArchivoMenu.create(self.menu_bar, actions, self.parent_window)

    def _build_separar_menu(self) -> None:
        self.separar_menu = self.menu_bar.addMenu("&Separar")
        self.separar_menu.addAction(self.exportar_separado_action)

    def _build_datos_menu(self) -> None:
        self.datos_menu = DatosMenu.create(
            self.menu_bar, self.cruzar_datos_action, self.limpieza_rapida_action
        )

    def _build_tabla_pivote_menu(self) -> None:
        self.tabla_pivote_menu = self.menu_bar.addMenu("&Tabla Pivote")
        self.tabla_pivote_menu.addAction(self.pivot_simple_action)
        self.tabla_pivote_menu.addSeparator()
        self.tabla_pivote_menu.addAction(self.export_pivot_action)

    def _build_vista_menu(self) -> None:
        actions: list[QAction | None] = [
            self.vista_principal_action,
            self.vista_datos_action,
            self.vista_perfil_action,
            self.vista_visualizador_action,
            None,
            self.vista_info_action,
        ]
        VistaMenu.create(self.menu_bar, actions, self.parent_window)

    def _build_ayuda_menu(self) -> None:
        ayuda_menu = self.menu_bar.addMenu("&Ayuda")
        ayuda_menu.addAction(self.acerca_de_action)

    # ==================== CONEXIONES ====================

    def _connect_actions(self, coordinator: Any, view_coordinator: Any) -> None:
        self.abrir_action.triggered.connect(coordinator.solicitar_apertura_archivo)
        self.cargar_carpeta_action.triggered.connect(coordinator.solicitar_carga_carpeta)
        self.exportar_pdf_action.triggered.connect(coordinator.exportar_a_pdf)
        self.exportar_imagen_action.triggered.connect(coordinator.exportar_a_imagen)
        self.exportar_xlsx_action.triggered.connect(coordinator.exportar_a_xlsx)
        self.exportar_csv_action.triggered.connect(coordinator.exportar_a_csv)
        self.exportar_sql_action.triggered.connect(coordinator.exportar_a_sql)
        self.salir_action.triggered.connect(self.parent_window.close)

        self.exportar_separado_action.triggered.connect(coordinator.exportar_datos_separados)
        self.cruzar_datos_action.triggered.connect(coordinator.abrir_cruzar_datos)
        self.limpieza_rapida_action.triggered.connect(coordinator.ejecutar_limpieza_rapida)

        self.pivot_simple_action.triggered.connect(coordinator.auto_pivot)
        self.export_pivot_action.triggered.connect(coordinator.exportar_resultado_pivote)

        self.vista_principal_action.triggered.connect(
            lambda: view_coordinator.switch_to(ViewRegistry.VIEW_MAIN)
        )
        self.vista_datos_action.triggered.connect(
            lambda: view_coordinator.switch_to(ViewRegistry.VIEW_DATA)
        )
        self.vista_info_action.triggered.connect(coordinator.mostrar_info)

        self.vista_perfil_action.triggered.connect(
            lambda: view_coordinator.switch_to(ViewRegistry.VIEW_PROFILING)
        )
        self.vista_visualizador_action.triggered.connect(
            lambda: view_coordinator.switch_to(ViewRegistry.VIEW_VISUALIZER)
        )

        self.acerca_de_action.triggered.connect(coordinator.mostrar_acerca_de)

    # ==================== ESTADO ====================

    def set_data_actions_enabled(self, enabled: bool) -> None:
        """Habilitar/deshabilitar acciones que requieren datos cargados."""
        for action in (
            self.exportar_separado_action,
            self.cruzar_datos_action,
            self.pivot_simple_action,
            self.export_pivot_action,
            self.limpieza_rapida_action,
            self.vista_perfil_action,
            self.vista_visualizador_action,
        ):
            action.setEnabled(enabled)

    def get_menu_references(self) -> dict[str, Any]:
        """Obtener referencias a los menús para uso externo."""
        return {
            'separar_menu': self.separar_menu,
            'datos_menu': self.datos_menu,
            'tabla_pivote_menu': self.tabla_pivote_menu,
        }
