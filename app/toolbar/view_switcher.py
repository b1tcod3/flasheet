"""
View Switcher for Flash View Sheet.

This module provides the view switching buttons widget.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame, QApplication, QStyle
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon

from app.resources import get_asset_path


def _make_vline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet("background-color: #c0c2c4; max-width: 1px; border: none;")
    line.setFixedWidth(4)
    return line


class ViewSwitcher(QWidget):
    """
    Widget containing buttons for switching between views.

    Provides:
    - Vista Principal button
    - Vista de Datos button
    - Cruzar Datos button
    - Tabla Pivote button
    - Ver Información button
    """

    view_main = Signal()
    view_data = Signal()
    view_info = Signal()
    view_joined = Signal()
    view_pivot = Signal()
    view_profile = Signal()
    view_visualizer = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.view_main_btn: QPushButton
        self.view_data_btn: QPushButton
        self.view_info_btn: QPushButton
        self.view_joined_btn: QPushButton
        self.view_pivot_btn: QPushButton
        self.view_profile_btn: QPushButton
        self.view_visualizer_btn: QPushButton

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(0, 0, 0, 0)

        style = QApplication.style()
        icon_size = QSize(20, 20)

        self.view_main_btn = self._make_button(
            style.standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon),
            "Vista Principal",
            icon_size
        )
        self._layout.addWidget(self.view_main_btn)

        self._layout.addWidget(_make_vline())

        self.view_data_btn = self._make_button(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Vista de Datos",
            icon_size
        )
        self._layout.addWidget(self.view_data_btn)

        self._layout.addWidget(_make_vline())

        self.view_joined_btn = self._make_button(
            style.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon),
            "Cruzar Datos",
            icon_size
        )
        self.view_joined_btn.setEnabled(False)
        self._layout.addWidget(self.view_joined_btn)

        self._layout.addWidget(_make_vline())

        self.view_pivot_btn = self._make_button(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "Tabla Pivote",
            icon_size
        )
        self.view_pivot_btn.setEnabled(False)
        self._layout.addWidget(self.view_pivot_btn)

        self._layout.addWidget(_make_vline())

        self.view_info_btn = self._make_button(
            style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation),
            "Ver Información del dataset",
            icon_size
        )
        self._layout.addWidget(self.view_info_btn)

        self._layout.addWidget(_make_vline())

        self.view_profile_btn = self._make_button(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView),
            "Perfil de Datos",
            icon_size
        )
        self.view_profile_btn.setEnabled(False)
        self._layout.addWidget(self.view_profile_btn)

        self._layout.addWidget(_make_vline())

        self.view_visualizer_btn = self._make_button(
            QIcon(str(get_asset_path("chart.svg"))),
            "Visualizador Rápido",
            icon_size
        )
        self.view_visualizer_btn.setEnabled(False)
        self._layout.addWidget(self.view_visualizer_btn)

    @staticmethod
    def _make_button(icon, tooltip: str, icon_size: QSize) -> QPushButton:  # type: ignore[no-untyped-def]
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setIconSize(icon_size)
        btn.setToolTip(tooltip)
        btn.setFlat(True)
        btn.setFixedSize(30, 28)
        btn.setStyleSheet("""
            QPushButton {
                border: 1px solid transparent;
                border-radius: 2px;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #e0e4e8;
                border-color: #b0b4b8;
            }
            QPushButton:pressed {
                background-color: #cdd2d6;
            }
            QPushButton:disabled {
                border: 1px solid transparent;
            }
        """)
        return btn

    def _connect_signals(self) -> None:
        self.view_main_btn.clicked.connect(self.view_main.emit)
        self.view_data_btn.clicked.connect(self.view_data.emit)
        self.view_info_btn.clicked.connect(self.view_info.emit)
        self.view_joined_btn.clicked.connect(self.view_joined.emit)
        self.view_pivot_btn.clicked.connect(self.view_pivot.emit)
        self.view_profile_btn.clicked.connect(self.view_profile.emit)
        self.view_visualizer_btn.clicked.connect(self.view_visualizer.emit)

    def set_joined_enabled(self, enabled: bool) -> None:
        self.view_joined_btn.setEnabled(enabled)

    def set_main_enabled(self, enabled: bool) -> None:
        self.view_main_btn.setEnabled(enabled)

    def set_data_enabled(self, enabled: bool) -> None:
        self.view_data_btn.setEnabled(enabled)

    def set_info_enabled(self, enabled: bool) -> None:
        self.view_info_btn.setEnabled(enabled)

    def set_pivot_enabled(self, enabled: bool) -> None:
        self.view_pivot_btn.setEnabled(enabled)

    def set_profile_enabled(self, enabled: bool) -> None:
        self.view_profile_btn.setEnabled(enabled)

    def set_visualizer_enabled(self, enabled: bool) -> None:
        self.view_visualizer_btn.setEnabled(enabled)
