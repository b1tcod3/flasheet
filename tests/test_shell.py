#!/usr/bin/env python3
"""
Shell de la aplicación: ventana sin marco, sidebar animado y paneles.

Sustituye al antiguo test de la toolbar (QToolBar ya no existe).
"""

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget

from app.shell import ShellWindow
from app.shell.extra_panels import PANEL_WIDTH
from app.shell.side_bar import WIDTH_COLLAPSED, WIDTH_EXPANDED
from app.view_manager import ViewRegistry


def make_shell() -> ShellWindow:
    shell = ShellWindow('Test', 'Subtítulo')
    pages = QStackedWidget()
    for _ in range(6):
        pages.addWidget(QStackedWidget())
    shell.set_pages(pages)
    return shell


class TestShellChrome:
    def test_window_is_frameless_with_grips(self) -> None:
        shell = make_shell()

        assert shell.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert sorted(shell._grips) == ['bottom', 'left', 'right', 'top']

    def test_pages_are_embedded(self) -> None:
        shell = make_shell()

        assert shell.pages is not None
        assert shell.pages.count() == 6

    def test_side_bar_starts_expanded(self) -> None:
        shell = make_shell()

        assert shell.side_bar.is_collapsed() is False
        assert shell.side_bar.width() == WIDTH_EXPANDED

    def test_collapse_hides_labels(self) -> None:
        shell = make_shell()

        shell.side_bar.set_collapsed(True)

        assert shell.side_bar.is_collapsed() is True
        button = shell.side_bar.page_button(ViewRegistry.VIEW_DATA)
        assert button is not None
        assert button.text() == ''

        shell.side_bar.set_collapsed(False)
        assert button.text() == 'Datos'

    def test_collapsed_width_constant(self) -> None:
        assert WIDTH_COLLAPSED < WIDTH_EXPANDED


class TestNavigation:
    def test_page_request_emits_view_registry_id(self) -> None:
        shell = make_shell()
        shell.on_datos_disponibles(True)  # las páginas de datos nacen deshabilitadas
        received: list[int] = []
        shell.side_bar.page_requested.connect(received.append)

        button = shell.side_bar.page_button(ViewRegistry.VIEW_PIVOT)
        assert button is not None
        button.click()

        assert received == [ViewRegistry.VIEW_PIVOT]

    def test_set_active_checks_only_one_button(self) -> None:
        shell = make_shell()

        shell.side_bar.set_active(ViewRegistry.VIEW_PROFILING)

        assert shell.side_bar.active_page() == ViewRegistry.VIEW_PROFILING
        checked = [
            view_id
            for view_id in (
                ViewRegistry.VIEW_MAIN,
                ViewRegistry.VIEW_DATA,
                ViewRegistry.VIEW_JOIN,
                ViewRegistry.VIEW_PIVOT,
                ViewRegistry.VIEW_PROFILING,
                ViewRegistry.VIEW_VISUALIZER,
            )
            if shell.side_bar.page_button(view_id).isChecked()
        ]
        assert checked == [ViewRegistry.VIEW_PROFILING]

    def test_page_info_updates(self) -> None:
        shell = make_shell()

        shell.set_page_info('Datos', 'Vista tabular')

        assert shell.page_title.text() == 'Datos'
        assert shell.page_description.text() == 'Vista tabular'


class TestExtraPanels:
    def test_opening_left_closes_right(self) -> None:
        shell = make_shell()

        shell.toggle_right_panel()
        assert shell.right_panel.is_open is True

        shell.toggle_left_panel()
        assert shell.left_panel.is_open is True
        assert shell.right_panel.is_open is False

    def test_toggle_closes_the_open_panel(self) -> None:
        shell = make_shell()

        shell.toggle_left_panel()
        shell.toggle_left_panel()

        assert shell.left_panel.is_open is False

    def test_panel_width_constant(self) -> None:
        assert PANEL_WIDTH > 0


