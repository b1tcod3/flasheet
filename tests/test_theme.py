#!/usr/bin/env python3
"""
Tema: oscuro Dracula por defecto y claro conmutable.

Los colores salen de `app/theme/palette.py`; el QSS es una plantilla que se
resuelve con esos tokens, así que cambiar de tema no requiere tocar widgets.
"""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from app.theme import (
    apply_theme,
    available_themes,
    build_palette,
    current_theme,
    render_stylesheet,
    toggle_theme,
)
from app.theme.palette import DARK, LIGHT


def test_available_themes() -> None:
    assert available_themes() == ['dark', 'light']


def test_dark_palette_uses_dracula_colors() -> None:
    palette = build_palette('dark')

    assert palette.color(QPalette.ColorRole.Window).name() == DARK.app_bg
    assert palette.color(QPalette.ColorRole.Base).name() == DARK.input_bg
    # Texto claro sobre fondo oscuro
    assert palette.color(QPalette.ColorRole.WindowText).lightness() > 128
    assert palette.color(QPalette.ColorRole.Window).lightness() < 128


def test_light_palette_is_light() -> None:
    palette = build_palette('light')

    assert palette.color(QPalette.ColorRole.Window).name() == LIGHT.app_bg
    assert palette.color(QPalette.ColorRole.Window).lightness() > 200


def test_stylesheet_resolves_tokens() -> None:
    dark_qss = render_stylesheet('dark')
    light_qss = render_stylesheet('light')

    assert '$' not in dark_qss, 'quedaron tokens sin resolver'
    assert DARK.app_bg in dark_qss
    assert LIGHT.app_bg in light_qss
    assert dark_qss != light_qss


def test_stylesheet_covers_known_dark_mode_gaps() -> None:
    qss = render_stylesheet('dark')

    # Desplegable de QComboBox (no hereda el estilo del combo)
    assert 'QComboBox QAbstractItemView' in qss
    # Indicador de checkbox
    assert 'QCheckBox::indicator' in qss
    # Viewport de QScrollArea
    assert 'QScrollArea > QWidget > QWidget' in qss
    assert 'QToolTip' in qss
    assert 'QMenu' in qss


def test_apply_theme_sets_palette_and_sheet() -> None:
    app = QApplication.instance() or QApplication([])

    apply_theme(app, 'dark')

    assert current_theme() == 'dark'
    assert app.palette().color(QPalette.ColorRole.Window).name() == DARK.app_bg
    assert DARK.app_bg in app.styleSheet()


def test_toggle_theme_switches_and_returns_back() -> None:
    app = QApplication.instance() or QApplication([])
    apply_theme(app, 'dark')

    assert toggle_theme(app) == 'light'
    assert app.palette().color(QPalette.ColorRole.Window).name() == LIGHT.app_bg

    assert toggle_theme(app) == 'dark'
    assert app.palette().color(QPalette.ColorRole.Window).name() == DARK.app_bg


class TestViewThemeRefresh:
    """Las vistas que fijan colores al construirse deben repintarse."""

    @staticmethod
    def _app() -> QApplication:
        return QApplication.instance() or QApplication([])

    def test_profiling_view_repaints_on_theme_change(self) -> None:
        from app.widgets.profiling_view import ProfilingView

        app = self._app()
        apply_theme(app, 'dark')
        view = ProfilingView()

        dark_style = view._header.styleSheet()
        assert DARK.text in dark_style

        apply_theme(app, 'light')
        view.refresh_theme()

        assert LIGHT.text in view._header.styleSheet()
        assert view._header.styleSheet() != dark_style

    def test_profiling_view_rebuilds_cards(self) -> None:
        from app.widgets.profiling_view import ProfilingView

        app = self._app()
        apply_theme(app, 'dark')
        view = ProfilingView()
        view.set_profile({
            'total_rows': 10,
            'total_columns': 1,
            'columns': {
                'importe': {
                    'dtype': 'int64',
                    'null_count': 0,
                    'null_percent': 0.0,
                    'unique_count': 10,
                    'unique_percent': 100.0,
                },
            },
            'memory_usage_mb': 0.1,
            'duplicated_rows': 0,
            'data_quality_summary': {},
        })
        cards_dark = view._cards_layout.count()

        apply_theme(app, 'light')
        view.refresh_theme()

        assert view._cards_layout.count() == cards_dark

    def test_visualizer_repaints_on_theme_change(self) -> None:
        from app.widgets.quick_visualizer_view import QuickVisualizerView

        app = self._app()
        apply_theme(app, 'dark')
        view = QuickVisualizerView()

        dark_style = view._header.styleSheet()
        assert DARK.text in dark_style

        apply_theme(app, 'light')
        view.refresh_theme()

        assert LIGHT.text in view._header.styleSheet()

    def test_view_coordinator_refreshes_views(self) -> None:
        from app.view_manager.view_coordinator import ViewCoordinator

        app = self._app()
        apply_theme(app, 'dark')

        class FakeView:
            def __init__(self) -> None:
                self.calls = 0

            def refresh_theme(self) -> None:
                self.calls += 1

        coordinator = ViewCoordinator()
        fake = FakeView()
        coordinator._views[0] = fake  # type: ignore[assignment]

        coordinator.refresh_theme()

        assert fake.calls == 1
