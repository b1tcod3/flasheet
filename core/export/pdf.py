"""
Exportación a PDF con reportlab.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def exportar_a_pdf(df: pd.DataFrame, filepath: str) -> bool:
    """
    Exportar DataFrame a archivo PDF
    
    Args:
        df: DataFrame a exportar
        filepath: Ruta de destino
        
    Returns:
        True si la exportación fue exitosa
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from reportlab.lib import colors
        
        # Crear documento
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        
        # Convertir DataFrame a lista de listas
        data = [df.columns.tolist()] + df.values.tolist()
        
        # DataFrame sin columnas no genera tabla válida en reportlab
        if not data or not data[0]:
            data = [['']]
        
        # Crear tabla
        tabla = Table(data)
        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        tabla.setStyle(estilo)
        
        # Construir documento
        doc.build([tabla])
        return True
        
    except Exception as e:
        logger.error("Error al exportar a PDF: %s", e)
        return False
