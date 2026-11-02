"""
Tests para el diálogo de exportación separada - Actualizado para implementación compacta con QSplitter
"""

import unittest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QApplication, QDialog

from app.widgets.export_separated_dialog import ExportSeparatedDialog


class TestExportSeparatedDialog(unittest.TestCase):
    """Tests para ExportSeparatedDialog"""
    
    @classmethod
    def setUpClass(cls) -> None:
        """Configurar QApplication para tests de UI"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self) -> None:
        """Configurar datos de prueba"""
        # Crear DataFrame de prueba
        self.df_test = pd.DataFrame({
            'Region': ['Norte', 'Norte', 'Sur', 'Sur', 'Este'],
            'Producto': ['A', 'B', 'A', 'B', 'A'],
            'Ventas': [1000, 1500, 800, 1200, 900],
            'Fecha': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-01', '2024-01-02', '2024-01-01'])
        })
    
    def test_init_with_dataframe(self) -> None:
        """Test inicialización con DataFrame"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        self.assertEqual(len(dialog.df), 5)
        self.assertEqual(list(dialog.df.columns), ['Region', 'Producto', 'Ventas', 'Fecha'])
        self.assertFalse(dialog.isVisible())  # Modal, no visible inicialmente
    
    def test_init_without_dataframe(self) -> None:
        """Test inicialización sin DataFrame"""
        dialog = ExportSeparatedDialog(None)
        
        self.assertIsNone(dialog.df)
    
    def test_setup_ui_components(self) -> None:
        """Test configuración de componentes UI"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Verificar que todos los componentes están inicializados
        self.assertIsNotNone(dialog.column_combo)
        self.assertIsNotNone(dialog.select_template_btn)
        self.assertIsNotNone(dialog.dest_folder_label)
        self.assertIsNotNone(dialog.select_folder_btn)
        self.assertIsNotNone(dialog.filename_template_edit)
        self.assertIsNotNone(dialog.start_cell_combo)
        self.assertIsNotNone(dialog.cancel_btn)
        self.assertIsNotNone(dialog.export_btn)
    
    def test_populate_separator_combo(self) -> None:
        """Test población del combo de separación"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Verificar que se llenan las columnas
        combo_count = dialog.column_combo.count()
        self.assertGreater(combo_count, 0)
        
        # Verificar nombres de columnas
        columns = [dialog.column_combo.itemText(i) for i in range(combo_count)]
        expected_columns = ['Region', 'Producto', 'Ventas', 'Fecha']
        
        for col in expected_columns:
            self.assertIn(col, columns)
    
    def test_populate_start_cell_combo(self) -> None:
        """Test población del combo de celda inicial"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Verificar opciones predefinidas
        combo_count = dialog.start_cell_combo.count()
        self.assertGreater(combo_count, 0)
        
        # Verificar opciones específicas
        options = [dialog.start_cell_combo.itemText(i) for i in range(combo_count)]
        self.assertIn('A1', options)
        self.assertIn('A2', options)
        self.assertIn('B1', options)
    
    def test_on_column_changed(self) -> None:
        """Test cambio de columna (equivalente a separator_changed)"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Simular selección de 'Region'
        dialog.column_combo.setCurrentText('Region')
        dialog.on_column_changed('Region')
        
        # Verificar que se actualiza el preview de valores
        # La implementación actual actualiza valores_preview automáticamente
        self.assertGreater(dialog.values_preview.count(), 0)
    
    def test_select_template_functionality(self) -> None:
        """Test funcionalidad de selección de plantilla"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Mock de QFileDialog y openpyxl
        with patch('app.widgets.export_separated.dialog.QFileDialog.getOpenFileName') as mock_file, \
             patch('app.widgets.export_separated.dialog.openpyxl.load_workbook') as mock_wb:
            mock_file.return_value = ('/path/to/template.xlsx', '')
            mock_workbook = MagicMock()
            mock_workbook.sheetnames = ['Sheet1', 'Sheet2']
            mock_wb.return_value = mock_workbook

            dialog.select_template()

            # Verificar que se actualiza el label
            self.assertIn('template.xlsx', dialog.template_path_label.text())
            self.assertTrue(dialog.sheet_combo.isEnabled())
            self.assertEqual(dialog.sheet_combo.count(), 2)
    
    def test_select_destination_folder_functionality(self) -> None:
        """Test funcionalidad de selección de carpeta de destino"""
        dialog = ExportSeparatedDialog(self.df_test)

        with patch('app.widgets.export_separated.dialog.QFileDialog.getExistingDirectory') as mock_dir_dialog:
            mock_dir_dialog.return_value = '/path/to/output'

            dialog.select_destination_folder()

            # Verificar que se guarda el Path y se muestra solo el nombre
            self.assertIsNotNone(dialog._dest_path)
            self.assertEqual(dialog.dest_folder_label.text(), 'output')
            self.assertEqual(dialog.dest_folder_label.toolTip(), '/path/to/output')
    
    def test_validate_configuration_valid(self) -> None:
        """Test validación con configuración válida"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Configurar valores básicos válidos para que _build_config devuelva config
        dialog.column_combo.setCurrentText('Region')
        dialog.filename_template_edit.setText('Reporte_{valor}.xlsx')
        dialog._template_path = '/test/template.xlsx'
        dialog._dest_path = Path('/test/output')
        dialog.dest_folder_label.setText('output')

        # Mock ExcelTemplateSplitter para evitar dependencia
        with patch('app.widgets.export_separated.dialog.ExcelTemplateSplitter') as mock_splitter_class:
            mock_splitter = MagicMock()
            mock_validation_result = MagicMock()
            mock_validation_result.is_valid = True
            mock_validation_result.errors = []
            mock_validation_result.warnings = []
            mock_splitter.validate_configuration.return_value = mock_validation_result
            mock_splitter_class.return_value = mock_splitter

            # Ejecutar validación
            dialog.validate_configuration()

            # Verificar que se llama al validador
            mock_splitter.validate_configuration.assert_called()
    
    def test_validate_configuration_invalid(self) -> None:
        """Test validación con configuración inválida"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # No configurar nada (configuración inválida)
        
        # Mock ExcelTemplateSplitter para simular error
        with patch('app.widgets.export_separated.dialog.ExcelTemplateSplitter') as mock_splitter_class:
            mock_splitter = MagicMock()
            mock_validation_result = MagicMock()
            mock_validation_result.is_valid = False
            mock_validation_result.errors = ['Error de prueba']
            mock_validation_result.warnings = []
            mock_splitter.validate_configuration.return_value = mock_validation_result
            mock_splitter_class.return_value = mock_splitter
            
            # Ejecutar validación
            dialog.validate_configuration()
            
            # Verificar que el botón se deshabilita
            self.assertFalse(dialog.export_btn.isEnabled())
    
    def test_get_configuration_basic(self) -> None:
        """Test obtención de configuración básica"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Configurar valores
        dialog.column_combo.setCurrentText('Region')
        dialog.filename_template_edit.setText('Reporte_{valor}.xlsx')
        dialog.start_cell_combo.setCurrentText('A1')

        # Mock del atributo _template_path y _dest_path
        dialog._template_path = '/path/to/template.xlsx'
        dialog._dest_path = Path('/path/to/output')
        dialog.dest_folder_label.setText('output')
        dialog.dest_folder_label.setToolTip('/path/to/output')

        config = dialog.get_configuration(validate=False)

        self.assertIsNotNone(config)
        self.assertEqual(config.separator_column, 'Region')
        self.assertEqual(config.file_template, 'Reporte_{valor}.xlsx')
        self.assertEqual(config.start_cell, 'A1')
        self.assertEqual(config.template_path, '/path/to/template.xlsx')
        self.assertEqual(config.output_folder, '/path/to/output')
    
    def test_get_configuration_custom_start_cell(self) -> None:
        """Test obtención de configuración con celda inicial personalizada"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Configurar valores
        dialog.column_combo.setCurrentText('Region')
        dialog.start_cell_combo.setCurrentText('Personalizado')
        dialog.start_cell_combo.lineEdit().setText('C5')

        # Mock del atributo _template_path y _dest_path
        dialog._template_path = '/path/to/template.xlsx'
        dialog._dest_path = Path('/path/to/output')
        dialog.dest_folder_label.setText('output')
        dialog.filename_template_edit.setText('Reporte.xlsx')

        config = dialog.get_configuration(validate=False)

        self.assertIsNotNone(config)
        self.assertEqual(config.start_cell, 'C5')
    
    def test_cancel_functionality(self) -> None:
        """Test funcionalidad de cancelar"""
        dialog = ExportSeparatedDialog(self.df_test)

        dialog.reject()
        self.assertEqual(dialog.result(), QDialog.Rejected)
    
    def test_accept_functionality_valid_config(self) -> None:
        """Test funcionalidad de aceptar con configuración válida"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Configurar valores válidos
        dialog.column_combo.setCurrentText('Region')
        dialog.filename_template_edit.setText('Reporte_{valor}.xlsx')
        dialog._template_path = '/test/template.xlsx'
        dialog._dest_path = Path('/test/output')
        dialog.dest_folder_label.setText('output')

        # Mock para evitar export real y diálogos bloqueantes
        with patch.object(dialog, '_build_config') as mock_build_config:
            mock_build_config.return_value = MagicMock()

            with patch.object(QDialog, 'accept') as mock_accept:
                dialog._on_export()

                # _on_export construye config y acepta el diálogo
                mock_accept.assert_called_once()

    def test_accept_functionality_invalid_config(self) -> None:
        """Test funcionalidad de aceptar con configuración inválida"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # No configurar nada (configuración inválida)
        
        # Mock para simular configuración inválida
        with patch.object(dialog, '_build_config', return_value=None):
            
            # Mock QMessageBox.warning
            with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
                # Llamar directamente al método accept en lugar de simular click
                dialog.accept()
                
                # Verificar que se muestra advertencia
                mock_warning.assert_called_once()
                
                # Verificar que no se acepta el diálogo
                self.assertEqual(dialog.result(), 0)
    
    def test_update_values_preview(self) -> None:
        """Test actualización de preview de valores"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Seleccionar columna
        dialog.column_combo.setCurrentText('Region')
        dialog.update_values_preview()
        
        # Verificar que se llenan valores
        self.assertGreater(dialog.values_preview.count(), 0)
        
        # Verificar que hay valores de región
        items_text = [dialog.values_preview.item(i).text() for i in range(dialog.values_preview.count())]
        self.assertTrue(any('Norte' in item for item in items_text))
        self.assertTrue(any('Sur' in item for item in items_text))
    
    def test_update_filename_preview(self) -> None:
        """Test actualización de preview de nombres de archivos"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Configurar valores
        dialog.column_combo.setCurrentText('Region')
        dialog.filename_template_edit.setText('Reporte_{valor}.xlsx')
        
        # Actualizar preview
        dialog.update_filename_preview()
        
        # Verificar que se generan nombres
        self.assertGreater(dialog.filenames_preview.count(), 0)
    
    def test_file_preview_dialog(self) -> None:
        """Test diálogo de vista previa de archivos"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Configurar valores mínimos
        dialog.column_combo.setCurrentText('Region')
        dialog.filename_template_edit.setText('Reporte_{valor}.xlsx')
        
        # Mock validation_result
        mock_validation = MagicMock()
        mock_validation.errors = []
        dialog.validation_result = mock_validation
        
        # Mock del diálogo de preview
        with patch('app.widgets.export_separated.dialog.FilePreviewDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog
            
            # Ejecutar vista previa
            dialog.show_file_preview()
            
            # Verificar que se crea el diálogo
            mock_dialog_class.assert_called_once()
    
    def test_handle_no_data(self) -> None:
        """Test manejo cuando no hay datos"""
        dialog = ExportSeparatedDialog(None)
        
        # Con datos nulos, el diálogo debe manejar gracefully
        # Los componentes deberían estar disponibles pero no funcionales
        self.assertIsNone(dialog.df)
        # No deberíamos obtener errores al verificar componentes básicos
        self.assertIsNotNone(dialog.column_combo)
    
    def test_error_handling_in_validation(self) -> None:
        """Test manejo de errores en validación"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Mock ExcelTemplateSplitter para lanzar excepción
        with patch('app.widgets.export_separated.dialog.ExcelTemplateSplitter') as mock_splitter_class:
            mock_splitter_class.side_effect = Exception("Error de prueba")
            
            # La validación debe manejar el error sin crashear
            try:
                dialog.validate_configuration()
                # Si llegamos aquí, el manejo de error funcionó
                self.assertFalse(dialog.export_btn.isEnabled())
            except Exception:
                self.fail("El diálogo debe manejar errores de validación gracefully")
    
    def test_mapping_widget_functionality(self) -> None:
        """Test funcionalidad del widget de mapeo"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Verificar que el mapping widget se inicializa
        self.assertIsNotNone(dialog.mapping_widget)
        
        # Verificar que se configuran las columnas
        self.assertGreater(len(dialog.mapping_widget.df_columns), 0)
        
        # Verificar que se puede obtener el mapeo
        mapping = dialog.mapping_widget.get_mapping()
        self.assertIsInstance(mapping, dict)
    
    def test_specific_start_cell_custom(self) -> None:
        """Test selección de celda inicial personalizada"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Seleccionar celda específica
        dialog.column_combo.setCurrentText('Region')
        dialog.start_cell_combo.setCurrentText('Personalizado')
        dialog.start_cell_combo.lineEdit().setText('C5')
        dialog._template_path = '/test/template.xlsx'
        dialog._dest_path = Path('/test/output')
        dialog.dest_folder_label.setText('output')
        dialog.filename_template_edit.setText('test.xlsx')

        config = dialog.get_configuration(validate=False)
        self.assertEqual(config.start_cell, 'C5')


class TestExportSeparatedDialogIntegration(unittest.TestCase):
    """Tests de integración para ExportSeparatedDialog"""
    
    @classmethod
    def setUpClass(cls) -> None:
        """Configurar QApplication para tests de UI"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self) -> None:
        """Configurar datos de prueba"""
        self.df_test = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [4, 5, 6],
            'C': [7, 8, 9]
        })
    
    def test_full_workflow_simulation(self) -> None:
        """Test simulación de flujo completo"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Paso 1: Seleccionar columna
        dialog.column_combo.setCurrentText('A')
        dialog.on_column_changed('A')

        # Paso 2: Configurar plantilla (mock)
        dialog._template_path = '/test/template.xlsx'
        dialog.template_path_label.setText('template.xlsx')
        dialog.sheet_combo.setEnabled(True)
        dialog.sheet_combo.addItems(['Sheet1'])

        # Paso 3: Configurar salida (mock)
        dialog._dest_path = Path('/test/output')
        dialog.dest_folder_label.setText('output')

        # Paso 4: Configurar nombre de archivo
        dialog.filename_template_edit.setText('Report_{valor}.xlsx')

        # Paso 5: Actualizar previews
        dialog.update_values_preview()
        dialog.update_filename_preview()

        # Verificar que se configuró correctamente
        self.assertEqual(dialog.column_combo.currentText(), 'A')
        self.assertEqual(dialog.filename_template_edit.text(), 'Report_{valor}.xlsx')

        # Verificar que los previews se actualizaron
        self.assertGreater(dialog.values_preview.count(), 0)
        self.assertGreater(dialog.filenames_preview.count(), 0)
    
    def test_cancel_workflow_integration(self) -> None:
        """Test flujo de cancelación en integración"""
        dialog = ExportSeparatedDialog(self.df_test)
        
        # Simular click en cancelar
        dialog.reject()
        
        # Verificar que se rechaza el diálogo
        self.assertEqual(dialog.result(), QDialog.Rejected)
    
    def test_export_with_minimal_config_integration(self) -> None:
        """Test exportación con configuración mínima en integración"""
        dialog = ExportSeparatedDialog(self.df_test)

        # Configuración mínima
        dialog.column_combo.setCurrentText('A')
        dialog._template_path = '/minimal/template.xlsx'
        dialog._dest_path = Path('/minimal/output')
        dialog.dest_folder_label.setText('output')
        dialog.filename_template_edit.setText('Simple.xlsx')
        dialog.start_cell_combo.setCurrentText('A1')

        config = dialog.get_configuration(validate=False)

        # Verificar configuración mínima
        self.assertIsNotNone(config)
        self.assertEqual(config.separator_column, 'A')
        self.assertEqual(config.file_template, 'Simple.xlsx')
        self.assertEqual(config.start_cell, 'A1')  # Default
    



if __name__ == '__main__':
    unittest.main()