# core/performance_optimizer.py — Documentación Completa

Optimizador de rendimiento de Flash View Sheet. Implementa chunking inteligente, gestión de memoria, monitoreo de recursos y optimizaciones de openpyxl para la exportación separada con plantillas Excel.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Importaciones](#2-importaciones)
3. [Enums y Dataclasses](#3-enums-y-dataclasses)
   - [3.1 ChunkingStrategy](#31-chunkingstrategy)
   - [3.2 ProcessingMetrics](#32-processingmetrics)
   - [3.3 SystemResources](#33-systemresources)
4. [Clase PerformanceOptimizer](#4-clase-performanceoptimizer)
5. [Clase ExcelFormatOptimizer](#5-clase-excelformatoptimizer)
6. [Clase ProgressMonitor](#6-clase-progressmonitor)
7. [Diagrama de Dependencias](#7-diagrama-de-dependencias)
8. [Resumen](#8-resumen)

---

## 1. Visión General

`core/performance_optimizer.py` (462 líneas) da soporte de rendimiento al sistema de exportación separada (`ExcelTemplateSplitter` en `core/data_handler.py`). Contiene tres clases:

- **`PerformanceOptimizer`** — determina estrategia de chunking, calcula chunk size óptimo, procesa DataFrames por chunks con cleanup de memoria, monitorea recursos del sistema y genera métricas de procesamiento
- **`ExcelFormatOptimizer`** — carga plantillas Excel optimizadas y preserva formato durante la inserción de datos (cache de formatos por rango)
- **`ProgressMonitor`** — controla cancelación/pausa/reanudación de operaciones y reporta progreso por callback

**Diseño:**
- `psutil` es obligatorio para monitoreo real; si falla, devuelve valores de respaldo
- El algoritmo de chunking implementa la heurística `determine_optimal_chunking_strategy` (IntelligentChunkingAlgorithm)
- `ProcessingMetrics` permite reportar en tiempo real (velocidad, memoria, tiempo restante)

---

## 2. Importaciones

| Símbolo | Módulo | Uso |
|---------|--------|-----|
| `time` | `time` | Medición de tiempos |
| `psutil` | `psutil` | Memoria, CPU, disco |
| `gc` | `gc` | Garbage collection |
| `threading` | `threading` | Sincronización (pausa) |
| `Iterator`, `Any`, `Callable` | `typing` | Tipos |
| `dataclass` | `dataclasses` | Dataclasses |
| `Enum` | `enum` | Estrategias |
| `pd` | `pandas` | DataFrames |
| `openpyxl` | `openpyxl` | Workbooks |
| `Table`, `TableStyleInfo` | `openpyxl.worksheet.table` | Tablas Excel |

---

## 3. Enums y Dataclasses

### 3.1 ChunkingStrategy

| Miembro | Valor | Descripción |
|---------|-------|-------------|
| `NONE` | `"none"` | Procesamiento directo |
| `MODERATE` | `"moderate"` | Chunking conservador |
| `SIZE_BASED` | `"size"` | Basado en tamaño de grupos |
| `GROUP_BASED` | `"group"` | Basado en número de grupos |
| `AGGRESSIVE` | `"aggressive"` | Chunking agresivo |

### 3.2 ProcessingMetrics (dataclass)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `start_time` | `float` | Inicio de la operación |
| `current_group` | `int` | Grupo actual |
| `total_groups` | `int` | Total de grupos |
| `groups_completed` | `int` | Grupos completados |
| `current_memory_mb` | `float` | Memoria actual |
| `peak_memory_mb` | `float` | Pico de memoria |
| `estimated_time_remaining` | `float` | Tiempo restante estimado |
| `current_processing_speed` | `float` | Velocidad (grupos/segundo) |
| `files_created` | `int` | Archivos creados |
| `total_rows_processed` | `int` | Filas procesadas |

### 3.3 SystemResources (dataclass)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `available_memory_mb` | `float` | Memoria disponible |
| `total_memory_mb` | `float` | Memoria total |
| `cpu_percent` | `float` | Uso de CPU |
| `disk_free_space_mb` | `float` | Espacio libre en disco |
| `disk_write_speed_mbps` | `float` | Velocidad de escritura estimada |

---

## 4. Clase PerformanceOptimizer

```python
class PerformanceOptimizer:
    def __init__(self, chunking_strategy: ChunkingStrategy = ChunkingStrategy.MODERATE) -> None
```

**Atributos:** `chunking_strategy`, `memory_threshold_mb=2048`, `performance_cache`, `format_cache`, `active_monitors`.

### API pública

| Método | Firma | Descripción |
|--------|-------|-------------|
| `determine_optimal_chunking_strategy` | `(df, separator_column) -> ChunkingStrategy` | **Algoritmo de decisión:** si memoria > 2048 MB o > 1M filas → `AGGRESSIVE`; si > 100 grupos y varianza de tamaño > 10000 → `GROUP_BASED`; si grupo más grande > 50000 → `SIZE_BASED`; si memoria > 500 MB → `MODERATE`; si no → `NONE`. Devuelve `NONE` si la columna no existe |
| `get_optimal_chunk_size` | `(strategy, total_rows, unique_groups) -> int` | `MODERATE`: `min(10000, max(1000, rows//4))`; `SIZE_BASED`: `min(5000, max(500, rows//10))`; `GROUP_BASED`: `min(1000, max(100, groups//2))`; `AGGRESSIVE`: `min(1000, max(100, rows//20))`; `NONE`: `total_rows` |
| `process_dataframe_in_chunks` | `(df, separator_column, chunk_size) -> Iterator[tuple[str, pd.DataFrame]]` | Yield de nulos primero como `('Valores_Nulos', ...)`, luego grupos (grupos grandes en sub-chunks `_chunk_N`); GC cada 5 chunks |
| `monitor_memory_usage` | `() -> SystemResources` | Lee psutil; valores de respaldo si falla |
| `optimize_memory_usage` | `() -> None` | `gc.collect()`; si memoria > 80%, limpia `format_cache` y fuerza GC 3 veces |
| `get_processing_metrics` | `(start_time, current_group, ...) -> ProcessingMetrics` | Métricas en tiempo real |

---

## 5. Clase ExcelFormatOptimizer

| Método | Firma | Descripción |
|--------|-------|-------------|
| `load_excel_template_optimized` | `(template_path) -> openpyxl.Workbook` | Carga plantilla con `data_only=False` |
| `preserve_format_during_insert` | `(workbook, worksheet, data_range) -> None` | Cachea y reaplica formatos durante la inserción |
| `_detect_existing_data_range` | `(sheet, start_cell) -> str` | Detecta rango de datos existente |
| `_cache_existing_formats` | `(sheet, data_range) -> dict[tuple[int,int], Any]` | Cache de formatos por celda |
| `_apply_cached_format` | `(cell, cached_format) -> None` | Aplica formato cacheado |
| `_cell_coordinates_to_indices` / `_column_letter_to_index` | — | Utilidades de coordenadas |

---

## 6. Clase ProgressMonitor

| Método | Firma | Descripción |
|--------|-------|-------------|
| `cancel_operation` | `() -> None` | Marca cancelado |
| `pause_operation` | `() -> None` | Pausa |
| `resume_operation` | `() -> None` | Reanuda |
| `is_cancelled` | `() -> bool` | Estado de cancelación |
| `is_paused` | `() -> bool` | Estado de pausa |
| `wait_if_paused` | `() -> None` | Bloquea mientras esté pausado |
| `add_progress_callback` | `(callback: Callable[[ProcessingMetrics], None])` | Registra callback |
| `update_progress` | `(metrics: ProcessingMetrics)` | Notifica a callbacks |
| `reset` | `() -> None` | Reinicia estado |

---

## 7. Diagrama de Dependencias

```
core/performance_optimizer.py
├── psutil (memoria/CPU/disco)
├── openpyxl (workbooks, tablas)
├── pandas (DataFrames)
└── usado por core/data_handler.py (ExcelTemplateSplitter)
    └── app/widgets/export_separated_dialog.py (config de rendimiento)
```

---

## 8. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Líneas** | 462 |
| **Clases** | `PerformanceOptimizer`, `ExcelFormatOptimizer`, `ProgressMonitor` |
| **Estrategias** | 5 (`ChunkingStrategy`) |
| **Dataclasses** | `ProcessingMetrics`, `SystemResources` |
| **Dependencias** | psutil (monitoreo), openpyxl, pandas |
| **Uso principal** | Exportación separada con plantillas Excel |
