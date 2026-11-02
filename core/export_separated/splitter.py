"""
Separación de un DataFrame en un archivo Excel por grupo, preservando el
formato de una plantilla.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config import optimization_config

from .config import (
    OPENPYXL_AVAILABLE,
    ExportResult,
    ExportSeparatedConfig,
    ValidationResult,
)

if OPENPYXL_AVAILABLE:
    from openpyxl import load_workbook
    from openpyxl.utils import column_index_from_string, coordinate_to_tuple


class ExcelTemplateSplitter:
    """Clase principal para separación de datos con plantillas Excel"""
    
    def __init__(self, df: pd.DataFrame, config: ExportSeparatedConfig) -> None:
        """
        Inicializar separador con DataFrame y configuración
        
        Args:
            df: DataFrame a separar
            config: Configuración de separación
        """
        self.df = df
        self.config = config
        self.progress_callback = config.progress_callback
        self.logger = self._setup_logger()
        self.created_files: list[str] = []
        self.failed_groups: dict[str, str] = {}
        self._cancelled = False

        # Verificar dependencias
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl es requerido para separación con plantillas Excel")
        
        # Configurar optimizaciones de rendimiento
        self._setup_performance_optimization()
    
    @staticmethod
    def _setup_logger() -> Any:
        """Configurar logging consistente con sistema existente"""
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        return logger
    
    def _setup_performance_optimization(self) -> None:
        """Decidir si conviene procesar el dataset por chunks."""
        row_threshold = optimization_config.VIRTUALIZATION_THRESHOLD
        memory_bytes = self.df.memory_usage(deep=True).sum()
        memory_limit_bytes = self.config.max_memory_mb * 1024 * 1024

        if len(self.df) > row_threshold or memory_bytes > memory_limit_bytes:
            self.enable_chunking = True
            self.chunk_size = min(
                optimization_config.DEFAULT_CHUNK_SIZE,
                max(1000, len(self.df) // 20)
            )
        else:
            self.enable_chunking = False
            self.chunk_size = len(self.df)

    def validate_configuration(self) -> ValidationResult:
        """Validar configuración completa antes de proceder"""
        result = ValidationResult()
        
        # Validación básica de configuración
        config_validation = self.config.validate()
        if not config_validation['valid']:
            for error in config_validation['errors']:
                result.add_error(error)
            for warning in config_validation['warnings']:
                result.add_warning(warning)
        
        # Validación de datos
        if self.df.empty:
            result.add_error("DataFrame está vacío")
            return result
        
        if self.config.separator_column not in self.df.columns:
            result.add_error(f"Columna '{self.config.separator_column}' no existe en DataFrame")
            return result
        
        # Validar valores únicos en columna de separación
        unique_values = self.df[self.config.separator_column].nunique()
        null_count = self.df[self.config.separator_column].isnull().sum()
        
        if unique_values == 0:
            result.add_error("No se encontraron valores únicos en columna de separación")
        elif unique_values + (1 if null_count > 0 else 0) == 0:
            result.add_error("No hay datos para separar")
        
        # Validación de plantilla Excel
        if Path(self.config.template_path).exists():
            try:
                workbook = load_workbook(self.config.template_path, read_only=True)
                workbook.close()
                result.add_info(f"Plantilla validada: {Path(self.config.template_path).name}")
            except Exception as e:
                result.add_error(f"Error validando plantilla Excel: {str(e)}")
        
        return result
    
    def analyze_data(self) -> dict[str, Any]:
        """Analizar DataFrame para generar preview y validar separación"""
        analysis: dict[str, Any] = {}
        
        # Análisis básico
        analysis['total_rows'] = len(self.df)
        analysis['total_columns'] = len(self.df.columns)
        analysis['memory_usage_mb'] = self.df.memory_usage(deep=True).sum() / 1024 / 1024
        
        # Análisis de columna de separación
        if self.config.separator_column in self.df.columns:
            separator_series = self.df[self.config.separator_column]
            analysis['separator_column'] = self.config.separator_column
            analysis['unique_values'] = separator_series.nunique()
            analysis['null_count'] = separator_series.isnull().sum()
            analysis['null_percentage'] = (analysis['null_count'] / len(separator_series)) * 100
            
            # Top valores más frecuentes
            value_counts = separator_series.value_counts()
            analysis['top_values'] = value_counts.head(10).to_dict()
            analysis['estimated_groups'] = analysis['unique_values'] + (1 if analysis['null_count'] > 0 else 0)
        
        # Estimación de rendimiento
        total_mb = analysis['memory_usage_mb']
        estimated_processing_time = total_mb * 0.5  # 0.5 segundos por MB (estimado)
        analysis['estimated_processing_time'] = estimated_processing_time
        analysis['recommended_chunking'] = (
            total_mb > 500 or
            analysis['estimated_groups'] > 100 or
            self.enable_chunking
        )
        
        # Recomendaciones
        recommendations = []
        if analysis['null_percentage'] > 20:
            recommendations.append("Alto porcentaje de nulos detectado - considerar limpieza de datos")
        if analysis['estimated_groups'] > 500:
            recommendations.append("Muchos grupos detectados - usar chunking para mejor rendimiento")
        if total_mb > 1024:
            recommendations.append("Dataset grande - habilitar chunking agresivo")
        
        analysis['recommendations'] = recommendations
        
        return analysis
    
    def generate_file_preview(self) -> list[dict[str, Any]]:
        """Generar preview de archivos que se crearán"""
        preview = []
        
        try:
            # Obtener grupos únicos
            groups = list(self.df.groupby(self.config.separator_column))
            
            for group_name, group_df in groups:
                # Generar nombre de archivo
                filename = self._generate_filename_for_group(group_name, len(group_df))
                file_path = str(Path(self.config.output_folder) / filename)
                
                # Estimar tamaño de archivo (aproximado)
                estimated_size_kb = len(group_df) * 0.5  # ~0.5KB por fila (estimado)
                
                preview.append({
                    'filename': filename,
                    'group_name': str(group_name),
                    'rows': len(group_df),
                    'estimated_size_kb': estimated_size_kb,
                    'file_path': file_path,
                    'status': 'ready'
                })
        
        except Exception as e:
            self.logger.error("Error generando preview: %s", str(e))
            return []
        
        return preview
    
    def _generate_filename_for_group(self, group_name: str, row_count: int) -> str:
        """Generar nombre de archivo para un grupo específico"""
        group_info = {
            'valor': group_name,
            'columna': self.config.separator_column,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'fecha_hora': datetime.now().strftime('%Y-%m-%d_%H%M'),
            'filas': row_count,
            'timestamp': str(int(time.time()))
        }
        
        return self._process_file_template(self.config.file_template, group_info)
    
    def _process_file_template(self, template: str, group_info: dict[str, Any]) -> str:
        """Procesar plantilla de nombre de archivo con placeholders"""
        processed = template
        
        # Placeholders soportados
        placeholders = {
            '{valor}': str(group_info.get('valor', '')),
            '{columna}': str(group_info.get('columna', '')),
            '{fecha}': str(group_info.get('fecha', '')),
            '{fecha_hora}': str(group_info.get('fecha_hora', '')),
            '{filas}': str(group_info.get('filas', '')),
            '{timestamp}': str(group_info.get('timestamp', ''))
        }
        
        # Reemplazar placeholders
        for placeholder, value in placeholders.items():
            processed = processed.replace(placeholder, value)
        
        # Sanitizar nombre de archivo
        return self._sanitize_filename(processed)
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitizar nombre para compatibilidad del SO"""
        # Caracteres prohibidos
        forbidden_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(forbidden_chars, '_', filename)
        
        # Remover puntos múltiples al final
        sanitized = re.sub(r'\.+$', '', sanitized)
        
        # Normalizar espacios
        sanitized = ' '.join(sanitized.split())
        
        # Asegurar que no esté vacío
        if not sanitized.strip():
            sanitized = 'archivo_sin_nombre.xlsx'
        
        # Límite de longitud
        if len(sanitized) > 255:
            name_part = Path(sanitized).stem
            ext = Path(sanitized).suffix
            available_length = 255 - len(ext)
            sanitized = name_part[:available_length-3] + '...' + ext
        
        return sanitized
    
    def separate_and_export(self) -> dict[str, Any]:
        """Ejecutar separación completa y exportación"""
        start_time = time.time()
        
        try:
            # 1. Validar configuración
            validation = self.validate_configuration()
            if not validation.is_valid:
                return {
                    'success': False,
                    'error': 'Configuración inválida: ' + '; '.join(validation.errors),
                    'validation_errors': validation.errors,
                    'validation_warnings': validation.warnings,
                    'errors': validation.errors,
                    'warnings': validation.warnings
                }
            
            # 2. Analizar datos
            analysis = self.analyze_data()
            if analysis.get('estimated_groups', 0) == 0:
                return {
                    'success': False,
                    'error': 'No hay grupos para separar'
                }
            
            # 3. Procesar separación
            results, groups_processed, group_errors = self._process_groups(analysis)
            
            # 4. Generar resumen
            return self._build_export_summary(
                validation, analysis, results, groups_processed, group_errors, start_time
            )
            
        except Exception as e:
            self.logger.error("Error crítico en separación: %s", str(e))
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }

    def _process_groups(self, analysis: dict[str, Any]) -> tuple[list[ExportResult], int, list[str]]:
        results = []
        groups_processed = 0
        group_errors = []
        
        for group_name, group_df in self.df.groupby(self.config.separator_column):
            try:
                # Verificar cancelación
                if hasattr(self, '_cancelled') and self._cancelled:
                    break
                
                # Procesar grupo individual
                result = self._export_group(str(group_name), group_df)
                results.append(result)
                groups_processed += 1
                
                if not result.success:
                    error_msg = result.error or "Error exportando grupo"
                    self.failed_groups[str(group_name)] = error_msg
                    group_errors.append(f"Grupo '{group_name}': {error_msg}")
                
                # Callback de progreso (se lee en cada iteración para soportar
                # asignación posterior a la creación del splitter)
                callback = self.config.progress_callback or self.progress_callback
                if callback:
                    callback(groups_processed, analysis['estimated_groups'])
                
            except Exception as e:
                self.logger.error("Error procesando grupo %s: %s", group_name, str(e))
                error_result = ExportResult(
                    success=False,
                    group_name=str(group_name),
                    error=str(e)
                )
                results.append(error_result)
                self.failed_groups[str(group_name)] = str(e)
                group_errors.append(f"Grupo '{group_name}': {str(e)}")
        
        return results, groups_processed, group_errors

    def _build_export_summary(
        self,
        validation: ValidationResult,
        analysis: dict[str, Any],
        results: list[ExportResult],
        groups_processed: int,
        group_errors: list[str],
        start_time: float
    ) -> dict[str, Any]:
        processing_time = time.time() - start_time
        successful_exports = [r for r in results if r.success]
        failed_exports = [r for r in results if not r.success]
        
        return {
            'success': len(successful_exports) > 0,
            'files_created': [r.file_path for r in successful_exports],
            'groups_processed': groups_processed,
            'total_rows': self.df.shape[0],
            'successful_exports': len(successful_exports),
            'failed_exports': len(failed_exports),
            'processing_time': processing_time,
            'errors': validation.errors + group_errors,
            'warnings': validation.warnings,
            'failed_groups': self.failed_groups,
            'analysis': analysis
        }
    
    def _export_group(self, group_name: str, group_df: pd.DataFrame) -> ExportResult:
        """Exportar un grupo individual"""
        start_time = time.time()
        result = ExportResult()
        result.group_name = group_name
        result.timestamp = datetime.now()
        
        try:
            # Generar nombre de archivo
            filename = self._generate_filename_for_group(group_name, len(group_df))
            file_path = str(Path(self.config.output_folder) / filename)
            
            # Verificar conflictos de nombres
            file_path = self._resolve_filename_conflicts(file_path)
            
            # Crear archivo Excel con plantilla
            success = self._create_excel_file_with_template(file_path, group_df)
            
            if success:
                result.success = True
                result.file_path = file_path
                result.rows_processed = len(group_df)
                result.processing_time = time.time() - start_time
                self.created_files.append(file_path)
            else:
                result.success = False
                result.error = "Error creando archivo Excel"
            
            return result
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.processing_time = time.time() - start_time
            return result
    
    def _create_excel_file_with_template(self, output_path: str, data: pd.DataFrame) -> bool:
        """Crear archivo Excel usando plantilla preservando formato"""
        try:
            # Usar preserver simple que evita problemas de recursión
            from core.simple_excel_preserver import create_excel_with_simple_format_preservation
            
            # Aplicar mapeo de columnas
            if not self.config.column_mapping:
                self.config.column_mapping = self.config.get_default_mapping(data.columns.tolist())
            
            # Convertir DataFrame a dict para el preserver
            data_dict: dict[str, Any] = {}
            for row_offset, (_, row_data) in enumerate(data.iterrows()):
                data_dict[str(row_offset)] = row_data.to_dict()
            
            # Crear archivo con preservación de formato
            success = create_excel_with_simple_format_preservation(
                template_path=self.config.template_path,
                output_path=output_path,
                data=data_dict,
                column_mapping=self.config.column_mapping,
                start_cell=self.config.start_cell
            )
            
            if success:
                self.logger.info("Archivo Excel creado con formato preservado: %s", output_path)
            
            return success
            
        except ImportError:
            # Fallback al método original si el preserver no está disponible
            self.logger.warning("SimpleExcelPreserver no disponible, usando método original")
            return self._create_excel_file_with_template_fallback(output_path, data)
            
        except Exception as e:
            self.logger.error("Error creando archivo Excel con formato preservado: %s", str(e))
            return False
    
    def _create_excel_file_with_template_fallback(self, output_path: str, data: pd.DataFrame) -> bool:
        """Método fallback para crear archivo Excel sin preserver de formato"""
        try:
            # Cargar plantilla
            workbook = load_workbook(self.config.template_path, data_only=False)
            sheet = workbook.active
            
            # Determinar posición inicial
            from openpyxl.utils import column_index_from_string
            start_row, _ = coordinate_to_tuple(self.config.start_cell)
            
            # Aplicar mapeo de columnas
            if not self.config.column_mapping:
                self.config.column_mapping = self.config.get_default_mapping(data.columns.tolist())
            
            # Insertar datos MINIMALISTA para preservar formato
            for row_offset, (_, row_data) in enumerate(data.iterrows()):
                excel_row = start_row + row_offset
                
                for df_col, excel_col_letter in self.config.column_mapping.items():
                    if df_col in data.columns:
                        excel_col_idx = column_index_from_string(excel_col_letter)
                        cell = sheet.cell(row=excel_row, column=excel_col_idx)
                        
                        # Solo cambiar el VALOR, no tocar otros atributos
                        value = row_data[df_col]
                        if pd.isna(value):
                            cell.value = None
                        else:
                            cell.value = value
            
            # Guardar archivo
            workbook.save(output_path)
            workbook.close()
            
            return True
            
        except Exception as e:
            self.logger.error("Error en método fallback creando archivo Excel: %s", str(e))
            return False
    
    @staticmethod
    def _resolve_filename_conflicts(file_path: str) -> str:
        """Resolver conflictos de nombres de archivo"""
        p = Path(file_path)
        if not p.exists():
            return file_path
        
        # Auto-numeración
        name_part = p.stem
        ext = p.suffix
        counter = 1
        
        while True:
            new_path = f"{name_part}_{counter:02d}{ext}"
            if not Path(new_path).exists():
                return new_path
            counter += 1
            
            # Límite de seguridad
            if counter > 999:
                timestamp = str(int(time.time()))
                return f"{name_part}_{timestamp}{ext}"
    
    def cancel_operation(self) -> None:
        """Cancelar operación en curso"""
        self._cancelled = True
    
    def cleanup_temp_files(self) -> None:
        """Limpiar archivos temporales en caso de cancelación"""
        for file_path in self.created_files:
            try:
                p = Path(file_path)
                if p.exists():
                    p.unlink()
            except Exception as e:
                self.logger.warning("No se pudo limpiar archivo temporal %s: %s", file_path, str(e))
