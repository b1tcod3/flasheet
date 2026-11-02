#!/usr/bin/env python3
"""
Flujo crítico: archivo en disco -> carga -> DataView -> tabla.

Antes era un script con QThread y QTimer que solo imprimía el estado. La carga
en hilo ya está cubierta en `test_file_loaders`/`test_task_thread`; aquí se
verifica el flujo completo de forma síncrona y con aserciones.
"""

from pathlib import Path

import pandas as pd

from app.widgets.data_view import DataView
from core.data_handler import cargar_datos_con_opciones

ROWS = 50


def build_expected_df() -> pd.DataFrame:
    return pd.DataFrame({
        'ID': list(range(1, ROWS + 1)),
        'Nombre': [f'Empleado_{i:03d}' for i in range(1, ROWS + 1)],
        'Edad': [25 + (i % 40) for i in range(ROWS)],
        'Departamento': ['Ventas', 'IT', 'RRHH', 'Marketing', 'Finanzas'] * 10,
        'Salario': [25000 + i * 500 for i in range(ROWS)],
        'Fecha_Ingreso': pd.date_range('2020-01-01', periods=ROWS, freq='D'),
        'Activo': [i % 3 == 0 for i in range(ROWS)],
    })


def write_csv(path: Path) -> None:
    build_expected_df().to_csv(path, index=False)


def test_load_file_and_populate_data_view(tmp_path: Path) -> None:
    filepath = tmp_path / 'empleados.csv'
    write_csv(filepath)

    df = cargar_datos_con_opciones(str(filepath))

    assert len(df) == ROWS
    assert list(df.columns) == list(build_expected_df().columns)

    data_view = DataView()
    data_view.set_data(df)

    manager = data_view.pagination_manager
    assert manager is not None
    assert manager.get_total_pages() > 1
    assert data_view.original_df is not None
    assert len(data_view.original_df) == ROWS

    page_data = manager.get_page_data()
    assert len(page_data) > 0
    assert data_view.table_view.model() is not None
    assert data_view.table_view.model().rowCount() == len(page_data)


def test_navigation_after_load_keeps_showing_rows(tmp_path: Path) -> None:
    filepath = tmp_path / 'empleados.csv'
    write_csv(filepath)

    data_view = DataView()
    data_view.set_data(cargar_datos_con_opciones(str(filepath)))
    manager = data_view.pagination_manager
    assert manager is not None

    first_page_ids = manager.get_page_data()['ID'].tolist()
    manager.next_page()
    second_page_ids = manager.get_page_data()['ID'].tolist()

    assert manager.get_current_page() == 2
    assert len(second_page_ids) > 0
    assert second_page_ids != first_page_ids
    assert data_view.pandas_model is not None
    assert data_view.pandas_model.rowCount() == len(second_page_ids)


def test_reload_replaces_data_without_leftovers(tmp_path: Path) -> None:
    first = tmp_path / 'uno.csv'
    second = tmp_path / 'dos.csv'
    write_csv(first)
    pd.DataFrame({'ID': [1, 2], 'Nombre': ['A', 'B']}).to_csv(second, index=False)

    data_view = DataView()
    data_view.set_data(cargar_datos_con_opciones(str(first)))
    data_view.set_data(cargar_datos_con_opciones(str(second)))

    manager = data_view.pagination_manager
    assert manager is not None
    assert manager.get_total_rows() == 2
    assert manager.get_total_pages() == 1
    assert manager.get_page_data()['ID'].tolist() == [1, 2]
