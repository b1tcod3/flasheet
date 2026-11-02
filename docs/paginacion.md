# Paginación — Documentación Completa

Documentación de la **paginación virtual** de Flash View Sheet, compuesta por el gestor lógico `PaginationManager` y el modelo virtualizado `VirtualizedPandasModel`.

---

## Índice

1. [Visión General](#1-visión-general)
2. [PaginationManager (app/services/pagination_manager.py)](#2-paginationmanager-appservicespagination_managerpy)
3. [VirtualizedPandasModel (app/models/pandas_model.py)](#3-virtualizedpandasmodel-appmodelspandas_modelpy)
4. [Formato de valores](#4-formato-de-valores)
5. [Integración con DataView](#5-integración-con-dataview)
6. [Resumen](#6-resumen)

---

## 1. Visión General

La paginación tiene dos capas:

1. **`PaginationManager`** — lógica de páginas (independiente de la UI): divide el DataFrame en páginas, navega y filtra. Emite señales Qt para notificar a la vista.
2. **`VirtualizedPandasModel`** — `QAbstractTableModel` que alimenta el `QTableView` con **carga bajo demanda por chunks**, evitando materializar filas que no se ven.

Flujo: `PaginationManager.get_page_data()` → página (≤ page_size filas) → `VirtualizedPandasModel` (que a su vez hace chunking si el dataset supera `VIRTUALIZATION_THRESHOLD`). Esto permite manejar datasets grandes sin copiar todo a la vista.

---

## 2. PaginationManager (app/services/pagination_manager.py)

```python
class PaginationManager(QObject):
    page_changed = Signal(int)          # Página actual cambió
    page_size_changed = Signal(int)     # Tamaño de página cambió
    data_changed = Signal()             # Datos subyacentes cambiaron
    total_pages_changed = Signal(int)   # Número total de páginas cambió

    def __init__(self, df: pd.DataFrame | None = None, page_size: int = 10) -> None
```

### Estado interno

| Campo | Descripción |
|-------|-------------|
| `original_df` | Copia del DataFrame original |
| `filtered_df` | Copia filtrada (mostrada) |
| `current_page` | Página actual (1-indexed) |
| `page_size` | Filas por página (default 10) |
| `total_pages` | `ceil(len(filtered_df) / page_size)`; 0 si vacío |

### Métodos

#### Navegación

| Método | Descripción |
|--------|-------------|
| `set_current_page(page)` | Valida `1 <= page <= total_pages`, emite `page_changed` |
| `next_page()` / `previous_page()` / `first_page()` / `last_page()` | Navegación con emisión condicionada |
| `can_go_next() -> bool` | `current_page < total_pages` |
| `can_go_previous() -> bool` | `current_page > 1` |

#### Datos

| Método | Descripción |
|--------|-------------|
| `set_data(df, preserve_page=True)` | Copia df; si `preserve_page` y la página sigue válida, la conserva; si no, resetea a 1. Emite `data_changed` (+ `page_changed` según el caso) |
| `set_page_size(size)` | Si `size > 0` y distinto, recalcula página para mantener **posición aproximada** (`old_start_row // new_size + 1`), emite `page_size_changed` |
| `get_page_size() -> int` | Tamaño actual |
| `get_page_data() -> pd.DataFrame` | `filtered_df.iloc[start:end].copy()` de la página actual |
| `get_total_pages() -> int` / `get_total_rows() -> int` / `get_current_page() -> int` | Getters |

#### Filtrado

| Método | Descripción |
|--------|-------------|
| `apply_filter(column, term)` | `str.contains(case=False, na=False, regex=False)`; término vacío → todos los datos. En error → datos completos. Resetea a página 1 y emite `data_changed` |
| `clear_filter()` | `filtered_df = original_df`, página 1, emite `data_changed` |
| `get_filter_info() -> dict` | `original_rows`, `filtered_rows`, `filtered_out`, `is_filtered` |

#### Información

| Método | Descripción |
|--------|-------------|
| `get_page_info() -> dict` | `current_page`, `total_pages`, `total_rows`, `start_row`, `end_row`, `rows_in_page` (0,0,0,0,0,0 si vacío; `start_row` 1-indexed) |
| `_update_total_pages()` | Recalcula, emite `total_pages_changed` y corrige página si excede (emit `page_changed`) |

---

## 3. VirtualizedPandasModel (app/models/pandas_model.py)

```python
class VirtualizedPandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame | None = None, chunk_size: int | None = None) -> None
```

Modelo que adapta un DataFrame para `QTableView`. Inserta la raíz del proyecto en `sys.path` e importa `config.optimization_config` para los umbrales.

### Estado interno

| Campo | Descripción |
|-------|-------------|
| `full_df` | DataFrame completo |
| `chunk_size` | Filas por chunk (`optimization_config.DEFAULT_CHUNK_SIZE` = 1000 si no se pasa) |
| `total_rows` / `total_cols` | Dimensiones |
| `data_cache` | `dict[int, pd.DataFrame]` chunks cacheados |
| `cache_size` | `optimization_config.MAX_CACHE_CHUNKS` = 10 |
| `enable_virtualization` | `row_count > VIRTUALIZATION_THRESHOLD` (5000) |

Si **no** se activa la virtualización, `current_df = full_df` (acceso directo). Si se activa, las celdas se sirven desde chunks cargados bajo demanda.

### API del modelo (Qt)

| Método | Descripción |
|--------|-------------|
| `rowCount(parent) -> int` | `total_rows` (0 si parent válido) |
| `columnCount(parent) -> int` | `total_cols` |
| `data(index, role) -> str | None` | Solo `DisplayRole`: virtualizado → chunk; no virtualizado → `full_df.iloc`; formatea con `_format_value` |
| `flags(index)` | `ItemIsSelectable | ItemIsEnabled` (solo lectura) |
| `headerData(section, orientation, role)` | Horizontal → nombre de columna; Vertical → `section + 1` |
| `setData(index, value, role)` | `EditRole`: actualiza `full_df` y el chunk cacheado; emite `dataChanged` |
| `sort(column, order)` | `layoutAboutToBeChanged` → `sort_values` → `reset_index` → limpia cache → `layoutChanged` |
| `get_sorted_data() -> pd.DataFrame` | Copia de `full_df` (datos ordenados) |

### Chunking

| Método | Descripción |
|--------|-------------|
| `_get_chunk_data(row) -> pd.DataFrame` | `chunk_index = row // chunk_size`; sirve desde `data_cache` o lo carga con `iloc[start:end].copy()` gestionando cache |
| `_manage_cache(current_chunk)` | Si el cache está lleno, elimina chunks con distancia `> cache_size // 2` del actual |
| `update_data(new_df)` | `beginResetModel` → limpia cache, actualiza df/dimensiones, recalcula virtualización → `endResetModel` |
| `get_chunk_size()` / `set_chunk_size(size)` | Getter/setter (setter limpia cache y resetea modelo) |

---

## 4. Formato de valores

`_format_value(value) -> str` (módulo `pandas_model.py`):

| Valor | Resultado |
|-------|-----------|
| NaN | `""` |
| `inf` / `-inf` | `""` |
| float entero (ej. `5.0`) | `"5"` |
| float decimal | `str(value).replace(".", ",")` (coma decimal) |
| otro | `str(value)` |

> ⚠️ Usa coma decimal en floats (convención de visualización en español).

---

## 5. Integración con DataView

```
DataView.set_data(df)
    └─ PaginationManager.set_data(df)
          ├─ _update_total_pages() → total_pages_changed
          └─ data_changed
                │
DataView._connect_pagination_signals()  # conecta las 4 señales del manager
DataView.update_view()
    └─ model = VirtualizedPandasModel(pagination_manager.get_page_data())
          ├─ chunking bajo demanda si > 5000 filas
          └─ data_updated.emit(filtered_df)

Navegación: next/prev/first/last → manager → page_changed → update_view
Filtro rápido/texto → manager.apply_filter(column, term) → data_changed → update_view
```

---

## 6. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Gestor** | `PaginationManager` (`app/services/`) — lógica pura + señales Qt |
| **Modelo** | `VirtualizedPandasModel` (`app/models/`) — carga bajo demanda |
| **Umbral de virtualización** | 5 000 filas (`OptimizationConfig.VIRTUALIZATION_THRESHOLD`) |
| **Chunk size** | 1 000 filas (configurable vía `FLASH_CHUNK_SIZE`) |
| **Cache** | 10 chunks (configurable vía `FLASH_CACHE_CHUNKS`) |
| **Página por defecto** | 10 filas (UI permite 10–1000) |
| **Filtrado** | case-insensitive, `regex=False`, sin contar NaN |
| **Formato numérico** | Coma decimal; NaN/Inf → vacío |
