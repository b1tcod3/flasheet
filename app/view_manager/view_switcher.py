"""
View Switcher

Maneja la lógica de cambio entre vistas.
Provides methods to switch between different views in the application.
"""

from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QStackedWidget

from .view_registry import ViewRegistry


class ViewSwitcher(QObject):
    """Manejador de cambio de vistas.

    Trabaja siempre con identificadores de `ViewRegistry`; la traducción al
    índice del QStackedWidget vive aquí y en un solo sentido.
    """

    # Señales (emiten IDs de ViewRegistry)
    view_changed = Signal(int)  # Emitido cuando cambia la vista
    view_about_to_change = Signal(int, int)  # (vista_actual, vista_nueva)

    def __init__(self, stacked_widget: QStackedWidget | None = None) -> None:
        super().__init__()
        self._stacked_widget = stacked_widget
        self._current_view = ViewRegistry.VIEW_MAIN
        self._view_history: list[int] = []
        self._registry_to_index: dict[int, int] = {}
        self._index_to_registry: dict[int, int] = {}

    def set_stacked_widget(self, stacked_widget: QStackedWidget | None) -> None:
        """Establecer el widget stacked"""
        self._stacked_widget = stacked_widget
        if stacked_widget:
            self._sync_current_view()

    def set_view_mapping(self, registry_to_index: dict[int, int]) -> None:
        """Establecer el mapeo ViewRegistry ID → índice del stacked widget."""
        self._registry_to_index = dict(registry_to_index)
        self._index_to_registry = {
            index: view_id for view_id, index in self._registry_to_index.items()
        }

    def set_index_mapping(self, index_to_registry: dict[int, int]) -> None:
        """Compatibilidad: mapeo índice del stacked → ViewRegistry ID."""
        self._index_to_registry = dict(index_to_registry)
        self._registry_to_index = {
            view_id: index for index, view_id in self._index_to_registry.items()
        }

    def get_current_view(self) -> int:
        """Obtener el ID de ViewRegistry de la vista actual"""
        return self._current_view

    def switch_to(self, view_id: int) -> bool:
        """Cambiar a la vista indicada por su ID de ViewRegistry

        Args:
            view_id: Identificador de `ViewRegistry`

        Returns:
            bool: True si el cambio fue exitoso
        """
        if not self._stacked_widget:
            return False

        index = self._registry_to_index.get(view_id)
        if index is None or index < 0 or index >= self._stacked_widget.count():
            return False

        # Emitir señal antes del cambio
        self.view_about_to_change.emit(self._current_view, view_id)

        # Realizar el cambio
        self._stacked_widget.setCurrentIndex(index)
        self._current_view = view_id
        self._view_history.append(view_id)

        # Limitar historial a 20 elementos
        if len(self._view_history) > 20:
            self._view_history.pop(0)

        # Emitir señal después del cambio
        self.view_changed.emit(view_id)

        return True

    def _sync_current_view(self) -> None:
        """Alinear el ID actual con el índice que muestra el stacked widget."""
        if not self._stacked_widget:
            return
        index = self._stacked_widget.currentIndex()
        self._current_view = self._index_to_registry.get(index, ViewRegistry.VIEW_MAIN)
    
    def switch_to_main(self) -> bool:
        """Cambiar a la vista principal"""
        return self.switch_to(ViewRegistry.VIEW_MAIN)
    
    def switch_to_data(self) -> bool:
        """Cambiar a la vista de datos"""
        return self.switch_to(ViewRegistry.VIEW_DATA)
    
    def switch_to_join(self) -> bool:
        """Cambiar a la vista de join"""
        return self.switch_to(ViewRegistry.VIEW_JOIN)
    
    def switch_to_pivot(self) -> bool:
        """Cambiar a la vista de pivote"""
        return self.switch_to(ViewRegistry.VIEW_PIVOT)
    
    def get_view_name(self) -> str:
        """Obtener nombre de la vista actual"""
        return ViewRegistry.get_view_name(self._current_view)
    
    def get_view_history(self) -> list:
        """Obtener historial de vistas visitadas"""
        return self._view_history.copy()
    
    def can_go_back(self) -> bool:
        """Verificar si se puede volver a la vista anterior"""
        return len(self._view_history) > 1
    
    def go_back(self) -> bool:
        """Volver a la vista anterior
        
        Returns:
            bool: True si se pudo volver
        """
        if not self.can_go_back():
            return False
        
        # Remover el actual del historial
        self._view_history.pop()
        # La vista anterior es el último elemento
        previous_view = self._view_history[-1]
        return self.switch_to(previous_view)
