# app/menus — Documentación Completa

Paquete de **gestión de menús** de Flash View Sheet. Centraliza la creación de la `QMenuBar` en `MenuBuilder` (todas las `QAction` como atributos de instancia, sin estado global) y delega cada menú en clases `*Menu` con método estático `create`.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Exportaciones públicas](#2-exportaciones-públicas)
3. [MenuBuilder (menu_builder.py)](#3-menubuilder-menu_builderpy)
4. [ArchivoMenu (archivo_menu.py)](#4-archivomenu-archivo_menupy)
5. [DatosMenu (datos_menu.py)](#5-datosmenu-datos_menupy)
6. [VistaMenu (vista_menu.py)](#6-vistamenu-vista_menupy)
7. [ExportarMenu (exportar_menu.py)](#7-exportarmenu-exportar_menupy)
8. [Diagrama de Dependencias](#8-diagrama-de-dependencias)
9. [Flujo de Construcción](#9-flujo-de-construcción)
10. [Acciones y Atajos](#10-acciones-y-atajos)
11. [Resumen](#11-resumen)

---

## 1. Visión General

`app/menus/` (5 archivos) construye la barra de menús:

- **`MenuBuilder`** — crea todas las acciones (estado de la app), construye los 6 menús, conecta con `AppCoordinator`/`ViewCoordinator` y gestiona habilitación según haya datos
- **`ArchivoMenu` / `DatosMenu` / `VistaMenu` / `ExportarMenu`** — fábricas estáticas triviales que añaden acciones (o separadores con `None`) a un menú

Menús construidos en `build()`: **Archivo · Separar · Datos · Tabla Pivote · Vista · Ayuda**

> `ExportarMenu` está disponible como fábrica reutilizable ("Exportar como..." submenú), aunque el `MenuBuilder` actual añade las acciones de exportación directamente en Archivo.

---

## 2. Exportaciones públicas

`app/menus/__init__.py` exporta:

```python
__all__ = ['MenuBuilder', 'ArchivoMenu', 'DatosMenu', 'VistaMenu', 'ExportarMenu']
```

---

## 3. MenuBuilder (menu_builder.py)

```python
class MenuBuilder:
    def __init__(self, parent_window: Any) -> None
```

### Estado interno

| Campo | Descripción |
|-------|-------------|
| `parent_window` | Ventana principal (accede a `.coordinator` y `.view_coordinator` al conectar) |
| `menu_bar` | `QMenuBar | None` |
| `separar_menu` / `datos_menu` / `tabla_pivote_menu` | Referencias para uso externo |
| `*_action` | 18 acciones creadas en `_create_actions()` |

### Acciones (creadas en `_create_actions`)

**Archivo:** `abrir_action` (Ctrl+O), `cargar_carpeta_action` (Ctrl+Shift+O), `exportar_pdf_action` (Ctrl+P), `exportar_imagen_action` (Ctrl+I), `exportar_xlsx_action` (Ctrl+X), `exportar_csv_action` (Ctrl+C), `exportar_sql_action` (Ctrl+S), `salir_action` (Ctrl+Q)

**Separar:** `exportar_separado_action` (Ctrl+Shift+S, deshabilitada inicialmente)

**Datos:** `cruzar_datos_action` (Ctrl+Shift+J, deshabilitada), `limpieza_rapida_action` (Ctrl+L, deshabilitada)

**Tabla Pivote:** `pivot_simple_action` (Ctrl+Alt+P, deshabilitada), `export_pivot_action` (Ctrl+Alt+E, deshabilitada)

**Vista:** `vista_principal_action` (Ctrl+1), `vista_datos_action` (Ctrl+2), `vista_info_action`, `vista_perfil_action` (Ctrl+3, deshabilitada), `vista_visualizador_action` (Ctrl+4, deshabilitada)

**Ayuda:** `acerca_de_action` (F1)

### Métodos

| Método | Descripción |
|--------|-------------|
| `build() -> QMenuBar` | Construye los 6 menús y conecta acciones con coordinadores |
| `_build_archivo_menu()` | Archivo con lista de acciones (incl. separadores `None`) vía `ArchivoMenu.create` |
| `_build_separar_menu()` | "&Separar" con `exportar_separado_action` |
| `_build_datos_menu()` | vía `DatosMenu.create` |
| `_build_tabla_pivote_menu()` | "&Tabla Pivote" con separador y las 2 acciones pivote |
| `_build_vista_menu()` | vía `VistaMenu.create` |
| `_build_ayuda_menu()` | "&Ayuda" con `acerca_de_action` |
| `_connect_actions(coordinator, view_coordinator)` | Conecta cada `triggered` al método del coordinador |
| `set_data_actions_enabled(enabled)` | Habilita/deshabilita las 7 acciones que requieren datos |
| `get_menu_references() -> dict` | `{'separar_menu', 'datos_menu', 'tabla_pivote_menu'}` |

### Conexiones (extracto)

```python
abrir_action          → coordinator.solicitar_apertura_archivo
cargar_carpeta_action → coordinator.solicitar_carga_carpeta
exportar_pdf/xlsx/csv/sql/imagen → coordinator.exportar_a_*
salir_action          → parent_window.close
exportar_separado_action → coordinator.exportar_datos_separados
cruzar_datos_action   → coordinator.abrir_cruzar_datos
limpieza_rapida_action→ coordinator.ejecutar_limpieza_rapida
pivot_simple_action   → coordinator.auto_pivot
export_pivot_action   → coordinator.exportar_resultado_pivote
vista_principal/datos → view_coordinator.switch_to(0|1)
vista_info_action     → coordinator.mostrar_info
vista_perfil_action   → view_coordinator.switch_to(VIEW_PROFILING)
vista_visualizador_action → view_coordinator.switch_to(VIEW_VISUALIZER)
acerca_de_action      → coordinator.mostrar_acerca_de
```

---

## 4. ArchivoMenu (archivo_menu.py)

```python
class ArchivoMenu:
    @staticmethod
    def create(menu_bar, actions: list[Any | None], parent_window) -> QMenu
```

Crea `&Archivo` y añade cada acción (o separador si `None`). Devuelve el menú.

---

## 5. DatosMenu (datos_menu.py)

```python
class DatosMenu:
    @staticmethod
    def create(menu_bar, cruzar_datos_action, limpieza_rapida_action: QAction | None = None) -> QMenu
```

Crea `&Datos` con `cruzar_datos_action` y, opcionalmente, separador + `limpieza_rapida_action`.

---

## 6. VistaMenu (vista_menu.py)

```python
class VistaMenu:
    @staticmethod
    def create(menu_bar, actions: list[Any | None], parent_window) -> QMenu
```

Crea `&Vista` añadiendo acciones/separadores igual que `ArchivoMenu`.

---

## 7. ExportarMenu (exportar_menu.py)

```python
class ExportarMenu:
    @staticmethod
    def create(parent_menu, actions: list[Any | None]) -> QMenu
```

Crea un submenú `&Exportar como...` bajo `parent_menu` con las acciones dadas. Reutilizable para añadir exportaciones a cualquier menú.

---

## 8. Diagrama de Dependencias

```
app/menus/
├── menu_builder.py   → PySide6.QtGui (QAction), PySide6.QtWidgets (QMenuBar)
│                     → .archivo_menu, .datos_menu, .vista_menu, .exportar_menu
│                     → app.view_manager.view_registry (ViewRegistry, local)
├── archivo_menu.py   → PySide6.QtWidgets (QMenu, QMenuBar)
├── datos_menu.py     → PySide6.QtGui (QAction), PySide6.QtWidgets (QMenu, QMenuBar)
├── vista_menu.py     → PySide6.QtWidgets (QMenu, QMenuBar)
└── exportar_menu.py  → PySide6.QtWidgets (QMenu)

Consumido por:
└── app/main_window.py (build_menu + set_data_actions_enabled)
```

---

## 9. Flujo de Construcción

```
MainWindow.__init__
        │
        ├─ menu_builder = MenuBuilder(self)
        ├─ menu_bar = menu_builder.build()
        │     ├─ _build_archivo_menu()        # &Archivo
        │     ├─ _build_separar_menu()        # &Separar
        │     ├─ _build_datos_menu()          # &Datos
        │     ├─ _build_tabla_pivote_menu()   # &Tabla Pivote
        │     ├─ _build_vista_menu()          # &Vista
        │     ├─ _build_ayuda_menu()          # &Ayuda
        │     └─ _connect_actions(coordinator, view_coordinator)
        │
        ├─ self.setMenuBar(menu_bar)
        └─ (AppCoordinator) → set_data_actions_enabled(has_data)  # habilita acciones
```

---

## 10. Acciones y Atajos

| Atajo | Acción |
|-------|--------|
| Ctrl+O / Ctrl+Shift+O | Abrir archivo / Cargar carpeta |
| Ctrl+P / Ctrl+I / Ctrl+X / Ctrl+C / Ctrl+S | Exportar PDF / Imagen / XLSX / CSV / SQL |
| Ctrl+Q | Salir |
| Ctrl+Shift+S | Exportar Datos Separados (requiere datos) |
| Ctrl+Shift+J | Cruzar Datos (requiere datos) |
| Ctrl+Alt+P / Ctrl+Alt+E | Pivote automático / Exportar pivote (requiere datos) |
| Ctrl+1 / Ctrl+2 / Ctrl+3 / Ctrl+4 | Vista Principal / Datos / Perfil / Visualizador |
| Ctrl+L | Limpieza Rápida (requiere datos) |
| F1 | Acerca de |

> Nota: `Ctrl+C` (exportar CSV) puede chocar con copiar en ciertos widgets; es el atajo definido en el código.

---

## 11. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Archivos** | 5 |
| **Menús** | Archivo, Separar, Datos, Tabla Pivote, Vista, Ayuda |
| **Acciones** | 18 (`QAction` como atributos de instancia) |
| **Acciones con datos** | 7 (separar, cruzar, pivote×2, limpieza, perfil, visualizador) |
| **Fábricas estáticas** | ArchivoMenu, DatosMenu, VistaMenu, ExportarMenu |
| **Conecta a** | `AppCoordinator` (acciones de datos) y `ViewCoordinator` (navegación) |
