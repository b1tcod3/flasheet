"""
Servicio de Tablas Pivote - PivotService

Servicio para operaciones de tablas pivote automáticas.
"""

import logging

import logging
from typing import Any, Callable

import pandas as pd
from pandas.api.types import is_numeric_dtype
from PySide6.QtCore import Signal

from app.services.task_thread import TaskThread

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

MAX_PIVOT_TABS = 5


class PivotService:
    """
    Servicio para operaciones de tablas pivote.
    """

    def __init__(self) -> None:
        self.last_result: pd.DataFrame | None = None

    def cleanup(self) -> None:
        self.last_result = None

    @staticmethod
    def detect_categorical_columns(df: pd.DataFrame) -> list[str]:
        """Solo columnas con ≤20 valores únicos."""
        return [c for c in df.columns if df[c].nunique() <= 20]

    @staticmethod
    def detect_numeric_columns(df: pd.DataFrame) -> list[str]:
        """Detectar columnas numéricas."""
        return [c for c in df.columns if is_numeric_dtype(df[c])]

    @staticmethod
    def rank_combinations(df: pd.DataFrame, cat_cols: list[str], num_cols: list[str]) -> list[tuple[str, str, int]]:
        """
        Rankear combinaciones categórica × numérica por volumen de datos.
        Retorna lista de (cat, num, score) ordenada de mayor a menor.
        """
        combos = []
        for cat in cat_cols:
            for num in num_cols:
                score = int(df[num].notna().sum())
                combos.append((cat, num, score))
        combos.sort(key=lambda x: x[2], reverse=True)
        return combos

    def generate_auto_pivots(
        self,
        df: pd.DataFrame,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """
        Generar tablas pivote automáticas (máximo MAX_PIVOT_TABS)
        para las combinaciones con más datos.
        """
        cat_cols = self.detect_categorical_columns(df)
        num_cols = self.detect_numeric_columns(df)

        logger.debug("Columnas categóricas detectadas: %s", cat_cols)
        logger.debug("Columnas numéricas detectadas: %s", num_cols)

        combos = self.rank_combinations(df, cat_cols, num_cols)
        top_combos = combos[:MAX_PIVOT_TABS]

        logger.debug("Top %s combinaciones: %s", len(top_combos), [(c, n) for c, n, _ in top_combos])

        results: dict[str, pd.DataFrame] = {}
        total = len(top_combos)
        idx = 0

        for cat, num, _ in top_combos:
            try:
                pivot_df = pd.pivot_table(
                    df, index=cat, values=num,
                    aggfunc=['count', 'nunique', 'sum'],
                    margins=False, dropna=True
                )

                if len(pivot_df.columns) == 3:
                    pivot_df.columns = ['conteo', 'conteo_unico', 'suma']
                else:
                    pivot_df.columns = ['_'.join(map(str, col)).strip() for col in pivot_df.columns]

                pivot_df = pivot_df.reset_index()

                totals = {pivot_df.columns[0]: 'Total'}
                for col in pivot_df.columns[1:]:
                    totals[col] = pivot_df[col].sum()
                pivot_df = pd.concat([pivot_df, pd.DataFrame([totals])], ignore_index=True)

                name = f"{cat} × {num}"
                results[name] = pivot_df

            except Exception as e:
                logger.error("Error generando pivote para %s × %s: %s", cat, num, e)

            idx += 1
            if progress_callback:
                progress_callback(idx, total)

        if results:
            first_key = next(iter(results))
            self.last_result = results[first_key]
        else:
            logger.warning("No se generó ningún resultado pivote.")

        return results

    def get_pivot_stats(self) -> dict[str, Any] | None:
        if self.last_result is None:
            return None
        return {
            'rows': len(self.last_result),
            'columns': len(self.last_result.columns),
            'shape': self.last_result.shape,
        }


class PivotWorkerThread(TaskThread):
    """Genera las tablas pivote fuera del hilo de la interfaz.

    Señales:
        progress(int, int): (completadas, total).
        results_ready(object): Dict nombre -> DataFrame con las tablas.
        error(str): Mensaje de error si falla el cálculo.
    """

    progress = Signal(int, int)
    results_ready = Signal(object)
    error = Signal(str)

    def __init__(self, df: pd.DataFrame, service: PivotService) -> None:
        super().__init__()
        self._df = df
        self._service = service

    def execute(self) -> object:
        return self._service.generate_auto_pivots(
            self._df, progress_callback=self._report_progress
        )

    def _report_progress(self, current: int, total: int) -> None:
        if not self.isInterruptionRequested():
            self.progress.emit(current, total)

    def _emit_result(self, result: object) -> None:
        self.results_ready.emit(result)

    def _emit_error(self, message: str) -> None:
        self.error.emit(message)


__all__ = ['MAX_PIVOT_TABS', 'PivotService', 'PivotWorkerThread']
