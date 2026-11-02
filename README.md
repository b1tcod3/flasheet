# Flasheet

Visor de datos tabulares con soporte para archivos Excel y CSV, construido con Python 3 y PySide6.

## Características

- Shell propio sin marco, con sidebar animado y paneles laterales (estilo PyDracula)
- Tema oscuro Dracula por defecto y tema claro conmutable

- Visualización de datos en tabla interactiva
- Filtrado avanzado con soporte regex
- Exportación a PDF, Excel, CSV, SQL e imágenes
- Tablas pivote (simple y combinada)
- Cruce de datos (join entre datasets)
- Carga de carpetas con múltiples archivos
- Optimizado para datasets grandes (paginación virtual)

## Requisitos

- Python 3.10+
- PySide6, Pandas, openpyxl, SQLAlchemy, reportlab

## Instalación

```bash
git clone https://github.com/b1tcod3/flasheet.git
cd flasheet
pip install -r requirements.txt
```

## Ejecución

```bash
python3 main.py
```

## Compilar ejecutable para Windows

1. **Instalar PyInstaller** (en Windows, con el venv activo):
   ```bash
   pip install -r requirements.txt pyinstaller
   ```

2. **Generar el ejecutable**:
   ```bash
   python build_exe.py
   ```

   La configuración completa (hidden imports de `pyarrow`, `tables`, `h5py`,
   `yaml`, `sqlalchemy`, `lxml`, `reportlab`, backends de matplotlib, iconos y
   assets) vive en `flashsheet.spec`, versionado con el código.

3. **Notas**:
   - El build debe ejecutarse en Windows: PyInstaller no compila de forma cruzada.
   - El ejecutable se genera en `dist/` (onefile, sin consola).
   - Si añades un import diferido nuevo (dentro de una función), añádelo a
     `hiddenimports` en `flashsheet.spec`.

## Estructura

```
flash-sheet/
├── main.py                    # Punto de entrada
├── config.py                  # Configuración
├── requirements.txt           # Dependencias
├── app/                       # Aplicación principal
│   ├── app_coordinator.py    # Orquestador
│   ├── shell/                # Ventana sin marco: title bar, sidebar y paneles
│   ├── theme/                # Paleta Dracula + plantilla QSS (oscuro/claro)
│   ├── services/             # Servicios (datos, exportación, filtros, pivote)
│   ├── view_manager/         # Gestor de vistas
│   └── widgets/              # Widgets UI
├── core/                     # Lógica de negocio
├── paginacion/               # Paginación virtual
└── tests/                    # Pruebas
```

## Licencia

MIT
