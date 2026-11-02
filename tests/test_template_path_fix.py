#!/usr/bin/env python3
"""
ExportSeparatedDialog: almacenamiento de la plantilla y validación de la
configuración (columnas, carpeta destino y nombre de archivo).

Antes estos tests devolvían True/False y se tragaban las aserciones, así que
"pasaban" aunque la validación estuviera rota.
"""

from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from app.widgets.export_separated import ExportSeparatedDialog


@pytest.fixture
def data() -> pd.DataFrame:
    return pd.DataFrame({
        'Region': ['Norte', 'Sur', 'Norte', 'Este'],
        'Ventas': [1000, 2000, 1500, 1800],
    })


@pytest.fixture
def template_path(tmp_path: Path) -> Path:
    path = tmp_path / 'plantilla.xlsx'
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet['A1'] = 'Región'
    sheet['B1'] = 'Ventas'
    workbook.save(path)
    workbook.close()
    return path


def make_dialog(
    data: pd.DataFrame,
    template: Path,
    output_folder: Path,
) -> ExportSeparatedDialog:
    dialog = ExportSeparatedDialog(data)
    dialog._template_path = str(template)
    dialog._template_ext = template.suffix.lower()
    dialog._dest_path = output_folder
    dialog.column_combo.setCurrentText('Region')
    dialog.filename_template_edit.setText('{valor}.xlsx')
    return dialog


def test_template_path_is_kept_in_configuration(
    data: pd.DataFrame, template_path: Path, tmp_path: Path
) -> None:
    dialog = make_dialog(data, template_path, tmp_path)

    config = dialog.get_configuration(validate=False)

    assert config is not None
    assert config.template_path == str(template_path)


def test_configuration_validates_with_stored_template(
    data: pd.DataFrame, template_path: Path, tmp_path: Path
) -> None:
    dialog = make_dialog(data, template_path, tmp_path)

    config = dialog.get_configuration(validate=True)

    assert config is not None
    assert config.separator_column == 'Region'
    assert config.output_folder == str(tmp_path)


def test_configuration_requires_separator_column(
    data: pd.DataFrame, template_path: Path, tmp_path: Path
) -> None:
    dialog = make_dialog(data, template_path, tmp_path)
    dialog.column_combo.setCurrentIndex(-1)  # QComboBox no editables: setCurrentText('') no limpia

    assert dialog.get_configuration(validate=False) is None


def test_configuration_requires_output_folder(
    data: pd.DataFrame, template_path: Path
) -> None:
    dialog = make_dialog(data, template_path, Path('/tmp'))
    dialog._dest_path = None

    assert dialog.get_configuration(validate=False) is None


@pytest.mark.parametrize(
    ('filename_template', 'expected'),
    [
        ('{valor}.xlsx', '{valor}.xlsx'),
        ('{valor}.xlsm', '{valor}.xlsm'),
        ('{valor}.XLSX', '{valor}.XLSX'),
        ('{valor}', '{valor}.xlsx'),
        ('{valor}.doc', '{valor}.doc.xlsx'),
    ],
)
def test_filename_extension_is_completed(
    data: pd.DataFrame,
    template_path: Path,
    tmp_path: Path,
    filename_template: str,
    expected: str,
) -> None:
    dialog = make_dialog(data, template_path, tmp_path)
    dialog.filename_template_edit.setText(filename_template)

    config = dialog.get_configuration(validate=False)

    assert config is not None
    assert config.file_template == expected
