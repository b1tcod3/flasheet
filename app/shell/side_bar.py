"""
Barra lateral de navegación, con colapso animado (60 px ↔ 220 px).

Los botones de página son `checkable` dentro de un `QButtonGroup` exclusivo:
el estado seleccionado se resuelve por QSS (`#sideBarBtn:checked`), sin
`setStyleSheet` dinámicos.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.resources import get_asset_path
from app.view_manager.view_registry import ViewRegistry

WIDTH_COLLAPSED = 60
WIDTH_EXPANDED = 220
ANIMATION_MS = 400

PAGE_ITEMS: tuple[tuple[int, str, str], ...] = (
    (ViewRegistry.VIEW_MAIN, 'Inicio', 'cil-home'),
    (ViewRegistry.VIEW_DATA, 'Datos', 'cil-view-quilt'),
    (ViewRegistry.VIEW_JOIN, 'Cruzar', 'cil-people'),
    (ViewRegistry.VIEW_PIVOT, 'Pivote', 'cil-chart-pie'),
    (ViewRegistry.VIEW_PROFILING, 'Perfil', 'cil-user'),
    (ViewRegistry.VIEW_VISUALIZER, 'Visualizador', 'cil-chart-line'),
)

ACTION_ITEMS: tuple[tuple[str, str, str], ...] = (
    ('open', 'Abrir archivo', 'cil-folder-open'),
    ('folder', 'Cargar carpeta', 'cil-file'),
    ('export', 'Exportar', 'cil-save'),
    ('separate', 'Datos separados', 'cil-external-link'),
    ('clean', 'Limpieza rápida', 'cil-reload'),
)

DATA_VIEWS = frozenset({
    ViewRegistry.VIEW_JOIN,
    ViewRegistry.VIEW_PIVOT,
    ViewRegistry.VIEW_PROFILING,
    ViewRegistry.VIEW_VISUALIZER,
})

DATA_ACTIONS = frozenset({'export', 'separate', 'clean'})


def _icon(name: str) -> QIcon:
    path = get_asset_path(f'icons/{name}.png')
    return QIcon(str(path)) if path.exists() else QIcon()


class SideBar(QFrame):
    """Menú lateral con páginas y acciones."""

    page_requested = Signal(int)
    action_requested = Signal(str)
    toggle_left_requested = Signal()
    collapse_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('leftMenuBg')
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(WIDTH_EXPANDED)
        self._collapsed = False
        self._animations: QParallelAnimationGroup | None = None

        self._page_buttons: dict[int, QPushButton] = {}
        self._action_buttons: dict[str, QPushButton] = {}
        self._labels: list[tuple[QPushButton, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        self._logo = QLabel()
        self._logo.setObjectName('topLogo')
        self._logo.setFixedHeight(48)
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo.setPixmap(_icon('cil-view-quilt').pixmap(QSize(26, 26)))
        layout.addWidget(self._logo)

        self._page_group = QButtonGroup(self)
        self._page_group.setExclusive(True)

        for view_id, label, icon_name in PAGE_ITEMS:
            button = self._make_button(label, icon_name, 'sideBarBtn')
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, vid=view_id: self.page_requested.emit(vid))
            self._page_group.addButton(button)
            self._page_buttons[view_id] = button
            layout.addWidget(button)

        layout.addWidget(self._make_divider())

        for action, label, icon_name in ACTION_ITEMS:
            button = self._make_button(label, icon_name, 'sideBarAction')
            button.clicked.connect(lambda _checked=False, name=action: self.action_requested.emit(name))
            self._action_buttons[action] = button
            layout.addWidget(button)

        layout.addStretch(1)
        layout.addWidget(self._make_divider())

        self._toggle_left_btn = self._make_button('Archivos', 'cil-history', 'sideBarAction')
        self._toggle_left_btn.setCheckable(True)
        self._toggle_left_btn.clicked.connect(self.toggle_left_requested)
        layout.addWidget(self._toggle_left_btn)

        self._exit_btn = self._make_button('Salir', 'cil-account-logout', 'sideBarAction')
        layout.addWidget(self._exit_btn)

        self.set_active(ViewRegistry.VIEW_MAIN)
        self.set_data_actions_enabled(False)

    # ==================== CONSTRUCCIÓN ====================

    def _make_button(self, label: str, icon_name: str, object_name: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName(object_name)
        button.setIcon(_icon(icon_name))
        button.setIconSize(QSize(20, 20))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(38)
        button.setToolTip(label)
        self._labels.append((button, label))
        return button

    def _make_divider(self) -> QFrame:
        divider = QFrame()
        divider.setObjectName('sideBarDivider')
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        return divider

    # ==================== ESTADO ====================

    def active_page(self) -> int:
        for view_id, button in self._page_buttons.items():
            if button.isChecked():
                return view_id
        return ViewRegistry.VIEW_MAIN

    def set_active(self, view_id: int) -> None:
        """Marcar la página actual sin emitir `page_requested`."""
        button = self._page_buttons.get(view_id)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def set_view_buttons_enabled(self, enabled: bool) -> None:
        """Compatibilidad con AppCoordinator: habilita las páginas de datos."""
        for view_id in DATA_VIEWS:
            button = self._page_buttons.get(view_id)
            if button is not None:
                button.setEnabled(enabled)

    def set_data_actions_enabled(self, enabled: bool) -> None:
        """Habilitar/deshabilitar acciones que requieren datos cargados."""
        for action in DATA_ACTIONS:
            button = self._action_buttons.get(action)
            if button is not None:
                button.setEnabled(enabled)
        self.set_view_buttons_enabled(enabled)

    @property
    def exit_button(self) -> QPushButton:
        return self._exit_btn

    def action_button(self, action: str) -> QPushButton | None:
        return self._action_buttons.get(action)

    def page_button(self, view_id: int) -> QPushButton | None:
        return self._page_buttons.get(view_id)

    def set_left_button_checked(self, checked: bool) -> None:
        self._toggle_left_btn.setChecked(checked)

    # ==================== COLAPSO ANIMADO ====================

    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed == self._collapsed:
            return

        self._collapsed = collapsed
        target = WIDTH_COLLAPSED if collapsed else WIDTH_EXPANDED

        for button, label in self._labels:
            button.setText('' if collapsed else label)

        self._logo.setVisible(not collapsed)
        self._animate_width(target)
        self.collapse_changed.emit(collapsed)

    def _animate_width(self, target: int) -> None:
        if self._animations is not None:
            self._animations.stop()

        group = QParallelAnimationGroup(self)
        for prop in (QByteArray(b'minimumWidth'), QByteArray(b'maximumWidth')):
            animation = QPropertyAnimation(self, prop, parent=self)
            animation.setDuration(ANIMATION_MS)
            animation.setStartValue(self.width())
            animation.setEndValue(target)
            animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
            group.addAnimation(animation)

        self._animations = group
        group.start()
