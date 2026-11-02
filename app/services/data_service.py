"""
Servicio de Datos - DataService

Servicio centralizado para la gestión de carga, guardado y manipulación
de datos en Flash View Sheet.
"""

import gc
from pathlib import Path
from typing import Any
import pandas as pd
from PySide6.QtCore import Signal
from core.data_handler import (
    cargar_datos_con_opciones,
    get_supported_file_formats
)
from core.loaders import get_format_descriptions
from core.loaders.folder_loader import FolderLoader
from app.services.task_thread import TaskThread, stop_thread
from core.consolidation.excel_consolidator import ExcelConsolidator
from core.models.folder_load_config import ColumnAlignmentStrategy

class DataLoaderThread(TaskThread):
    """Hilo para cargar datos en segundo plano"""

    data_loaded = Signal(object)
    error_occurred = Signal(str)
    progress_updated = Signal(int, int)

    def __init__(self, filepath: str, skip_rows: int = 0, column_names: dict[str, str] | None = None, separator: str | None = None, sheet_name: str | None = None) -> None:
        super().__init__()
        self.filepath = filepath
        self.skip_rows = skip_rows
        self.column_names = column_names if column_names else {}
        self.separator = separator
        self.sheet_name = sheet_name

    def execute(self) -> object:
        """Cargar el archivo respetando las opciones recibidas."""
        self.progress_updated.emit(0, 100)
        df = cargar_datos_con_opciones(
            self.filepath,
            self.skip_rows,
            self.column_names,
            separator=self.separator,
            sheet_name=self.sheet_name,
        )
        self.progress_updated.emit(100, 100)
        return df

    def _emit_result(self, result: object) -> None:
        self.data_loaded.emit(result)

    def _emit_error(self, message: str) -> None:
        self.error_occurred.emit(message)


class FolderLoaderThread(TaskThread):
    """Hilo para cargar y consolidar archivos de una carpeta en segundo plano."""

    data_loaded = Signal(object)
    error_occurred = Signal(str)
    progress_updated = Signal(int, int)

    def __init__(self, folder_path: str, config: Any | None = None) -> None:
        super().__init__()
        self.folder_path = folder_path
        self.config = config

    def execute(self) -> object:
        """Escanear, seleccionar y consolidar los archivos de la carpeta."""
        folder_loader = FolderLoader(self.folder_path)
        all_metadata = folder_loader.get_all_metadata()

        if self.isInterruptionRequested():
            return None

        selected_files = self._select_files(all_metadata)

        if not selected_files:
            raise FileNotFoundError("No se encontraron archivos válidos en la carpeta.")

        total_files = len(selected_files)
        self.progress_updated.emit(0, total_files)

        consolidator = ExcelConsolidator()
        self._apply_rename_mapping(consolidator)

        def _progress_callback(progress: float) -> None:
            if self.isInterruptionRequested():
                raise InterruptedError("Thread interrupted")
            current = int(progress / 100 * total_files)
            self.progress_updated.emit(current, total_files)

        alignment_strategy = getattr(
            self.config, 'alignment_strategy', ColumnAlignmentStrategy.BY_POSITION
        )

        consolidated_df = consolidator.consolidate_chunked(
            selected_files,
            alignment=alignment_strategy,
            chunk_size=10,
            progress_callback=_progress_callback
        )

        self.progress_updated.emit(total_files, total_files)
        return consolidated_df

    def _emit_result(self, result: object) -> None:
        self.data_loaded.emit(result)

    def _emit_error(self, message: str) -> None:
        self.error_occurred.emit(message)

    def _select_files(self, all_metadata: list[dict[str, Any]]) -> list[str]:
        if self.config and hasattr(self.config, 'should_include_file'):
            return [
                meta['filepath'] for meta in all_metadata
                if self.config.should_include_file(meta['filename'])
            ]
        return [meta['filepath'] for meta in all_metadata]

    def _apply_rename_mapping(self, consolidator: ExcelConsolidator) -> None:
        if self.config and hasattr(self.config, 'column_rename_mapping') and self.config.column_rename_mapping:
            consolidator.set_column_mappings(self.config.column_rename_mapping)

