"""
Paneles laterales animados (estilo PyDracula): 0 px ↔ 220 px.

El panel izquierdo muestra los archivos recientes; el derecho, los ajustes.
Solo uno puede estar abierto: abrir uno cierra el otro.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    QAbstractItemView,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.resources import get_asset_path

PANEL_WIDTH = 220
ANIMATION_MS = 400


def _icon(name: str) -> QIcon:
    path = get_asset_path(f'icons/{name}.png')
    return QIcon(str(path)) if path.exists() else QIcon()


class ExtraPanel(QFrame):
    """Panel lateral con apertura/cierre animado."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(0)
        self._open = False
        self._animations: QParallelAnimationGroup | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)

        header = QFrame()
        header.setObjectName('extraTopBg')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)

        title_label = QLabel(title)
        title_label.setObjectName('extraTitle')
        header_layout.addWidget(title_label)

        self._layout.addWidget(header)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    @property
    def is_open(self) -> bool:
        return self._open

    def open_panel(self) -> None:
        if self._open:
            return
        self._open = True
        self._animate_width(PANEL_WIDTH)

    def close_panel(self) -> None:
        if not self._open:
            return
        self._open = False
        self._animate_width(0)

    def toggle(self) -> None:
        if self._open:
            self.close_panel()
        else:
            self.open_panel()

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


class LeftPanel(ExtraPanel):
    """Panel de archivos: acciones de carga y lista de recientes."""

    open_file_requested = Signal()
    open_folder_requested = Signal()
    recent_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__('Archivos', parent)

        open_btn = QPushButton('  Abrir archivo')
        open_btn.setObjectName('primaryBtn')
        open_btn.setIcon(_icon('cil-folder-open'))
        open_btn.setIconSize(QSize(16, 16))
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(self.open_file_requested)
        self.content_layout.addWidget(open_btn)

        folder_btn = QPushButton('  Cargar carpeta')
        folder_btn.setIcon(_icon('cil-file'))
        folder_btn.setIconSize(QSize(16, 16))
        folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_btn.clicked.connect(self.open_folder_requested)
        self.content_layout.addWidget(folder_btn)

        recent_label = QLabel('Recientes')
        recent_label.setObjectName('mutedLabel')
        self.content_layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setObjectName('recentList')
        self.recent_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recent_list.itemClicked.connect(self._on_item_clicked)
        self.content_layout.addWidget(self.recent_list, 1)

        self.content_layout.addStretch(0)

    def set_recent_files(self, entries: list[dict[str, Any]]) -> None:
        """Poblar la lista con las entradas de `RecentFilesService`."""
        self.recent_list.clear()
        for entry in entries:
            path = str(entry.get('filepath', ''))
            if not path:
                continue
            name = str(entry.get('filename') or Path(path).name)
            item = QListWidgetItem(name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.recent_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_clicked.emit(str(path))


class RightPanel(ExtraPanel):
    """Panel de ajustes: tema, filas por página y acerca de."""

    theme_toggle_requested = Signal()
    page_size_changed = Signal(int)
    about_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__('Ajustes', parent)

        theme_label = QLabel('Tema')
        theme_label.setObjectName('mutedLabel')
        self.content_layout.addWidget(theme_label)

        self.theme_btn = QPushButton('  Tema claro')
        self.theme_btn.setIcon(_icon('cil-moon'))
        self.theme_btn.setIconSize(QSize(16, 16))
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self.theme_toggle_requested)
        self.content_layout.addWidget(self.theme_btn)

        page_label = QLabel('Filas por página')
        page_label.setObjectName('mutedLabel')
        self.content_layout.addWidget(page_label)

        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(10, 1000)
        self.page_size_spin.setSingleStep(10)
        self.page_size_spin.setValue(10)
        self.page_size_spin.valueChanged.connect(self.page_size_changed)
        self.content_layout.addWidget(self.page_size_spin)

        self.content_layout.addStretch(1)

        about_btn = QPushButton('  Acerca de')
        about_btn.setIcon(_icon('cil-lightbulb'))
        about_btn.setIconSize(QSize(16, 16))
        about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        about_btn.clicked.connect(self.about_requested)
        self.content_layout.addWidget(about_btn)

    def set_theme_name(self, theme: str) -> None:
        self.theme_btn.setText('  Tema claro' if theme == 'dark' else '  Tema oscuro')

    def set_page_size(self, size: int) -> None:
        if self.page_size_spin.value() != size:
            self.page_size_spin.blockSignals(True)
            self.page_size_spin.setValue(size)
            self.page_size_spin.blockSignals(False)


__all__ = ['ExtraPanel', 'LeftPanel', 'PANEL_WIDTH', 'RightPanel']
