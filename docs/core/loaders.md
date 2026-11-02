# core/loaders — Documentación Completa

Sistema modular de carga de archivos con **patrón Factory**. Abstrae la lectura de 16 formatos en una interfaz común `FileLoader` y resuelve el loader adecuado según la extensión del archivo.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Importaciones](#2-importaciones)
3. [Clase FileLoader (base)](#3-clase-fileloader-base)
4. [Factory y funciones de conveniencia](#4-factory-y-funciones-de-conveniencia)
5. [Loaders por formato](#5-loaders-por-formato)
   - [5.1 CsvLoader](#51-csvloader)
   - [5.2 ExcelLoader](#52-exceltloader)
   - [5.3 JsonLoader](#53-jsonloader)
   - [5.4 XmlLoader](#54-xmlloader)
   - [5.5 ParquetLoader / FeatherLoader / Hdf5Loader / PickleLoader](#55-parquetloader--featherloader--hdf5loader--pickleloader)
   - [5.6 SqliteLoader](#56-sqliteltooloader)
   - [5.7 YamlLoader](#57-yamlloader)
6. [FolderLoader](#6-folderloader)
7. [Modelos de datos](#7-modelos-de-datos)
8. [Diagrama de Dependencias](#8-diagrama-de-dependencias)
9. [Resumen](#9-resumen)

---

## 1. Visión General

El paquete `core/loaders/` (12 archivos) implementa la carga de archivos de forma desacoplada:

- **`FileLoader`** — clase abstracta (ABC) con la interfaz común: `load()`, `get_file_info()`, `get_memory_usage_info()`, y soporte opcional de chunks
- **`FileLoaderFactory`** — mapa extensión → clase loader; decide qué loader instanciar
- **12 loaders concretos** — CSV/TSV, Excel, JSON, XML, Parquet, Feather, HDF5, Pickle, SQLite, YAML
- **`FolderLoader`** — carga y metadatos de carpetas de Excel (no hereda de `FileLoader`)

**Formato esperado** (según `core/loaders/__init__.py`):
- `FileLoader`, `FileLoaderFactory`, `get_file_loader`, `is_file_supported`, `get_supported_formats`

**Diseño:**
- Dependencias opcionales (pyarrow, tables, pyyaml, sqlalchemy) se importan con try/except dentro de cada loader y fallan con mensaje claro
- La validación de archivo vive en `FileLoader.__init__` vía `_validate_file()`
- Los loaders con chunks heredan `can_load_chunks()`/`load_in_chunks()` de la base solo cuando el formato lo permite

---

## 2. Importaciones

### `__init__.py`
| Símbolo | Módulo |
|---------|--------|
| `FileLoader` | `.base_loader` |
| `FileLoaderFactory`, `get_file_loader`, `is_file_supported`, `get_supported_formats` | `.file_loader_factory` |

### Base y Factory
| Símbolo | Módulo | Uso |
|---------|--------|-----|
| `ABC`, `abstractmethod` | `abc` | Interfaz abstracta |
| `pd` | `pandas` | DataFrames |
| `Path` | `pathlib` | Rutas |
| `Type` | `typing` | Tipos de loader en el mapa de la Factory |

---

## 3. Clase FileLoader (base)

```python
class FileLoader(ABC):
    def __init__(self, filepath: str) -> None
```

**Constructor:** guarda `self.filepath` y llama `_validate_file()`.

### `_validate_file()`
- Lanza `FileNotFoundError` si el archivo no existe
- Lanza `ValueError` si la extensión no está en `get_supported_extensions()`

### Métodos abstractos
| Método | Firma | Descripción |
|--------|-------|-------------|
| `get_supported_extensions` | `() -> list[str]` | Extensiones del loader (ej. `['.csv', '.tsv']`) |
| `load` | `(skip_rows=0, column_names=None) -> pd.DataFrame` | Carga completa |
| `get_file_info` | `() -> dict[str, Any]` | Información del archivo |

### Métodos concretos
| Método | Firma | Descripción |
|--------|-------|-------------|
| `can_load_chunks` | `() -> bool` | Por defecto `False` |
| `load_in_chunks` | `(chunk_size=1000) -> pd.DataFrame` | Por defecto lanza `NotImplementedError` |
| `get_memory_usage_info` | `() -> dict` | `file_size_bytes`, `file_size_mb`, `estimated_data_rows`, `supports_chunked_loading` |
| `_estimate_rows` | `() -> int` | Estimación `file_size // 100` (longitud de línea promedio) |

---

## 4. Factory y funciones de conveniencia

### `FileLoaderFactory`

| Método | Firma | Descripción |
|--------|-------|-------------|
| `get_loader` | `(filepath) -> FileLoader` | `FileNotFoundError` si no existe; `ValueError` si la extensión no está en el mapa; instancia el loader |
| `is_supported` | `(filepath) -> bool` | `extension in _loader_mapping` |
| `get_supported_extensions` | `() -> list[str]` | Claves del mapa |
| `get_loader_info` | `(filepath) -> dict` | `extension`, `loader_class`, `supports_chunks`, `file_info`, `memory_info` |
| `register_loader` | `(extension, loader_class)` | Registra un loader nuevo (debe heredar de `FileLoader`) |
| `get_format_description` | `(extension) -> str` | Descripción legible de cada formato |

### Mapa de extensiones

| Extensión | Loader |
|-----------|--------|
| `.csv`, `.tsv` | `CsvLoader` |
| `.xlsx`, `.xls` | `ExcelLoader` |
| `.json` | `JsonLoader` |
| `.xml` | `XmlLoader` |
| `.parquet` | `ParquetLoader` |
| `.feather` | `FeatherLoader` |
| `.hdf5` | `Hdf5Loader` |
| `.pkl`, `.pickle` | `PickleLoader` |
| `.db`, `.sqlite` | `SqliteLoader` |
| `.yaml`, `.yml` | `YamlLoader` |

> **Nota:** `.sqlite3`, `.h5` y `.sqlite` aparecen en `data_service.py` pero no en el mapa del factory. Los formatos soportados por el sistema de carga son los del mapa.

### Funciones de conveniencia (instancia global `_global_factory`)
```python
get_file_loader(filepath) -> FileLoader
is_file_supported(filepath) -> bool
get_supported_formats() -> list[str]
```

---

## 5. Loaders por formato

Todos heredan de `FileLoader`. Columnas renombrables vía `column_names: dict[str, str]` (`{original: nuevo}`).

### 5.1 CsvLoader
| Método | Detalle |
|--------|---------|
| `load(skip_rows=0, column_names=None, separator=None)` | Detección de separador: explícito `separator` > `.tsv` → `'\t'` > `','`. `header=skip_rows` para respetar filas saltadas. Fallback de codificaciones (utf-8 → latin-1) |
| `get_file_info()` | size, lines, estimated rows |
| `can_load_chunks()` / `load_in_chunks(chunk_size=1000, separator=None)` | `pd.read_csv(..., chunksize=...)` + concat |
| `_estimate_rows()` | Count de líneas |

### 5.2 ExcelLoader
| Método | Detalle |
|--------|---------|
| `load(skip_rows=0, column_names=None, sheet_name=None)` | `pd.read_excel` con hoja opcional |
| `get_file_info()` | Hojas, tamaño |
| `can_load_chunks()` | `False` (sin soporte de chunks) |

### 5.3 JsonLoader
| Método | Detalle |
|--------|---------|
| `load(skip_rows=0, column_names=None)` | `pd.read_json` con fallback a orientación `records` |
| `can_load_chunks()` | `False` |

### 5.4 XmlLoader
| Método | Detalle |
|--------|---------|
| `load(skip_rows=0, column_names=None)` | Estrategia doble: `pd.read_xml` (si disponible) → fallback con `xml.etree.ElementTree` (estándar) |
| `can_load_chunks()` | `False` |

### 5.5 ParquetLoader / FeatherLoader / Hdf5Loader / PickleLoader
Requisito opcional: `pyarrow` (Parquet/Feather), `tables` (HDF5). Si falta la dependencia, `load()` lanza `ImportError` con mensaje de instalación.

| Loader | `can_load_chunks()` | `load_in_chunks()` |
|--------|---------------------|--------------------|
| `ParquetLoader` | `True` | `pd.read_parquet(..., engine='pyarrow')` por lotes de filas |
| `FeatherLoader` | `True` | Lectura por rangos de filas |
| `Hdf5Loader` | `True` | `pd.read_hdf` por rangos |
| `PickleLoader` | `False` | — |

### 5.6 SqliteLoader
Requisito opcional: `sqlalchemy`.

| Método | Detalle |
|--------|---------|
| `load(skip_rows=0, column_names=None, table_name=None)` | `SELECT * FROM <tabla> LIMIT -1 OFFSET skip_rows` vía `create_engine` |
| `_get_first_table()` | Devuelve nombre de la primera tabla si no se especifica |
| `get_table_names()` | Lista de tablas de la base |
| `can_load_chunks()` / `load_in_chunks()` | Lectura por lotes OFFSET/LIMIT |

### 5.7 YamlLoader
Requisito opcional: `pyyaml`. `load()` lee el YAML y normaliza a DataFrame (lista de dicts o dict plano).

---

## 6. FolderLoader

```python
class FolderLoader:
    SUPPORTED_EXTENSIONS = ['.xlsx', '.xls']
    def __init__(self, folder_path: str) -> None
```

Carga y metadatos de carpetas con archivos Excel. **No hereda de `FileLoader`.**

| Método | Firma | Descripción |
|--------|-------|-------------|
| `_validate_folder()` | `() -> None` | `FileNotFoundError` / `ValueError` si no es directorio |
| `_scan_excel_files()` | `() -> list[Path]` | `rglob` + filtro por `SUPPORTED_EXTENSIONS`, ordenado |
| `get_excel_files()` | `() -> list[str]` | Rutas de archivos Excel |
| `get_file_metadata(file_path)` | `() -> dict` | `FileMetadata` → dict (hojas, columnas, filas, errores) |
| `get_all_metadata()` | `() -> list[dict]` | Metadatos de todos los archivos |
| `get_metadata_batch(start_idx=0, batch_size=10)` | `() -> list[dict]` | Lote para cargas progresivas |
| `get_metadata_count()` | `() -> int` | Nº de archivos Excel |
| `_estimate_rows(file_path)` | `() -> int` | Estimación de filas |
| `clear_metadata_cache()` | `() -> None` | Limpia cache de metadatos |

---

## 7. Modelos de datos

### `core/models/file_metadata.py` — `FileMetadata` (dataclass)
Campos: `filename`, `filepath`, `file_size_bytes`, `file_size_mb`, `sheets`, `sheet_count`, `columns`, `num_columns`, `num_rows`, `error` (default `None`).
Métodos: `has_error` (property), `to_dict()`.

### `core/models/folder_load_config.py`
- **`ColumnAlignmentStrategy`** (Enum): `BY_POSITION = "position"`, `BY_NAME = "name"`
- **`FolderLoadConfig`** (dataclass): `folder_path`, `included_files`, `excluded_files`, `included_columns`, `excluded_columns`, `alignment_strategy`, `column_rename_mapping`, `skip_rows`, `add_source_column=True`, `source_column_name="__source__"`
  - `should_include_file(filename)` — excluye si está en `excluded_files`; incluye solo si está en `included_files` (vacío = todos)
  - `should_include_column(column_name)` — misma lógica para columnas
  - `to_dict()` — serialización

---

## 8. Diagrama de Dependencias

```
core/loaders/
├── base_loader.py            → FileLoader (ABC)
├── file_loader_factory.py    → FileLoaderFactory + funciones globales
├── *_loader.py (10)          → loaders concretos (heredan FileLoader)
├── folder_loader.py          → FolderLoader (independiente)
└── core/models/              → FileMetadata, FolderLoadConfig

Consumido por:
├── core/data_handler.py      → cargar_datos(), cargar_datos_con_opciones()
├── app/services/data_service.py → DataLoaderThread (carga), FolderLoaderThread (carpetas)
```

---

## 9. Resumen

| Aspecto | Detalle |
|---------|---------|
| **Líneas** | ~1500 (12 archivos) |
| **Patrón** | Factory |
| **Formatos** | CSV, TSV, XLSX, XLS, JSON, XML, Parquet, Feather, HDF5, PKL/PICKLE, DB/SQLITE, YAML/YML |
| **Loaders** | 10 concretos + `FolderLoader` |
| **Interfaz común** | `FileLoader` (ABC) |
| **Dependencias opcionales** | pyarrow, tables, pyyaml, sqlalchemy |
