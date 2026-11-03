"""
Carga y aplicación del tema.

`base.qss` es una plantilla con tokens (`$text`, `$accent`…) que se sustituyen
con la paleta elegida. Cambiar de tema es volver a aplicar el stylesheet: no
hay colores hardcodeados en los widgets del shell.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from string import Template

from PySide6.QtGui import QFont, QFontDatabase, QPalette, QColor
from PySide6.QtWidgets import QApplication

from app.theme.palette import PALETTES, ThemePalette, get_palette

_QSS_PATH = Path(__file__).resolve().parent / 'base.qss'
_ICONS_DIR = Path(__file__).resolve().parent / 'icons'
_SVG_CACHE_DIR = Path(tempfile.gettempdir()) / 'flashsheet-theme'
_current_theme = 'dark'

logger = logging.getLogger(__name__)


def current_theme() -> str:
    """Nombre del tema activo."""
    return _current_theme


def available_themes() -> list[str]:
    return list(PALETTES)


def _read_template() -> Template:
    return Template(_QSS_PATH.read_text(encoding='utf-8'))



def _themed_svg(name: str, color: str) -> str:
    """Generar el SVG del indicador de orden con el color del tema.

    QSS no permite variables en `url()`, así que se escribe una copia
    coloreada en un directorio de caché y se referencia por ruta absoluta.
    """
    template = _ICONS_DIR / f'{name}.svg.tmpl'
    if not template.exists():
        return ''

    target = _SVG_CACHE_DIR / f'{name}-{color.lstrip("#")}.svg'
    try:
        if not target.exists():
            _SVG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            target.write_text(
                template.read_text(encoding='utf-8').replace('@COLOR@', color),
                encoding='utf-8',
            )
    except OSError:
        return ''
    return target.as_posix()


def render_stylesheet(theme: str = 'dark') -> str:
    """Resolver la plantilla QSS con los colores y los SVG del tema."""
    palette = get_palette(theme)
    tokens = {
        key: value for key, value in vars(palette).items() if isinstance(value, str)
    }
    tokens['sort_down'] = _themed_svg('sort_down', palette.accent)
    tokens['sort_up'] = _themed_svg('sort_up', palette.accent)

    try:
        template = _read_template()
    except OSError:
        # Bundle sin la hoja de estilos: la app sigue arrancando con la paleta.
        logger.warning("No se encontró base.qss; se aplica solo la paleta del tema")
        return ''

    return template.substitute(tokens)


def build_palette(theme: str = 'dark') -> QPalette:
    """QPalette coherente con el QSS (para widgets nativos y menús)."""
    tokens: ThemePalette = get_palette(theme)
    palette = QPalette()
    roles = QPalette.ColorRole
    groups = QPalette.ColorGroup

    palette.setColor(roles.Window, QColor(tokens.app_bg))
    palette.setColor(roles.WindowText, QColor(tokens.text))
    palette.setColor(roles.Base, QColor(tokens.input_bg))
    palette.setColor(roles.AlternateBase, QColor(tokens.menu_bg))
    palette.setColor(roles.Text, QColor(tokens.text))
    palette.setColor(roles.Button, QColor(tokens.surface))
    palette.setColor(roles.ButtonText, QColor(tokens.text))
    palette.setColor(roles.ToolTipBase, QColor(tokens.menu_bg))
    palette.setColor(roles.ToolTipText, QColor(tokens.text))
    palette.setColor(roles.Highlight, QColor(tokens.accent))
    palette.setColor(roles.HighlightedText, QColor(tokens.menu_bg))
    palette.setColor(roles.PlaceholderText, QColor(tokens.text_muted))
    palette.setColor(roles.BrightText, QColor(tokens.danger))

    palette.setColor(groups.Disabled, roles.Text, QColor(tokens.text_muted))
    palette.setColor(groups.Disabled, roles.WindowText, QColor(tokens.text_muted))
    palette.setColor(groups.Disabled, roles.ButtonText, QColor(tokens.text_muted))

    return palette


def _resolve_font() -> QFont:
    """Usar Segoe UI si existe; si no, la fuente por defecto del sistema."""
    families = set(QFontDatabase.families())
    for candidate in ('Segoe UI', 'Noto Sans', 'DejaVu Sans'):
        if candidate in families:
            font = QFont(candidate, 10)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            return font
    return QFont()


def apply_theme(app: QApplication, theme: str = 'dark') -> None:
    """Aplicar estilo Fusion, paleta y QSS del tema indicado."""
    global _current_theme
    _current_theme = theme if theme in PALETTES else 'dark'

    app.setStyle('Fusion')
    app.setPalette(build_palette(_current_theme))
    app.setFont(_resolve_font())
    app.setStyleSheet(render_stylesheet(_current_theme))


def toggle_theme(app: QApplication) -> str:
    """Alternar entre oscuro y claro y devolver el tema resultante."""
    next_theme = 'light' if _current_theme == 'dark' else 'dark'
    apply_theme(app, next_theme)
    return next_theme


# --- Compatibilidad con la API anterior (tema claro explícito) ---
def apply_light_theme(app: QApplication) -> None:
    apply_theme(app, 'light')


def build_light_palette() -> QPalette:
    return build_palette('light')


def base_stylesheet(theme: str = 'dark') -> str:
    return render_stylesheet(theme)


__all__ = [
    'apply_light_theme',
    'apply_theme',
    'available_themes',
    'base_stylesheet',
    'build_light_palette',
    'build_palette',
    'current_theme',
    'render_stylesheet',
    'toggle_theme',
]
