# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller para FlashSheet (onefile, sin consola).

Se versiona junto al código para que el build sea reproducible:

    python build_exe.py

Motivos de las opciones (ver reglas del skill pyside6-desktop):
- `assets` se empaqueta como dato: los iconos se leen por ruta de fichero.
- No se empaqueta `app/` ni `core/` como datos: son módulos y PyInstaller los
  recoge del bytecode.
- Los loaders importan pyarrow/tables/h5py/yaml/sqlalchemy/lxml dentro de
  funciones y matplotlib/reportlab cargan backends y datos dinámicamente:
  necesitan hidden imports y collect_*.
- QtSvg es necesario para los iconos .svg de la toolbar.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve()
ASSETS_DIR = PROJECT_ROOT / 'assets'
ICON_FILE = ASSETS_DIR / 'logo.ico'
if not ICON_FILE.exists():
    ICON_FILE = ASSETS_DIR / 'logo.png'

hiddenimports = [
    # Qt: QIcon con .svg y plugins de plataforma
    'PySide6.QtSvg',
    'PySide6.QtNetwork',
    # Imports diferidos de los loaders
    'yaml',
    'lxml.etree',
    'pyarrow',
    'pyarrow.parquet',
    'tables',
    'h5py',
    'sqlalchemy.dialects.sqlite',
    # Exportación
    'reportlab.pdfbase._fontdata',
    'openpyxl',
]

hiddenimports += collect_submodules('matplotlib.backends')
hiddenimports += collect_submodules('pyarrow')

datas = [
    (str(ASSETS_DIR), 'assets'),
    (str(PROJECT_ROOT / 'app' / 'theme' / 'base.qss'), 'app/theme'),
]
datas += collect_data_files('reportlab')

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Evitar que se arrastren bindings alternativos
        'PyQt5',
        'PyQt6',
        'PySide2',
        'tkinter',
        # Frameworks de ML que no son dependencias y engordan el .exe
        # (si están instalados, sus hooks de PyInstaller pueden fallar)
        'torch',
        'torchvision',
        'tensorflow',
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FlashSheet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3*.dll', 'Qt6*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE) if ICON_FILE.exists() else None,
)

if sys.platform != 'win32':
    print('AVISO: este spec está pensado para Windows; en Linux/Mac genera un binario nativo.')
