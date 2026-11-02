#!/usr/bin/env python3
"""
Columnas con tipos mixtos (int + str).

Un Excel real suele traer una columna `object` como `[10, 'A-2', 30, 'B-1']`.
Comparar esos valores con `<` lanza TypeError, así que ordenar (filtros
rápidos, orden de la tabla y joins) debe tolerarlo sin romper la carga.
"""

import pandas as pd
import pytest
from PySide6.QtCore import Qt

from app.services.filter_service import FilterService
from app.services.pagination_manager import PaginationManager
from app.widgets.data_view import _MAX_QUICK_FILTER_VALUES, DataView
from core.join.data_join_manager import safe_sort_values

MIXED_VALUES = [10, 'A-2', 30, 'B-1', None, 50]


def mixed_df() -> pd.DataFrame:
    return pd.DataFrame({
        'Codigo': list(MIXED_VALUES),
        'Valor': [5, 3, 1, 6, 2, 4],
    })


def test_column_is_really_mixed() -> None:
    df = mixed_df()

    assert df['Codigo'].dtype == object
    with pytest.raises(TypeError):
        sorted(df['Codigo'].dropna().tolist())


class TestDataViewWithMixedColumn:
    def test_load_does_not_raise(self) -> None:
        data_view = DataView()

        data_view.set_data(mixed_df())

        manager = data_view.pagination_manager
        assert manager is not None
        assert manager.get_total_rows() == 6
        assert data_view.table_view.model() is not None
        assert data_view.table_view.model().rowCount() == 6

    def test_quick_filters_are_built_and_bounded(self) -> None:
        data_view = DataView()

        data_view.set_data(mixed_df())

        group = data_view._quick_filter_groups.get('Codigo')
        assert group is not None
        buttons = group.buttons()
        assert buttons[0].text() == 'Todos'
        assert 1 < len(buttons) <= _MAX_QUICK_FILTER_VALUES + 1

    def test_quick_filter_still_filters(self) -> None:
        data_view = DataView()
        data_view.set_data(mixed_df())
        manager = data_view.pagination_manager
        assert manager is not None

        data_view._apply_quick_filter('Codigo', 'A-2')

        assert manager.filtered_df['Codigo'].tolist() == ['A-2']


class TestSortingWithMixedColumn:
    def test_sort_by_ascending_keeps_rows_and_values(self) -> None:
        manager = PaginationManager(mixed_df(), page_size=10)

        manager.sort_by('Codigo', ascending=True)

        assert len(manager.original_df) == 6
        # Los valores siguen siendo los originales (no se convierten a str)
        assert 10 in manager.original_df['Codigo'].tolist()
        assert 'A-2' in manager.original_df['Codigo'].tolist()

    def test_sort_by_descending_is_reverse_of_ascending(self) -> None:
        manager = PaginationManager(mixed_df(), page_size=10)
        manager.sort_by('Codigo', ascending=True)
        ascending = [value for value in manager.original_df['Codigo'].tolist() if value is not None]

        manager.sort_by('Codigo', ascending=False)
        descending = [value for value in manager.original_df['Codigo'].tolist() if value is not None]

        assert descending == list(reversed(ascending))

    def test_data_view_sorts_through_the_model(self) -> None:
        data_view = DataView()
        data_view.set_data(mixed_df())

        assert data_view.pandas_model is not None
        data_view.pandas_model.sort(0, Qt.DescendingOrder)

        manager = data_view.pagination_manager
        assert manager is not None
        assert len(manager.original_df) == 6
        assert manager.get_page_data().shape[0] == 6


class TestFilteringWithMixedColumn:
    def test_text_filter_casts_before_comparing(self) -> None:
        service = FilterService()

        filtered = service.apply_text_filter(mixed_df(), 'Codigo', 'A')

        assert filtered['Codigo'].tolist() == ['A-2']

    def test_null_values_do_not_match_text_searches(self) -> None:
        """Regresión: NaN -> 'nan' hacía que un nulo coincidiera con 'a'."""
        service = FilterService()

        filtered = service.apply_text_filter(mixed_df(), 'Codigo', 'a')

        assert filtered['Codigo'].tolist() == ['A-2']

    def test_null_values_do_not_match_regex(self) -> None:
        service = FilterService()

        filtered = service.apply_regex_filter(mixed_df(), 'Codigo', 'nan')

        assert filtered.empty

    def test_numeric_filter_on_mixed_column_does_not_crash(self) -> None:
        service = FilterService()

        filtered = service.apply_numeric_filter(mixed_df(), 'Codigo', '>=', 30)

        # Solo los valores numéricos comparables: 30 y 50 ('A-2' y 'B-1' se descartan)
        assert filtered['Codigo'].tolist() == [30, 50]


class TestJoinSortingWithMixedColumn:
    def test_safe_sort_ascending(self) -> None:
        df = pd.DataFrame({'clave': [10, 'B-1', 30, None, 'A-2']})

        ordered = safe_sort_values(df, 'clave')

        assert ordered['clave'].tolist()[-1] is None or pd.isna(ordered['clave'].tolist()[-1])
        assert len(ordered) == 5

    def test_safe_sort_keeps_original_types(self) -> None:
        df = pd.DataFrame({'clave': [10, 'B-1', 30]})

        ordered = safe_sort_values(df, 'clave')

        assert set(ordered['clave']) == {10, 'B-1', 30}

    def test_safe_sort_numeric_column(self) -> None:
        df = pd.DataFrame({'clave': [3, 1, 2]})

        ordered = safe_sort_values(df, 'clave', ascending=False)

        assert ordered['clave'].tolist() == [3, 2, 1]
