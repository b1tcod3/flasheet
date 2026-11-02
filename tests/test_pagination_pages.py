#!/usr/bin/env python3
"""
Paginación: límites de página, casos extremos y flujo en DataView.

Sustituye a los antiguos scripts de depuración (test_pagination_bug,
test_pagination_comprehensive, test_pagination_final, test.py, test_page_debug)
que imprimían resultados pero no fallaban nunca.
"""

import pandas as pd

from app.models.pandas_model import VirtualizedPandasModel
from app.services.pagination_manager import PaginationManager
from app.widgets.data_view import DataView

TOTAL_ROWS = 35
PAGE_SIZE = 10


def build_df(total: int = TOTAL_ROWS) -> pd.DataFrame:
    return pd.DataFrame({
        'ID': list(range(1, total + 1)),
        'Nombre': [f'Fila_{i}' for i in range(1, total + 1)],
        'Valor': [i * 10 for i in range(1, total + 1)],
    })


class TestPageBoundaries:
    def test_total_pages_rounds_up(self) -> None:
        manager = PaginationManager(build_df(TOTAL_ROWS), PAGE_SIZE)

        assert manager.get_total_pages() == 4

    def test_exact_multiple_has_no_trailing_empty_page(self) -> None:
        manager = PaginationManager(build_df(30), PAGE_SIZE)

        assert manager.get_total_pages() == 3

    def test_every_page_has_rows_and_correct_ids(self) -> None:
        manager = PaginationManager(build_df(TOTAL_ROWS), PAGE_SIZE)

        for page in range(1, manager.get_total_pages() + 1):
            manager.set_current_page(page)
            page_data = manager.get_page_data()

            expected_start = (page - 1) * PAGE_SIZE + 1
            expected_end = min(page * PAGE_SIZE, TOTAL_ROWS)

            assert len(page_data) == expected_end - expected_start + 1
            assert page_data.iloc[0]['ID'] == expected_start
            assert page_data.iloc[-1]['ID'] == expected_end

    def test_page_info_reports_visible_range(self) -> None:
        manager = PaginationManager(build_df(TOTAL_ROWS), PAGE_SIZE)

        manager.set_current_page(4)
        info = manager.get_page_info()

        assert info['start_row'] == 31
        assert info['end_row'] == 35
        assert info['rows_in_page'] == 5
        assert info['total_rows'] == TOTAL_ROWS
        assert info['current_page'] == 4

    def test_last_page_is_reachable_and_previous_works(self) -> None:
        manager = PaginationManager(build_df(TOTAL_ROWS), PAGE_SIZE)

        manager.last_page()
        assert manager.get_current_page() == 4

        manager.previous_page()
        assert manager.get_current_page() == 3

        manager.first_page()
        assert manager.get_current_page() == 1


class TestPaginationEdgeCases:
    def test_dataset_smaller_than_page_size(self) -> None:
        manager = PaginationManager(build_df(3), PAGE_SIZE)

        page_data = manager.get_page_data()
        model = VirtualizedPandasModel(page_data)

        assert manager.get_total_pages() == 1
        assert len(page_data) == 3
        assert model.rowCount() == 3
        assert model.data(model.index(0, 0)) == '1'

    def test_empty_dataset(self) -> None:
        manager = PaginationManager(pd.DataFrame(), PAGE_SIZE)

        assert manager.get_total_pages() == 0
        assert manager.get_page_data().empty
        assert manager.get_page_info()['total_rows'] == 0
        assert manager.can_go_next() is False
        assert manager.can_go_previous() is False

    def test_missing_values_render_as_empty_string(self) -> None:
        df = pd.DataFrame({
            'ID': [1, 2, 3],
            'Nombre': ['A', None, 'C'],
            'Valor': [10, None, 30],
        })
        manager = PaginationManager(df, PAGE_SIZE)
        model = VirtualizedPandasModel(manager.get_page_data())

        assert model.data(model.index(1, 1)) == ''
        assert model.data(model.index(1, 2)) == ''

    def test_page_size_change_keeps_approximate_position(self) -> None:
        manager = PaginationManager(build_df(24), page_size=5)
        manager.set_current_page(3)  # filas 11-15

        manager.set_page_size(10)

        assert manager.get_page_size() == 10
        assert manager.get_total_pages() == 3
        assert manager.get_current_page() == 2  # fila 11 cae en la 2ª página de 10

    def test_page_size_change_triggers_signal(self) -> None:
        manager = PaginationManager(build_df(24), page_size=5)
        sizes: list[int] = []
        manager.page_size_changed.connect(sizes.append)

        manager.set_page_size(20)

        assert sizes == [20]


