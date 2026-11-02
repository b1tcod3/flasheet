"""
FilterService - pure filtering operations for DataFrames.

Single source of truth for filtering semantics in the application.
It has no Qt dependency: `PaginationManager` composes it and the UI only
translates the resulting DataFrame into widgets.

Contract: the returned DataFrame is a new object when rows are filtered out;
the input DataFrame is never mutated.
"""

from __future__ import annotations

import operator
from typing import Any, Callable

import pandas as pd


class FilterError(ValueError):
    """Raised when a filter cannot be applied."""


class ColumnNotFoundError(FilterError):
    """Raised when the target column does not exist in the DataFrame."""


_NUMERIC_OPERATORS: dict[str, Callable[[Any, Any], Any]] = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
}


class FilterService:
    """
    Stateless filtering strategies plus an optional history of applied filters.

    Responsibilities:
    - Apply text, regex, numeric, date and value-list filters.
    - Keep a trace of applied filters for reporting.

    It does not own the data: every method receives the DataFrame to filter.
    """

    def __init__(self) -> None:
        self.filter_history: list[dict[str, Any]] = []

    # ==================== TEXT ====================

    def apply_text_filter(
        self,
        df: pd.DataFrame,
        column: str,
        term: str,
        case_sensitive: bool = False,
        record: bool = True,
    ) -> pd.DataFrame:
        """Filter rows whose `column` contains `term` as literal text."""
        self._require_column(df, column)

        if not term:
            return df

        # Se filtra sobre los no nulos: `astype(str)` convertiría NaN en "nan",
        # que coincidiría con búsquedas de texto que contengan "a" o "n".
        column_values = df[column]
        mask = column_values.notna() & column_values.astype(str).str.contains(
            term, case=case_sensitive, regex=False, na=False
        )
        filtered = df[mask]
        self._record({
            'column': column,
            'term': term,
            'case_sensitive': case_sensitive,
            'type': 'text',
            'original_rows': len(df),
            'filtered_rows': len(filtered),
        }, record)
        return filtered

    def apply_filter(
        self,
        df: pd.DataFrame,
        column: str,
        term: str,
        case_sensitive: bool = False,
        record: bool = True,
    ) -> pd.DataFrame:
        """Backwards-compatible alias for `apply_text_filter`."""
        return self.apply_text_filter(
            df, column, term, case_sensitive=case_sensitive, record=record
        )

    def apply_regex_filter(self, df: pd.DataFrame, column: str, pattern: str) -> pd.DataFrame:
        """Filter rows whose `column` matches the regular expression `pattern`."""
        self._require_column(df, column)

        try:
            column_values = df[column]
            mask = column_values.notna() & column_values.astype(str).str.contains(
                pattern, regex=True, na=False
            )
        except Exception as exc:  # invalid regex or non-string dtype
            raise FilterError(f"Patrón regex inválido: {exc}") from exc

        filtered = df[mask]
        self._record({
            'column': column,
            'term': pattern,
            'regex': True,
            'type': 'regex',
            'original_rows': len(df),
            'filtered_rows': len(filtered),
        })
        return filtered

    # ==================== NUMERIC ====================

    def apply_numeric_filter(
        self,
        df: pd.DataFrame,
        column: str,
        op: str,
        value: float,
    ) -> pd.DataFrame:
        """Filter rows comparing `column` against `value` with `op`."""
        self._require_column(df, column)

        compare = _NUMERIC_OPERATORS.get(op)
        if compare is None:
            raise FilterError(
                f"Operador desconocido: '{op}'. "
                f"Válidos: {', '.join(_NUMERIC_OPERATORS)}"
            )

        try:
            threshold = float(value)
        except (TypeError, ValueError) as exc:
            raise FilterError(f"Valor numérico inválido: {value!r}") from exc

        # En columnas object con texto la comparación directa lanzaría TypeError:
        # se coacciona a numérico y se descartan los valores no comparables.
        numeric = pd.to_numeric(df[column], errors='coerce')
        mask = compare(numeric, threshold) & numeric.notna()

        filtered = df[mask]
        self._record({
            'column': column,
            'operator': op,
            'value': threshold,
            'type': 'numeric',
            'original_rows': len(df),
            'filtered_rows': len(filtered),
        })
        return filtered

    # ==================== DATES ====================

    def apply_date_filter(
        self,
        df: pd.DataFrame,
        column: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Filter rows whose `column` falls inside the given date range."""
        self._require_column(df, column)

        try:
            dates = pd.to_datetime(df[column], errors='coerce')
            mask = dates.notna()
            if start_date:
                mask &= dates >= pd.to_datetime(start_date)
            if end_date:
                mask &= dates <= pd.to_datetime(end_date)
        except (TypeError, ValueError) as exc:
            raise FilterError(f"Rango de fechas inválido: {exc}") from exc

        filtered = df[mask]
        self._record({
            'column': column,
            'start_date': start_date,
            'end_date': end_date,
            'type': 'date',
            'original_rows': len(df),
            'filtered_rows': len(filtered),
        })
        return filtered

    # ==================== VALUE LISTS ====================

    def apply_value_filter(
        self,
        df: pd.DataFrame,
        column: str,
        values: list[Any],
        exclude: bool = False,
    ) -> pd.DataFrame:
        """Keep (or exclude) rows whose `column` is one of `values`."""
        self._require_column(df, column)

        mask = df[column].isin(values)
        if exclude:
            mask = ~mask

        filtered = df[mask]
        self._record({
            'column': column,
            'values': values,
            'exclude': exclude,
            'type': 'value_list',
            'original_rows': len(df),
            'filtered_rows': len(filtered),
        })
        return filtered

    # ==================== HISTORY ====================

    def clear_filters(self) -> None:
        """Forget the filter history."""
        self.filter_history = []

    def get_filter_info(self) -> dict[str, Any] | None:
        """Return the last applied filter, if any."""
        return self.filter_history[-1] if self.filter_history else None

    def get_filter_summary(self) -> str:
        """Human readable summary of every applied filter."""
        if not self.filter_history:
            return "No hay filtros aplicados."

        return "\n".join(
            f"{index}. {self._describe(entry)}"
            for index, entry in enumerate(self.filter_history, 1)
        )

    # ==================== COLUMN INSPECTION ====================

    @staticmethod
    def get_unique_values(df: pd.DataFrame, column: str, limit: int = 100) -> list[Any]:
        """Return up to `limit` unique non-null values of `column`."""
        if column not in df.columns:
            return []
        values: list[Any] = list(df[column].dropna().unique())
        return values[:limit]

    @staticmethod
    def get_column_stats(df: pd.DataFrame, column: str) -> dict[str, Any] | None:
        """Descriptive statistics used to build filters."""
        if column not in df.columns:
            return None

        series = df[column]
        stats: dict[str, Any] = {
            'count': len(series),
            'null_count': int(series.isna().sum()),
            'unique_count': int(series.nunique()),
            'dtype': str(series.dtype),
        }

        if pd.api.types.is_numeric_dtype(series):
            stats.update({
                'min': series.min(),
                'max': series.max(),
                'mean': series.mean(),
                'median': series.median(),
            })

        if pd.api.types.is_string_dtype(series):
            stats['empty_count'] = int((series == '').sum())
            stats['avg_length'] = series.astype(str).map(len).mean()

        return stats

    # ==================== INTERNALS ====================

    @staticmethod
    def _require_column(df: pd.DataFrame, column: str) -> None:
        if column not in df.columns:
            raise ColumnNotFoundError(f"La columna '{column}' no existe en el DataFrame")

    def _record(self, entry: dict[str, Any], record: bool = True) -> None:
        if record:
            self.filter_history.append(entry)

    @staticmethod
    def _describe(entry: dict[str, Any]) -> str:
        column = entry.get('column')
        kind = entry.get('type')
        if kind == 'numeric':
            return f"Columna '{column}' {entry['operator']} {entry['value']}"
        if kind == 'date':
            end = entry.get('end_date') or ''
            return f"Columna '{column}' entre {entry.get('start_date') or ''} y {end}".strip()
        if kind == 'value_list':
            action = "excluye" if entry.get('exclude') else "incluye"
            return f"Columna '{column}' {action} {len(entry['values'])} valores"
        return f"Columna '{column}' contiene '{entry.get('term')}'"
