"""
DataJoinManager: Clase principal para operaciones de cruce de datos
"""

import pandas as pd
import time
from datetime import datetime

from .models import JoinConfig, JoinResult, JoinMetadata, ValidationResult, JoinType
from .exceptions import JoinExecutionError, UnsupportedJoinError

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

HOW_MAP = {
    JoinType.INNER: 'inner',
    JoinType.LEFT: 'left',
    JoinType.RIGHT: 'right',
    JoinType.OUTER: 'outer',
}


def safe_sort_values(df: pd.DataFrame, column: str, ascending: bool = True) -> pd.DataFrame:
    """Ordenar por `column` tolerando columnas con tipos mixtos (int + str).

    pandas lanza TypeError al comparar tipos no homogéneos; en ese caso se
    ordena por la representación textual sin alterar los valores.
    """
    try:
        return df.sort_values(
            by=column, ascending=ascending, kind='stable', na_position='last'
        )
    except TypeError:
        keys = df[column].astype(str)
        return df.loc[keys.sort_values(ascending=ascending, kind='stable').index]


class DataJoinManager:
    """Clase principal responsable de ejecutar operaciones de cruce entre datasets"""

    def __init__(self, left_df: pd.DataFrame, right_df: pd.DataFrame) -> None:
        """
        Inicializar DataJoinManager con los datasets

        Args:
            left_df: DataFrame del dataset izquierdo
            right_df: DataFrame del dataset derecho
        """
        self.left_df = left_df.copy()
        self.right_df = right_df.copy()

    def execute_join(self, config: JoinConfig) -> JoinResult:
        """
        Ejecutar operación de join según configuración

        Args:
            config: Configuración del join

        Returns:
            JoinResult con datos y metadatos
        """
        start_time = time.time()

        try:
            validation = self.validate_join(config)
            if not validation.is_valid:
                return JoinResult(
                    data=pd.DataFrame(),
                    metadata=self._create_empty_metadata(config, start_time),
                    config=config,
                    success=False,
                    error_message="; ".join(validation.errors)
                )

            estimated_memory = self._estimate_memory_usage(config)
            available_memory = self._get_available_memory_mb()

            use_chunking = self._should_use_chunking(config, estimated_memory, available_memory)

            try:
                if use_chunking:
                    result_df = self._perform_chunked_join(config)
                else:
                    result_df = self._perform_join(config)
            except Exception as e:
                raise JoinExecutionError(f"Error ejecutando join: {str(e)}")

            metadata = self._calculate_metadata(config, result_df, start_time)

            return JoinResult(
                data=result_df,
                metadata=metadata,
                config=config,
                success=True
            )

        except Exception as e:
            return JoinResult(
                data=pd.DataFrame(),
                metadata=self._create_empty_metadata(config, start_time),
                config=config,
                success=False,
                error_message=str(e)
            )

    def validate_join(self, config: JoinConfig) -> ValidationResult:
        """
        Validar configuración de join

        Args:
            config: Configuración a validar

        Returns:
            ValidationResult con resultado de validación
        """
        result = ValidationResult()

        if config.join_type not in [JoinType.INNER, JoinType.LEFT, JoinType.RIGHT, JoinType.OUTER, JoinType.CROSS]:
            raise UnsupportedJoinError(f"Tipo de join no soportado: {config.join_type}")

        if config.join_type == JoinType.CROSS:
            if config.left_keys or config.right_keys:
                result.warnings.append("Cross join no requiere columnas de join")
            return result

        result.errors.extend(self._validate_key_columns(config))
        result.is_valid = not result.errors

        if result.is_valid and config.validate_integrity:
            result.warnings.extend(self._validate_dtype_mismatches(config))

        left_cols = set(self.left_df.columns)
        right_cols = set(self.right_df.columns)
        duplicated = left_cols & right_cols - set(config.left_keys) - set(config.right_keys)
        if duplicated:
            result.warnings.append(f"Columnas duplicadas detectadas: {list(duplicated)}")
            result.suggestions.append("Considere usar sufijos personalizados")

        return result

    def _validate_key_columns(self, config: JoinConfig) -> list[str]:
        errors = []
        if not config.left_keys:
            errors.append("Columnas de join del dataset izquierdo son requeridas")
        if not config.right_keys:
            errors.append("Columnas de join del dataset derecho son requeridas")
        if len(config.left_keys) != len(config.right_keys):
            errors.append("Número de columnas de join debe ser igual en ambos datasets")
        missing_left = [col for col in config.left_keys if col not in self.left_df.columns]
        if missing_left:
            errors.append(f"Columnas no encontradas en dataset izquierdo: {missing_left}")
        missing_right = [col for col in config.right_keys if col not in self.right_df.columns]
        if missing_right:
            errors.append(f"Columnas no encontradas en dataset derecho: {missing_right}")
        return errors

    def _validate_dtype_mismatches(self, config: JoinConfig) -> list[str]:
        warnings = []
        for left_key, right_key in zip(config.left_keys, config.right_keys):
            left_dtype = self.left_df[left_key].dtype
            right_dtype = self.right_df[right_key].dtype
            if left_dtype != right_dtype:
                warnings.append(
                    f"Tipos de datos diferentes para {left_key} ({left_dtype}) y {right_key} ({right_dtype})"
                )
        return warnings

    def get_join_preview(self, config: JoinConfig, max_rows: int = 100) -> pd.DataFrame:
        """
        Obtener preview del resultado del join

        Args:
            config: Configuración del join
            max_rows: Número máximo de filas a devolver

        Returns:
            DataFrame con preview de resultados
        """
        try:
            if config.join_type == JoinType.CROSS:
                left_sample = self.left_df.head(min(50, len(self.left_df)))
                right_sample = self.right_df.head(min(50, len(self.right_df)))
                temp_manager = DataJoinManager(left_sample, right_sample)
                result_df = temp_manager._perform_join(config)
                return result_df.head(max_rows)
            else:
                result_df = self._perform_join(config)
                return result_df.head(max_rows)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _extract_matched_count(result_df: pd.DataFrame) -> int:
        """Contar filas con coincidencia ('both') de la columna _merge.

        Args:
            result_df: DataFrame con columna _merge

        Returns:
            Número de filas que coincidieron
        """
        if '_merge' not in result_df.columns:
            return 0
        return len(result_df[result_df['_merge'] == 'both'])

    def _compute_merge_stats(
        self, config: JoinConfig
    ) -> tuple[int, int, int]:
        """Calcular estadísticas de merge via outer join temporal.

        Usa un merge outer con indicator para obtener conteos precisos
        de matched, left_only y right_only, incluyendo el caso de
        claves duplicadas donde las filas del resultado pueden exceder
        las filas de un dataset.

        Args:
            config: Configuración del join

        Returns:
            Tupla (matched_rows, left_only_rows, right_only_rows)
        """
        if config.join_type == JoinType.CROSS:
            return (len(self.left_df) * len(self.right_df), 0, 0)

        temp_result = pd.merge(
            self.left_df,
            self.right_df,
            left_on=config.left_keys,
            right_on=config.right_keys,
            how='outer',
            indicator=True
        )

        matched = len(temp_result[temp_result['_merge'] == 'both'])
        left_only = len(temp_result[temp_result['_merge'] == 'left_only'])
        right_only = len(temp_result[temp_result['_merge'] == 'right_only'])
        return (matched, left_only, right_only)

    @staticmethod
    def _apply_include_columns(df: pd.DataFrame, config: JoinConfig) -> pd.DataFrame:
        """Filtrar columnas del resultado si include_columns está configurado.

        Args:
            df: DataFrame a filtrar
            config: Configuración con posibles include_columns

        Returns:
            DataFrame filtrado o sin cambios
        """
        if config.include_columns:
            existing_columns = [col for col in config.include_columns if col in df.columns]
            if existing_columns:
                return df[existing_columns]
        return df

    def _perform_join(self, config: JoinConfig) -> pd.DataFrame:
        """
        Ejecutar la operación de join según configuración

        Args:
            config: Configuración del join

        Returns:
            DataFrame con resultado del join
        """
        if config.join_type == JoinType.CROSS:
            result = pd.merge(
                self.left_df,
                self.right_df,
                how='cross',
                suffixes=config.suffixes
            )
            return self._apply_include_columns(result, config)

        result = pd.merge(
            self.left_df,
            self.right_df,
            left_on=config.left_keys,
            right_on=config.right_keys,
            how=HOW_MAP[config.join_type],
            suffixes=config.suffixes,
            indicator=True,
            validate=config.integrity_mode if config.validate_integrity else None
        )

        if not config.indicator:
            result = result.drop(columns=['_merge'])

        if config.sort_results and config.left_keys:
            result = safe_sort_values(result, config.left_keys[0])

        return self._apply_include_columns(result, config)

    def _calculate_metadata(
        self,
        config: JoinConfig,
        result_df: pd.DataFrame,
        start_time: float
    ) -> JoinMetadata:
        """
        Calcular metadatos del join realizado

        Args:
            config: Configuración del join
            result_df: DataFrame resultado
            start_time: Tiempo de inicio

        Returns:
            JoinMetadata con estadísticas
        """
        processing_time = time.time() - start_time

        left_rows = len(self.left_df)
        right_rows = len(self.right_df)
        result_rows = len(result_df)

        matched_rows, left_only_rows, right_only_rows = self._compute_merge_stats(config)

        memory_usage = result_df.memory_usage(deep=True).sum() / 1024 / 1024

        return JoinMetadata(
            left_rows=left_rows,
            right_rows=right_rows,
            result_rows=result_rows,
            join_type=config.join_type,
            join_keys=config.left_keys + config.right_keys,
            matched_rows=matched_rows,
            left_only_rows=left_only_rows,
            right_only_rows=right_only_rows,
            memory_usage_mb=memory_usage,
            processing_time_seconds=processing_time,
            timestamp=datetime.now()
        )

    def _create_empty_metadata(self, config: JoinConfig, start_time: float) -> JoinMetadata:
        """Crear JoinMetadata con valores por defecto para casos de error.

        Args:
            config: Configuración del join
            start_time: Tiempo de inicio

        Returns:
            JoinMetadata con contadores a cero
        """
        return JoinMetadata(
            left_rows=len(self.left_df),
            right_rows=len(self.right_df),
            result_rows=0,
            join_type=config.join_type,
            join_keys=config.left_keys + config.right_keys,
            matched_rows=0,
            left_only_rows=0,
            right_only_rows=0,
            memory_usage_mb=0.0,
            processing_time_seconds=time.time() - start_time,
            timestamp=datetime.now()
        )

    @staticmethod
    def _get_available_memory_mb() -> float:
        """Obtener memoria disponible en MB de forma segura.

        Returns:
            Memoria disponible en MB, o 1024 como fallback
        """
        if _HAS_PSUTIL:
            try:
                return psutil.virtual_memory().available / 1024 / 1024
            except Exception:
                pass
        return 1024.0

    def _should_use_chunking(self, config: JoinConfig, estimated_memory: float, available_memory: float) -> bool:
        """
        Determinar si se debe usar chunking basado en estimaciones de memoria

        Args:
            config: Configuración del join
            estimated_memory: Memoria estimada en MB
            available_memory: Memoria disponible en MB

        Returns:
            True si se debe usar chunking
        """
        memory_threshold = available_memory * 0.5

        if config.join_type == JoinType.CROSS:
            cross_product_size = len(self.left_df) * len(self.right_df)
            if cross_product_size >= 1_000_000:
                return True

        return estimated_memory > memory_threshold

    def _perform_chunked_join(self, config: JoinConfig) -> pd.DataFrame:
        """
        Ejecutar join usando procesamiento por chunks para datasets grandes

        Args:
            config: Configuración del join

        Returns:
            DataFrame con resultado del join
        """
        if config.join_type == JoinType.CROSS:
            return self._perform_chunked_cross_join(config)
        else:
            return self._perform_chunked_regular_join(config)

    def _perform_chunked_cross_join(self, config: JoinConfig) -> pd.DataFrame:
        """
        Ejecutar cross join usando chunks para evitar problemas de memoria

        Args:
            config: Configuración del join

        Returns:
            DataFrame con resultado del cross join
        """
        if len(self.left_df) <= len(self.right_df):
            smaller_df, larger_df = self.left_df, self.right_df
            swap_order = False
        else:
            smaller_df, larger_df = self.right_df, self.left_df
            swap_order = True

        chunk_size = max(1000, len(smaller_df) // 10)
        results = []

        for i in range(0, len(smaller_df), chunk_size):
            chunk = smaller_df.iloc[i:i + chunk_size]
            chunk_result = pd.merge(
                chunk if not swap_order else larger_df,
                larger_df if not swap_order else chunk,
                how='cross',
                suffixes=config.suffixes
            )
            results.append(chunk_result)

        final_result = pd.concat(results, ignore_index=True)
        return self._apply_include_columns(final_result, config)

    def _perform_chunked_regular_join(self, config: JoinConfig) -> pd.DataFrame:
        """
        Ejecutar join regular usando chunks para optimizar memoria

        Args:
            config: Configuración del join

        Returns:
            DataFrame con resultado del join
        """
        if len(self.left_df) <= len(self.right_df):
            reference_df, chunk_df = self.left_df, self.right_df
            left_on, right_on = config.left_keys, config.right_keys
            swap_order = False
        else:
            reference_df, chunk_df = self.right_df, self.left_df
            left_on, right_on = config.right_keys, config.left_keys
            swap_order = True

        if len(reference_df) < 10000:
            return self._perform_join(config)

        chunk_size = max(5000, len(chunk_df) // 5)
        results = []

        for i in range(0, len(chunk_df), chunk_size):
            chunk = chunk_df.iloc[i:i + chunk_size]

            if swap_order:
                chunk_result = pd.merge(
                    chunk, reference_df,
                    left_on=right_on, right_on=left_on,
                    how=HOW_MAP[config.join_type],
                    suffixes=config.suffixes,
                    indicator=True,
                    validate=config.integrity_mode if config.validate_integrity else None
                )
            else:
                chunk_result = pd.merge(
                    reference_df, chunk,
                    left_on=left_on, right_on=right_on,
                    how=HOW_MAP[config.join_type],
                    suffixes=config.suffixes,
                    indicator=True,
                    validate=config.integrity_mode if config.validate_integrity else None
                )

            results.append(chunk_result)

        final_result = pd.concat(results, ignore_index=True)

        if config.join_type == JoinType.INNER:
            final_result = final_result.drop_duplicates()

        if not config.indicator:
            final_result = final_result.drop(columns=['_merge'])

        if config.sort_results and config.left_keys:
            sort_key = config.left_keys[0] if not swap_order else config.right_keys[0]
            if sort_key in final_result.columns:
                final_result = safe_sort_values(final_result, sort_key)

        return self._apply_include_columns(final_result, config)

    def _estimate_memory_usage(self, config: JoinConfig) -> float:
        """
        Estimar uso de memoria para la operación de join

        Args:
            config: Configuración del join

        Returns:
            Memoria estimada en MB
        """
        if config.join_type == JoinType.CROSS:
            estimated_rows = len(self.left_df) * len(self.right_df)
            estimated_cols = len(self.left_df.columns) + len(self.right_df.columns)
        else:
            estimated_rows = max(len(self.left_df), len(self.right_df))
            estimated_cols = len(self.left_df.columns) + len(self.right_df.columns)

        estimated_memory = (estimated_rows * estimated_cols * 8) / 1024 / 1024

        return estimated_memory * 1.5
