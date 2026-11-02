# core/join — Documentación Completa

Sistema de cruce de datasets (join) de Flash View Sheet. Implementa operaciones INNER, LEFT, RIGHT, OUTER y CROSS sobre pandas, con validación, metadatos de resultado, chunking por memoria, historial persistente y excepciones tipadas.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Modelos de datos (models.py)](#2-modelos-de-datos-modelspy)
3. [Excepciones (exceptions.py)](#3-excepciones-exceptionspy)
4. [DataJoinManager](#4-datajoinmanager)
5. [Historial de Joins (join_history.py)](#5-historial-de-joins-joinhistorypy)
6. [Servicios de capa UI (join_service.py)](#6-servicios-de-capa-ui-joinservicepy)
7. [Diagrama de Dependencias](#7-diagrama-de-dependencias)
8. [Resumen](#8-resumen)

---

## 1. Visión General

El paquete `core/join/` (4 archivos) implementa la lógica pura de cruce de datos, sin dependencias de UI:

- **`models.py`** — `JoinType` (Enum), `JoinConfig`, `JoinResult`, `JoinMetadata`, `ValidationResult`
- **`exceptions.py`** — jerarquía `JoinError` + 4 subclases
- **`data_join_manager.py`** — `DataJoinManager`, la clase principal que ejecuta el merge con validación, estimación de memoria, chunking y estadísticas
- **`join_history.py`** — `JoinHistory`, historial persistente en JSON (`core/join/join_history.json`)

En la capa de aplicación, `app/services/join_service.py` envuelve a `DataJoinManager` en un servicio stateless con hilo `JoinWorkerThread` (ver `docs/app/services.md`).

**Diseño:**
- `DataJoinManager.__init__` hace `.copy()` de ambos DataFrames (no muta los originales)
- `psutil` es opcional (`_HAS_PSUTIL`); si falta, memoria disponible = 1024 MB
- Los joins por chunks evitan estallidos de memoria en cruces grandes o cross joins
- El resultado siempre incluye `JoinMetadata` con estadísticas detalladas

---

## 2. Modelos de datos (models.py)

### `JoinType` (Enum)
| Miembro | Valor |
|---------|-------|
| `INNER` | `"inner"` |
| `LEFT` | `"left"` |
| `RIGHT` | `"right"` |
| `OUTER` | `"outer"` |
| `CROSS` | `"cross"` |

### `JoinConfig` (dataclass)

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `join_type` | `JoinType` | (requerido) | Tipo de join |
| `left_keys` | `list[str]` | `[]` | Columnas de unión del lado izquierdo |
| `right_keys` | `list[str]` | `[]` | Columnas de unión del lado derecho |
| `suffixes` | `tuple[str, str]` | `('_left', '_right')` | Sufijos para columnas duplicadas |
| `validate_integrity` | `bool` | `True` | Validar tipos de las columnas clave |
| `sort_results` | `bool` | `True` | Ordenar por primera clave izquierda |
| `indicator` | `bool` | `False` | Incluir columna `_merge` |
| `include_columns` | `list[str]` | `[]` | Columnas a conservar en el resultado (vacío = todas) |
| `integrity_mode` | `str | None` | `'m:m'` | Modo `validate` de `pd.merge` |

### `JoinResult` (dataclass)
```python
data: pd.DataFrame
metadata: JoinMetadata
config: JoinConfig | None = None
success: bool = True
error_message: str = ""
```

### `JoinMetadata` (dataclass)
```python
left_rows, right_rows, result_rows: int
join_type: JoinType
join_keys: list[str]
matched_rows, left_only_rows, right_only_rows: int
memory_usage_mb: float
processing_time_seconds: float
timestamp: datetime
```

### `ValidationResult` (dataclass)
```python
is_valid: bool = True
errors: list[str] = []
warnings: list[str] = []
suggestions: list[str] = []
```

---

## 3. Excepciones (exceptions.py)

| Clase | Herencia | Propósito |
|-------|----------|-----------|
| `JoinError` | `Exception` | Base. Campos extra: `error_code`, `details` |
| `JoinValidationError` | `JoinError` | Error de validación de configuración |
| `JoinExecutionError` | `JoinError` | Error durante la ejecución |
| `MemoryLimitExceededError` | `JoinError` | Límite de memoria excedido |
| `UnsupportedJoinError` | `JoinError` | Tipo de join no soportado |

---

## 4. DataJoinManager

```python
class DataJoinManager:
    def __init__(self, left_df: pd.DataFrame, right_df: pd.DataFrame) -> None
```

Guarda `self.left_df = left_df.copy()` y `self.right_df = right_df.copy()`.

### `HOW_MAP` (módulo)
```python
HOW_MAP = {INNER: 'inner', LEFT: 'left', RIGHT: 'right', OUTER: 'outer'}
```
> `CROSS` **no** está en `HOW_MAP`; se maneja por separado con `how='cross'`.

### API pública

| Método | Firma | Descripción |
|--------|-------|-------------|
| `execute_join` | `(config) -> JoinResult` | Ejecuta validación → estimación de memoria → join (chunked o directo) → metadatos. Si validación falla, devuelve `JoinResult` vacío con `success=False`. Mide `start_time` |
| `validate_join` | `(config) -> ValidationResult` | Valida tipo soportado, claves requeridas, longitudes iguales, columnas existentes, warnings de dtype y columnas duplicadas |
| `get_join_preview` | `(config, max_rows=100) -> pd.DataFrame` | Preview del resultado (para CROSS usa muestras de 50 filas) |

### Métodos privados

| Método | Descripción |
|--------|-------------|
| `_extract_matched_count(result_df)` | Cuenta filas `_merge == 'both'` |
| `_compute_merge_stats(config)` | Merge OUTER temporal con indicator para conteos exactos de matched/left_only/right_only |
| `_apply_include_columns(df, config)` | Filtra por `include_columns` si está configurado |
| `_perform_join(config)` | `pd.merge` con `HOW_MAP`, `suffixes`, `indicator` (opcional), `validate` (si `validate_integrity`). Para CROSS usa `how='cross'`. Ordena si `sort_results` |
| `_calculate_metadata(config, result_df, start_time)` | `JoinMetadata` con stats, memoria y tiempo |
| `_create_empty_metadata(config, start_time)` | Metadatos con contadores a cero (para errores) |
| `_get_available_memory_mb()` | `psutil.virtual_memory().available / 1024 / 1024` o `1024.0` fallback |
| `_should_use_chunking(config, estimated_memory, available_memory)` | CROSS con ≥ 1M filas de producto → True; si no, `estimated_memory > available * 0.5` |
| `_perform_chunked_join(config)` | Despacha a cross o regular |
| `_perform_chunked_cross_join(config)` | Cruza el df menor por chunks de `max(1000, len//10)` |
| `_perform_chunked_regular_join(config)` | Si el df de referencia tiene < 10000 filas, delega a `_perform_join`. Si no, chunking de `max(5000, len//5)`; INNER hace `drop_duplicates` |
| `_estimate_memory_usage(config)` | Estimación `(filas_estimadas * columnas * 8) / 1024/1024 * 1.5` |

---

## 5. Historial de Joins (join_history.py)

### `JoinHistoryEntry` (dataclass)
```python
id, timestamp, left_dataset_name, right_dataset_name: str
config: dict, result_metadata: dict, success: bool, error_message: str
```

### `JoinHistory`
```python
def __init__(self, max_entries: int = 50, history_dir: Path | None = None, use_uuid: bool = True) -> None
```
Persiste en `core/join/join_history.json` (por defecto) hasta 50 entradas.

| Método | Firma | Descripción |
|--------|-------|-------------|
| `add_entry` | `(left_name, right_name, config: JoinConfig, result: JoinResult)` | Crea y guarda una entrada |
| `get_entries` | `(limit=None) -> list[JoinHistoryEntry]` | Entradas en orden |
| `get_entry` | `(entry_id) -> JoinHistoryEntry | None` | Busca por ID |
| `clear_history` | `() -> None` | Vacía el historial |
| `export_history` | `(filepath) -> None` | Exporta a JSON |
| `import_history` | `(filepath) -> None` | Importa desde JSON |
| `_entry_to_dict` / `_dict_to_entry` | — | Serialización |
| `_load_history` / `_save_history` | — | Persistencia |

---

## 6. Servicios de capa UI (join_service.py)

En `app/services/join_service.py` (detalle completo en `docs/app/services.md`):

- **`JoinService`** — stateless; cada método crea un `DataJoinManager` temporal:
  - `validate_config(left_df, right_df, config) -> ValidationResult`
  - `execute_join(left_df, right_df, config) -> JoinResult`
  - `get_preview(left_df, right_df, config, max_rows=10) -> pd.DataFrame`
  - `estimate_operation_time(left_df, right_df, config) -> float` (heurística: CROSS = `producto/1e6` s, INNER = `min/5e4` s, resto = `left/3e4` s; ×1.2 si valida integridad, ×1.1 si ordena; clamp 0.5–30 s)
- **`JoinWorkerThread(QThread)`** — señales `progress_updated(int)`, `finished(object)`, `error_occurred(str)`; emite 10 → 30 → 100
- **`compute_result_columns(left_columns, right_columns, left_keys, right_keys, suffixes=('_left','_right')) -> list[str]`** — replica la lógica de nombres de columna de `pd.merge` sin ejecutarlo

---

## 7. Diagrama de Dependencias

```
core/join/
├── models.py              → JoinType, JoinConfig, JoinResult, JoinMetadata, ValidationResult
├── exceptions.py          → JoinError + subclases
├── data_join_manager.py   → DataJoinManager (usa models + exceptions, psutil opcional)
├── join_history.py        → JoinHistory, JoinHistoryEntry (persiste join_history.json)
└── __init__.py            → (paquete; no exporta símbolos)

Consumido por:
└── app/services/join_service.py → JoinService, JoinWorkerThread, compute_result_columns
    └── app/widgets/join/join_dialog.py, joined_data_view.py
```

---

## 8. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Líneas** | ~800 (4 archivos) |
| **Tipos de join** | INNER, LEFT, RIGHT, OUTER, CROSS |
| **Clase principal** | `DataJoinManager` |
| **Extras** | Validación, metadatos, chunking por memoria, historial JSON |
| **Excepciones** | 5 (base + 4) |
| **Dependencia opcional** | psutil |
| **Persistencia** | `core/join/join_history.json` (50 entradas) |
