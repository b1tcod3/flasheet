"""
ProfilerService: Perfilado de datos de un DataFrame.

Calcula estadísticas por columna (tipo, nulos, cardinalidad, métricas
numéricas, valores más frecuentes y distribución de valores) sin mutar
el DataFrame de entrada. El cálculo es stateless, tolerante a fallos por
columna y reporta progreso mediante un callback opcional. Se ejecuta en
segundo plano mediante ProfilerWorkerThread para no bloquear la interfaz.
"""

from typing import Any, Callable

import pandas as pd
from PySide6.QtCore import Signal

from app.services.task_thread import TaskThread
from core.data_handler import obtener_estadisticas_basicas

_MAX_TOP_VALUES_UNIQUE = 1000
_TOP_VALUES_COUNT = 5
_HIGH_CARDINALITY_RATIO = 0.9
_HIGH_NULL_PERCENT = 50.0
_PROGRESS_START = 5
_PROGRESS_END = 95


class ProfilerService:
    """Servicio stateless para el perfilado de datos.

    Cada llamada recibe el DataFrame como parámetro; el servicio no
    mantiene estado entre llamadas ni modifica el DataFrame recibido.
    """

    def generate_profile(
        self,
        df: pd.DataFrame,
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict[str, Any]:
        """Generar el perfil completo del DataFrame.

        Args:
            df: DataFrame a perfilar.
            progress_callback: Función opcional para reportar el progreso
                (0-100) columna a columna.

        Returns:
            Diccionario con métricas generales del dataset, un perfil por
            cada columna y un resumen de calidad de datos.
        """
        if df is None or len(df) == 0:
            if progress_callback:
                progress_callback(100)
            return self._empty_profile(df)

        total_rows = len(df)
        total_columns = len(df.columns)

        basic = obtener_estadisticas_basicas(df)
        memory_usage_mb = float(basic.get('memoria_uso_mb', 0.0))
        duplicated_rows = int(basic.get('filas_duplicadas', 0))

        columns: dict[str, dict[str, Any]] = {}
        high_cardinality_columns = 0
        high_null_columns = 0

        for i, col in enumerate(df.columns):
            if progress_callback:
                progress_callback(int(_PROGRESS_START + (i / total_columns) * (_PROGRESS_END - _PROGRESS_START)))

            try:
                col_profile = self._profile_column(df, col, total_rows)
                if col_profile.get('unique_count', 0) / total_rows > _HIGH_CARDINALITY_RATIO:
                    high_cardinality_columns += 1
                if col_profile.get('null_percent', 0.0) > _HIGH_NULL_PERCENT:
                    high_null_columns += 1
            except Exception as e:
                col_profile = {
                    'error': True,
                    'error_msg': f"Fallo al perfilar: {e}",
                }
            columns[str(col)] = col_profile

        if progress_callback:
            progress_callback(100)

        quality = self._quality_summary(df, total_rows, total_columns, duplicated_rows,
                                        high_cardinality_columns, high_null_columns)

        return {
            'total_rows': total_rows,
            'total_columns': total_columns,
            'memory_usage_mb': memory_usage_mb,
            'duplicated_rows': duplicated_rows,
            'data_quality_summary': quality,
            'columns': columns,
        }

    @staticmethod
    def _empty_profile(df: pd.DataFrame | None) -> dict[str, Any]:
        return {
            'total_rows': 0,
            'total_columns': 0 if df is None else len(df.columns),
            'memory_usage_mb': 0.0,
            'duplicated_rows': 0,
            'data_quality_summary': {},
            'columns': {},
        }

    @staticmethod
    def _quality_summary(
        df: pd.DataFrame,
        total_rows: int,
        total_columns: int,
        duplicated_rows: int,
        high_cardinality_columns: int,
        high_null_columns: int,
    ) -> dict[str, Any]:
        """Resumen ligero de calidad reutilizando métricas ya calculadas."""
        null_cells = int(df.isna().sum().sum())
        null_percent = _safe_percent(null_cells, total_rows * total_columns)
        duplicate_percent = _safe_percent(duplicated_rows, total_rows)
        overall_quality_score = max(0.0, round(100.0 - null_percent - duplicate_percent, 1))
        return {
            'null_percent': null_percent,
            'duplicate_percent': duplicate_percent,
            'high_cardinality_columns': high_cardinality_columns,
            'high_null_columns': high_null_columns,
            'overall_quality_score': overall_quality_score,
        }

    def _profile_column(self, df: pd.DataFrame, col: Any, total_rows: int) -> dict[str, Any]:
        series = df[col]
        null_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))

        profile: dict[str, Any] = {
            'dtype': self._get_detailed_type(series),
            'null_count': null_count,
            'null_percent': _safe_percent(null_count, total_rows),
            'unique_count': unique_count,
            'unique_percent': _safe_percent(unique_count, total_rows),
            'numeric_stats': None,
            'date_range': None,
            'top_values': None,
            'value_distribution': None,
        }

        if pd.api.types.is_numeric_dtype(series):
            profile['numeric_stats'] = self._numeric_stats(series)

        if pd.api.types.is_datetime64_any_dtype(series.dtype):
            profile['date_range'] = self._date_range(series)

        if unique_count <= _MAX_TOP_VALUES_UNIQUE:
            profile['top_values'] = self._top_values(series)
        elif pd.api.types.is_numeric_dtype(series):
            profile['value_distribution'] = self._value_distribution_numeric(series)
        elif pd.api.types.is_datetime64_any_dtype(series.dtype):
            profile['value_distribution'] = self._value_distribution_datetime(series)

        return profile

    @staticmethod
    def _get_detailed_type(series: pd.Series) -> str:
        """Descripción legible del tipo de dato de la columna."""
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_integer_dtype(series):
            return "integer"
        if pd.api.types.is_float_dtype(series):
            return "float"
        if pd.api.types.is_datetime64_any_dtype(series.dtype):
            return "datetime"
        if pd.api.types.is_string_dtype(series):
            return "string"
        if pd.api.types.is_object_dtype(series):
            inferred = pd.api.types.infer_dtype(series, skipna=True)
            mapping = {
                'string': 'string',
                'boolean': 'boolean',
                'integer': 'integer',
                'floating': 'float',
                'datetime': 'datetime',
                'date': 'date',
                'empty': 'empty',
                'mixed': 'mixed',
            }
            return str(mapping.get(inferred, inferred))
        return str(series.dtype)

    @staticmethod
    def _numeric_stats(series: pd.Series) -> dict[str, float] | None:
        """Métricas numéricas (min, max, media, mediana, std, cuartiles)."""
        if series.count() == 0:
            return None
        try:
            stats = series.describe(percentiles=[0.25, 0.5, 0.75])
            return {
                'count': int(stats['count']),
                'min': _to_native(stats.get('min')),
                'max': _to_native(stats.get('max')),
                'mean': _to_native(stats.get('mean')),
                'median': _to_native(stats.get('50%')),
                'std': _to_native(stats.get('std')),
                'q25': _to_native(stats.get('25%')),
                'q75': _to_native(stats.get('75%')),
            }
        except (TypeError, ValueError, KeyError):
            return None

    @staticmethod
    def _date_range(series: pd.Series) -> dict[str, Any] | None:
        """Rango temporal de columnas datetime."""
        valid = series.dropna()
        if valid.empty:
            return None
        try:
            return {
                'min': _to_native(valid.min()),
                'max': _to_native(valid.max()),
                'days_span': int((valid.max() - valid.min()).days),
            }
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _top_values(series: pd.Series) -> list[list[Any]]:
        """Valores más frecuentes (hasta 5), pares [valor, conteo]."""
        try:
            counts = series.dropna().value_counts()
            if counts.empty:
                return []
            top = counts.head(_TOP_VALUES_COUNT)
            return [[_to_native(idx), int(count)] for idx, count in top.items()]
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _value_distribution_numeric(series: pd.Series) -> list[list[Any]]:
        """Distribución en bins para columnas numéricas de alta cardinalidad."""
        try:
            valid = series.dropna()
            if valid.empty:
                return []
            min_val = valid.min()
            max_val = valid.max()
            if min_val == max_val:
                return [[str(min_val), int(valid.count())]]

            data_range = max_val - min_val
            if data_range > 10000:
                num_bins = 20
            elif data_range > 1000:
                num_bins = 15
            else:
                num_bins = 10

            bins = pd.cut(valid, bins=num_bins, include_lowest=True)
            counts = bins.value_counts().sort_index()

            return [
                [f"{interval.left:.2f}-{interval.right:.2f}", int(count)]
                for interval, count in counts.items()
            ]
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _value_distribution_datetime(series: pd.Series) -> list[list[Any]]:
        """Distribución por mes para columnas datetime de alta cardinalidad."""
        try:
            valid = series.dropna()
            if valid.empty:
                return []
            monthly = valid.dt.to_period('M').value_counts().sort_index()
            return [
                [str(period.start_time.date()), int(count)]
                for period, count in monthly.items()
            ][:_TOP_VALUES_COUNT]
        except (TypeError, ValueError):
            return []


