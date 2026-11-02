#!/usr/bin/env python3
"""
Integración de DataView: navegación, ordenamiento, tamaño de página y filtros.

Sustituye al script que devolvía un diccionario con banderas y nunca fallaba.
"""

import pandas as pd

from app.widgets.data_view import DataView

ROWS = 200


def build_df() -> pd.DataFrame:
    return pd.DataFrame({
        'ID': list(range(1, ROWS + 1)),
        'Nombre': [f'Usuario_{i:03d}' for i in range(1, ROWS + 1)],
        'Edad': [(i * 7) % 60 + 18 for i in range(ROWS)],
        'Departamento': ['Ventas', 'Marketing', 'IT', 'HR', 'Finance'] * 40,
        'Activo': [i % 2 == 0 for i in range(ROWS)],
    })


def test_navigation_moves_between_pages() -> None:
    data_view = DataView()
    data_view.set_data(build_df())
    manager = data_view.pagination_manager
    assert manager is not None

    assert manager.get_current_page() == 1
    manager.set_current_page(3)
    assert manager.get_current_page() == 3
    manager.set_current_page(5)
    assert manager.get_current_page() == 5

    manager.next_page()
    assert manager.get_current_page() == 6
    manager.previous_page()
    assert manager.get_current_page() == 5


def test_sorting_preserves_page_and_orders_data() -> None:
    from PySide6.QtCore import Qt

    data_view = DataView()
    data_view.set_data(build_df())
    manager = data_view.pagination_manager
    assert manager is not None
    manager.set_current_page(3)

    assert data_view.pandas_model is not None
    data_view.pandas_model.sort(2, Qt.DescendingOrder)  # columna 'Edad'

    assert manager.get_current_page() == 3
    page_ages = manager.get_page_data()['Edad'].tolist()
    assert page_ages == sorted(page_ages, reverse=True)

    full_ages = manager.original_df['Edad'].tolist()
    assert full_ages == sorted(full_ages, reverse=True)


def test_page_size_change_updates_total_pages() -> None:
    data_view = DataView()
    data_view.set_data(build_df())
    manager = data_view.pagination_manager
    assert manager is not None

    assert manager.get_page_size() == 10
    data_view._change_page_size(25)

    assert manager.get_page_size() == 25
    assert manager.get_total_pages() == len(build_df()) // 25


def test_filter_narrows_rows_and_resets_page() -> None:
    data_view = DataView()
    data_view.set_data(build_df())
    manager = data_view.pagination_manager
    assert manager is not None
    manager.set_current_page(4)

    data_view.search_column_combo.setCurrentText('Departamento')
    data_view.search_input.setText('IT')
    data_view.filter_btn.click()

    assert manager.get_current_page() == 1
    info = data_view.get_current_filter_info()
    assert info['is_filtered'] is True
    assert info['filtered_rows'] == ROWS // 5
    assert set(manager.filtered_df['Departamento']) == {'IT'}

    data_view.clear_filter()
    assert data_view.get_current_filter_info()['is_filtered'] is False


def test_sorting_after_filtering_keeps_filter() -> None:
    from PySide6.QtCore import Qt

    data_view = DataView()
    data_view.set_data(build_df())

    data_view.search_column_combo.setCurrentText('Departamento')
    data_view.search_input.setText('HR')
    data_view.filter_btn.click()

    assert data_view.pandas_model is not None
    data_view.pandas_model.sort(0, Qt.AscendingOrder)

    manager = data_view.pagination_manager
    assert manager is not None
    assert set(manager.filtered_df['Departamento']) == {'HR'}
    assert manager.filtered_df['ID'].tolist() == sorted(manager.filtered_df['ID'].tolist())