class TestDataDependentActions:
    def test_actions_disabled_without_data(self) -> None:
        shell = make_shell()

        shell.on_datos_disponibles(False)

        for action in ('export', 'separate', 'clean'):
            button = shell.side_bar.action_button(action)
            assert button is not None
            assert button.isEnabled() is False
        assert shell.export_btn.isEnabled() is False

    def test_actions_enabled_with_data(self) -> None:
        shell = make_shell()

        shell.on_datos_disponibles(True)

        for action in ('export', 'separate', 'clean'):
            assert shell.side_bar.action_button(action).isEnabled() is True
        assert shell.export_btn.isEnabled() is True


class TestMainWindowIntegration:
    def test_main_window_builds_shell_and_views(self) -> None:
        from app.theme import apply_theme
        from PySide6.QtWidgets import QApplication

        apply_theme(QApplication.instance(), 'dark')
        import main

        window = main.MainWindow()

        assert window.pages is not None
        assert window.pages.count() == 6
        assert window.title_bar.title_label.text() == main.APP_TITLE
        assert window.page_title.text() == 'Inicio'

        window._on_page_requested(ViewRegistry.VIEW_DATA)
        assert window.view_coordinator.get_current_view() == ViewRegistry.VIEW_DATA
        assert window.page_title.text() == 'Datos'
        assert window.side_bar.active_page() == ViewRegistry.VIEW_DATA

        window.close()

    def test_shortcuts_are_registered(self) -> None:
        from app.theme import apply_theme
        from PySide6.QtWidgets import QApplication

        apply_theme(QApplication.instance(), 'dark')
        import main

        window = main.MainWindow()
        sequences = {shortcut.key().toString() for shortcut in window._shortcuts}

        for expected in ('Ctrl+O', 'Ctrl+E', 'Ctrl+Shift+J', 'Ctrl+Q', 'F1'):
            assert expected in sequences

        window.close()


class TestLoadingFlow:
    """El cableado señal -> vista debe poblar la tabla al cargar un archivo."""

    @staticmethod
    def _window():  # type: ignore[no-untyped-def]
        from PySide6.QtWidgets import QApplication

        from app.theme import apply_theme
        import main

        apply_theme(QApplication.instance(), 'dark')
        window = main.MainWindow()
        window.show()
        return window

    def test_loading_file_populates_table(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import pandas as pd
        from PySide6.QtWidgets import QApplication

        from app.view_manager import ViewRegistry

        window = self._window()
        app = QApplication.instance()

        csv_path = tmp_path / 'datos.csv'
        pd.DataFrame({
            'A': list(range(1, 31)),
            'B': [f'x{i}' for i in range(30)],
        }).to_csv(csv_path, index=False)

        window.coordinator.iniciar_carga_archivo(str(csv_path))

        thread = window.coordinator._loader_thread
        assert thread is not None
        assert thread.wait(8000) is True, 'la carga no terminó'

        for _ in range(5):
            app.processEvents()

        data_view = window.view_coordinator.get_data_view()
        assert data_view is not None
        assert data_view.pagination_manager is not None, 'la vista no recibió los datos'
        assert data_view.original_df is not None
        assert len(data_view.original_df) == 30
        assert data_view.pagination_manager.get_total_pages() == 3

        model = data_view.table_view.model()
        assert model is not None
        assert model.rowCount() == 10

        assert window.view_coordinator.get_current_view() == ViewRegistry.VIEW_DATA
        assert window.side_bar.active_page() == ViewRegistry.VIEW_DATA
        assert '30 filas' in window.rows_label.text()

        window.close()

    def test_datasets_signals_are_connected(self) -> None:
        """Regresión: sin estas conexiones la tabla queda vacía."""
        window = self._window()
        coordinator = window.coordinator
        view_coordinator = window.view_coordinator

        # Emitir datos_actualizados debe llegar a DataView.set_data
        import pandas as pd

        df = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        coordinator.datos_actualizados.emit(df)

        data_view = view_coordinator.get_data_view()
        assert data_view is not None
        assert data_view.pagination_manager is not None
        assert len(data_view.original_df) == 3

        window.close()
