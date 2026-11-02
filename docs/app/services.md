# app/services — Documentación Completa

Paquete de **servicios de la aplicación** Flash View Sheet. Cada servicio encapsula una responsabilidad de negocio y mantiene separación de la UI (excepto por hilos Qt `QThread`). Es la capa que `AppCoordinator` y `MainWindow` consumen.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Exportaciones públicas](#2-exportaciones-públicas)
3. [DataService (data_service.py)](#3-dataservice-dataservicepy)
4. [ExportService (export_service.py)](#4-exportservice-exportservicepy)
5. [FilterService (filter_service.py)](#5-filterservice-filterservicepy)
6. [PivotService (pivot_service.py)](#6-pivotservice-pivotservicepy)
7. [CleaningService (cleaning_service.py)](#7-cleaningservice-cleaningservicepy)
8. [PaginationManager (pagination_manager.py)](#8-paginationmanager-paginationmanagerpy)
9. [RecentFilesService (recent_files_service.py)](#9-recentfilesservice-recentfilesservicepy)
10. [JoinService (join_service.py)](#10-joinservice-joinservicepy)
11. [ProfilerService (profiler_service.py)](#11-profilerservice-profilerservicepy)
12. [VisualizationService (visualization_service.py)](#12-visualizationservice-visualizationservicepy)
13. [Diagrama de Dependencias](#13-diagrama-de-dependencias)
14. [Flujo de Señales](#14-flujo-de-señales)
15. [Resumen](#15-resumen)

---

## 1. Visión General

`app/services/` (10 archivos) agrupa la lógica de servicio:

- **`DataService`** — carga y estado de datos (ver `docs/data_service.md`, documentado en detalle aparte)
- **`ExportService`** — exportación a PDF/XLSX/CSV/SQL/imagen y exportación separada
- **`FilterService`** — filtrado con historial
- **`PivotService`** — tablas pivote automáticas (refactorizado; ver `docs/core/pivot.md`)
- **`CleaningService`** — limpieza de datos (delega en `core/data_cleaner.py`)
- **`PaginationManager`** — paginación de DataView (ver `docs/paginacion.md`)
- **`RecentFilesService`** — archivos recientes persistentes en `~/.flashsheet/recent_files.json`
- **`JoinService`** — orquestación stateless de joins + `JoinWorkerThread`
- **`ProfilerService`** — perfilado de datos + `ProfilerWorkerThread`
- **`VisualizationService`** — gráficos minimalistas (Tufte) + `VisualizerWorkerThread`

**Diseño:**
- Servicios "stateless" (`JoinService`, `ProfilerService`, `VisualizationService`) reciben el DataFrame por parámetro en cada llamada
- Los hilos `QThread` (`...WorkerThread`) evitan bloquear la UI
- `DataService` y `ExportService` mantienen estado ligero (DataFrames, diálogo de progreso)

---

## 2. Exportaciones públicas

`app/services/__init__.py` exporta:

```python
DataService, ExportService, FilterService, PivotService,
CleaningService, PaginationManager, RecentFilesService,
JoinService, JoinWorkerThread, compute_result_columns,
ProfilerService, ProfilerWorkerThread,
VisualizationService, VisualizerWorkerThread
```

---

## 3. DataService (data_service.py)

> Documentado en detalle en `docs/data_service.md` (390 líneas). Resumen:

- **`DataLoaderThread(QThread)`** — señales `data_loaded(object)`, `error_occurred(str)`, `progress_updated(int,int)`; carga vía `cargar_datos_con_opciones`
- **`FolderLoaderThread(QThread)`** — carga y consolida carpetas con `FolderLoader` + `ExcelConsolidator.consolidate_chunked`
- **`DataService`** — estado `df_original`/`df_vista_actual`, properties `has_data`, `datos_actuales`, `datos_originales`, `get_file_filter()`, `create_loader_thread()`, `create_progress_dialog()`, `cleanup()` (agresivo) / `clear_data()` (liviano)

---

## 4. ExportService (export_service.py)

```python
class ExportService:
    def __init__(self, parent_window=None) -> None
```

Delega en las funciones de `core/data_handler`.

### Método genérico

#### `_export_dataframe(df, filepath, extension, valid_extensions, export_func, success_message, error_prefix, *args, **kwargs) -> tuple[bool, str]`
1. Si `df is None or df.empty` → `(False, "No hay datos para exportar.")`
2. `filepath = self._ensure_extension(...)` — añade la extensión si no coincide con `valid_extensions`
3. Llama `export_func(df, filepath, *args, **kwargs)` y formatea el mensaje

### API de exportación

| Método | Firma | Extensión(es) |
|--------|-------|----------------|
| `export_to_pdf` | `(df, filepath)` | `.pdf` |
| `export_to_xlsx` | `(df, filepath)` | `.xlsx`, `.xls` |
| `export_to_csv` | `(df, filepath, delimiter=',')` | `.csv` |
| `export_to_sql` | `(df, filepath, table_name)` | `.db`, `.sqlite`, `.sqlite3` |
| `export_to_image` | `(table_widget, filepath)` | `.png`, `.jpg`, `.jpeg` |
| `export_separated` | `(df, config) -> dict` | Excel separado (usa `exportar_datos_separados`) |

### Otros métodos
- `_ensure_extension(filepath, extension, valid_extensions) -> str` — añade extensión si falta
- `_format_export_error(error_str) -> str` — formatea errores de exportación con sugerencias (Excel corrupto, permisos, plantilla, memoria)

---

## 5. FilterService (filter_service.py)

```python
class FilterService:
    def __init__(self) -> None:
        self.filter_history: list[dict] = []
```

Todas las operaciones devuelven `None` si `df is None or df.empty` y lanzan `ValueError` si la columna no existe.

| Método | Firma | Descripción |
|--------|-------|-------------|
| `apply_filter` | `(df, column, term, case_sensitive=False)` | `str.contains(regex=False, na=False)`, case-insensitive por defecto |
| `apply_regex_filter` | `(df, column, pattern)` | `str.contains(regex=True)` |
| `apply_numeric_filter` | `(df, column, operator, value)` | `>`, `<`, `>=`, `<=`, `==`, `!=` |
| `apply_date_filter` | `(df, column, start_date=None, end_date=None)` | `pd.to_datetime(errors='coerce')` + rango |
| `apply_value_filter` | `(df, column, values, exclude=False)` | `isin()` incluido/excluido |
| `clear_filters` | `() -> None` | Vacía historial |
| `get_filter_info` | `() -> dict | None` | Último filtro |
| `get_filter_summary` | `() -> str` | Resumen legible |
| `get_unique_values` | `(df, column, limit=100)` | Valores únicos |
| `get_column_stats` | `(df, column)` | count, null_count, unique_count, dtype + min/max/mean/median (num) o empty/avg_length (texto) |

Cada filtro registra su entrada en `filter_history`.

---

## 6. PivotService (pivot_service.py)

> Detalle completo en `docs/core/pivot.md`. Resumen (API actual, 115 líneas):

```python
MAX_PIVOT_TABS = 5

class PivotService:
    def __init__(self) -> None: self.last_result = None
```

| Método | Descripción |
|--------|-------------|
| `cleanup()` | Libera `last_result` |
| `detect_categorical_columns(df) -> list[str]` | `nunique() <= 20` |
| `detect_numeric_columns(df) -> list[str]` | `is_numeric_dtype` |
| `rank_combinations(df, cat_cols, num_cols) -> list[tuple[str,str,int]]` | Score = nº de no-nulos, desc |
| `generate_auto_pivots(df, progress_callback=None) -> dict[str, pd.DataFrame]` | Top-5 combinaciones `cat × num` con `pivot_table(aggfunc=['count','nunique','sum'])` + fila Total |
| `get_pivot_stats() -> dict | None` | rows/columns/shape de `last_result` |

---

## 7. CleaningService (cleaning_service.py)

```python
class CleaningService:  # Sin imports de PySide6
```

| Método | Descripción |
|--------|-------------|
| `ejecutar_limpieza_rapida(df) -> tuple[df, resumen]` | Aplica `limpieza_rapida` de `core/data_cleaner` (nulos→eliminar, duplicados, espacios) |
| `ejecutar_limpieza_personalizada(df, opciones) -> tuple[df, resumen]` | `opciones`: `'nulos'` ('eliminar'/'cero'/'promedio'), `'duplicados'` (bool), `'espacios'` (bool) |

Ambos lanzan `ValueError("No hay datos para limpiar")` si `df is None or df.empty`. Retornan `(DataFrame, resumen)`.

---

## 8. PaginationManager (pagination_manager.py)

> Detalle completo en `docs/paginacion.md`. Resumen:

```python
class PaginationManager(QObject):
    page_changed = Signal(int)
    page_size_changed = Signal(int)
    data_changed = Signal()
    total_pages_changed = Signal(int)
```

Gestor de paginación independiente de la UI (`original_df`, `filtered_df`, `current_page=1`, `page_size=10`, `total_pages`).

| Método | Descripción |
|--------|-------------|
| `set_data(df, preserve_page=True)` | Cambia datos conservando página si es posible |
| `set_page_size(size)` | Ajusta página para mantener posición aproximada |
| `get_page_data()` | Datos de la página actual (copia) |
| `next_page` / `previous_page` / `first_page` / `last_page` | Navegación |
| `can_go_next` / `can_go_previous` | Estado |
| `apply_filter(column, term)` / `clear_filter()` | Filtrado interno |
| `get_filter_info()` / `get_page_info()` | Información |
| `_update_total_pages()` | Recalcula y emite `total_pages_changed` |

---

## 9. RecentFilesService (recent_files_service.py)

```python
_MAX_RECENT = 10
```

Persistencia en `~/.flashsheet/recent_files.json`. Funciones de módulo: `_config_dir()`, `_recent_file()`, `_relative_time(ts)` (produce "ahora mismo", "hace N min", "hace N h", "hace N días", o fecha `%d/%m/%Y`).

| Método | Descripción |
|--------|-------------|
| `add(filepath)` | Inserta al inicio (dedupe por ruta resuelta), limita a 10, guarda |
| `get_recent(limit=10) -> list[dict]` | Solo entradas cuyo archivo exista; añade `relative_time` |
| `remove(filepath)` | Elimina por ruta resuelta |
| `clear()` | Vacía y guarda |
| `_load()` / `_save()` | Persistencia tolerante a `JSONDecodeError`/`OSError` |

Entradas: `{'filepath', 'filename', 'loaded_at'}`.

---

## 10. JoinService (join_service.py)

```python
class JoinService:  # stateless
```

Cada método crea un `DataJoinManager` temporal (detalle en `docs/core/join.md`).

| Método | Firma | Descripción |
|--------|-------|-------------|
| `validate_config` | `(left_df, right_df, config) -> ValidationResult` | `manager.validate_join(config)` |
| `execute_join` | `(left_df, right_df, config) -> JoinResult` | `manager.execute_join(config)` |
| `get_preview` | `(left_df, right_df, config, max_rows=10) -> pd.DataFrame` | `manager.get_join_preview(...)` |
| `estimate_operation_time` | `(left_df, right_df, config) -> float` | Heurística (CROSS `producto/1e6`, INNER `min/5e4`, resto `left/3e4`; ×1.2 integridad, ×1.1 sort; clamp 0.5–30 s) |

### `JoinWorkerThread(QThread)`

Señales: `progress_updated(int)`, `finished(object)`, `error_occurred(str)`. `run()` emite 10 → ejecuta join → 30 → 100. Respetan `isInterruptionRequested()`.

### `compute_result_columns(left_columns, right_columns, left_keys, right_keys, suffixes=('_left','_right')) -> list[str]`
Replica la lógica de nombres de columna de `pd.merge` sin ejecutar el merge (aplica sufijos a columnas en conflicto).

---

## 11. ProfilerService (profiler_service.py)

```python
class ProfilerService:  # stateless, tolerante a fallos por columna
```

Constantes de módulo: `_MAX_TOP_VALUES_UNIQUE=1000`, `_TOP_VALUES_COUNT=5`, `_HIGH_CARDINALITY_RATIO=0.9`, `_HIGH_NULL_PERCENT=50.0`, `_PROGRESS_START=5`, `_PROGRESS_END=95`.

| Método | Descripción |
|--------|-------------|
| `generate_profile(df, progress_callback=None) -> dict` | Perfil completo: `total_rows`, `total_columns`, `memory_usage_mb`, `duplicated_rows`, `data_quality_summary`, `columns` (perfil por columna) |
| `_empty_profile(df)` | Perfil vacío para df vacío/None |
| `_quality_summary(...)` | Resumen de calidad (alta cardinalidad, nulos altos, duplicados) |
| `_profile_column(df, col, total_rows)` | Tipo detallado, nulos, cardinalidad, top values, distribución |
| `_numeric_stats(series)` | min/max/mean/median/std/quartiles |
| `_date_range(series)` | min/max/range de fechas |
| `_top_values(series)` | Top-5 valores |
| `_value_distribution_numeric/datetime(series)` | Distribución |

### `ProfilerWorkerThread(QThread)`
- Señales: `finished(object)`, `progress(int)`, `error(str)`
- `run()` llama `generate_profile` con callback de progreso

Helpers: `_safe_percent(count, total)`, `_to_native(value)`.

---

## 12. VisualizationService (visualization_service.py)

> Paleta minimalista (Tufte) — alto Data-Ink Ratio.

```python
class VisualizationService:  # métodos estáticos, stateless
```

Constantes de módulo (colores): `_ACCENT_COLOR="#4f46e5"`, `_ACCENT_FILL="#e0e7ff"`, `_MEDIAN_COLOR="#1e1b4b"`, `_SPINE_COLOR="#cbd5e1"`, `_GRID_COLOR="#e2e8f0"`, `_TICK_COLOR="#475569"`, `_LABEL_COLOR="#64748b"`, `_EDGE_COLOR="#ffffff"`, `_OUTLIER_COLOR="#ef4444"`, `_FIGURE_BG="#f8fafc"`. Parámetros: `_MAX_POINTS=10000`, `_BINS=25`, `_TOP_VALUES=10`, `_MAX_LABEL_LENGTH=20`, `_FONT_SIZE=9`, `_DISPLAYED_DPI=100`. Usa `matplotlib.use("Agg")`.

### `apply_minimal_theme(ax)`
Elimina spines top/right, estiliza left/bottom, rejilla Y sutil, ticks discretos.

### Métodos estáticos

| Método | Descripción |
|--------|-------------|
| `prepare_scatter_data(df, x_col, y_col, max_points=10000) -> (x, y)` | Submuestreo aleatorio si es masivo |
| `generate_histogram(df, column, bins=25) -> Figure` | Histograma de distribución |
| `generate_scatter(df, x_col, y_col, max_points) -> Figure` | Dispersión con transparencia (alpha 0.35) |
| `generate_bar_counts(df, column, top=10) -> Figure` | Barras horizontales Top-N |
| `generate_boxplot(df, column) -> Figure` | Cajas horizontal con outliers |
| `generate_figure(df, chart_type, x_col, y_col) -> Figure` | Dispatch: histogram/scatter/bar/boxplot; `ValueError` si no soportado |

### `VisualizerWorkerThread(QThread)`
Señales: `finished(object)`, `error(str)`. Llama `generate_figure` en `run()`.

---

## 13. Diagrama de Dependencias

```
app/services/
├── data_service.py        → core.data_handler, core.loaders.folder_loader, core.consolidation
├── export_service.py      → core.data_handler (exportar_*)
├── filter_service.py      → pandas
├── pivot_service.py       → pandas (pivot_table, is_numeric_dtype)
├── cleaning_service.py    → core.data_cleaner
├── pagination_manager.py  → pandas + PySide6 (QObject/Signal)
├── recent_files_service.py→ pathlib, json, time
├── join_service.py        → core.join (DataJoinManager, models)
├── profiler_service.py    → core.data_handler (obtener_estadisticas_basicas)
└── visualization_service.py → matplotlib

Consumido por:
├── app/app_coordinator.py (orquestador central)
├── app/menus/menu_builder.py (vía coordinator)
├── app/toolbar/toolbar_manager.py
└── app/widgets/ (vistas y diálogos)
```

---

## 14. Flujo de Señales

```
MainWindow._init_services() → crea DataService, ExportService, FilterService, PivotService
AppCoordinator.auto_pivot()      → PivotService.generate_auto_pivots() → PivotResultsView
AppCoordinator (join)            → JoinService.execute_join() en JoinWorkerThread
    JoinWorkerThread.progress_updated/finished/error_occurred → JoinDialog
AppCoordinator (perfil)          → ProfilerService.generate_profile() en ProfilerWorkerThread
    ProfilerWorkerThread.finished/progress/error → ViewCoordinator (ProfilingView)
AppCoordinator (visualizador)    → VisualizationService.generate_figure() en VisualizerWorkerThread
    VisualizerWorkerThread.finished/error → QuickVisualizerView
```

---

## 15. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Archivos** | 10 |
| **Servicios** | Data, Export, Filter, Pivot, Cleaning, Pagination, RecentFiles, Join, Profiler, Visualization |
| **Hilos** | DataLoaderThread, FolderLoaderThread, JoinWorkerThread, ProfilerWorkerThread, VisualizerWorkerThread |
| **Stateless** | Join, Profiler, Visualization |
| **Con estado** | Data (DataFrames), Filter (historial), Pivot (last_result), Pagination (páginas), RecentFiles (JSON) |
| **Dependencias core** | data_handler, data_cleaner, join, loaders, consolidation |
