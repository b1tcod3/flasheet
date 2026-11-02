"""
Gestión centralizada de recursos estáticos de la aplicación.
"""

import sys
from pathlib import Path


def _assets_dir() -> Path:
    """Localizar la carpeta `assets` tanto en desarrollo como empaquetada.

    En un ejecutable PyInstaller (onefile) `__file__` apunta al directorio
    temporal de extracción, por lo que la referencia fiable es `sys._MEIPASS`.
    """
    if getattr(sys, 'frozen', False):
        bundle_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        return bundle_dir / "assets"

    return Path(__file__).resolve().parent.parent / "assets"


def get_asset_path(asset_name: str) -> Path:
    """
    Devuelve la ruta absoluta a un recurso dentro de la carpeta assets/.

    Args:
        asset_name: Nombre del archivo (ej. 'logo.png').

    Returns:
        Path completo al recurso.
    """
    return _assets_dir() / asset_name
