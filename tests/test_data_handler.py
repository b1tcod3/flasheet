"""
Pruebas unitarias para el módulo data_handler
"""

import unittest
import pandas as pd
import tempfile
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.data_handler import (
    cargar_datos, obtener_estadisticas, obtener_estadisticas_basicas
)


class TestDataHandler(unittest.TestCase):
    """Pruebas para las funciones del data_handler"""

    def setUp(self) -> None:
        """Configuración antes de cada prueba"""
        # Crear DataFrame de prueba
        self.test_df = pd.DataFrame({
            'Nombre': ['Juan', 'María', 'Pedro', 'Ana', 'Carlos'],
            'Edad': [25, 30, 35, 28, 42],
            'Ciudad': ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao'],
            'Salario': [25000.50, 30000.75, 35000.25, 28000.00, 45000.00]
        })

        # Crear directorio temporal para archivos de prueba
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Limpieza después de cada prueba"""
        # Limpiar archivos temporales
        for file in Path(self.temp_dir).iterdir():
            if file.is_file():
                file.unlink()
        Path(self.temp_dir).rmdir()

    def test_cargar_datos_csv(self) -> None:
        """Probar carga de datos desde CSV"""
        # Crear archivo CSV temporal
        csv_path = str(Path(self.temp_dir) / 'test.csv')
        self.test_df.to_csv(csv_path, index=False)

        # Cargar datos
        loaded_df = cargar_datos(csv_path)

        # Verificar que los datos se cargaron correctamente
        pd.testing.assert_frame_equal(loaded_df, self.test_df)

    def test_cargar_datos_excel(self) -> None:
        """Probar carga de datos desde Excel"""
        # Crear archivo Excel temporal
        excel_path = str(Path(self.temp_dir) / 'test.xlsx')
        self.test_df.to_excel(excel_path, index=False)

        # Cargar datos
        loaded_df = cargar_datos(excel_path)

        # Verificar que los datos se cargaron correctamente
        pd.testing.assert_frame_equal(loaded_df, self.test_df)

    def test_cargar_datos_archivo_inexistente(self) -> None:
        """Probar carga de datos con archivo inexistente"""
        with self.assertRaises(FileNotFoundError):
            cargar_datos('/ruta/inexistente/test.csv')

    def test_cargar_datos_formato_no_soportado(self) -> None:
        """Probar carga de datos con formato no soportado"""
        # Crear archivo temporal con extensión no soportada
        txt_path = str(Path(self.temp_dir) / 'test.txt')
        with open(txt_path, 'w') as f:
            f.write('contenido de texto')

        with self.assertRaises(ValueError):
            cargar_datos(txt_path)

    def test_obtener_estadisticas_basicas(self) -> None:
        """Probar obtención de estadísticas básicas"""
        stats = obtener_estadisticas_basicas(self.test_df)

        # Verificar estadísticas básicas
        self.assertEqual(stats['total_filas'], 5)
        self.assertEqual(stats['total_columnas'], 4)
        self.assertEqual(stats['columnas_numericas'], 2)  # Edad y Salario
        self.assertEqual(stats['columnas_texto'], 2)  # Nombre y Ciudad
        self.assertGreater(stats['memoria_uso_mb'], 0)
        self.assertEqual(stats['filas_duplicadas'], 0)

    def test_obtener_estadisticas_dataframe_vacio(self) -> None:
        """Probar obtención de estadísticas con DataFrame vacío"""
        empty_df = pd.DataFrame()
        stats = obtener_estadisticas_basicas(empty_df)

        # Verificar estadísticas para DataFrame vacío
        self.assertEqual(stats['total_filas'], 0)
        self.assertEqual(stats['total_columnas'], 0)
        self.assertEqual(stats['columnas_numericas'], 0)
        self.assertEqual(stats['columnas_texto'], 0)

    def test_carga_csv_grande_con_chunks(self) -> None:
        """Probar carga de CSV grande con chunks"""
        # Crear CSV grande (simulado)
        large_csv_path = str(Path(self.temp_dir) / 'large_test.csv')

        # Crear DataFrame más grande
        large_df = pd.DataFrame({
            'id': range(10000),
            'nombre': [f'Persona_{i}' for i in range(10000)],
            'valor': [i * 1.5 for i in range(10000)]
        })

        large_df.to_csv(large_csv_path, index=False)

        # Cargar con chunks
        loaded_df = cargar_datos(large_csv_path, chunk_size=1000)

        # Verificar que se cargaron todos los datos
        pd.testing.assert_frame_equal(loaded_df, large_df)

    def test_obtener_estadisticas_con_columnas_especificas(self) -> None:
        """Probar obtención de estadísticas con columnas específicas"""
        # Obtener estadísticas solo para columnas numéricas
        numeric_cols = ['Edad', 'Salario']
        stats = obtener_estadisticas(self.test_df, columnas=numeric_cols)

        # Verificar que solo se incluyeron las columnas especificadas
        self.assertEqual(len(stats.columns), 2)
        self.assertIn('Edad', stats.columns)
        self.assertIn('Salario', stats.columns)
        self.assertNotIn('Nombre', stats.columns)
        self.assertNotIn('Ciudad', stats.columns)


if __name__ == '__main__':
    unittest.main()