"""
Barra de título personalizada (ventana sin marco).

Contiene el logo, el título de la app y los botones de ventana. El arrastre
delega en `QWindow.startSystemMove()` para que el movimiento lo gestione el
compositor (multi-monitor y HiDPI incluidos).
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.resources import get_asset_path


def _icon(name: str) -> QIcon:
    path = get_asset_path(f'icons/{name}.png')
    return QIcon(str(path)) if path.exists() else QIcon()


class TitleBar(QFrame):
    """Barra superior con el título de la app y los controles de ventana."""

    menu_requested = Signal()
    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()
    settings_requested = Signal()

    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('titleBar')
        self.setFixedHeight(56)
        self._maximized = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(10)

        self.menu_btn = self._make_icon_button('icon_menu', 'Mostrar u ocultar el menú')
        self.menu_btn.setObjectName('toggleButton')
        self.menu_btn.clicked.connect(self.menu_requested)
        layout.addWidget(self.menu_btn)

        logo = QLabel()
        logo.setObjectName('appLogo')
        logo.setFixedSize(28, 28)
        self._logo_path = get_asset_path('logo.png')
        if self._logo_path.exists():
            logo.setPixmap(QIcon(str(self._logo_path)).pixmap(QSize(24, 24)))
        layout.addWidget(logo)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(0)

        self.title_label = QLabel(title)
        self.title_label.setObjectName('titleLeftApp')
        titles.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName('titleLeftDescription')
        titles.addWidget(self.subtitle_label)

        layout.addLayout(titles)
        layout.addStretch(1)

        self.settings_btn = self._make_icon_button('cil-settings', 'Ajustes')
        self.settings_btn.setObjectName('settingsTopBtn')
        self.settings_btn.setCheckable(True)
        self.settings_btn.setToolTip('Ajustes')
        self.settings_btn.clicked.connect(self.settings_requested)
        layout.addWidget(self.settings_btn)

        window_buttons = QFrame()
        window_buttons.setObjectName('windowButtons')
        buttons_layout = QHBoxLayout(window_buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(2)

        self.minimize_btn = self._make_icon_button('icon_minimize', 'Minimizar')
        self.minimize_btn.setObjectName('minimizeAppBtn')
        self.minimize_btn.clicked.connect(self.minimize_requested)

        self.maximize_btn = self._make_icon_button('icon_maximize', 'Maximizar')
        self.maximize_btn.setObjectName('maximizeRestoreAppBtn')
        self.maximize_btn.clicked.connect(self.maximize_requested)

        self.close_btn = self._make_icon_button('icon_close', 'Cerrar')
        self.close_btn.setObjectName('closeAppBtn')
        self.close_btn.clicked.connect(self.close_requested)

        for button in (self.minimize_btn, self.maximize_btn, self.close_btn):
            buttons_layout.addWidget(button)

        layout.addWidget(window_buttons)

    @staticmethod
    def _make_icon_button(icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setIcon(_icon(icon_name))
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(30, 26)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    # ==================== ESTADO ====================

    def set_maximized(self, maximized: bool) -> None:
        """Cambiar el icono maximizar/restaurar."""
        self._maximized = maximized
        icon_name = 'icon_restore' if maximized else 'icon_maximize'
        self.maximize_btn.setIcon(_icon(icon_name))
        self.maximize_btn.setToolTip('Restaurar' if maximized else 'Maximizar')

    def set_window_controls_visible(self, visible: bool) -> None:
        """Ocultar los botones de ventana cuando el SO pone el marco."""
        for button in (self.minimize_btn, self.maximize_btn, self.close_btn):
            button.setVisible(visible)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)

    # ==================== ARRASTRE ====================

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            handle = window.windowHandle() if window is not None else None
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


__all__ = ['TitleBar']
