#!/usr/bin/env python3
"""
SimpleExcelFormatPreserver: insertar datos sin perder el formato de la plantilla.
"""

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill

from core.simple_excel_preserver import SimpleExcelFormatPreserver


def build_template(path: Path) -> None:
    """Plantilla con título, cabecera, bordes, anchos y formato numérico."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Test'

    sheet['A1'] = 'TITULO CON FORMATO'
    sheet['A1'].font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    sheet['A1'].fill = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
    sheet['A1'].alignment = Alignment(horizontal='center')

    sheet['A3'] = 'Header 1'
    sheet['A3'].font = Font(bold=True, color='0000FF')
    sheet['A3'].border = Border(left=openpyxl.styles.Side(border_style='thin', color='000000'))

    sheet['B3'] = 'Header 2'
    sheet['B3'].number_format = '#,##0.00'

    sheet.column_dimensions['A'].width = 25.0
    sheet.column_dimensions['B'].width = 15.0

    sheet['A5'] = 'Dato 1'
    sheet['B5'] = 1000

    workbook.save(path)
    workbook.close()


def test_insert_data_preserves_template_format(tmp_path: Path) -> None:
    template_path = tmp_path / 'plantilla.xlsx'
    output_path = tmp_path / 'salida.xlsx'
    build_template(template_path)

    preserver = SimpleExcelFormatPreserver()
    workbook = openpyxl.load_workbook(template_path, data_only=False)
    sheet = workbook.active

    data = {
        0: {'Región': 'Norte', 'Ventas': 1234},
        1: {'Región': 'Sur', 'Ventas': 5678},
    }
    preserver.insert_data_simple_preservation(
        sheet, data, {'Región': 'A', 'Ventas': 'B'}, 'A5'
    )
    workbook.save(output_path)
    workbook.close()

    result = openpyxl.load_workbook(output_path, data_only=False)
    result_sheet = result.active

    title = result_sheet['A1']
    assert title.value == 'TITULO CON FORMATO'
    assert title.font.name == 'Arial'
    assert title.font.size == 14
    assert title.font.bold
    # openpyxl normaliza el alfa del relleno ('FF0000' -> '00FF0000'): comparar el RGB
    assert title.fill.start_color.rgb[-6:] == 'FF0000'

    header = result_sheet['A3']
    assert header.value == 'Header 1'
    assert header.font.bold
    assert header.font.color.rgb[-6:] == '0000FF'

    assert result_sheet.column_dimensions['A'].width == 25.0
    assert result_sheet.column_dimensions['B'].width == 15.0

    assert result_sheet['A5'].value == 'Norte'
    assert result_sheet['B5'].value == 1234
    assert result_sheet['A6'].value == 'Sur'
    assert result_sheet['B6'].value == 5678

    result.close()


def test_helper_builds_file_with_preserved_format(tmp_path: Path) -> None:
    """El helper de una sola llamada debe producir el mismo resultado."""
    from core.simple_excel_preserver import create_excel_with_simple_format_preservation

    template_path = tmp_path / 'plantilla.xlsx'
    output_path = tmp_path / 'salida_helper.xlsx'
    build_template(template_path)

    success = create_excel_with_simple_format_preservation(
        template_path=str(template_path),
        output_path=str(output_path),
        data={'0': {'Región': 'Centro', 'Ventas': 99}},
        column_mapping={'Región': 'A', 'Ventas': 'B'},
        start_cell='A5',
    )

    assert success is True
    assert output_path.exists()

    workbook = openpyxl.load_workbook(output_path, data_only=False)
    sheet = workbook.active
    assert sheet['A1'].value == 'TITULO CON FORMATO'
    assert sheet['A5'].value == 'Centro'
    assert sheet['B5'].value == 99
    workbook.close()
