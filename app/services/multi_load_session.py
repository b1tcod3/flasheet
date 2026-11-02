"""
Estado de una carga múltiple de archivos.

Encapsula los contadores y los DataFrames pendientes para que el coordinador
no tenga que mantener cinco campos sueltos ni recalcular el progreso a mano.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class MultiLoadSession:
    """Carga en paralelo de varios archivos que se consolidan al finalizar."""

    paths: list[str]
    frames: list[pd.DataFrame] = field(default_factory=list)
    completed: int = 0
    errors: int = 0

    @property
    def total(self) -> int:
        return len(self.paths)

    @property
    def successful(self) -> int:
        return len(self.frames)

    def register_success(self, df: pd.DataFrame) -> None:
        """Registrar un archivo cargado correctamente."""
        self.frames.append(df)
        self.completed += 1

    def register_error(self) -> None:
        """Registrar un archivo que falló."""
        self.errors += 1
        self.completed += 1

    def is_complete(self) -> bool:
        """True cuando ya se procesaron todos los archivos pedidos."""
        return self.completed >= self.total

    def consolidate(self) -> pd.DataFrame | None:
        """Concatenar los DataFrames cargados, o None si no hubo ninguno."""
        if not self.frames:
            return None
        return pd.concat(self.frames, ignore_index=True)