class TestLargeDatasetPagination:
    def test_large_dataset_first_and_last_cell(self) -> None:
        manager = PaginationManager(build_df(6000), page_size=100)

        page_data = manager.get_page_data()
        model = VirtualizedPandasModel(page_data)

        assert manager.get_total_pages() == 60
        assert len(page_data) == 100
        assert model.data(model.index(0, 0)) == '1'
        assert model.data(model.index(99, 0)) == '100'

    def test_model_reads_positional_rows_after_filter(self) -> None:
        """Regresión: el chunk usaba el índice del DataFrame como posición."""
        manager = PaginationManager(build_df(200), page_size=50)
        manager.apply_filter('Nombre', 'Fila_1')

        page_data = manager.get_page_data()
        model = VirtualizedPandasModel(page_data)

        assert model.data(model.index(0, 0)) == str(page_data.iloc[0]['ID'])
        assert model.data(model.index(len(page_data) - 1, 0)) == str(page_data.iloc[-1]['ID'])


class TestDataViewPaginationFlow:
    def test_navigating_every_page_shows_matching_data(self) -> None:
        data_view = DataView()
        data_view.set_data(build_df(30))
        manager = data_view.pagination_manager
        assert manager is not None

        for page in range(1, manager.get_total_pages() + 1):
            manager.set_current_page(page)

            model = data_view.pandas_model
            page_data = manager.get_page_data()

            assert model is not None
            assert model.rowCount() == len(page_data)
            assert model.data(model.index(0, 0)) == str(page_data.iloc[0]['ID'])
            assert model.data(model.index(len(page_data) - 1, 0)) == str(page_data.iloc[-1]['ID'])

    def test_navigation_does_not_blank_the_page(self) -> None:
        """Regresión: la página 2 aparecía vacía al navegar."""
        data_view = DataView()
        data_view.set_data(build_df(TOTAL_ROWS))
        manager = data_view.pagination_manager
        assert manager is not None

        manager.next_page()

        assert manager.get_current_page() == 2
        assert len(manager.get_page_data()) == PAGE_SIZE
        assert data_view.pandas_model is not None
        assert data_view.pandas_model.rowCount() == PAGE_SIZE


class TestFilterAndPageState:
    def test_filter_resets_to_first_page_and_clear_restores(self) -> None:
        manager = PaginationManager(build_df(250), page_size=50)
        manager.set_current_page(3)
        original_rows = manager.get_total_rows()

        manager.apply_filter('Nombre', 'Fila_1')
        assert manager.get_current_page() == 1
        assert manager.get_total_rows() < original_rows

        manager.clear_filter()
        assert manager.get_total_rows() == original_rows
        assert manager.get_current_page() == 1

    def test_model_from_two_page_slices_reads_each_slice(self) -> None:
        """Cada página se renderiza con su propio recorte del dataset."""
        full_df = build_df(20)
        page1 = full_df.iloc[0:10].copy()
        page2 = full_df.iloc[10:20].copy()

        model1 = VirtualizedPandasModel(page1)
        model2 = VirtualizedPandasModel(page2)

        assert model1.data(model1.index(0, 0)) == str(page1.iloc[0]['ID'])
        assert model1.data(model1.index(9, 0)) == str(page1.iloc[-1]['ID'])
        assert model2.data(model2.index(0, 0)) == str(page2.iloc[0]['ID'])
        assert model2.data(model2.index(9, 0)) == str(page2.iloc[-1]['ID'])

    def test_export_current_page_returns_visible_rows(self) -> None:
        data_view = DataView()
        data_view.set_data(build_df(TOTAL_ROWS))
        manager = data_view.pagination_manager
        assert manager is not None

        manager.set_current_page(2)
        exported = data_view.export_current_page()

        assert exported['ID'].tolist() == manager.get_page_data()['ID'].tolist()
        assert len(exported) == PAGE_SIZE
