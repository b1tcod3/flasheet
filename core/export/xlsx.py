"""
Exportación a Excel con openpyxl.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def exportar_a_xlsx(df: pd.DataFrame, filepath: str) -> bool:
    """
    Exportar DataFrame a archivo Excel (.xlsx)

    Args:
        df: DataFrame a exportar
        filepath: Ruta de destino

    Returns:
        True si la exportación fue exitosa
    """
    try:
        # Verificar que openpyxl esté disponible
        import openpyxl
        from openpyxl.utils.dataframe import dataframe_to_rows

        # Crear workbook y worksheet
        workbook = openpyxl.Workbook()
        worksheet = workbook.active

        # Convertir DataFrame a filas y escribir en worksheet
        for r, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
            for c, value in enumerate(row, 1):
                worksheet.cell(row=r, column=c, value=value)

        # Guardar archivo
        workbook.save(filepath)
        workbook.close()

        return True

    except ImportError:
        logger.error("openpyxl no está instalado. Instale con: pip install openpyxl")
        return False
    except Exception as e:
        logger.error("Error al exportar a XLSX: %s", e)
        return False