class DataService:
    """
    Servicio unificado para operaciones de datos.
    
    Responsabilidades:
    - Carga de archivos (Excel, CSV, JSON, etc.)
    - Carga de carpetas con consolidación
    - Gestión del estado de datos
    """
    
    def __init__(self) -> None:
        """Inicializar el servicio de datos"""
        self.df_original: pd.DataFrame | None = None
        self.df_vista_actual: pd.DataFrame | None = None
        self.loading_thread: DataLoaderThread | None = None
        self.folder_loading_thread: FolderLoaderThread | None = None
        self._active_threads: list[DataLoaderThread] = []
        self.current_source: str | None = None
    
    @property
    def has_data(self) -> bool:
        """Verificar si hay datos cargados"""
        return self.df_vista_actual is not None and not self.df_vista_actual.empty
    
    @property
    def datos_actuales(self) -> pd.DataFrame | None:
        """Obtener los datos actuales"""
        return self.df_vista_actual
    
    @property
    def datos_originales(self) -> pd.DataFrame | None:
        """Obtener los datos originales"""
        return self.df_original
    
    def get_file_filter(self) -> str:
        """Obtener filtro de archivos para diálogos de apertura"""
        supported_formats = get_supported_file_formats()
        descriptions = get_format_descriptions()

        format_filters = [
            f"{descriptions[ext]} (*{ext})"
            for ext in supported_formats
            if ext in descriptions
        ]

        # Añadir filtro de "Todos los soportados"
        all_extensions = " ".join(f"*{ext}" for ext in supported_formats)
        all_formats = f"Todos los archivos soportados ({all_extensions})"
        format_filters.insert(0, all_formats)

        return ";;".join(format_filters)
    
    def create_loader_thread(self, filepath: str, skip_rows: int = 0, column_names: dict[str, str] | None = None, separator: str | None = None, sheet_name: str | None = None) -> DataLoaderThread:
        """Crear un hilo de carga de datos"""
        thread = DataLoaderThread(filepath, skip_rows, column_names, separator, sheet_name)
        self.loading_thread = thread
        self.current_source = filepath
        self._active_threads.append(thread)
        thread.finished.connect(
            lambda t=thread: self._active_threads.remove(t) if t in self._active_threads else None
        )
        thread.finished.connect(
            lambda t=thread: setattr(self, 'loading_thread', None) if self.loading_thread is t else None
        )
        return thread
    
    def create_folder_loader_thread(self, folder_path: str, config: Any | None = None) -> FolderLoaderThread:
        """Crear un hilo de carga de carpeta"""
        self.folder_loading_thread = FolderLoaderThread(folder_path, config)
        self.current_source = folder_path
        return self.folder_loading_thread
    
    def set_current_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Establecer datos actuales"""
        self.df_vista_actual = df
        return df

    def set_original_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Establecer los datos originales (snapshot de referencia)"""
        self.df_original = df.copy()
        return self.df_original

    def clear_data(self) -> None:
        """Reset data state without stopping threads or closing dialogs."""
        self.df_original = None
        self.df_vista_actual = None
        self.current_source = None
        gc.collect()

    @staticmethod
    def extensiones_permitidas() -> list[str]:
        """Obtener lista de extensiones de archivo soportadas"""
        return get_supported_file_formats()
    
    def get_column_names(self) -> list[str]:
        """Obtener nombres de columnas"""
        if self.df_vista_actual is None:
            return []
        columns: list[str] = list(self.df_vista_actual.columns)
        return columns
    
    def get_data_shape(self) -> tuple[int, int]:
        """Obtener forma de los datos actuales"""
        if self.df_vista_actual is None:
            return (0, 0)
        shape: tuple[int, int] = self.df_vista_actual.shape
        return shape
    
    def get_filepath(self) -> str | None:
        """Obtener ruta del archivo o carpeta cargada"""
        return self.current_source
    
    def get_filename(self) -> str:
        """Obtener nombre del archivo cargado"""
        filepath = self.get_filepath()
        if filepath:
            return Path(filepath).name
        return "Archivo cargado"
    
    def cleanup(self) -> None:
        """Libera agresivamente la memoria de los DataFrames cargados."""
        # 1. Detener hilos activos (cancelación cooperativa)
        for thread in self._active_threads[:]:
            stop_thread(thread)
        self._active_threads.clear()

        threads: tuple[DataLoaderThread | FolderLoaderThread | None, ...] = (self.loading_thread, self.folder_loading_thread)
        for active_thread in threads:
            stop_thread(active_thread)

        # 2. Sobrescribir DataFrames pesados
        self.df_original = None
        self.df_vista_actual = None
        self.current_source = None

        # 3. Forzar recolección de basura
        gc.collect()

        # 5. Liberar referencias a hilos
        self.loading_thread = None
        self.folder_loading_thread = None
