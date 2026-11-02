"""
Flash View Sheet - Paquete Principal de la Aplicación

Este módulo export los componentes principales de la aplicación.
"""

# Servicios
from app.services import (
    DataService,
    ExportService,
    FilterService,
    PivotService,
)

# Widgets
from app.widgets import (
    MainView,
    InfoModal,
    DataView,
)

__version__ = "1.1.0"

__all__ = [
    # Servicios
    'DataService',
    'ExportService',
    'FilterService',
    'PivotService',
    
    # Widgets
    'MainView',
    'InfoModal',
    'DataView',
]
