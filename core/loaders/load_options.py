"""
Opciones de carga compartidas por todos los loaders.

Un único objeto de opciones evita que cada loader amplíe la firma de `load()`
con sus propios parámetros, lo que rompía la substitución (LSP) y obligaba a
quien llama a hacer `isinstance` por formato.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LoadOptions:
    """Opciones de lectura aplicables a cualquier formato.

    Cada loader usa solo las que entiende e ignora el resto, de modo que el
    llamante puede construir un único objeto sin conocer el formato.
    """

    skip_rows: int = 0
    column_names: dict[str, str] = field(default_factory=dict)
    separator: str | None = None
    sheet_name: str | None = None
    table_name: str | None = None
    chunk_size: int = 1000
