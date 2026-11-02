#!/usr/bin/env python3
"""
Wiring de vistas: registro, coordinador y toolbar deben usar los mismos IDs.

Regresión: la toolbar y los menús usaban índices literales (0, 1, 3) en lugar
de `ViewRegistry.VIEW_*`, por lo que cambiar el orden de creación de vistas
rompía la navegación en silencio.
"""

from PySide6.QtWidgets import QMainWindow

from app.toolbar.toolbar_manager import ToolbarManager
from app.view_manager.view_coordinator import ViewCoordinator
from app.view_manager.view_registry import ViewRegistry

ALL_VIEWS = [
    ViewRegistry.VIEW_MAIN,
    ViewRegistry.VIEW_DATA,
    ViewRegistry.VIEW_JOIN,
    ViewRegistry.VIEW_PIVOT,
    ViewRegistry.VIEW_PROFILING,
    ViewRegistry.VIEW_VISUALIZER,
]


class _FakeCoordinator:
    """Coordinador mínimo: solo registra las llamadas de la toolbar."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def mostrar_info(self) -> None:
        self.calls.append('mostrar_info')

    def auto_pivot(self) -> None:
        self.calls.append('auto_pivot')

    def exportar_datos_separados(self) -> None:
        self.calls.append('exportar_datos_separados')


def test_registry_has_no_dangling_views() -> None:
    for view_id in ALL_VIEWS:
        assert ViewRegistry.is_valid_view(view_id)
        assert ViewRegistry.get_view_name(view_id) != f"Vista {view_id}"


def test_every_registered_view_can_be_shown() -> None:
    window = QMainWindow()
    coordinator = ViewCoordinator(window)
    coordinator.create_views(window)

    for view_id in ALL_VIEWS:
        assert coordinator.switch_to(view_id) is True
        assert coordinator.get_current_view() == view_id


def test_toolbar_switcher_reaches_data_view() -> None:
    window = QMainWindow()
    view_coordinator = ViewCoordinator(window)
    view_coordinator.create_views(window)

    toolbar = ToolbarManager(window)
    toolbar.set_coordinators(view_coordinator, _FakeCoordinator())
    toolbar.create_toolbar()

    assert toolbar.view_switcher is not None
    toolbar.view_switcher.view_data.emit()

    assert view_coordinator.get_current_view() == ViewRegistry.VIEW_DATA


def test_toolbar_pivot_button_requests_pivot() -> None:
    window = QMainWindow()
    view_coordinator = ViewCoordinator(window)
    view_coordinator.create_views(window)

    fake = _FakeCoordinator()
    toolbar = ToolbarManager(window)
    toolbar.set_coordinators(view_coordinator, fake)
    toolbar.create_toolbar()

    assert toolbar.view_switcher is not None
    toolbar.view_switcher.view_pivot.emit()

    assert fake.calls == ['auto_pivot']


def test_toolbar_enables_join_and_separar_with_data() -> None:
    window = QMainWindow()
    view_coordinator = ViewCoordinator(window)
    view_coordinator.create_views(window)

    toolbar = ToolbarManager(window)
    toolbar.set_coordinators(view_coordinator, _FakeCoordinator())
    toolbar.create_toolbar()

    toolbar.on_datos_disponibles(False)
    assert toolbar.separar_btn is not None
    assert toolbar.separar_btn.isEnabled() is False

    toolbar.on_datos_disponibles(True)
    assert toolbar.separar_btn.isEnabled() is True
