# app/toolbar — Documentación Completa

Paquete de la **barra de herramientas principal** de Flash View Sheet. Implementa una barra tipo *ribbon* con una sección "Herramientas" que contiene el conmutador de vistas, el botón de separación de datos y el botón de salida.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Exportaciones públicas](#2-exportaciones-públicas)
3. [ToolbarManager (toolbar_manager.py)](#3-toolbarmanager-toolbar_managerpy)
4. [ViewSwitcher de toolbar (view_switcher.py)](#4-viewswitcher-de-toolbar-view_switcherpy)
5. [Diagrama de Dependencias](#5-diagrama-de-dependencias)
6. [Flujo de Construcción](#6-flujo-de-construcción)
7. [Flujo de Señales](#7-flujo-de-señales)
8. [Resumen](#8-resumen)

---

## 1. Visión General

`app/toolbar/` (2 archivos) agrupa la UI de la barra superior:

- **`ToolbarManager`** — construye el `QToolBar` con la sección ribbon "Herramientas" y orquesta los clics hacia `ViewCoordinator`/`AppCoordinator`
- **`ViewSwitcher`** (toolbar) — widget con 7 botones que emiten señales (`view_main`, `view_data`, `view_info`, `view_joined`, `view_pivot`, `view_profile`, `view_visualizer`), separados por líneas verticales

> ⚠️ **Atención:** hay dos clases `ViewSwitcher` distintas:
> - `app/toolbar/view_switcher.py` — widget de **botones** con señales
> - `app/view_manager/view_switcher.py` — **lógica** de cambio de vista sobre `QStackedWidget` (ver `docs/app/view_manager.md`)
> `ToolbarManager` usa el de `app.toolbar` y delega la navegación real en `ViewCoordinator` (que internamente usa el de `app.view_manager`).

---

## 2. Exportaciones públicas

`app/toolbar/__init__.py` exporta:

```python
__all__ = ['ToolbarManager', 'ViewSwitcher']
```

---

## 3. ToolbarManager (toolbar_manager.py)

```python
class ToolbarManager:
    def __init__(self, main_window: QWidget) -> None
```

### Estado interno

| Campo | Descripción |
|-------|-------------|
| `main_window` | Ventana principal (target del botón Salir) |
| `tool_bar` | `QToolBar | None` "Herramientas" |
| `view_switcher` | Widget de botones (`app.toolbar.ViewSwitcher`) |
| `separar_btn` | Botón de exportación separada (deshabilitado hasta tener datos) |
| `view_coordinator` / `coordinator` | `ViewCoordinator` / `AppCoordinator` inyectados |

### Métodos principales

| Método | Descripción |
|--------|-------------|
| `set_coordinators(view_coordinator, coordinator)` | Inyecta coordinadores (usado tras creación) |
| `create_toolbar() -> QToolBar` | Crea el `QToolBar` "Herramientas" (no movible/flotable), añade wrapper ribbon con la sección "Herramientas" |
| `set_view_buttons_enabled(enabled)` | Habilita/deshabilita el botón de Cruzar Datos |
| `on_datos_disponibles(has_data)` | Activa/desactiva join, pivote, perfil, visualizador y separar según haya datos |
| `get_toolbar() -> QToolBar | None` | Getter |

### Construcción de la sección ribbon

- `_create_section_frame(title) -> QFrame` — frame `#RibbonSection` (fondo `#f5f6f7`, borde inferior `#a8a8a8`) con título en azul `#2b579a` y línea separadora `HLine`
- `_create_herramientas_section() -> QFrame` — sección "Herramientas": crea el conmutador de vistas, el botón Separar y el botón Salir (`assets/power.svg`), con `addStretch()` al final
- `_create_view_switcher()` — crea el widget de botones y conecta sus 7 señales a los manejadores
- `_create_separar_button()` — botón `assets/split.svg`, tooltip "Separar datos por columna", deshabilitado inicialmente

### Manejadores de clics

| Método | Acción |
|--------|--------|
| `_on_view_switch(index)` | `view_coordinator.switch_to(index)` (índices 0, 1, 3: Principal, Datos, Cruzar) |
| `_on_info_requested` | `coordinator.mostrar_info()` |
| `_on_pivot_requested` | `coordinator.auto_pivot()` |
| `_on_profile_requested` | `view_coordinator.switch_to(VIEW_PROFILING)` |
| `_on_visualizer_requested` | `view_coordinator.switch_to(VIEW_VISUALIZER)` |
| `_on_separar_requested` | `coordinator.exportar_datos_separados()` |

---

## 4. ViewSwitcher de toolbar (view_switcher.py)

Widget de botones para cambiar entre vistas.

### Señales

```python
view_main = Signal()
view_data = Signal()
view_info = Signal()
view_joined = Signal()
view_pivot = Signal()
view_profile = Signal()
view_visualizer = Signal()
```

### Botones (en orden de layout)

| Botón | Icono | Tooltip | Habilitado inicialmente |
|-------|-------|---------|-------------------------|
| `view_main_btn` | `SP_DirHomeIcon` | Vista Principal | sí |
| `view_data_btn` | `SP_FileDialogContentsView` | Vista de Datos | sí |
| `view_joined_btn` | `SP_DriveNetIcon` | Cruzar Datos | **no** |
| `view_pivot_btn` | `SP_FileDialogDetailedView` | Tabla Pivote | **no** |
| `view_info_btn` | `SP_MessageBoxInformation` | Ver Información del dataset | sí |
| `view_profile_btn` | `SP_FileDialogListView` | Perfil de Datos | **no** |
| `view_visualizer_btn` | `assets/chart.svg` | Visualizador Rápido | **no** |

### Métodos

| Método | Descripción |
|--------|-------------|
| `set_joined_enabled` / `set_main_enabled` / `set_data_enabled` / `set_info_enabled` / `set_pivot_enabled` / `set_profile_enabled` / `set_visualizer_enabled` | Habilita/deshabilita cada botón |

Botones estilo *flat* (30×28 px, iconos 20×20), hover `#e0e4e8`, separados por `QFrame.VLine` (4 px).

---

## 5. Diagrama de Dependencias

```
app/toolbar/
├── toolbar_manager.py  → PySide6.QtWidgets, PySide6.QtGui, PySide6.QtCore
│                        → app.resources (get_asset_path)
│                        → app.toolbar.view_switcher (widget de botones)
│                        → app.view_manager (ViewCoordinator) [TYPE_CHECKING]
│                        → app.app_coordinator (AppCoordinator) [TYPE_CHECKING]
└── view_switcher.py    → PySide6.QtWidgets/Gui/Core
                        → app.resources (get_asset_path)

Consumido por:
└── app/main_window.py (create_toolbar + set_coordinators + on_datos_disponibles)
```

---

## 6. Flujo de Construcción

```
MainWindow.__init__
        │
        ├─ toolbar = ToolbarManager(self.main_window)
        ├─ toolbar.create_toolbar()         # QToolBar "Herramientas"
        │     └─ _create_herramientas_section()
        │           ├─ _create_view_switcher()   # widget de 7 botones
        │           ├─ _create_separar_button()
        │           └─ botón Salir (power.svg) → main_window.close
        ├─ toolbar.set_coordinators(view_coordinator, coordinator)
        └─ toolbar.on_datos_disponibles(has_data)  # habilita botones según datos
```

---

## 7. Flujo de Señales

```
Clic en botón → señal emitida → handler en ToolbarManager
  ├─ view_main/view_data/view_joined → _on_view_switch(0|1|3)
  │     → view_coordinator.switch_to(index) → ViewSwitcher (view_manager)
  │           → view_about_to_change.emit + setCurrentIndex + view_changed.emit
  ├─ view_info → coordinator.mostrar_info()
  ├─ view_pivot → coordinator.auto_pivot()
  ├─ view_profile → switch_to(VIEW_PROFILING)
  ├─ view_visualizer → switch_to(VIEW_VISUALIZER)
  └─ separar_btn → coordinator.exportar_datos_separados()

AppCoordinator → on_datos_originales_cargados → on_datos_disponibles(has_data)
  → set_joined_enabled/set_pivot_enabled/set_profile_enabled/set_visualizer_enabled/separar_btn
```

---

## 8. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Archivos** | 2 |
| **Botones de vista** | 7 (4 habilitados solo con datos) |
| **Estilo** | Ribbon `#f5f6f7`, título azul `#2b579a`, botones flat |
| **Recursos** | `assets/power.svg`, `assets/split.svg`, `assets/chart.svg` |
| **Coordinación** | `ToolbarManager` → `ViewCoordinator` + `AppCoordinator` |
| **Aviso de nombres** | `ViewSwitcher` existe en `app/toolbar` (botones) y en `app/view_manager` (lógica) |