class ProfilerWorkerThread(TaskThread):
    """Hilo para calcular el perfil sin bloquear la interfaz.

    Señales:
        progress(int): Porcentaje de progreso (0-100).
        finished(object): Diccionario con el perfil completo.
        error(str): Mensaje de error si falla el cálculo.
    """

    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__()
        self.df = df

    def execute(self) -> object:
        """Calcular el perfil reportando progreso mientras se recorre."""
        self.progress.emit(0)
        profiler = ProfilerService()

        def _report_progress(percent: int) -> None:
            if not self.isInterruptionRequested():
                self.progress.emit(percent)

        return profiler.generate_profile(self.df, progress_callback=_report_progress)

    def _emit_result(self, result: object) -> None:
        self.finished.emit(result)

    def _emit_error(self, message: str) -> None:
        self.error.emit(message)


def _safe_percent(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total * 100, 2)


def _to_native(value: Any) -> Any:
    """Convertir numpy scalars / Timestamps a tipos nativos de Python."""
    try:
        if value is None or pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return value.total_seconds()
    if hasattr(value, 'item'):
        try:
            item = value.item()
        except (ValueError, AttributeError):
            item = value
        return _to_native(item)
    return value


__all__ = ['ProfilerService', 'ProfilerWorkerThread', '_safe_percent', '_to_native']
