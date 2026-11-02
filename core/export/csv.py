"""
Exportación a CSV.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def exportar_a_csv(df: pd.DataFrame, filepath: str, delimiter: str = ',', encoding: str = 'utf-8') -> bool:
    """
    Exportar DataFrame a archivo CSV

    Args:
        df: DataFrame a exportar
        filepath: Ruta de destino
        delimiter: Delimitador para CSV (default: ',')
        encoding: Codificación del archivo (default: 'utf-8')

    Returns:
        True si la exportación fue exitosa
    """
    try:
        # Exportar a CSV usando pandas
        df.to_csv(filepath, index=False, sep=delimiter, encoding=encoding)
        return True

    except Exception as e:
        logger.error("Error al exportar a CSV: %s", e)
        return False
