#!/usr/bin/env python3
"""
Tema claro: la app no debe depender de la paleta del sistema operativo.
"""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from app.theme import apply_light_theme, base_stylesheet, build_light_palette


def test_palette_is_light() -> None:
    palette = build_light_palette()

    window = palette.color(QPalette.ColorRole.Window)
    text = palette.color(QPalette.ColorRole.WindowText)

    assert window.name() == '#f8fafc'
    assert text.name() == '#0f172a'
    # El texto debe ser oscuro sobre fondo claro
    assert text.lightness() < window.lightness()


def test_disabled_text_stays_readable() -> None:
    palette = build_light_palette()
    disabled = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)

    assert disabled.name() == '#94a3b8'


def test_stylesheet_covers_known_dark_mode_gaps() -> None:
    qss = base_stylesheet()

    # Desplegable de QComboBox (no hereda el estilo del combo)
    assert 'QComboBox QAbstractItemView' in qss
    # Indicador de checkbox
    assert 'QCheckBox::indicator' in qss
    # Viewport de QScrollArea
    assert 'QScrollArea > QWidget > QWidget' in qss
    # Tooltips y menús
    assert 'QToolTip' in qss
    assert 'QMenu' in qss


def test_apply_light_theme_sets_style_palette_and_sheet() -> None:
    app = QApplication.instance() or QApplication([])

    apply_light_theme(app)

    # Al fijar un stylesheet Qt envuelve el estilo base en QStyleSheetStyle,
    # así que se comprueba el efecto (paleta y hoja), no el nombre del estilo.
    assert app.palette().color(QPalette.ColorRole.Window).name() == '#f8fafc'
    assert app.palette().color(QPalette.ColorRole.WindowText).name() == '#0f172a'
    assert 'QComboBox QAbstractItemView' in app.styleSheet()
