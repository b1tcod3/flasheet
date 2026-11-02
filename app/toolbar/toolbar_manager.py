"""
Toolbar Manager for Flash View Sheet.

This module manages the main toolbar creation and coordination.
"""

from PySide6.QtWidgets import QToolBar, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtGui import QIcon

from app.resources import get_asset_path
from app.view_manager.view_registry import ViewRegistry
from typing import TYPE_CHECKING

from app.toolbar.view_switcher import ViewSwitcher

if TYPE_CHECKING:
    from app.view_manager import ViewCoordinator
    from app.app_coordinator import AppCoordinator


class ToolbarManager:
    """
    Manages the main toolbar for the application.

    Responsibilities:
    - Create and configure the main toolbar
    - Manage view switcher buttons
    - Coordinate toolbar components
    """

    def __init__(self, main_window: QWidget) -> None:
        self.main_window = main_window
        self.tool_bar: QToolBar | None = None
        self.view_switcher: ViewSwitcher | None = None
        self.separar_btn: QPushButton | None = None
        self.view_coordinator: 'ViewCoordinator' | None = None
        self.coordinator: 'AppCoordinator' | None = None
        self.buttons_layout: QHBoxLayout | None = None

    def set_coordinators(self, view_coordinator: 'ViewCoordinator', coordinator: 'AppCoordinator') -> None:
        self.view_coordinator = view_coordinator
        self.coordinator = coordinator

    def create_toolbar(self) -> QToolBar:
        self.tool_bar = QToolBar("Herramientas")
        self.tool_bar.setMovable(False)
        self.tool_bar.setFloatable(False)
        self.tool_bar.setStyleSheet("""
            QToolBar {
                background: transparent;
                border: none;
                spacing: 6px;
            }
        """)

        ribbon_wrapper = QWidget()
        ribbon_layout = QHBoxLayout(ribbon_wrapper)
        ribbon_layout.setContentsMargins(0, 0, 0, 0)
        ribbon_layout.setSpacing(8)

        ribbon_layout.addWidget(self._create_herramientas_section())

        self.tool_bar.addWidget(ribbon_wrapper)
        return self.tool_bar

    @staticmethod
    def _create_section_frame(title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("RibbonSection")
        frame.setStyleSheet("""
            QFrame#RibbonSection {
                background-color: #f5f6f7;
                border: 1px solid #c0c2c4;
                border-bottom: 2px solid #a8a8a8;
                border-radius: 3px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #2b579a;
            font-family: Arial, sans-serif;
            font-size: 11px;
            font-weight: bold;
            border: none;
        """)
        layout.addWidget(title_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #d4d4d4; max-height: 1px; border: none;")
        layout.addWidget(separator)

        return frame

    def _create_herramientas_section(self) -> QFrame:
        section = self._create_section_frame("Herramientas")

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 2, 0, 0)
        self.buttons_layout.setSpacing(6)

        self._create_view_switcher()

        self._create_separar_button()

        quit_btn = QPushButton()
        quit_btn.setIcon(QIcon(str(get_asset_path("power.svg"))))
        quit_btn.setToolTip("Salir")
        quit_btn.setFixedSize(28, 28)
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
                color: #334155;
            }
            QPushButton:hover { background-color: #e2e8f0; }
            QPushButton:pressed { background-color: #cbd5e1; }
        """)
        quit_btn.clicked.connect(self.main_window.close)
        self.buttons_layout.addWidget(quit_btn)

        self.buttons_layout.addStretch()
        section_layout = section.layout()
        assert isinstance(section_layout, QVBoxLayout)
        section_layout.addLayout(self.buttons_layout)

        return section

    def _create_view_switcher(self) -> None:
        self.view_switcher = ViewSwitcher(self.main_window)

        self.view_switcher.view_main.connect(
            lambda: self._on_view_switch(ViewRegistry.VIEW_MAIN))
        self.view_switcher.view_data.connect(
            lambda: self._on_view_switch(ViewRegistry.VIEW_DATA))
        self.view_switcher.view_joined.connect(
            lambda: self._on_view_switch(ViewRegistry.VIEW_JOIN))
        self.view_switcher.view_pivot.connect(self._on_pivot_requested)
        self.view_switcher.view_info.connect(self._on_info_requested)
        self.view_switcher.view_profile.connect(self._on_profile_requested)
        self.view_switcher.view_visualizer.connect(self._on_visualizer_requested)

        if self.buttons_layout is not None:
            self.buttons_layout.addWidget(self.view_switcher)

    def _on_view_switch(self, index: int) -> None:
        if self.view_coordinator:
            self.view_coordinator.switch_to(index)

    def _on_info_requested(self) -> None:
        if self.coordinator:
            self.coordinator.mostrar_info()

    def _on_pivot_requested(self) -> None:
        if self.coordinator:
            self.coordinator.auto_pivot()

    def _on_profile_requested(self) -> None:
        if self.view_coordinator:
            self.view_coordinator.switch_to(ViewRegistry.VIEW_PROFILING)

    def _on_visualizer_requested(self) -> None:
        if self.view_coordinator:
            self.view_coordinator.switch_to(ViewRegistry.VIEW_VISUALIZER)

    def _create_separar_button(self) -> None:
        self.separar_btn = QPushButton()
        self.separar_btn.setIcon(QIcon(str(get_asset_path("split.svg"))))
        self.separar_btn.setToolTip("Separar datos por columna")
        self.separar_btn.setFixedSize(28, 28)
        self.separar_btn.setEnabled(False)
        self.separar_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
                color: #334155;
            }
            QPushButton:hover { background-color: #e2e8f0; }
            QPushButton:pressed { background-color: #cbd5e1; }
            QPushButton:disabled { border: 1px solid transparent; }
        """)
        self.separar_btn.clicked.connect(self._on_separar_requested)
        if self.buttons_layout is not None:
            self.buttons_layout.addWidget(self.separar_btn)

    def _on_separar_requested(self) -> None:
        if self.coordinator:
            self.coordinator.exportar_datos_separados()

    def set_view_buttons_enabled(self, enabled: bool) -> None:
        if self.view_switcher:
            self.view_switcher.set_joined_enabled(enabled)

    def on_datos_disponibles(self, has_data: bool) -> None:
        self.set_view_buttons_enabled(has_data)
        if self.view_switcher:
            self.view_switcher.set_pivot_enabled(has_data)
            self.view_switcher.set_profile_enabled(has_data)
            self.view_switcher.set_visualizer_enabled(has_data)
        if self.separar_btn:
            self.separar_btn.setEnabled(has_data)

    def get_toolbar(self) -> QToolBar | None:
        return self.tool_bar
