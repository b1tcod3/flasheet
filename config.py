"""
Configuración de optimización para Flash View Sheet.

Los valores se leen de variables de entorno al construir la instancia, de modo
que `optimization_config` puede sustituirse por otra instancia en pruebas o en
tiempo de ejecución sin tocar el resto del código.
"""

import os


class OptimizationConfig:
    """Configuración de límites de memoria y rendimiento"""

    # Límites para activar optimizaciones
    VIRTUALIZATION_THRESHOLD = 5000  # Número de filas para activar paginación virtual
    CHUNK_LOADING_THRESHOLD = 100 * 1024 * 1024  # 100MB para activar carga por chunks

    # Configuración de paginación virtual
    DEFAULT_CHUNK_SIZE = 1000  # Filas por chunk en el modelo virtual
    MAX_CACHE_CHUNKS = 10  # Número máximo de chunks en cache

    # Configuración de carga de archivos
    CSV_CHUNK_SIZE_SMALL = 50000   # Chunk size para archivos pequeños
    CSV_CHUNK_SIZE_MEDIUM = 25000  # Chunk size para archivos medianos
    CSV_CHUNK_SIZE_LARGE = 10000   # Chunk size para archivos grandes

    # Configuración de estadísticas
    STATS_SAMPLE_THRESHOLD = 100000  # Usar sample para datasets > 100k filas
    STATS_SAMPLE_SIZE = 50000        # Tamaño de muestra para estadísticas

    # Configuración de filtrado
    FILTER_OPTIMIZATION_THRESHOLD = 50000  # Usar optimización para datasets > 50k filas

    # Configuración de exportación
    PDF_MAX_ROWS = 10000  # Máximo de filas para exportación a PDF
    IMAGE_MAX_SIZE = 50 * 1024 * 1024  # 50MB máximo para exportación a imagen

    # Variable de entorno que sobrescribe cada valor
    ENV_OVERRIDES = {
        'FLASH_CHUNK_SIZE': 'DEFAULT_CHUNK_SIZE',
        'FLASH_CACHE_CHUNKS': 'MAX_CACHE_CHUNKS',
        'FLASH_VIRT_THRESHOLD': 'VIRTUALIZATION_THRESHOLD',
    }

    def get_csv_chunk_size(self, file_size_bytes: int) -> int:
        """
        Obtener el tamaño de chunk apropiado basado en el tamaño del archivo

        Args:
            file_size_bytes: Tamaño del archivo en bytes

        Returns:
            Tamaño de chunk en filas
        """
        if file_size_bytes > 500 * 1024 * 1024:  # > 500MB
            return self.CSV_CHUNK_SIZE_LARGE
        if file_size_bytes > 100 * 1024 * 1024:  # > 100MB
            return self.CSV_CHUNK_SIZE_MEDIUM
        return self.CSV_CHUNK_SIZE_SMALL

    def should_use_virtualization(self, row_count: int) -> bool:
        """Determinar si se debe usar paginación virtual"""
        return row_count > self.VIRTUALIZATION_THRESHOLD

    def should_optimize_filtering(self, row_count: int) -> bool:
        """Determinar si se debe optimizar el filtrado"""
        return row_count > self.FILTER_OPTIMIZATION_THRESHOLD

    def should_sample_stats(self, row_count: int) -> bool:
        """Determinar si se deben usar muestras para estadísticas"""
        return row_count > self.STATS_SAMPLE_THRESHOLD


def get_config_from_env() -> OptimizationConfig:
    """Crear una configuración aplicando las variables de entorno definidas."""
    config = OptimizationConfig()

    for env_var, attribute in OptimizationConfig.ENV_OVERRIDES.items():
        raw_value = os.environ.get(env_var)
        if raw_value is None:
            continue
        try:
            value = int(raw_value)
        except ValueError:
            continue
        setattr(config, attribute, value)

    return config


# Configuración global
optimization_config = get_config_from_env()
