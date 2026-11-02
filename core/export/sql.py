"""
Exportación a SQLite con SQLAlchemy.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def exportar_a_sql(df: pd.DataFrame, filepath: str, nombre_tabla: str) -> bool:
    """
    Exportar DataFrame a base de datos SQL

    Args:
        df: DataFrame a exportar
        filepath: Ruta de la base de datos
        nombre_tabla: Nombre de la tabla en la base de datos

    Returns:
        True si la exportación fue exitosa
    """
    try:
        from sqlalchemy import create_engine

        # Crear engine para SQLite
        engine = create_engine(f'sqlite:///{filepath}')

        # Exportar a SQL
        if df.empty and len(df.columns) == 0:
            # SQLAlchemy no puede crear una tabla sin columnas
            dummy = df.copy()
            dummy['_placeholder'] = pd.Series(dtype='object')
            dummy.to_sql(nombre_tabla, engine, if_exists='replace', index=False)
        else:
            df.to_sql(nombre_tabla, engine, if_exists='replace', index=False)
        return True

    except Exception as e:
        logger.error("Error al exportar a SQL: %s", e)
        return False
