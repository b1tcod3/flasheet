"""
Tokens de color del tema Dracula.

Paleta basada en el tema de PyDracula (Wanderson M. Pimenta, MIT):
https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Colores de un tema concreto."""

    name: str
    app_bg: str
    menu_bg: str
    surface: str
    surface_hover: str
    input_bg: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_pink: str
    accent_blue: str
    selected_bg: str
    danger: str


DARK = ThemePalette(
    name='dark',
    app_bg='#282c34',
    menu_bg='#21252b',
    surface='#343b48',
    surface_hover='#3a4250',
    input_bg='#1b1d23',
    border='#2c313a',
    text='#dddddd',
    text_muted='#717e95',
    accent='#bd93f9',
    accent_pink='#ff79c6',
    accent_blue='#55aaff',
    selected_bg='#282c34',
    danger='#ff5555',
)

LIGHT = ThemePalette(
    name='light',
    app_bg='#f8f8f2',
    menu_bg='#ececf0',
    surface='#dfe1ea',
    surface_hover='#d3d6e2',
    input_bg='#ffffff',
    border='#c8ccda',
    text='#282a36',
    text_muted='#6272a4',
    accent='#7c5cd6',
    accent_pink='#d63384',
    accent_blue='#2c7be5',
    selected_bg='#ffffff',
    danger='#c0392b',
)

PALETTES = {'dark': DARK, 'light': LIGHT}


def get_palette(name: str) -> ThemePalette:
    """Devolver la paleta por nombre (por defecto, oscura)."""
    return PALETTES.get(name, DARK)


__all__ = ['DARK', 'LIGHT', 'PALETTES', 'ThemePalette', 'get_palette']
