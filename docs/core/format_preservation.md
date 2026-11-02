# Preservación de Formato Excel — Documentación Completa

Sistema que preserva el formato de plantillas Excel al insertar datos. Compuesto por dos módulos en `core/`: `simple_excel_preserver.py` y `excel_format_preserver.py`.

---

## Índice

1. [Visión General](#1-visión-general)
2. [simple_excel_preserver.py](#2-simpleexcelpreserverpy)
   - [2.1 Clase SimpleExcelFormatPreserver](#21-clase-simpleexcelformatpreserver)
   - [2.2 Función utilitaria](#22-función-utilitaria)
3. [excel_format_preserver.py](#3-excelformatpreserverpy)
   - [3.1 Clase ExcelFormatPreserver](#31-clase-excelformatpreserver)
   - [3.2 Función utilitaria](#32-función-utilitaria)
4. [Comparación de enfoques](#4-comparación-de-enfoques)
5. [Diagrama de Dependencias](#5-diagrama-de-dependencias)
6. [Resumen](#6-resumen)

---

## 1. Visión General

Al insertar datos en una plantilla Excel con openpyxl, escribir `cell.value = ...` puede **alterar el formato** de la celda (fuente, relleno, bordes, número). Estos dos módulos solucionan ese problema:

- **`SimpleExcelFormatPreserver`** — solución simplificada que **no usa `deepcopy`** (evita recursión infinita con Font/estilos de openpyxl). Serializa el formato a dicts y lo reconstruye. Es el usado actualmente por `ExcelTemplateSplitter._create_excel_file_with_template()`.
- **`ExcelFormatPreserver`** — solución completa que cachea formatos a nivel de workbook (celdas, columnas, filas, estilos nombrados, merged cells). Usa `copy.copy` para estilos.

**Diseño:**
- Ambos mantienen el mismo contrato: `insert_data_preserving_format` / `insert_data_simple_preservation` reciben `(worksheet, data, column_mapping, start_cell)`
- `data` es un dict `{row_offset: {col_name: value}}`
- `column_mapping` es `{columna_df: letra_excel}`
- Ambos exportan una función utilitaria `create_*()` que devuelve `bool`

---

## 2. simple_excel_preserver.py

### 2.1 Clase SimpleExcelFormatPreserver

```python
class SimpleExcelFormatPreserver:
    def __init__(self) -> None:
        self.saved_cell_data: dict[str, Any] = {}
```

#### `save_cell_format(cell) -> dict[str, Any]`
Serializa el formato de una celda **sin deepcopy**:
- `value`, `font` (name, size, bold, italic, color rgb), `fill` (start_color, fill_type), `border` (4 lados vía `_serialize_border`), `alignment` (horizontal, vertical, wrap_text), `number_format`

#### `_serialize_border(side) -> dict`
`{'style': ..., 'color': rgb}`.

#### `restore_cell_format(cell, format_info)`
Reconstruye el formato **construyendo nuevos objetos** (Font, PatternFill, Border, Alignment) en vez de asignar los originales — evita mutar estilos inmutables. Solo aplica si el número de formato es distinto de `'General'`.

#### `backup_area_formatting(worksheet, start_cell, area_size) -> dict`
Respalda formato de un área rectangular `(filas, columnas)` a partir de `start_cell`. Solo celdas con valor no None; clave = coordenada `"A1"`.

#### `insert_data_simple_preservation(worksheet, data, column_mapping, start_cell)`
1. Backup del área `(max_rows + 5, max_cols + 2)`
2. Inserta valores (None → `cell.value = None`)
3. Restaura formato de las celdas respaldadas
4. Llama `_inherit_header_format()` para copiar el estilo de la fila de encabezados (fila 1) hacia las filas de datos

#### `_has_style(cell) -> bool`
Detecta formato no predeterminado: bold/italic, color rgb distinto de negro, fill_type no none, bordes, number_format ≠ General.

#### `_inherit_header_format(worksheet, column_mapping, start_cell, max_rows, restored_coords=None)`
Si `start_row > 1`, para cada columna mapeada cuyo encabezado (fila 1) tiene estilo, construye `base_styles` una sola vez con `copy.copy(font/fill/border)` y los aplica a las filas de datos que **no** estén en `restored_coords`.

### 2.2 Función utilitaria

```python
def create_excel_with_simple_format_preservation(
    template_path, output_path, data, column_mapping, start_cell
) -> bool
```

Carga la plantilla (`data_only=False`), crea el preserver, inserta y guarda. Devuelve `False` en cualquier error.

> **Uso actual:** llamado por `ExcelTemplateSplitter._create_excel_file_with_template()` en `core/data_handler.py` (línea 1217).

---

## 3. excel_format_preserver.py

### 3.1 Clase ExcelFormatPreserver

```python
class ExcelFormatPreserver:
    def __init__(self) -> None:
        self.cached_formats: dict = {}
        self.original_styles: dict = {}
        self.worksheet_cache: dict = {}
```

#### `cache_workbook_formats(workbook) -> dict`
Cache completo del workbook:
- `named_styles` — soporta tanto dict como lista (`deepcopy`)
- `worksheet_formats[sheet]` — `cell_formats` (por coordenada, `copy.copy` de Font/PatternFill/Border/Alignment), `column_widths`, `row_heights`, `merged_cells` (ranges), `page_setup`, `print_options`

#### `restore_workbook_formats(workbook, formats_cache)`
Restaura estilos nombrados, merged cells, anchos/alturas y formatos de celda.

#### `_extract_cell_format(cell) -> dict`
Extrae font/fill/border/alignment/number_format/protection solo si difieren del default (`copy.copy`).

#### `_apply_cell_format(cell, format_dict)`
Asigna cada atributo preservando el valor.

#### `_has_formatting(cell) -> bool`
Compara contra objetos `Font()`, `PatternFill()`, `Border()`, `Alignment()` por defecto.

#### `insert_data_preserving_format(worksheet, data, column_mapping, start_cell)`
1. `_cache_worksheet_formats(worksheet)` — cachea todas las celdas con formato
2. Inserta valores; si la celda tiene formato, restaura con `_restore_cell_format`
3. En caso de error, `_restore_all_formats(worksheet)`

#### Métodos privados
`_cache_worksheet_formats`, `_restore_cell_format(cell, row, col)`, `_restore_all_formats`.

### 3.2 Función utilitaria

```python
def create_template_with_preserved_format(
    template_path, output_path, data, column_mapping, start_cell
) -> bool
```

Carga la plantilla con `data_only=False`, `keep_vba=True`, `keep_links=True`, `keep_images=True`. Itera todos los worksheets, cachea formatos e inserta datos preservando formato.

---

## 4. Comparación de enfoques

| Aspecto | SimpleExcelFormatPreserver | ExcelFormatPreserver |
|---------|----------------------------|----------------------|
| Archivo | `core/simple_excel_preserver.py` | `core/excel_format_preserver.py` |
| Líneas | 321 | 340 |
| Copia de estilos | Reconstruye objetos nuevos (no deepcopy) | `copy.copy` (per-celda) |
| Alcance de cache | Área de inserción + fila header | Workbook completo (celdas, cols, rows, named_styles, merged) |
| `data` soportado | `{row_offset: {col: val}}` | `{row_offset: {col: val}}` |
| Funciones creadas | `create_excel_with_simple_format_preservation` | `create_template_with_preserved_format` |
| Uso actual | `ExcelTemplateSplitter._create_excel_file_with_template` | (disponible; no usado por el splitter actual) |

---

## 5. Diagrama de Dependencias

```
core/simple_excel_preserver.py          core/excel_format_preserver.py
├── openpyxl (workbook, utils)          ├── openpyxl (+ styles)
├── copy (copy.copy)                    ├── copy (deepcopy para named_styles, copy.copy)
└── consumido por                       └── (módulo independiente, sin consumidor activo)
    core/data_handler.py
    → ExcelTemplateSplitter._create_excel_file_with_template()
```

---

## 6. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Módulos** | 2 (`simple_excel_preserver`, `excel_format_preserver`) |
| **Objetivo** | Evitar que insertar datos rompa el formato de plantillas |
| **Enfoque activo** | `SimpleExcelFormatPreserver` (sin deepcopy, sin recursión) |
| **Enfoque completo** | `ExcelFormatPreserver` (cache a nivel workbook) |
| **Funciones utilitarias** | 2 (`create_*()`) |
| **Dependencias** | openpyxl, copy |
