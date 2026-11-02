"""
Modelo personalizado para conectar DataFrames de Pandas con QTableView
Implementa paginación virtual para optimizar el rendimiento con datasets grandes
"""

import logging

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, Signal
import sys
from pathlib import Path
from typing import Any

# Añadir directorio raíz para importar config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import optimization_config
from app.models.formatting import format_cell

logger = logging.getLogger(__name__)

class VirtualizedPandasModel(QAbstractTableModel):
    """
    Modelo optimizado que adapta un DataFrame de Pandas para QTableView
    Implementa paginación virtual para manejar datasets grandes eficientemente

    El modelo es de solo lectura sobre el dataset que recibe: no reordena ni
    filtra datos. Cuando la vista pide ordenar, emite `sort_requested` para
    que el dueño del estado (PaginationManager) ordene el dataset completo.
    """

    sort_requested = Signal(str, bool)  # (nombre_columna, ascendente)

    def __init__(self, df: pd.DataFrame | None = None, chunk_size: int | None = None) -> None:
        super().__init__()
        self.full_df: pd.DataFrame = df if df is not None else pd.DataFrame()

        # Usar configuración si no se especifica chunk_size
        if chunk_size is None:
            chunk_size = optimization_config.DEFAULT_CHUNK_SIZE

        self.chunk_size: int = chunk_size
        self.total_rows: int = len(self.full_df)
        self.total_cols: int = len(self.full_df.columns) if self.total_rows > 0 else 0

        # Cache para chunks de datos
        self.data_cache: dict[int, pd.DataFrame] = {}
        self.cache_size: int = optimization_config.MAX_CACHE_CHUNKS

        # Configuración de virtualización usando configuración global
        self.enable_virtualization: bool = optimization_config.should_use_virtualization(self.total_rows)
        
    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        """
        Retornar número de filas en el DataFrame

        Args:
            parent: Índice padre

        Returns:
            Número de filas
        """
        if parent.isValid():
            return 0
        return self.total_rows

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        """
        Retornar número de columnas en el DataFrame

        Args:
            parent: Índice padre

        Returns:
            Número de columnas
        """
        if parent.isValid():
            return 0
        return self.total_cols
    
    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        """
        Retornar datos para la celda especificada con carga bajo demanda

        Args:
            index: Índice de la celda
            role: Rol de los datos

        Returns:
            Valor de la celda o None
        """
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            column = index.column()

            # Verificar que el índice está dentro del rango
            if row < self.total_rows and column < self.total_cols:
                # Para datos no virtualizados, acceso directo
                if not self.enable_virtualization:
                    value = self.full_df.iloc[row, column]
                    return format_cell(value)
                
                # Para datos virtualizados, usar chunk system
                chunk_data = self._get_chunk_data(row)
                if chunk_data is not None and column < len(chunk_data.columns):
                    local_row = row - (row // self.chunk_size) * self.chunk_size
                    value = chunk_data.iloc[local_row, column]
                    return format_cell(value)

        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        """
        Retornar flags para la celda especificada

        Args:
            index: Índice de la celda

        Returns:
            Flags de la celda
        """
        if not index.isValid():
            return Qt.ItemFlag()

        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """
        Solicitar el ordenamiento del dataset al dueño del estado.

        El modelo NO reordena sus datos: solo notifica qué columna y en qué
        dirección se pidió ordenar. DataView delega en PaginationManager,
        que ordena el dataset completo (no la página visible).

        Args:
            column: Índice de la columna
            order: Qt.SortOrder.AscendingOrder o Qt.SortOrder.DescendingOrder
        """
        if column < 0 or column >= self.total_cols:
            return

        self.sort_requested.emit(str(self.full_df.columns[column]), order == Qt.SortOrder.AscendingOrder)

    def get_sorted_data(self) -> pd.DataFrame:
        """
        Obtener los datos actuales del modelo

        Returns:
            Copia del DataFrame mostrado por el modelo
        """
        return self.full_df.copy()

    def _get_chunk_data(self, row: int) -> pd.DataFrame:
        """
        Obtener datos del chunk que contiene la fila especificada

        Args:
            row: Índice de la fila

        Returns:
            DataFrame con el chunk de datos
        """
        if not self.enable_virtualization:
            # Si no está activada la virtualización, usar datos completos
            return self.full_df

        # Calcular qué chunk contiene esta fila
        chunk_index = row // self.chunk_size

        # Verificar si el chunk ya está en cache
        if chunk_index in self.data_cache:
            return self.data_cache[chunk_index]

        # Cargar chunk desde el DataFrame completo
        start_row = chunk_index * self.chunk_size
        end_row = min(start_row + self.chunk_size, self.total_rows)

        chunk_df = self.full_df.iloc[start_row:end_row].copy()

        # Gestionar cache (eliminar chunks antiguos si es necesario)
        self._manage_cache(chunk_index)

        # Almacenar en cache
        self.data_cache[chunk_index] = chunk_df

        return chunk_df

    def _manage_cache(self, current_chunk: int) -> None:
        """
        Gestionar el cache de chunks para evitar usar demasiada memoria

        Args:
            current_chunk: Índice del chunk actual
        """
        if len(self.data_cache) >= self.cache_size:
            # Eliminar chunks más lejanos del actual
            chunks_to_remove = []
            for chunk_idx in self.data_cache:
                distance = abs(chunk_idx - current_chunk)
                if distance > self.cache_size // 2:
                    chunks_to_remove.append(chunk_idx)

            for chunk_idx in chunks_to_remove:
                del self.data_cache[chunk_idx]
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        """
        Retornar datos para los encabezados

        Args:
            section: Sección del encabezado
            orientation: Orientación (horizontal o vertical)
            role: Rol de los datos

        Returns:
            Nombre del encabezado
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                # Retornar nombre de la columna
                if section < self.total_cols:
                    return str(self.full_df.columns[section])
            elif orientation == Qt.Orientation.Vertical:
                # Retornar índice de la fila
                return str(section + 1)

        return None
    
    def setData(self, index: QModelIndex | QPersistentModelIndex, value: object, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        Establecer datos en la celda especificada

        Args:
            index: Índice de la celda
            value: Nuevo valor
            role: Rol de los datos

        Returns:
            True si se estableció correctamente
        """
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        column = index.column()

        # Verificar que el índice está dentro del rango
        if not (row < self.total_rows and column < self.total_cols):
            return False

        # Actualizar el DataFrame completo
        self.full_df.iloc[row, column] = value

        # Si el chunk está en cache, actualizarlo también
        chunk_index = row // self.chunk_size
        if chunk_index in self.data_cache:
            chunk_start = chunk_index * self.chunk_size
            chunk_end = min(chunk_start + self.chunk_size, self.total_rows)
            if chunk_start <= row < chunk_end:
                local_row = row - chunk_start
                self.data_cache[chunk_index].iloc[local_row, column] = value

        # Emitir señal de que los datos han cambiado
        self.dataChanged.emit(index, index, [role])
        return True

    def update_data(self, new_df: pd.DataFrame) -> None:
        """
        Actualizar los datos del modelo

        Args:
            new_df: Nuevo DataFrame
        """
        self.beginResetModel()

        # Limpiar cache
        self.data_cache.clear()

        # Actualizar datos
        self.full_df = new_df
        self.total_rows = len(self.full_df)
        self.total_cols = len(self.full_df.columns) if self.total_rows > 0 else 0

        # Recalcular si necesita virtualización usando configuración
        self.enable_virtualization = optimization_config.should_use_virtualization(self.total_rows)

        if self.enable_virtualization:
            logger.debug("Virtualización %s para dataset de %s filas", self.enable_virtualization, self.total_rows)

        self.endResetModel()

    def get_chunk_size(self) -> int:
        """Obtener el tamaño de chunk actual"""
        return self.chunk_size

    def set_chunk_size(self, size: int) -> None:
        """Establecer nuevo tamaño de chunk"""
        self.chunk_size = size
        # Limpiar cache y recalcular
        self.data_cache.clear()
        self.beginResetModel()
        self.endResetModel()