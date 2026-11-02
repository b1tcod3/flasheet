"""
CSV/TSV File Loader
Handles Comma-Separated Values and Tab-Separated Values formats
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class CsvLoader(FileLoader):
    """
    File loader for CSV and TSV formats
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.csv', '.tsv']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load CSV/TSV file into DataFrame
        
        Args:
            skip_rows: Number of rows to skip at the beginning
            column_names: Dictionary for renaming columns
            separator: Custom separator character (overrides default detection)
            
        Returns:
            DataFrame with loaded data
        """
        opts = options or LoadOptions()
        skip_rows = opts.skip_rows
        column_names = opts.column_names
        separator = opts.separator
        try:
            # Determine separator: explicit > extension-based > default comma
            if separator is not None:
                sep = separator
            elif self.filepath.lower().endswith('.tsv'):
                sep = '\t'
            else:
                sep = ','
            
            # Load with skip_rows if specified
            if skip_rows > 0:
                df = pd.read_csv(self.filepath, sep=sep, header=skip_rows)
                df = df.reset_index(drop=True)
            else:
                df = pd.read_csv(self.filepath, sep=sep)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading CSV/TSV file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the CSV/TSV file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get first few lines to detect delimiter
            with open(self.filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                delimiter = '\t' if self.filepath.lower().endswith('.tsv') else ','
                delimiter = delimiter if delimiter in first_line else ','
            
            return {
                'format': 'CSV/TSV',
                'delimiter': delimiter,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 6)
            }
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        CSV/TSV files support chunk loading
        """
        return True

    def load_in_chunks(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load CSV/TSV file in chunks for better memory management
        """
        opts = options or LoadOptions()
        chunk_size = opts.chunk_size
        separator = opts.separator
        try:
            if separator is not None:
                sep = separator
            elif self.filepath.lower().endswith('.tsv'):
                sep = '\t'
            else:
                sep = ','
            
            chunk_list = []
            for chunk in pd.read_csv(self.filepath, sep=sep, chunksize=chunk_size):
                chunk_list.append(chunk)
            
            return pd.concat(chunk_list, ignore_index=True)
            
        except Exception as e:
            raise LoaderError(f"Error loading CSV/TSV file in chunks: {str(e)}") from e

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in CSV/TSV file
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                # Count lines efficiently
                line_count = sum(1 for _ in f)
                return line_count - 1  # Subtract header row
        except Exception:
            return super()._estimate_rows()