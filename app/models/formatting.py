"""
Formato de valores para mostrarlos en la tabla.

El modelo Qt no debe decidir cómo se representa un número o una fecha: esta
función aísla esa política para poder probarla y cambiarla sin tocar el modelo.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

DEFAULT_DECIMAL_SEPARATOR = ','


def format_cell(value: Any, decimal_separator: str = DEFAULT_DECIMAL_SEPARATOR) -> str:
    """Convertir un valor de celda a texto.

    - Nulos y NaN -> cadena vacía
    - Infinitos -> cadena vacía
    - Floats enteros -> sin decimales
    - Resto de floats -> con el separador decimal indicado
    """
    if _is_missing(value):
        return ""

    if isinstance(value, float):
        if math.isinf(value):
            return ""
        if value == int(value):
            return str(int(value))
        return str(value).replace('.', decimal_separator)

    return str(value)


def _is_missing(value: Any) -> bool:
    """`pd.isna` seguro para valores no escalares (listas, arrays)."""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
