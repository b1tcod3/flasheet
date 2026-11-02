"""
Shell visual de la aplicación (ventana sin marco estilo PyDracula).

Inspirado en PyDracula de Wanderson M. Pimenta (MIT):
https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6
"""

from .extra_panels import ExtraPanel, LeftPanel, RightPanel
from .main_window import FRAME_MARGIN, ShellWindow
from .side_bar import SideBar
from .title_bar import TitleBar

__all__ = [
    'ExtraPanel',
    'FRAME_MARGIN',
    'LeftPanel',
    'RightPanel',
    'ShellWindow',
    'SideBar',
    'TitleBar',
]
