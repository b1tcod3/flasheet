"""
Build del ejecutable de Windows con PyInstaller.

Uso:
    python build_exe.py

Toda la configuración del empaquetado vive en `flashsheet.spec` (versionado),
de modo que el build es reproducible y no depende de una línea de comandos
larga que se desincroniza del README.
"""

import shutil
import sys
from pathlib import Path

from PyInstaller.__main__ import run

PROJECT_ROOT = Path(__file__).resolve().parent
SPEC_FILE = PROJECT_ROOT / 'flashsheet.spec'


def clean_build_artifacts() -> None:
    """Eliminar restos de builds anteriores."""
    for folder in ('build', 'dist'):
        path = PROJECT_ROOT / folder
        if path.exists():
            shutil.rmtree(path)
            print(f'Limpiado: {path}')


def build_executable() -> int:
    """Ejecutar PyInstaller y devolver el código de salida."""
    if not SPEC_FILE.exists():
        print(f'ERROR: no se encontró {SPEC_FILE.name}')
        return 1

    if sys.platform != 'win32':
        print('AVISO: el ejecutable de Windows debe generarse en Windows.')
        print('       En Linux/Mac este build produce un binario nativo distinto.')

    clean_build_artifacts()
    print(f'Construyendo con {SPEC_FILE.name}...')

    run([
        str(SPEC_FILE),
        '--noconfirm',
        '--clean',
        f'--distpath={PROJECT_ROOT / "dist"}',
        f'--workpath={PROJECT_ROOT / "build"}',
    ])

    executable = PROJECT_ROOT / 'dist' / ('FlashSheet.exe' if sys.platform == 'win32' else 'FlashSheet')
    if executable.exists():
        size_mb = executable.stat().st_size / (1024 * 1024)
        print(f'OK: {executable} ({size_mb:.1f} MB)')
        return 0

    print('ERROR: no se generó el ejecutable')
    return 1


if __name__ == '__main__':
    sys.exit(build_executable())
