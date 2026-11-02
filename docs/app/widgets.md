# app/widgets — Documentación Completa

Paquete de **widgets de UI** de Flash View Sheet. Contiene todas las vistas, diálogos y componentes visuales de la aplicación, incluyendo el modelo de datos virtualizado y el widget de paginación.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Exportaciones públicas](#2-exportaciones-públicas)
3. [Vistas principales](#3-vistas-principales)
4. [Vista de Datos (data_view.py)](#4-vista-de-datos-data_viewpy)
5. [Join (join/)](#5-join-join)
6. [Diálogos de carga y formato](#6-diálogos-de-carga-y-formato)
7. [Diálogos de exportación separada](#7-diálogos-de-exportación-separada)
8. [Diálogos auxiliares](#8-diálogos-auxiliares)
9. [Visualizador rápido](#9-visualizador-rápido)
10. [Diagrama de Dependencias](#10-diagrama-de-dependencias)
11. [Flujo de Datos](#11-flujo-de-datos)
12. [Resumen](#12-resumen)

---

## 1. Visión General

`app/widgets/` (16 módulos, ~5 300 líneas) agrupa toda la capa visual:

- **Vistas** (páginas del `QStackedWidget`): `MainView`, `DataView`, `JoinedDataView`, `PivotResultsView`, `ProfilingView`, `QuickVisualizerView`
- **Paneles/modal de información**: `InfoPanel`, `InfoModal`
- **Diálogos de carga**: `LoadOptionsDialog`, `CSVSeparatorDialog`, `ExcelSheetDialog`, `FolderLoadDialog` (+ `ColumnAlignmentPreview`)
- **Diálogos de exportación**: `ExportSeparatedDialog` (+ `ColumnMappingWidget`, `FilePreviewDialog`, `ExcelTemplateDialog`)
- **Otros**: `JoinDialog`, `AboutDialog`

Los widgets importan de **`core.*`** (raíz del proyecto) y de **`app.services`** / **`app.models`**. El `ViewCoordinator` los instancia lazy (ver `docs/app/view_manager.md`).

---

## 2. Exportaciones públicas

`app/widgets/__init__.py` exporta:

```python
InfoPanel, MainView, InfoModal, LoadOptionsDialog, CSVSeparatorDialog,
ExcelSheetDialog, ExportSeparatedDialog, AboutDialog, FolderLoadDialog,
JoinDialog, JoinedDataView, PivotResultsView, DataView, QuickVisualizerView
```

**No exportados:** `ColumnAlignmentPreview` (usado por `FolderLoadDialog`) y `ProfilingView` (usado vía `ViewCoordinator`).

---

## 3. Vistas principales

### MainView (main_view.py, 487 líneas)

```python
class MainView(QWidget):
    load_file_clicked = Signal()
    files_dropped = Signal(list)
    reload_with_options = Signal(str, int, dict, bool)   # (archivo, skip_rows, column_names, enable_visibility)
    recent_file_clicked = Signal(str)
    recent_file_remove = Signal(str)
```

Vista de bienvenida/carga: zona drag & drop (acepta archivos) + lista de archivos + recientes.

| Método | Descripción |
|--------|-------------|
| `load_file()` | Emite `load_file_clicked` |
| `add_file_to_list(filepath) -> FileItemWidget` | Añade ítem |
| `clear_file_list()` / `remove_file_from_list(filepath)` | Gestión de lista |
| `update_file_progress(filepath, loaded, total)` | Barra de progreso del ítem |
| `set_file_completed(filepath)` | Marca carga terminada, muestra botón de opciones |
| `set_file_info(filepath)` | Retrocompatibilidad (añade + completa) |
| `show_options()` | Abre `LoadOptionsDialog` (lazy) y emite `reload_with_options` |
| `set_original_columns(columns)` | Guarda columnas originales |
| `set_recent_files(entries)` | Puebla recientes |
| `dragEnterEvent` / `dropEvent` | Manejo de drag & drop → `files_dropped` |

**Widgets internos:** `FileItemWidget(QFrame)` — señales `cancel_clicked(str)`, `delete_clicked(str)`; `RecentFileWidget(QFrame)` — señales `clicked(str)`, `remove_clicked(str)`.

### ProfilingView (profiling_view.py, 426 líneas) — no exportada

```python
class ProfilingView(QWidget):
    visualize_requested = Signal(str)   # columna a graficar
```

Muestra el perfil de datos en tarjetas por columna con barras `_PercentBar`. Métodos: `show_loading()`, `set_progress(percent)`, `clear_profile()`, `set_profile(profile)`, `get_profile()`. Incluye botón "visualizar" que emite `visualize_requested` (icono `chart.svg`).

### PivotResultsView (pivot_results_view.py, 177 líneas)

```python
class PivotResultsView(QWidget):
    def set_pivot_results(results: dict[str, pd.DataFrame]) -> None
    def get_results() -> dict[str, pd.DataFrame]
    def _export_all() -> None     # todas las pestañas a un único .xlsx
```

Cada pestaña es `PivotTabWidget(QWidget)` con `QTableView` + `VirtualizedPandasModel`.

### QuickVisualizerView (quick_visualizer_view.py, 193 líneas)

```python
class QuickVisualizerView(QWidget):
    generate_requested = Signal(str, str, str)   # (chart_type, x_col, y_col)
```

Canvas Matplotlib (`FigureCanvasQTAgg`). Métodos: `set_dataframe(df)`, `set_selected_column(column)`, `current_chart_type()`, `show_figure(fig)`, `show_placeholder(msg)`, `show_error(msg)`, `get_df()`. Tipos: `histogram`, `scatter`, `bar`, `boxplot` (combo Y solo visible en scatter).

---

## 4. Vista de Datos (data_view.py)

```python
class DataView(QWidget):
    filter_applied = Signal(str, str)   # (columna, valor)
    filter_cleared = Signal()
    data_updated = Signal(object)       # DataFrame actual
```

Vista tabular con **filtros rápidos segmentados**, búsqueda por texto y **paginación**. Base de `JoinedDataView`.

### Estado interno

| Campo | Descripción |
|-------|-------------|
| `pagination_manager` | `PaginationManager` (ver `docs/paginacion.md`) |
| `pandas_model` | `VirtualizedPandasModel` (ver `docs/paginacion.md`) |
| `original_df` | DataFrame original (copia) |
| `_quick_filter_groups` | `dict[str, QButtonGroup]` de filtros segmentados |

### Métodos principales

| Método | Descripción |
|--------|-------------|
| `set_data(df)` | Copia df, crea/actualiza `PaginationManager`, filtros rápidos y `update_view` |
| `update_view()` | Página con `VirtualizedPandasModel`, actualiza info y emite `data_updated(filtered_df)` |
| `_apply_text_filter()` | Filtro por texto (botón o Enter) |
| `clear_filter()` | Limpia y emite `filter_cleared` |
| `first_page()` / `previous_page()` / `next_page()` / `last_page()` | Paginación |
| `_change_page_size(size)` | Cambia filas/página |
| `get_current_filter_info()` | Delega en el manager |
| `export_current_page() -> pd.DataFrame` | Página actual |
| `set_column_visibility_enabled(enabled)` | Stub (no-op) |

**Filtros rápidos:** para columnas con `1 < n_únicos <= 5` genera botones segmentados excluyentes (`_MAX_QUICK_FILTER_VALUES = 5`) que aplican filtro vía `PaginationManager`.

**Ordenamiento:** sorting habilitado en `QTableView`; `_on_model_sorted()` sincroniza protegido por `_sorting_in_progress`.

---

## 5. Join (join/)

### JoinDialog (join_dialog.py, 822 líneas)

```python
class JoinDialog(QDialog):
    join_completed = Signal(object, str)   # (JoinResult, right_file_path)
    join_cancelled = Signal()
    def __init__(self, left_df, parent=None, join_service: JoinService | None = None) -> None
```

Diálogo de cruce de datasets con pestañas **Configuración** y **Vista Previa**.

| Método | Descripción |
|--------|-------------|
| `load_right_dataset()` | `QFileDialog` + `cargar_datos`; habilita config y sugiere columnas |
| `update_column_combos()` / `_suggest_matching_columns(...)` | Autosugerencia (case-insensitive o "id"/"key") |
| `on_join_type_changed(button)` | Para CROSS deshabilita keys |
| `update_available_columns()` | Simula columnas del resultado con `compute_result_columns` |
| `add_selected_columns()` / `remove_selected_columns()` / `select_all_columns()` / `clear_column_selection()` | Selección de columnas |
| `add_join_column()` | Avisa que joins múltiples no están implementados |
| `update_preview()` / `update_preview_table(df)` | Preview con `get_preview(..., max_rows=10)` |
| `get_config() -> JoinConfig` | Config actual |
| `validate_config()` | `join_service.validate_config` |
| `execute_join()` | Valida, lanza `JoinWorkerThread` con `QProgressDialog` (avisa cross > 1M filas) |
| `_cancel_worker()` / `_restore_buttons()` | Cancelación (`requestInterruption`/`terminate`) |
| `reject()` | Cancela worker y emite `join_cancelled` |

**Imports:** `core.data_handler.cargar_datos`, `core.join.models` (JoinConfig, JoinType), `core.join.exceptions` (JoinValidationError, JoinExecutionError), `app.services.join_service` (JoinService, JoinWorkerThread, compute_result_columns).

### JoinedDataView (joined_data_view.py, 306 líneas)

```python
class JoinedDataView(DataView):
    new_join_requested = Signal()
    export_requested = Signal(str)
    history_requested = Signal()
    history_entry_selected = Signal(str)
    history_export_requested = Signal(str)
    history_clear_requested = Signal()
```

Vista de resultados de join (hereda toda la paginación de `DataView`).

| Método | Descripción |
|--------|-------------|
| `set_join_result(result: JoinResult, left_name="", right_name="")` | Guarda metadatos, `super().set_data(result.data)`, habilita export |
| `update_join_metadata_display()` | Tipo de join, filas, tiempo, memoria, cobertura |
| `_on_export_clicked()` | Emite `export_requested` |
| `show_history()` | Emite `history_requested` |
| `populate_history(entries: list[JoinHistoryEntry])` | Diálogo local con historial + exportar/limpiar |
| `show_help()` | `QMessageBox` de ayuda |
| `get_join_info() -> dict` | Metadatos del join |

> ⚠️ `_on_export_clicked` emite `export_requested.emit(self.original_df)` (DataFrame) sobre una señal tipada `Signal(str)` — desajuste de tipo aparente en el código.

---

## 6. Diálogos de carga y formato

| Diálogo | Líneas | Descripción |
|---------|--------|-------------|
| `LoadOptionsDialog(QDialog)` | 98 | Saltar filas (`QSpinBox` 0–1000), renombrar columnas (tabla), checkbox de visibilidad. `get_options() -> (skip_rows, column_names, enable_column_visibility)` |
| `CSVSeparatorDialog(QDialog)` | 69 | Delimitador CSV (`;`, `,`, `\t`, `\|`). `get_separator() -> str` |
| `ExcelSheetDialog(QDialog)` | 80 | Selector de hoja Excel (`pd.ExcelFile`; fallback `["Sheet1"]`). `get_sheet_name() -> str` |
| `FolderLoadDialog(QDialog)` | 219 | Carga de carpeta: `QFileDialog` + lista de archivos con `QCheckBox`, `ColumnAlignmentPreview` y tabla de renombrado. `get_config() -> FolderLoadConfig` (usa `FolderLoader`; incluye `included_files`, `excluded_files`, `column_rename_mapping`, `included_columns`) |

**`ColumnAlignmentPreview(QWidget)`** (column_alignment_preview.py, 340 líneas, no exportada) — tabla de alineación de columnas entre archivos. Métodos: `set_file_metadata(metadata)`, `update_preview()`, `align_by_position()` (re-alinea y muestra `QMessageBox`), `align_by_name()` (solo informativo), `edit_column_name(item)` (edición inline), `on_include_changed(position, state)`, `get_column_mappings() -> dict`, `get_alignment_data()`, `get_included_columns()`. Implementa drag & drop manual (`mousePressEvent`/`mouseMoveEvent`/`dropEvent`) para intercambiar celdas.

---

## 7. Diálogos de exportación separada

### ExportSeparatedDialog (export_separated_dialog.py, 928 líneas)

```python
class ExportSeparatedDialog(QDialog):
    configuration_changed = Signal()
    validation_updated = Signal(bool, str)
    def __init__(self, dataframe: pd.DataFrame, parent=None) -> None
```

Diálogo principal (QSplitter: config a la izquierda, mapeo a la derecha). Usa `ExcelTemplateSplitter` de `core.data_handler` para validar.

**Flujo:** validación con **debounce de 500 ms** (`QTimer` single-shot) → `validate_configuration()` → emite `validation_updated`.

| Método | Descripción |
|--------|-------------|
| `select_template()` | `QFileDialog` + hojas con `openpyxl` |
| `select_destination_folder()` | Carpeta destino |
| `update_values_preview()` | Top-15 valores de la columna separadora (muestra de 5000) |
| `update_filename_preview()` | Previsualiza nombres (`{valor}`, `{fecha}`, `{contador}`, `{columna_nombre}`) |
| `validate_configuration()` | `ExcelTemplateSplitter.validate_configuration()` |
| `_build_config(validate=True) -> ExportSeparatedConfig | None` | Construye config |
| `show_file_preview()` | Abre `FilePreviewDialog` |
| `_on_export()` / `accept()` | Guarda settings, valida y acepta |
| `get_configuration(validate=True) -> ExportSeparatedConfig | None` | API pública |
| `_save_settings()` / `_load_settings()` | `QSettings("FlashSheet", "ExportSeparated")` |

**Widgets internos del mismo módulo:**
- `ColumnMappingWidget(QWidget)` — mapeo DataFrame ↔ Excel
- `FilePreviewDialog(QDialog)` — vista previa de archivos a generar (`files_info: list[dict]`)
- `ExcelTemplateDialog(QDialog)` — selector/validador de plantilla (definido, no usado internamente)

> ⚠️ El módulo hace `sys.path.append('..')` antes de importar `core.data_handler`.

---

## 8. Diálogos auxiliares

### InfoPanel / InfoModal (info_panel.py 192 / info_modal.py 215)

Ambos muestran: Información General (filas/columnas), Columnas (lista con dtype), Estadísticas Descriptivas. `InfoPanel` es un widget embebido; `InfoModal` es un `QDialog` modal 600×500 con `lbl_filename` y botón Cerrar. Ambos usan `obtener_estadisticas_basicas`/`obtener_estadisticas` de `core.data_handler` (imports lazy). Para `df > 10000` filas muestran mensaje de optimización en vez de estadísticas detalladas.

### AboutDialog (about_dialog.py, 154 líneas)

```python
class AboutDialog(QDialog):
    VERSION = "1.1.0"
    AUTHOR = "b1tcod3"
    GITHUB_URL = "https://github.com/b1tcod3"
    @classmethod
    def show_about(cls, parent=None) -> None
```

Modal 500×400 con logo (`assets/logo.png`, con fallback), título, versión, descripción, creador y botón OK.

---

## 9. Visualizador rápido

Ver [Sección 3 — QuickVisualizerView](#3-vistas-principales). Orquesta la generación de figuras con `VisualizationService`/`VisualizerWorkerThread` vía `AppCoordinator` (ver `docs/app/services.md`).

---

## 10. Diagrama de Dependencias

```
app/widgets/
├── main_view.py           → app.resources; lazy: load_options_dialog
├── data_view.py           → app.services.pagination_manager, app.models.pandas_model
├── join/joined_data_view.py → app.widgets.data_view (hereda); core.join.models, core.join.join_history
├── join/join_dialog.py    → app.services.join_service; core.data_handler; core.join.models/exceptions
├── pivot_results_view.py  → app.models.pandas_model
├── profiling_view.py      → app.resources
├── quick_visualizer_view.py → matplotlib
├── export_separated_dialog.py → core.data_handler (ExcelTemplateSplitter, ExportSeparatedConfig, ValidationResult, excepciones)
├── folder_load_dialog.py  → core.loaders.folder_loader; core.models.folder_load_config; .column_alignment_preview
├── info_panel.py / info_modal.py → core.data_handler (lazy)
├── csv_separator_dialog.py / excel_sheet_dialog.py / load_options_dialog.py / about_dialog.py → (sin deps de app/core)

Consumidos por:
├── app/view_manager/view_coordinator.py (factories lazy)
├── app/app_coordinator.py
└── app/main_window.py
```

---

## 11. Flujo de Datos

```
AppCoordinator → ViewCoordinator → vistas
        │
        ├─ DataView.set_data(df)
        │     → PaginationManager.set_data(df)
        │     → VirtualizedPandasModel (página) → QTableView
        │     → data_updated.emit(filtered_df)
        │
        ├─ JoinedDataView.set_join_result(JoinResult, ...)
        │     → update_join_metadata_display + super().set_data(result.data)
        │
        ├─ PivotResultsView.set_pivot_results(results)
        │     → 1 pestaña PivotTabWidget por DataFrame
        │
        ├─ ProfilingView.set_profile(profile)   # desde ProfilerWorkerThread
        │     → tarjetas por columna
        │
        └─ QuickVisualizerView.set_dataframe(df)
              → generate_requested.emit → VisualizationService.generate_figure
              → show_figure(fig)
```

---

## 12. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Módulos** | 16 (~5 300 líneas) |
| **Exportados** | 14 clases |
| **Vistas** | MainView, DataView, JoinedDataView, PivotResultsView, ProfilingView, QuickVisualizerView |
| **Diálogos** | InfoModal, AboutDialog, LoadOptionsDialog, CSVSeparatorDialog, ExcelSheetDialog, ExportSeparatedDialog, FolderLoadDialog, JoinDialog |
| **Modelo** | `VirtualizedPandasModel` (`app.models.pandas_model`) |
| **Paginación** | `PaginationManager` (`app.services`) |
| **Importa de** | `core.*`, `app.services`, `app.models`, `app.resources` |
