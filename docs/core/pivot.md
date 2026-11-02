# Tablas Pivote — Documentación Completa

Documentación del sistema de tablas pivote de Flash View Sheet. El pivote automático moderno vive en `app/services/pivot_service.py` (PivotService), que genera múltiples tablas por combinación categórica × numérica; `core/data_handler.py` conserva una función pivote clásica de referencia.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Arquitectura](#2-arquitectura)
3. [PivotService (app/services/pivot_service.py)](#3-pivotservice-appservicespivotservicepy)
   - [3.1 Constructor y estado](#31-constructor-y-estado)
   - [3.2 Detección de columnas](#32-detección-de-columnas)
   - [3.3 Ranking de combinaciones](#33-ranking-de-combinaciones)
   - [3.4 Generación de pivotes automáticos](#34-generación-de-pivotes-automáticos)
   - [3.5 Estadísticas](#35-estadísticas)
4. [pivotar_datos (core/data_handler.py)](#4-pivotardatos-coredatahandlerpy)
5. [Vista de resultados (PivotResultsView)](#5-vista-de-resultados-pivotresultsview)
6. [Flujo de ejecución](#6-flujo-de-ejecución)
7. [Diagrama de Dependencias](#7-diagrama-de-dependencias)
8. [Resumen](#8-resumen)

---

## 1. Visión General

Flash View Sheet genera **tablas pivote automáticas**: sin que el usuario configure índices, columnas y valores, el sistema:

1. Detecta las columnas **categóricas** (≤ 20 valores únicos) y **numéricas** del dataset
2. Rankea todas las combinaciones `categórica × numérica` por volumen de datos no nulos
3. Genera hasta `MAX_PIVOT_TABS = 5` tablas con las combinaciones de mayor score
4. Muestra los resultados en `PivotResultsView` como pestañas exportables

**Importante (cambio relevante):** el `PivotService` fue **refactorizado de 471 → 115 líneas**. La versión actual **ya no** usa `pd.crosstab`, agregaciones de fallback, ni la cache `last_config`. El doc `docs/pivot_service.md` describe la API antigua (véase la nota al final).

---

## 2. Arquitectura

```
app/services/pivot_service.py   → PivotService (lógica de generación, stateless salvo last_result)
    └── app/widgets/pivot_results_view.py → PivotResultsView, PivotTabWidget (UI)
core/data_handler.py            → pivotar_datos() (función clásica de referencia)

AppCoordinator.auto_pivot()     → orquesta: PivotService.generate_auto_pivots() → ViewCoordinator.set_pivot_result
```

---

## 3. PivotService (app/services/pivot_service.py)

```python
class PivotService:
    def __init__(self) -> None
```

### 3.1 Constructor y estado

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `last_result` | `pd.DataFrame \| None` | Último pivote generado (primera combinación) |

Métodos de ciclo de vida:
- `cleanup() -> None` — libera `last_result`

### 3.2 Detección de columnas

#### `detect_categorical_columns(df) -> list[str]`
```python
[c for c in df.columns if df[c].nunique() <= 20]
```
Solo columnas con **≤ 20 valores únicos**.

#### `detect_numeric_columns(df) -> list[str]`
```python
[c for c in df.columns if is_numeric_dtype(df[c])]
```
Usa `pandas.api.types.is_numeric_dtype` (soporta Int64, float32, int32, nullable integers).

### 3.3 Ranking de combinaciones

#### `rank_combinations(df, cat_cols, num_cols) -> list[tuple[str, str, int]]`
- Genera todas las combinaciones `(cat, num)`
- Score = `int(df[num].notna().sum())` (volumen de datos no nulos)
- Ordena de mayor a menor score

### 3.4 Generación de pivotes automáticos

#### `generate_auto_pivots(df, progress_callback=None) -> dict[str, pd.DataFrame]`
1. Detecta categóricas y numéricas
2. Rankea y toma las **top 5** combinaciones (`MAX_PIVOT_TABS`)
3. Por cada combinación:
   - `pd.pivot_table(df, index=cat, values=num, aggfunc=['count', 'nunique', 'sum'], margins=False, dropna=True)`
   - Renombra columnas: `['conteo', 'conteo_unico', 'suma']` si hay 3, si no `'_'.join(...)` por col MultiIndex
   - `reset_index()` y añade una fila **Total** al final (`pd.concat`)
   - Guarda como `{f"{cat} × {num}": pivot_df}`
4. Si hubo resultados, `last_result = results[primera_clave]`
5. Llama `progress_callback(idx, total)` por cada combinación

**Clave de resultado:** `"<cat> × <num>"` (ej. `"Region × Ventas"`).

### 3.5 Estadísticas

#### `get_pivot_stats() -> dict[str, Any] | None`
Si `last_result` existe, devuelve `{'rows', 'columns', 'shape'}`; si no, `None`.

---

## 4. pivotar_datos (core/data_handler.py)

```python
def pivotar_datos(df, index, columns, values, aggfunc='mean') -> pd.DataFrame
```

Función clásica de pivote único:
- `aggfunc`: `'mean'` → `np.mean`, `'sum'` → `np.sum`, `'count'`, o cualquier función pasada como string
- Usa `df.pivot_table(...)` y `reset_index()`
- Devuelve `pd.DataFrame()` vacío si falla

**Uso actual:** función de referencia/legacy; la generación automática se delega a `PivotService`.

---

## 5. Vista de resultados (PivotResultsView)

En `app/widgets/pivot_results_view.py` (detalle en `docs/app/widgets.md`):

- **`PivotTabWidget(df, title)`** — pestaña individual con tabla por pivote
- **`PivotResultsView(QWidget)`**:
  - `set_pivot_results(results: dict[str, pd.DataFrame])` — crea pestañas QTabWidget
  - `get_results() -> dict[str, pd.DataFrame]`
  - `_export_all()` — exporta todos los resultados

---

## 6. Flujo de ejecución

```
Usuario → menú "Tabla Pivote → Generar Pivote Automático" (pivot_simple_action)
       → toolbar botón "Tabla Pivote" (view_pivot)
       → AppCoordinator.auto_pivot()
            → PivotService.generate_auto_pivots(df, progress)
            → ViewCoordinator / MainWindow actualiza PivotResultsView
            → PivotService.last_result = primer pivote
```

**Conectores relevantes:**
- `MenuBuilder.pivot_simple_action.triggered` → `coordinator.auto_pivot`
- `ToolbarManager.ViewSwitcher.view_pivot` → `_on_pivot_requested` → `coordinator.auto_pivot`
- `MenuBuilder.export_pivot_action.triggered` → `coordinator.exportar_resultado_pivote`

---

## 7. Diagrama de Dependencias

```
PivotService (app/services)
├── pandas (pivot_table, is_numeric_dtype)
├── config: MAX_PIVOT_TABS = 5
└── usado por AppCoordinator.auto_pivot()
      └── AppCoordinator → ViewCoordinator → PivotResultsView

core/data_handler.pivotar_datos() (legacy)
└── pandas + numpy
```

---

## 8. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Servicio** | `PivotService` (115 líneas, refactorizado) |
| **Límite de pestañas** | `MAX_PIVOT_TABS = 5` |
| **Detección categórica** | `nunique() <= 20` |
| **Detección numérica** | `is_numeric_dtype` |
| **Ranking** | Score = nº de valores no nulos, desc |
| **Agregaciones** | `count`, `nunique`, `sum` |
| **Estado** | Solo `last_result` |

---

## Nota sobre docs/pivot_service.md

El archivo `docs/pivot_service.md` describe la **API antigua** del servicio (471 líneas, con `pd.crosstab`, pivotes combinados, agregaciones de fallback, validación y cache `last_config`). Tras el refactor a 115 líneas, ese documento quedó desactualizado. La fuente de verdad actual es este documento y `docs/app/services.md`. Se recomienda reemplazar `docs/pivot_service.md` por una versión acorde al nuevo `PivotService` (o eliminarlo si `docs/app/services.md` lo cubre).
