"""
Estadísticas descriptivas de DataFrames.
"""

import logging

import pandas as pd

from config import optimization_config

logger = logging.getLogger(__name__)


def obtener_estadisticas(df: pd.DataFrame, columnas: list | None = None, percentiles: list | None = None) -> pd.DataFrame:
    """
    Obtener estadísticas descriptivas del DataFrame con optimización para datasets grandes

    Args:
        df: DataFrame de Pandas
        columnas: Lista de columnas específicas (si None, usar todas las numéricas)
        percentiles: Lista de percentiles a calcular (si None, usar [25, 50, 75])

    Returns:
        DataFrame con estadísticas descriptivas
    """
    try:
        if len(df) == 0:
            return pd.DataFrame()

        # Si no se especifican columnas, usar solo las numéricas para optimizar
        if columnas is None:
            columnas = df.select_dtypes(include=['number']).columns.tolist()
            if not columnas:
                # Si no hay columnas numéricas, usar todas
                columnas = df.columns.tolist()

        # Configurar percentiles por defecto (convertir a decimales)
        if percentiles is None:
            percentiles = [0.25, 0.5, 0.75]  # Usar decimales en lugar de porcentajes
        else:
            # Convertir percentiles de porcentaje a decimal si es necesario
            percentiles = [p/100 if p > 1 else p for p in percentiles]

        # Para datasets muy grandes, usar sample para estadísticas aproximadas
        if optimization_config.should_sample_stats(len(df)):
            logger.info("Dataset grande detectado (%s filas), calculando estadísticas con sample...", len(df))
            sample_size = min(optimization_config.STATS_SAMPLE_SIZE, len(df))
            df_sample = df.sample(n=sample_size, random_state=42)
        else:
            df_sample = df

        # Calcular estadísticas solo para las columnas especificadas
        estadisticas = df_sample[columnas].describe(percentiles=percentiles, include='all')

        return estadisticas
    except Exception as e:
        logger.error("Error al calcular estadísticas: %s", e)
        # Si hay error, devolver DataFrame vacío
        return pd.DataFrame()


def obtener_estadisticas_basicas(df: pd.DataFrame) -> dict:
    """
    Obtener estadísticas básicas optimizadas para datasets grandes

    Args:
        df: DataFrame de Pandas

    Returns:
        Diccionario con estadísticas básicas
    """
    try:
        basic_stats = {
            'total_filas': len(df),
            'total_columnas': len(df.columns),
            'columnas_numericas': len(df.select_dtypes(include=['number']).columns),
            'columnas_texto': len(df.select_dtypes(include=['object']).columns),
            'columnas_fecha': len(df.select_dtypes(include=['datetime']).columns),
            'memoria_uso_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
            'filas_duplicadas': df.duplicated(keep=False).sum(),
            'valores_nulos_total': df.isnull().sum().sum()
        }

        return basic_stats
    except Exception as e:
        logger.error("Error al calcular estadísticas básicas: %s", e)
        return {}
