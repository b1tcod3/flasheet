"""
Exportadores por formato.

Cada módulo expone una función `exportar_a_<formato>(df, filepath, ...) -> bool`
sin dependencias de la UI.
"""

from .csv import exportar_a_csv
from .image import exportar_a_imagen
from .pdf import exportar_a_pdf
from .sql import exportar_a_sql
from .xlsx import exportar_a_xlsx

__all__ = [
    'exportar_a_csv',
    'exportar_a_imagen',
    'exportar_a_pdf',
    'exportar_a_sql',
    'exportar_a_xlsx',
]
