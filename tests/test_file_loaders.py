"""
Test suite for file loaders
Tests the new modular file loader system
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from core.loaders import (
    get_file_loader, 
    is_file_supported, 
    get_supported_formats,
    LoadOptions,
)
from core.loaders.csv_loader import CsvLoader
from core.loaders.json_loader import JsonLoader


class TestFileLoaderFactory:
    """Test the FileLoaderFactory"""

    @staticmethod
    def test_get_supported_formats() -> None:
        """Test getting supported formats"""
        formats = get_supported_formats()
        assert isinstance(formats, list)
        assert '.csv' in formats
        assert '.json' in formats
        assert '.xml' in formats
        assert '.parquet' in formats

    @staticmethod
    def test_is_file_supported() -> None:
        """Test checking if file format is supported"""
        # Supported formats
        assert is_file_supported('test.csv') is True
        assert is_file_supported('test.json') is True
        assert is_file_supported('test.parquet') is True
        
        # Unsupported formats
        assert is_file_supported('test.txt') is False
        assert is_file_supported('test.doc') is False

    @staticmethod
    def test_get_loader() -> None:
        """Test getting appropriate loader for file"""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            loader = get_file_loader(tmp_path)
            assert isinstance(loader, CsvLoader)
        finally:
            Path(tmp_path).unlink()

    @staticmethod
    def test_unsupported_format() -> None:
        """Test error for unsupported format"""
        with tempfile.NamedTemporaryFile(suffix='.unsupported', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                get_file_loader(tmp_path)
        finally:
            Path(tmp_path).unlink()

    @staticmethod
    def test_nonexistent_file() -> None:
        """Test error for nonexistent file"""
        with pytest.raises(FileNotFoundError):
            get_file_loader('nonexistent_file.csv')


class TestCsvLoader:
    """Test CSV/TSV loader"""

    def setup_method(self) -> None:
        """Set up test data"""
        # Create test CSV file
        self.csv_content = "name,age,city\nAlice,25,NYC\nBob,30,LA\nCharlie,35,Chicago"
        self.csv_file = "test_data.csv"
        with open(self.csv_file, 'w') as f:
            f.write(self.csv_content)
        
        # Create test TSV file
        self.tsv_content = "name\tage\tcity\nAlice\t25\tNYC\nBob\t30\tLA\nCharlie\t35\tChicago"
        self.tsv_file = "test_data.tsv"
        with open(self.tsv_file, 'w') as f:
            f.write(self.tsv_content)

    def teardown_method(self) -> None:
        """Clean up test files"""
        for file in [self.csv_file, self.tsv_file]:
            if Path(file).exists():
                Path(file).unlink()

    def test_csv_loader_creation(self) -> None:
        """Test CSV loader creation"""
        loader = CsvLoader(self.csv_file)
        assert loader.get_supported_extensions() == ['.csv', '.tsv']

    def test_csv_load(self) -> None:
        """Test loading CSV file"""
        loader = CsvLoader(self.csv_file)
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ['name', 'age', 'city']

    def test_tsv_load(self) -> None:
        """Test loading TSV file"""
        loader = CsvLoader(self.tsv_file)
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ['name', 'age', 'city']

    def test_csv_skip_rows(self) -> None:
        """Test loading CSV with skip_rows"""
        loader = CsvLoader(self.csv_file)
        df = loader.load(LoadOptions(skip_rows=1))
        assert len(df) == 2
        assert not any('Alice' in str(row) for row in df.values)

    def test_csv_column_rename(self) -> None:
        """Test loading CSV with column renaming"""
        loader = CsvLoader(self.csv_file)
        df = loader.load(LoadOptions(column_names={'name': 'first_name', 'age': 'years'}))
        assert 'first_name' in df.columns
        assert 'years' in df.columns
        assert 'name' not in df.columns

    def test_csv_file_info(self) -> None:
        """Test getting CSV file info"""
        loader = CsvLoader(self.csv_file)
        info = loader.get_file_info()
        assert info['format'] == 'CSV/TSV'
        assert 'delimiter' in info
        assert info['file_size_mb'] > 0

    def test_csv_chunk_loading(self) -> None:
        """Test CSV chunk loading support"""
        loader = CsvLoader(self.csv_file)
        assert loader.can_load_chunks() is True
        
        df = loader.load_in_chunks(LoadOptions(chunk_size=1))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3


class TestJsonLoader:
    """Test JSON loader"""

    def setup_method(self) -> None:
        """Set up test data"""
        self.json_content = '[{"name": "Alice", "age": 25, "city": "NYC"}, {"name": "Bob", "age": 30, "city": "LA"}]'
        self.json_file = "test_data.json"
        with open(self.json_file, 'w') as f:
            f.write(self.json_content)

    def teardown_method(self) -> None:
        """Clean up test file"""
        if Path(self.json_file).exists():
            Path(self.json_file).unlink()

    def test_json_loader_creation(self) -> None:
        """Test JSON loader creation"""
        loader = JsonLoader(self.json_file)
        assert loader.get_supported_extensions() == ['.json']

    def test_json_load(self) -> None:
        """Test loading JSON file"""
        loader = JsonLoader(self.json_file)
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['name', 'age', 'city']

    def test_json_file_info(self) -> None:
        """Test getting JSON file info"""
        loader = JsonLoader(self.json_file)
        info = loader.get_file_info()
        assert info['format'] == 'JSON'
        assert info['file_size_mb'] > 0

    def test_json_no_chunk_loading(self) -> None:
        """Test JSON doesn't support chunk loading"""
        loader = JsonLoader(self.json_file)
        assert loader.can_load_chunks() is False


class TestDataHandlerIntegration:
    """Test integration with data_handler.py"""

    def setup_method(self) -> None:
        """Set up test data"""
        self.csv_file = "test_integration.csv"
        with open(self.csv_file, 'w') as f:
            f.write("name,age\nAlice,25\nBob,30")

    def teardown_method(self) -> None:
        """Clean up test file"""
        if Path(self.csv_file).exists():
            Path(self.csv_file).unlink()

    def test_cargar_datos_integration(self) -> None:
        """Test cargar_datos function integration"""
        from core.data_handler import cargar_datos
        df = cargar_datos(self.csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_cargar_datos_con_opciones_integration(self) -> None:
        """Test cargar_datos_con_opciones function integration"""
        from core.data_handler import cargar_datos_con_opciones
        df = cargar_datos_con_opciones(self.csv_file, skip_rows=0, column_names={'name': 'nombre'})
        assert isinstance(df, pd.DataFrame)
        assert 'nombre' in df.columns
        assert 'name' not in df.columns

    @staticmethod
    def test_supported_formats_function() -> None:
        """Test get_supported_file_formats function"""
        from core.data_handler import get_supported_file_formats
        formats = get_supported_file_formats()
        assert isinstance(formats, list)
        assert '.csv' in formats

    def test_is_format_supported_function(self) -> None:
        """Test is_file_supported function"""
        from core.loaders import is_file_supported
        assert is_file_supported(self.csv_file) is True
        assert is_file_supported('test.txt') is False


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])