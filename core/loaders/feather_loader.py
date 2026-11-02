"""
Feather File Loader
Handles Feather format (requires pyarrow)
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class FeatherLoader(FileLoader):
    """
    File loader for Feather format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.feather']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load Feather file into DataFrame
        
        Args:
            skip_rows: Number of rows to skip at the beginning
            column_names: Dictionary for renaming columns
            
        Returns:
            DataFrame with loaded data
        """
        opts = options or LoadOptions()
        skip_rows = opts.skip_rows
        column_names = opts.column_names
        try:
            # Check if pyarrow is available
            try:
                import pyarrow  # noqa
            except ImportError:
                raise ImportError(
                    "PyArrow is required to load Feather files. "
                    "Install it with: pip install pyarrow"
                )
            
            # Load Feather file
            df = pd.read_feather(self.filepath)
            
            # Apply skip_rows if specified
            if 0 < skip_rows < len(df):
                df = df.iloc[skip_rows:].reset_index(drop=True)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading Feather file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the Feather file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get Feather metadata
            try:
                import pyarrow.feather as pf
                feather_file = pf.read_table(self.filepath)
                
                return {
                    'format': 'Feather',
                    'columns': feather_file.column_names,
                    'column_count': len(feather_file.column_names),
                    'rows': len(feather_file),
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'pyarrow_version': pf.__version__
                }
            except ImportError:
                return {
                    'format': 'Feather',
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'note': 'PyArrow not available for detailed metadata'
                }
                
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        Feather files support chunk loading
        """
        return True

    def load_in_chunks(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load Feather file in chunks
        """
        opts = options or LoadOptions()
        chunk_size = opts.chunk_size
        try:
            # Check if pyarrow is available
            try:
                import pyarrow.feather as pf  # noqa
            except ImportError:
                raise ImportError(
                    "PyArrow is required to load Feather files. "
                    "Install it with: pip install pyarrow"
                )
            
            # Load entire file (Feather is fast, chunking not as beneficial)
            df = pd.read_feather(self.filepath)
            
            # Split into chunks if requested
            if chunk_size < len(df):
                chunk_list = [df.iloc[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
                return pd.concat(chunk_list, ignore_index=True)
            else:
                return df
            
        except Exception as e:
            raise LoaderError(f"Error loading Feather file in chunks: {str(e)}") from e

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in Feather file
        """
        try:
            import pyarrow.feather as pf
            feather_file = pf.read_table(self.filepath)
            return len(feather_file)
        except Exception:
            return super()._estimate_rows()