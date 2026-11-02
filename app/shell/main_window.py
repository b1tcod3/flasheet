"""
Ventana principal del shell (estilo PyDracula).

Estructura:

    ┌──────────────────────────────────────────────┐
    │ barra de título (logo, título, botones)      │
    ├──────┬────────┬─────────────────────┬────────┤
    │ menú │ panel  │  cabecera + páginas │ panel  │
    │      │ izq.   │                     │ der.   │
    ├──────┴────────┴─────────────────────┴────────┤
    │ barra inferior (estado)                      │
    └──────────────────────────────────────────────┘

La ventana no tiene marco del sistema: se arrastra desde la barra de título
(`startSystemMove`) y se redimensiona con grips (`startSystemResize`). En
Wayland se usa el marco nativo para evitar problemas del compositor.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.shell.extra_panels import LeftPanel, RightPanel
from app.shell.grips import create_grips, position_grips
from app.shell.side_bar import SideBar
from app.shell.title_bar import TitleBar

FRAME_MARGIN = 10


class ShellWindow(QMainWindow):
    """Contenedor visual de la aplicación (sin lógica de negocio)."""

    export_requested = Signal()
    closed = Signal()

    def __init__(self, app_title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._custom_frame = QGuiApplication.platformName() != 'wayland'
        self._maximized = False

        self.setWindowTitle(app_title)
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)

        if self._custom_frame:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui(app_title, subtitle)
        self._grips = create_grips(self) if self._custom_frame else {}
        self._apply_frame_state()

    # ==================== CONSTRUCCIÓN ====================

    def _build_ui(self, app_title: str, subtitle: str) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(FRAME_MARGIN, FRAME_MARGIN, FRAME_MARGIN, FRAME_MARGIN)
        outer.setSpacing(0)
        self._outer_layout = outer

        self.bg_app = QFrame()
        self.bg_app.setObjectName('bgApp')
        outer.addWidget(self.bg_app)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(17)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.bg_app.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.bg_app)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(app_title, subtitle)
        self.title_bar.menu_requested.connect(self.toggle_side_bar)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self.toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.settings_requested.connect(self.toggle_right_panel)
        root.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.side_bar = SideBar()
        body.addWidget(self.side_bar)

        self.left_panel = LeftPanel()
        body.addWidget(self.left_panel)

        body.addWidget(self._build_content(), 1)

        self.right_panel = RightPanel()
        body.addWidget(self.right_panel)

        root.addLayout(body, 1)
        root.addWidget(self._build_bottom_bar())

        self.left_panel.open_file_requested.connect(self._on_left_open_file)
        self.left_panel.open_folder_requested.connect(self._on_left_open_folder)

    def _build_content(self) -> QFrame:
        content = QFrame()
        content.setObjectName('contentBox')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QFrame()
        top.setObjectName('contentTopBg')
        top.setFixedHeight(62)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(16, 8, 16, 8)
        top_layout.setSpacing(10)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(0)

        self.page_title = QLabel('Inicio')
        self.page_title.setObjectName('contentTitle')
        titles.addWidget(self.page_title)

        self.page_description = QLabel('Carga un archivo para empezar')
        self.page_description.setObjectName('contentDescription')
        titles.addWidget(self.page_description)

        top_layout.addLayout(titles)
        top_layout.addStretch(1)

        self.export_btn = QPushButton('  Exportar')
        self.export_btn.setObjectName('primaryBtn')
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_requested)
        self.export_btn.setEnabled(False)
        top_layout.addWidget(self.export_btn)

        layout.addWidget(top)

        self._pages_host = QVBoxLayout()
        self._pages_host.setContentsMargins(12, 12, 12, 12)
        self._pages_host.setSpacing(0)
        layout.addLayout(self._pages_host, 1)

        self.pages: QStackedWidget | None = None
        return content

    def _build_bottom_bar(self) -> QFrame:
        bottom = QFrame()
        bottom.setObjectName('bottomBar')
        bottom.setFixedHeight(30)

        layout = QHBoxLayout(bottom)
        layout.setContentsMargins(14, 0, 14, 0)

        self.status_label = QLabel('Listo')
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.rows_label = QLabel('Sin datos')
        layout.addWidget(self.rows_label)
        return bottom

    # ==================== API PARA MAIN ====================

    def set_pages(self, stacked: QStackedWidget) -> None:
        """Insertar el stacked widget con las vistas de la aplicación."""
        if self.pages is not None:
            self._pages_host.removeWidget(self.pages)
            self.pages.setParent(None)

        stacked.setObjectName('pages')
        self.pages = stacked
        self._pages_host.addWidget(stacked)

    def set_page_info(self, title: str, description: str) -> None:
        self.page_title.setText(title)
        self.page_description.setText(description)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_rows_info(self, text: str) -> None:
        self.rows_label.setText(text)

    def set_data_available(self, available: bool) -> None:
        self.export_btn.setEnabled(available)

    def on_datos_disponibles(self, available: bool) -> None:
        """Habilitar/deshabilitar las acciones que requieren datos cargados."""
        self.side_bar.set_data_actions_enabled(available)
        self.set_data_available(available)

    # ==================== PANELES ====================

    def toggle_side_bar(self) -> None:
        self.side_bar.toggle_collapsed()

    def toggle_left_panel(self) -> None:
        if self.left_panel.is_open:
            self.left_panel.close_panel()
            self.side_bar.set_left_button_checked(False)
            return

        self.right_panel.close_panel()
        self.title_bar.settings_btn.setChecked(False)
        self.left_panel.open_panel()
        self.side_bar.set_left_button_checked(True)

    def toggle_right_panel(self) -> None:
        if self.right_panel.is_open:
            self.right_panel.close_panel()
            self.title_bar.settings_btn.setChecked(False)
            return

        self.left_panel.close_panel()
        self.side_bar.set_left_button_checked(False)
        self.right_panel.open_panel()
        self.title_bar.settings_btn.setChecked(True)

    def _on_left_open_file(self) -> None:
        self.left_panel.close_panel()
        self.side_bar.set_left_button_checked(False)

    def _on_left_open_folder(self) -> None:
        self.left_panel.close_panel()
        self.side_bar.set_left_button_checked(False)

    # ==================== VENTANA ====================

    def is_maximized(self) -> bool:
        return self._maximized

    def toggle_maximize(self) -> None:
        self._maximized = not self._maximized
        if self._maximized:
            self.showMaximized()
        else:
            self.showNormal()
        self._apply_frame_state()

    def _apply_frame_state(self) -> None:
        margin = 0 if (self._maximized or not self._custom_frame) else FRAME_MARGIN
        self._outer_layout.setContentsMargins(margin, margin, margin, margin)

        self.title_bar.set_maximized(self._maximized)
        self.title_bar.set_window_controls_visible(self._custom_frame)

        shadow = self.bg_app.graphicsEffect()
        if shadow is not None:
            shadow.setEnabled(margin != 0)

        for grip in self._grips.values():
            grip.setVisible(margin != 0 and self._custom_frame)

    def changeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.type() == QEvent.Type.WindowStateChange:
            maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)
            if maximized != self._maximized:
                self._maximized = maximized
                self._apply_frame_state()
        super().changeEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if self._grips:
            position_grips(self, self._grips)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.closed.emit()
        super().closeEvent(event)


__all__ = ['FRAME_MARGIN', 'ShellWindow']
