"""
Punto de entrada de la exportación separada.
"""

import logging

from typing import Any

import pandas as pd

from .config import ExportSeparatedConfig
from .splitter import ExcelTemplateSplitter

logger = logging.getLogger(__name__)


def exportar_datos_separados(df: pd.DataFrame, config_dict: dict) -> dict:
    """
    Exportar DataFrame a archivos Excel separados usando plantillas
    
    Args:
        df: DataFrame a separar
        config_dict: Configuración de separación
            - separator_column: str
            - template_path: str
            - start_cell: str (ej: 'A5')
            - output_folder: str
            - file_template: str
            - column_mapping: dict[str, str]
            - handle_duplicates: str ('overwrite', 'append', 'skip')
    
    Returns:
        dict con resultado:
            - success: bool
            - files_created: list[str]
            - groups_processed: int
            - total_rows: int
            - processing_time: float
            - errors: list[str]
            - warnings: list[str]
    """
    try:
        # Crear configuración
        config = ExportSeparatedConfig(
            separator_column=config_dict.get('separator_column', ''),
            template_path=config_dict.get('template_path', ''),
            start_cell=config_dict.get('start_cell', 'A1'),
            output_folder=config_dict.get('output_folder', ''),
            file_template=config_dict.get('file_template', '{valor}.xlsx'),
            column_mapping=config_dict.get('column_mapping', {}),
            handle_duplicates=config_dict.get('handle_duplicates', 'overwrite'),
            create_summary=config_dict.get('create_summary', True),
            preserve_format=config_dict.get('preserve_format', True),
            enable_chunking=config_dict.get('enable_chunking', True),
            max_memory_mb=config_dict.get('max_memory_mb', 2048)
        )
        
        # Crear splitter y ejecutar
        splitter = ExcelTemplateSplitter(df, config)
        result = splitter.separate_and_export()
        
        return {
            'success': result.get('success', False),
            'files_created': result.get('files_created', []),
            'groups_processed': result.get('groups_processed', 0),
            'total_rows': result.get('total_rows', 0),
            'successful_exports': result.get('successful_exports', 0),
            'failed_exports': result.get('failed_exports', 0),
            'processing_time': result.get('processing_time', 0.0),
            'errors': result.get('errors', []),
            'warnings': result.get('warnings', []),
            'failed_groups': result.get('failed_groups', {}),
            'analysis': result.get('analysis', {})
        }
        
    except Exception as e:
        logger.error("Error en separación de datos: %s", e)
        return {
            'success': False,
            'files_created': [],
            'groups_processed': 0,
            'total_rows': 0,
            'successful_exports': 0,
            'failed_exports': 0,
            'processing_time': 0.0,
            'errors': [str(e)],
            'warnings': [],
            'failed_groups': {},
            'analysis': {}
        }
