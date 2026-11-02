"""
Exportación de un widget Qt a imagen.
"""

import logging

from typing import Any

logger = logging.getLogger(__name__)


def exportar_a_imagen(table_view: Any, filepath: str) -> bool:
    """
    Exportar vista de tabla a imagen

    Args:
        table_view: QTableView a capturar
        filepath: Ruta de destino para la imagen

    Returns:
        True si la exportación fue exitosa
    """
    try:
        # Capturar la vista de la tabla como pixmap
        pixmap = table_view.grab()

        # Guardar como imagen (PNG por defecto)
        success = pixmap.save(filepath)

        if success:
            return True
        else:
            logger.error("No se pudo guardar la imagen en %s", filepath)
            return False

    except Exception as e:
        logger.error("Error al exportar a imagen: %s", e)
        return False
