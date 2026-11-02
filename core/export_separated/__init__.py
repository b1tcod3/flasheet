"""
Exportación separada por columna usando plantillas Excel.
"""

from .config import ExportResult, ExportSeparatedConfig, ValidationResult
from .service import exportar_datos_separados
from .splitter import ExcelTemplateSplitter

__all__ = [
    'ExportResult',
    'ExportSeparatedConfig',
    'ExcelTemplateSplitter',
    'ValidationResult',
    'exportar_datos_separados',
]
