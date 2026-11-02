"""
Fachada de compatibilidad para carga y exportación de datos.

La implementación vive en módulos con una sola responsabilidad:

- `core.loaders`        carga de archivos (factory + loaders)
- `core.stats`          estadísticas descriptivas
- `core.export`         exportadores por formato
- `core.export_separated`  exportación separada con plantillas Excel

Este módulo mantiene las funciones históricas para no romper imports
existentes (`from core.data_handler import exportar_a_pdf`).
"""

import logging

import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Añadir directorio raíz para importar config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import optimization_config

from core.export import (
    exportar_a_csv,
    exportar_a_imagen,
    exportar_a_pdf,
    exportar_a_sql,
    exportar_a_xlsx,
)
from core.export_separated import (
    ExcelTemplateSplitter,
    ExportResult,
    ExportSeparatedConfig,
    ValidationResult,
    exportar_datos_separados,
)
from core.stats import obtener_estadisticas, obtener_estadisticas_basicas

logger = logging.getLogger(__name__)


def _resolve_chunk_size(loader: Any, chunk_size: int | None) -> int | None:
    """
    Decidir si conviene cargar por chunks y con qué tamaño.

    Returns:
        Tamaño de chunk a usar, o None si la carga debe ser completa.
    """
    if chunk_size is not None:
        return chunk_size

    if not loader.can_load_chunks():
        return None

    file_info = loader.get_memory_usage_info()
    if file_info.get('file_size_mb', 0) <= 100:
        return None

    estimated_rows = file_info.get('estimated_data_rows', 1000)
    if estimated_rows > optimization_config.VIRTUALIZATION_THRESHOLD:
        return 1000
    return 10000


def cargar_datos(filepath: str, chunk_size: int | None = None) -> pd.DataFrame:
    """
    Cargar datos desde un archivo usando el sistema de loaders

    Args:
        filepath: Ruta del archivo a cargar
        chunk_size: Tamaño de chunk para lectura (si el formato lo soporta)

    Returns:
        DataFrame de Pandas con los datos cargados

    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si el archivo no es soportado
        Exception: Para otros errores de carga
    """
    from core.loaders import LoadOptions, get_file_loader

    loader = get_file_loader(filepath)
    resolved_size = _resolve_chunk_size(loader, chunk_size)

    if resolved_size is not None:
        try:
            return loader.load_in_chunks(LoadOptions(chunk_size=resolved_size))
        except Exception as e:
            # Si falla el chunk loading, usar carga normal
            logger.warning("Chunk loading falló, usando carga normal: %s", e)

    return loader.load()


def cargar_datos_con_opciones(
    filepath: str,
    skip_rows: int = 0,
    column_names: dict | None = None,
    chunk_size: int | None = None,
    separator: str | None = None,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """
    Cargar datos desde un archivo con opciones adicionales usando el sistema de loaders

    Args:
        filepath: Ruta del archivo a cargar
        skip_rows: Número de filas a saltar al inicio (la siguiente fila se usa como header)
        column_names: Diccionario con nombres de columnas a renombrar {original: nuevo}
        chunk_size: Tamaño de chunk para lectura (si el formato lo soporta)
        separator: Separador personalizado para archivos CSV/TSV
        sheet_name: Nombre de la hoja para archivos Excel

    Returns:
        DataFrame de Pandas con los datos cargados y opciones aplicadas
    """
    from core.loaders import LoadOptions, get_file_loader

    loader = get_file_loader(filepath)
    options = LoadOptions(
        skip_rows=skip_rows or 0,
        column_names=dict(column_names or {}),
        separator=separator,
        sheet_name=sheet_name,
    )

    # load_in_chunks no soporta skip_rows/column_names: usar carga normal si se requieren
    has_options = options.skip_rows > 0 or bool(options.column_names)

    if not has_options:
        resolved_size = _resolve_chunk_size(loader, chunk_size)
        if resolved_size is not None:
            try:
                chunk_options = LoadOptions(
                    skip_rows=options.skip_rows,
                    column_names=options.column_names,
                    separator=options.separator,
                    sheet_name=options.sheet_name,
                    chunk_size=resolved_size,
                )
                return loader.load_in_chunks(chunk_options)
            except Exception as e:
                # Si falla el chunk loading, usar carga normal
                logger.warning("Chunk loading falló, usando carga normal: %s", e)

    return loader.load(options)


def get_supported_file_formats() -> list:
    """
    Get list of all supported file formats

    Returns:
        List of supported file extensions
    """
    from core.loaders import get_supported_formats
    return get_supported_formats()


__all__ = [
    'ExcelTemplateSplitter',
    'ExportResult',
    'ExportSeparatedConfig',
    'ValidationResult',
    'cargar_datos',
    'cargar_datos_con_opciones',
    'exportar_a_csv',
    'exportar_a_imagen',
    'exportar_a_pdf',
    'exportar_a_sql',
    'exportar_a_xlsx',
    'exportar_datos_separados',
    'get_supported_file_formats',
    'obtener_estadisticas',
    'obtener_estadisticas_basicas',
]
