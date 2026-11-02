#!/usr/bin/env python3
"""
Ordenamiento con paginación.

Contrato verificado aquí:
- El orden se aplica al dataset completo, no a la página visible.
- La página actual se conserva si sigue siendo válida.
- El filtro activo se reaplica después de ordenar.
- El modelo no muta datos: solo emite `sort_requested`.
"""

import pandas as pd
import pytest
from PySide6.QtCore import Qt

from app.models.pandas_model import VirtualizedPandasModel
from app.services.filter_service import ColumnNotFoundError
from app.services.pagination_manager import PaginationManager
from app.widgets.data_view import DataView

PAGE_SIZE = 10
TOTAL_ROWS = 100


def create_unsorted_df() -> pd.DataFrame:
    """Dataset de 100 filas con valores descendentes y categorías cíclicas."""
    return pd.DataFrame({
        'Nombre': [f'Item_{i:03d}' for i in range(TOTAL_ROWS)],
        'Valor': list(range(TOTAL_ROWS, 0, -1)),
        'Categoria': [f'Cat_{i % 10}' for i in range(TOTAL_ROWS)],
    })


class TestPaginationManagerSorting:
    def test_sort_by_orders_full_dataset(self) -> None:
        manager = PaginationManager(create_unsorted_df(), PAGE_SIZE)

        manager.sort_by('Valor', ascending=True)

        assert manager.original_df['Valor'].tolist() == sorted(range(1, TOTAL_ROWS + 1))
        assert len(manager.filtered_df) == TOTAL_ROWS

    def test_sort_by_descending(self) -> None:
        manager = PaginationManager(create_unsorted_df(), PAGE_SIZE)

        manager.sort_by('Valor', ascending=False)

        valores = manager.original_df['Valor'].tolist()
        assert valores == sorted(valores, reverse=True)

    def test_sort_by_preserves_current_page(self) -> None:
        manager = PaginationManager(create_unsorted_df(), PAGE_SIZE)
        manager.set_current_page(3)

        manager.sort_by('Valor', ascending=False)

        assert manager.get_current_page() == 3
        assert len(manager.get_page_data()) == PAGE_SIZE

    def test_sort_by_resets_page_when_requested(self) -> None:
        manager = PaginationManager(create_unsorted_df(), PAGE_SIZE)
        manager.set_current_page(4)

        manager.sort_by('Nombre', ascending=True, preserve_page=False)

        assert manager.get_current_page() == 1

    def test_sort_by_reapplies_active_filter(self) -> None:
        manager = PaginationManager(create_unsorted_df(), PAGE_SIZE)
        manager.apply_filter('Categoria', 'Cat_1')
        assert len(manager.filtered_df) == TOTAL_ROWS // 10

        manager.sort_by('Valor', ascending=True)

        assert len(manager.filtered_df) == TOTAL_ROWS // 10
        assert set(manager.filtered_df['Categoria']) == {'Cat_1'}
        valores = manager.filtered_df['Valor'].tolist()
        assert valores == sorted(valores)

    def test_sort_by_unknown_column_raises(self) -> None:
        manager = PaginationManager(create_unsorted_df(), PAGE_SIZE)

        with pytest.raises(ColumnNotFoundError):
            manager.sort_by('NoExiste', ascending=True)


class TestModelSortContract:
    def test_model_sort_emits_request_without_mutating(self) -> None:
        page = create_unsorted_df().head(PAGE_SIZE)
        model = VirtualizedPandasModel(page)
        received: list[tuple[str, bool]] = []
        model.sort_requested.connect(lambda name, asc: received.append((name, asc)))

        model.sort(1, Qt.DescendingOrder)

        assert received == [('Valor', False)]
        assert model.full_df['Valor'].tolist() == page['Valor'].tolist()

    def test_model_sort_ignores_out_of_range_column(self) -> None:
        model = VirtualizedPandasModel(create_unsorted_df().head(PAGE_SIZE))
        received: list[tuple[str, bool]] = []
        model.sort_requested.connect(lambda name, asc: received.append((name, asc)))

        model.sort(99, Qt.AscendingOrder)

        assert received == []

    def test_set_data_rejects_out_of_range_index(self) -> None:
        model = VirtualizedPandasModel(create_unsorted_df().head(PAGE_SIZE))

        assert model.setData(model.index(999, 0), 'x') is False


class TestDataViewSortingIntegration:
    def test_data_view_sorts_full_dataset_and_keeps_page(self) -> None:
        data_view = DataView()
        data_view.set_data(create_unsorted_df())
        manager = data_view.pagination_manager
        assert manager is not None
        manager.set_current_page(3)

        assert data_view.pandas_model is not None
        data_view.pandas_model.sort(1, Qt.DescendingOrder)

        assert manager.get_current_page() == 3
        page_values = manager.get_page_data()['Valor'].tolist()
        assert page_values == sorted(page_values, reverse=True)

        full_values = manager.original_df['Valor'].tolist()
        assert full_values == sorted(full_values, reverse=True)

    def test_data_view_sorts_by_clicked_column_not_first(self) -> None:
        """Regresión: antes se ordenaba siempre por la primera columna."""
        data_view = DataView()
        data_view.set_data(create_unsorted_df())

        assert data_view.pandas_model is not None
        data_view.pandas_model.sort(1, Qt.AscendingOrder)

        manager = data_view.pagination_manager
        assert manager is not None
        valores = manager.original_df['Valor'].tolist()
        assert valores == sorted(range(1, TOTAL_ROWS + 1))
        # Si se hubiera ordenado por 'Nombre' (columna 0), 'Valor' seguiría descendente.
        assert manager.original_df['Nombre'].tolist()[0] == 'Item_099'
