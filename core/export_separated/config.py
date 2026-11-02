"""
Modelos de dominio para la exportación separada con plantillas Excel.
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

try:
    from openpyxl.utils import coordinate_to_tuple, get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:  # pragma: no cover - depende del entorno
    OPENPYXL_AVAILABLE = False


@dataclass
class ExportSeparatedConfig:
    """Configuración completa para separación de datos"""
    
    # Datos de origen - Argumentos requeridos primero
    separator_column: str  # Columna para separar
    template_path: str  # Ruta a plantilla .xlsx
    output_folder: str  # Carpeta destino
    
    # Argumentos opcionales con valores por defecto
    start_cell: str = "A1"  # Celda inicial para datos
    file_template: str = "{valor}.xlsx"  # Plantilla nombre archivo
    
    # Mapeo de columnas
    column_mapping: dict[str, str] = field(default_factory=dict)
    # Ej: {'columna_df': 'A', 'otra_columna': 'C'}
    
    # Opciones avanzadas
    handle_duplicates: str = "overwrite"  # 'overwrite', 'append', 'skip'
    create_summary: bool = True  # Crear archivo resumen
    preserve_format: bool = True  # Preservar formato Excel
    
    # Opciones de rendimiento
    enable_chunking: bool = True  # Habilitar chunking automático
    max_memory_mb: int = 2048  # Límite de memoria
    progress_callback: Callable | None = None  # Callback de progreso
    
    def validate(self) -> dict[str, Any]:
        """Validar configuración completa"""
        errors = []
        warnings = []
        
        # Validar columna de separación
        if not self.separator_column:
            errors.append("Columna de separación es requerida")
        
        # Validar plantilla Excel
        if not Path(self.template_path).exists():
            errors.append(f"Plantilla no encontrada: {self.template_path}")
        elif not self.template_path.lower().endswith(('.xlsx', '.xlsm')):
            errors.append("Plantilla debe ser archivo .xlsx o .xlsm")
        
        # Validar carpeta destino
        try:
            Path(self.output_folder).mkdir(parents=True, exist_ok=True)
            if not os.access(self.output_folder, os.W_OK):
                errors.append(f"Sin permisos de escritura en: {self.output_folder}")
        except Exception as e:
            errors.append(f"Error en carpeta destino: {str(e)}")
        
        # Validar celda inicial
        try:
            coordinate_to_tuple(self.start_cell)
        except Exception:
            errors.append(f"Celda inicial inválida: {self.start_cell}")
        
        # Validar plantilla de nombre
        if not self.file_template:
            errors.append("Plantilla de nombre de archivo es requerida")
        elif not self.file_template.endswith('.xlsx'):
            warnings.append("Plantilla de nombre no tiene extensión .xlsx")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def get_default_mapping(df_columns: list[str]) -> dict[str, str]:
        """Obtener mapeo por defecto (posicional)"""
        mapping = {}
        for i, col in enumerate(df_columns):
            mapping[col] = get_column_letter(i + 1)
        return mapping

    def to_dict(self) -> dict[str, Any]:
        """Convertir configuración a diccionario (para exportar_datos_separados)"""
        return {
            'separator_column': self.separator_column,
            'template_path': self.template_path,
            'start_cell': self.start_cell,
            'output_folder': self.output_folder,
            'file_template': self.file_template,
            'column_mapping': dict(self.column_mapping),
            'handle_duplicates': self.handle_duplicates,
            'create_summary': self.create_summary,
            'preserve_format': self.preserve_format,
            'enable_chunking': self.enable_chunking,
            'max_memory_mb': self.max_memory_mb
        }

@dataclass

class ValidationResult:
    """Resultado de validación"""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
    
    def add_info(self, info: str) -> None:
        self.info.append(info)

@dataclass

class ExportResult:
    """Resultado de exportación individual"""
    success: bool = False
    file_path: str = ""
    group_name: str = ""
    rows_processed: int = 0
    processing_time: float = 0.0
    error: str = ""
    timestamp: datetime | None = None
