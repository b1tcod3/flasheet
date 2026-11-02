"""
Tema visual de la aplicación.

Un único punto que fija la paleta clara y el QSS base. Sin esto, en Windows
con modo oscuro la app hereda la paleta del sistema mientras los widgets
hardcodean fondos claros, y el texto queda invisible.

Regla: cualquier widget que se pinte por su cuenta (setStyleSheet) debe
declarar `color:` explícito; el QSS de aquí cubre el resto.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

WINDOW_BG = "#f8fafc"
SURFACE = "#ffffff"
TEXT = "#0f172a"
TEXT_MUTED = "#475569"
BORDER = "#cbd5e1"
ACCENT = "#3b82f6"
ACCENT_SOFT = "#dbeafe"
ACCENT_TEXT = "#1e40af"

_BASE_STYLESHEET = f"""
QWidget {{
    color: {TEXT};
}}

QToolTip {{
    color: {TEXT};
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    padding: 4px 6px;
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    color: {TEXT};
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT_TEXT};
}}

QLineEdit:disabled, QSpinBox:disabled, QTextEdit:disabled {{
    color: {TEXT_MUTED};
    background-color: {WINDOW_BG};
}}

/* El desplegable de los QComboBox no hereda su estilo: necesita su propia regla. */
QComboBox QAbstractItemView {{
    color: {TEXT};
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    outline: none;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT_TEXT};
}}

QAbstractItemView {{
    color: {TEXT};
    background-color: {SURFACE};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT_TEXT};
}}

QCheckBox {{
    color: {TEXT};
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {SURFACE};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QCheckBox::indicator:disabled {{
    background-color: {WINDOW_BG};
    border-color: #e2e8f0;
}}

QScrollArea {{
    background: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QMenu {{
    color: {TEXT};
    background-color: {SURFACE};
    border: 1px solid {BORDER};
}}

QMenu::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_TEXT};
}}

QMenu::separator {{
    height: 1px;
    background: #e2e8f0;
    margin: 4px 8px;
}}

QTabBar::tab {{
    color: {TEXT_MUTED};
    background: #f1f5f9;
    padding: 6px 12px;
    border: 1px solid #e2e8f0;
    border-bottom: none;
}}

QTabBar::tab:selected {{
    color: {ACCENT_TEXT};
    background: {SURFACE};
}}

QGroupBox {{
    color: {TEXT};
}}

QLabel {{
    color: {TEXT};
}}

QProgressBar {{
    color: {TEXT};
    background-color: #e2e8f0;
    border: none;
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 4px;
}}

QToolBar {{
    background: transparent;
    border: none;
}}
"""


def build_light_palette() -> QPalette:
    """Paleta clara explícita, independiente del tema del sistema."""
    palette = QPalette()
    roles = QPalette.ColorRole
    groups = QPalette.ColorGroup

    palette.setColor(roles.Window, QColor(WINDOW_BG))
    palette.setColor(roles.WindowText, QColor(TEXT))
    palette.setColor(roles.Base, QColor(SURFACE))
    palette.setColor(roles.AlternateBase, QColor(WINDOW_BG))
    palette.setColor(roles.Text, QColor(TEXT))
    palette.setColor(roles.Button, QColor("#f5f6f7"))
    palette.setColor(roles.ButtonText, QColor(TEXT))
    palette.setColor(roles.ToolTipBase, QColor(SURFACE))
    palette.setColor(roles.ToolTipText, QColor(TEXT))
    palette.setColor(roles.Highlight, QColor(ACCENT_SOFT))
    palette.setColor(roles.HighlightedText, QColor(ACCENT_TEXT))
    palette.setColor(roles.PlaceholderText, QColor("#94a3b8"))
    palette.setColor(roles.BrightText, QColor("#dc2626"))

    palette.setColor(groups.Disabled, roles.Text, QColor("#94a3b8"))
    palette.setColor(groups.Disabled, roles.WindowText, QColor("#94a3b8"))
    palette.setColor(groups.Disabled, roles.ButtonText, QColor("#94a3b8"))

    return palette


def apply_light_theme(app: QApplication) -> None:
    """Fijar estilo Fusion, paleta clara y QSS base de la aplicación."""
    app.setStyle("Fusion")
    app.setPalette(build_light_palette())
    app.setStyleSheet(_BASE_STYLESHEET)


def base_stylesheet() -> str:
    """Exponer el QSS base (útil en pruebas)."""
    return _BASE_STYLESHEET
