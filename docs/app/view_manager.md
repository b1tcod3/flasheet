# app/view_manager — Documentación Completa

Paquete de **gestión de vistas** de Flash View Sheet. Aplica el patrón **Coordinator** para centralizar la creación, navegación y coordinación de estado entre todas las vistas de la aplicación.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Exportaciones públicas](#2-exportaciones-públicas)
3. [ViewRegistry (view_registry.py)](#3-viewregistry-view_registrypy)
4. [ViewSwitcher (view_switcher.py)](#4-viewswitcher-view_switcherpy)
5. [ViewCoordinator (view_coordinator.py)](#5-viewcoordinator-view_coordinatorpy)
6. [Diagrama de Dependencias](#6-diagrama-de-dependencias)
7. [Flujo de Creación de Vistas](#7-flujo-de-creación-de-vistas)
8. [Flujo de Señales](#8-flujo-de-señales)
9. [Resumen](#9-resumen)

---

## 1. Visión General

`app/view_manager/` (3 archivos) define tres responsabilidades separadas:

- **`ViewRegistry`** — registro estático: constantes de IDs, nombres y descripciones de cada vista
- **`ViewSwitcher`** — lógica de cambio de vista sobre un `QStackedWidget` (navegación, historial, señales)
- **`ViewCoordinator`** — orquestador: crea las vistas (factories lazy), mantiene sus referencias, traduce IDs ↔ índices del stacked y actualiza el estado

**Vistas registradas (7 en total, 6 instanciables):**

| ID | Constante | Nombre | Descripción |
|----|-----------|--------|-------------|
| 0 | `VIEW_MAIN` | Principal | Pantalla de bienvenida y carga de archivos |
| 1 | `VIEW_DATA` | Datos | Visualización tabular con paginación |
| 2 | `VIEW_INFO` | Información | Información estadística del dataset (modal, no página) |
| 3 | `VIEW_JOIN` | Datos Cruzados | Resultado de cruce de datasets |
| 4 | `VIEW_PIVOT` | Pivote | Tablas pivote automáticas (categórica × numérica) |
| 5 | `VIEW_PROFILING` | Perfil de Datos | Tipo, nulos y cardinalidad por columna |
| 6 | `VIEW_VISUALIZER` | Visualizador Rápido | Gráficos exploratorios rápidos |

> `VIEW_INFO` (2) no tiene factory en `_view_factories`: se materializa como `InfoModal` modal y se muestra bajo demanda (no ocupa una página del stacked).

---

## 2. Exportaciones públicas

`app/view_manager/__init__.py` exporta:

```python
__all__ = ['ViewRegistry', 'ViewSwitcher', 'ViewCoordinator']
```

---

## 3. ViewRegistry (view_registry.py)

Registro **estático** (solo classmethods/constantes, no requiere instancia).

### Constantes

```python
VIEW_MAIN = 0
VIEW_DATA = 1
VIEW_INFO = 2
VIEW_JOIN = 3
VIEW_PIVOT = 4
VIEW_PROFILING = 5
VIEW_VISUALIZER = 6

VIEW_NAMES = { ... }          # ID → "Principal", "Datos", ...
VIEW_DESCRIPTIONS = { ... }   # ID → descripción funcional
```

### Classmethods

| Método | Firma | Descripción |
|--------|-------|-------------|
| `get_view_name` | `(index: int) -> str` | Nombre o `f"Vista {index}"` |
| `get_view_description` | `(index: int) -> str` | Descripción o `""` |
| `get_all_view_indices` | `() -> list` | Lista de IDs (keys de `VIEW_NAMES`) |
| `is_valid_view` | `(index: int) -> bool` | `index in VIEW_NAMES` |

---

## 4. ViewSwitcher (view_switcher.py)

Maneja la lógica de cambio de vista sobre un `QStackedWidget`.

```python
class ViewSwitcher(QObject):
    view_changed = Signal(int)              # Emitido cuando cambia la vista
    view_about_to_change = Signal(int, int)  # (vista_actual, vista_nueva)
```

### Estado interno

| Campo | Descripción |
|-------|-------------|
| `_stacked_widget` | `QStackedWidget | None` |
| `_current_view` | Índice actual (int) |
| `_current_registry_id` | ID de ViewRegistry del índice actual |
| `_view_history` | `list[int]` de índices visitados (máx. 20) |
| `_index_to_registry` | `dict[int, int]` índice stacked → ID registro |

### Métodos

| Método | Firma | Descripción |
|--------|-------|-------------|
| `set_stacked_widget` | `(stacked_widget)` | Asigna widget; sincroniza `_current_view` |
| `set_index_mapping` | `(index_to_registry: dict[int, int])` | Mapeo índice → registro |
| `get_current_view` | `() -> int` | Índice actual (del stacked si existe) |
| `switch_to` | `(index: int) -> bool` | Valida rango, emite `view_about_to_change`, cambia índice, registra historial, emite `view_changed` |
| `switch_to_main` | `() -> bool` | → `VIEW_MAIN` |
| `switch_to_data` | `() -> bool` | → `VIEW_DATA` |
| `switch_to_join` | `() -> bool` | → `VIEW_JOIN` |
| `switch_to_pivot` | `() -> bool` | → `VIEW_PIVOT` |
| `get_view_name` | `() -> str` | Nombre de la vista actual |
| `get_view_history` | `() -> list` | Copia del historial |
| `can_go_back` | `() -> bool` | `len(historial) > 1` |
| `go_back` | `() -> bool` | Pop del actual y switch al anterior |

---

## 5. ViewCoordinator (view_coordinator.py)

```python
class ViewCoordinator(QObject):
    view_created = Signal(int)
```

Coordina la creación y estado de todas las vistas. Importa los widgets **lazy** (dentro de cada factory) para evitar dependencias circulares.

### Creación de vistas

`create_views(parent_widget: QWidget) -> dict[int, QWidget]`

1. Crea (si no existe) el `QStackedWidget` con `parent_widget`
2. Itera `_view_factories` (en orden de `dict`) añadiendo cada vista al stacked e incrementando `stacked_index`
3. Registra la vista en `_views[view_id]`, `_id_to_index[view_id]` y en el atributo tipado correspondiente
4. Emite `view_created(view_id)` por cada vista
5. Conecta el stacked al `ViewSwitcher` y aplica `reverse_mapping` (índice → registro)
6. Muestra el índice 0 (`VIEW_MAIN`) y devuelve `_views`

**Factories (imports lazy):**

| ID | Factory | Widget |
|----|---------|--------|
| 0 | `_create_main_view` | `app.widgets.main_view.MainView` |
| 1 | `_create_data_view` | `app.widgets.data_view.DataView` |
| 3 | `_create_joined_data_view` | `app.widgets.join.joined_data_view.JoinedDataView` |
| 4 | `_create_pivot_view` | `app.widgets.pivot_results_view.PivotResultsView` |
| 5 | `_create_profiling_view` | `app.widgets.profiling_view.ProfilingView` |
| 6 | `_create_quick_visualizer_view` | `app.widgets.quick_visualizer_view.QuickVisualizerView` |

### Getters

`get_stacked_widget`, `get_view(view_id)`, `get_main_view`, `get_data_view`, `get_joined_data_view`, `get_pivot_view`, `get_profiling_view`, `get_quick_visualizer_view`, `get_view_switcher`.

### Navegación

| Método | Descripción |
|--------|-------------|
| `switch_to(index) -> bool` | Traduce ID de registro → índice stacked vía `_id_to_index` y delega en `ViewSwitcher.switch_to` |
| `get_current_view() -> int` | Índice actual |
| `get_current_view_name() -> str` | Nombre actual |

### Actualización de vistas

| Método | Descripción |
|--------|-------------|
| `update_data_view(df)` | `data_view.set_data(df)` |
| `update_main_view(filepath)` | Añade el archivo a la lista del `MainView` y lo marca completado |
| `show_info_modal(df, filename)` | Crea `InfoModal` una vez (lazy) y lo muestra con `exec()` |
| `set_join_result(result, left_name, right_name)` | Delega en `JoinedDataView` |
| `set_profile_data(profile)` | `profiling_view.set_profile(dict(profile))` |
| `show_profile_loading()` / `show_profile_progress(percent)` / `clear_profile_data()` | Estado de `ProfilingView` |

### Slots de señales

| Método | Descripción |
|--------|-------------|
| `on_datos_originales_cargados(df)` | Pasa `df.columns.tolist()` al `MainView` |
| `on_datos_actualizados(df)` | `update_data_view(df)` + sincroniza `QuickVisualizerView.set_dataframe(df)` |
| `open_visualizer_for_column(column)` | Preselecciona columna en el visualizador y navega a él |
| `set_column_visibility_enabled(enabled)` | Habilita/deshabilita visibilidad de columnas en `DataView` |

### Cleanup

`cleanup()` — cierra/elimina el `InfoModal`, anula referencias a vistas, limpia `_views`, `_view_factories` y `_parent`.

---

## 6. Diagrama de Dependencias

```
app/view_manager/
├── view_registry.py       → (sin imports externos)
├── view_switcher.py       → PySide6.QtCore (Signal, QObject); importa ViewRegistry local
└── view_coordinator.py    → PySide6.QtCore/Widgets + view_registry + view_switcher

Depende de (lazy): app.widgets.main_view, data_view, join.joined_data_view,
                   pivot_results_view, profiling_view, quick_visualizer_view, info_modal

Consumido por:
├── app/app_coordinator.py (AppCoordinator → ViewCoordinator)
├── app/main_window.py
└── app/toolbar/toolbar_manager.py (switch de vistas)
```

---

## 7. Flujo de Creación de Vistas

```
AppCoordinator.__init__ / MainWindow
        │
        ▼
ViewCoordinator.create_views(parent_widget)
        │  1. QStackedWidget(parent_widget)
        ▼
for view_id, factory in _view_factories:      # MAIN → DATA → JOIN → PIVOT → PROFILING → VISUALIZER
        │
        ├─ view = factory(parent)             # import lazy del widget
        ├─ stacked_widget.addWidget(view)
        ├─ _views[view_id] = view
        ├─ _id_to_index[view_id] = index
        └─ view_created.emit(view_id)
        │
        ▼
ViewSwitcher.set_stacked_widget(stacked)
ViewSwitcher.set_index_mapping(reverse_mapping)   # {índice: registro}
stacked_widget.setCurrentIndex(0)                 # Vista Principal
```

---

## 8. Flujo de Señales

```
AppCoordinator.on_datos_originales_cargados(df)  →  ViewCoordinator.on_datos_originales_cargados
        → main_view.set_original_columns(df.columns)

AppCoordinator.on_datos_actualizados(df)  →  ViewCoordinator.on_datos_actualizados
        → data_view.set_data(df)
        → quick_visualizer_view.set_dataframe(df)

ViewSwitcher.switch_to(index)
        ├─ view_about_to_change.emit(actual, nueva)
        ├─ setCurrentIndex(index) + historial
        └─ view_changed.emit(index)   → toolbar/coordinator actualizan estado de UI

ViewCoordinator.show_info_modal(df, filename)  →  InfoModal.update_info + exec()
ViewCoordinator.open_visualizer_for_column(col) → set_selected_column + switch_to(VIEW_VISUALIZER)
```

---

## 9. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Archivos** | 3 |
| **Patrón** | Coordinator + Registry + Switcher |
| **Vistas registradas** | 7 IDs (6 instanciables + `VIEW_INFO` modal) |
| **Historial de navegación** | Máx. 20 entradas, soporte `go_back()` |
| **Imports de widgets** | Lazy (dentro de factories) para evitar ciclos |
| **Señales** | `view_changed`, `view_about_to_change`, `view_created` |
