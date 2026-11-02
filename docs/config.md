# config — Documentación Completa

Documentación del módulo de **configuración de optimización** de Flash View Sheet (`config.py`, en la raíz del proyecto).

---

## Índice

1. [Visión General](#1-visión-general)
2. [OptimizationConfig](#2-optimizationconfig)
3. [Variables de entorno](#3-variables-de-entorno)
4. [Uso en la aplicación](#4-uso-en-la-aplicación)
5. [Resumen](#5-resumen)

---

## 1. Visión General

`config.py` centraliza los **umbrales de rendimiento y memoria** usados por la aplicación para decidir cuándo activar optimizaciones (virtualización, carga por chunks, muestreo de estadísticas, etc.).

Exporta:
- `OptimizationConfig` — clase de configuración con constantes y classmethods
- `get_config_from_env()` — función que aplica variables de entorno
- `optimization_config` — instancia global creada con `get_config_from_env()` (importada por `app/models/pandas_model.py`)

---

## 2. OptimizationConfig

```python
class OptimizationConfig:
```

### Constantes de límites

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `VIRTUALIZATION_THRESHOLD` | `5000` | Filas para activar paginación virtual |
| `CHUNK_LOADING_THRESHOLD` | `100 * 1024 * 1024` (100 MB) | Tamaño de archivo para carga por chunks |

### Paginación virtual

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `DEFAULT_CHUNK_SIZE` | `1000` | Filas por chunk en `VirtualizedPandasModel` |
| `MAX_CACHE_CHUNKS` | `10` | Máximo de chunks en cache |

### Carga de archivos (CSV)

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `CSV_CHUNK_SIZE_SMALL` | `50000` | Chunk para archivos pequeños (≤ 100 MB) |
| `CSV_CHUNK_SIZE_MEDIUM` | `25000` | Chunk para archivos medianos (100–500 MB) |
| `CSV_CHUNK_SIZE_LARGE` | `10000` | Chunk para archivos grandes (> 500 MB) |

### Estadísticas y filtrado

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `STATS_SAMPLE_THRESHOLD` | `100000` | Usar muestra para datasets > 100k filas |
| `STATS_SAMPLE_SIZE` | `50000` | Tamaño de la muestra |
| `FILTER_OPTIMIZATION_THRESHOLD` | `50000` | Optimizar filtrado para datasets > 50k filas |

### Exportación

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `PDF_MAX_ROWS` | `10000` | Máximo de filas para exportación a PDF |
| `IMAGE_MAX_SIZE` | `50 * 1024 * 1024` (50 MB) | Máximo para exportación a imagen |

### Classmethods

| Método | Firma | Descripción |
|--------|-------|-------------|
| `get_csv_chunk_size` | `(file_size_bytes: int) -> int` | `>500 MB` → LARGE, `>100 MB` → MEDIUM, resto → SMALL |
| `should_use_virtualization` | `(row_count: int) -> bool` | `row_count > VIRTUALIZATION_THRESHOLD` |
| `should_optimize_filtering` | `(row_count: int) -> bool` | `row_count > FILTER_OPTIMIZATION_THRESHOLD` |
| `should_sample_stats` | `(row_count: int) -> bool` | `row_count > STATS_SAMPLE_THRESHOLD` |

---

## 3. Variables de entorno

`get_config_from_env() -> OptimizationConfig` permite sobrescribir tres valores vía variables de entorno:

| Variable | Config que modifica |
|----------|---------------------|
| `FLASH_CHUNK_SIZE` | `DEFAULT_CHUNK_SIZE` |
| `FLASH_CACHE_CHUNKS` | `MAX_CACHE_CHUNKS` |
| `FLASH_VIRT_THRESHOLD` | `VIRTUALIZATION_THRESHOLD` |

Ejemplo:

```bash
FLASH_CHUNK_SIZE=2000 FLASH_CACHE_CHUNKS=5 python main.py
```

---

## 4. Uso en la aplicación

- **`app/models/pandas_model.py`** importa `optimization_config` (agrega la raíz del proyecto a `sys.path`): usa `DEFAULT_CHUNK_SIZE`, `MAX_CACHE_CHUNKS` y `should_use_virtualization()`.
- El chunk size de CSV (función `get_csv_chunk_size`) es usado por los loaders de `core/loaders/` para archivos grandes.
- `PDF_MAX_ROWS` limita exportaciones PDF y `IMAGE_MAX_SIZE` las de imagen en `ExportService`.

---

## 5. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Clase** | `OptimizationConfig` (constantes + classmethods) |
| **Instancia global** | `optimization_config` (de `get_config_from_env()`) |
| **Áreas** | Virtualización, chunking CSV, estadísticas, filtrado, exportación |
| **Env vars** | `FLASH_CHUNK_SIZE`, `FLASH_CACHE_CHUNKS`, `FLASH_VIRT_THRESHOLD` |
| **Consumidor principal** | `app/models/pandas_model.py` |
