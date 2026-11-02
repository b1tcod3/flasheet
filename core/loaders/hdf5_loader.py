"""
HDF5 File Loader
Handles Hierarchical Data Format version 5 (requires tables)
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class Hdf5Loader(FileLoader):
    """
    File loader for HDF5 format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.hdf5', '.h5']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load HDF5 file into DataFrame
        
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
            # Check if tables is available
            try:
                import tables  # noqa
            except ImportError:
                raise ImportError(
                    "PyTables is required to load HDF5 files. "
                    "Install it with: pip install tables"
                )
            
            # Load HDF5 file
            df = pd.read_hdf(self.filepath)
            
            # Apply skip_rows if specified
            if 0 < skip_rows < len(df):
                df = df.iloc[skip_rows:].reset_index(drop=True)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading HDF5 file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the HDF5 file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get HDF5 metadata
            try:
                import tables
                import h5py
                
                with h5py.File(self.filepath, 'r') as f:
                    # Get all keys (datasets)
                    keys = list(f.keys())
                    
                return {
                    'format': 'HDF5',
                    'datasets': keys,
                    'dataset_count': len(keys),
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'pytables_version': tables.__version__
                }
            except ImportError:
                return {
                    'format': 'HDF5',
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'note': 'PyTables/h5py not available for detailed metadata'
                }
                
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        HDF5 files support chunk loading
        """
        return True

    def load_in_chunks(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load HDF5 file in chunks
        """
        opts = options or LoadOptions()
        chunk_size = opts.chunk_size
        try:
            # Check if tables is available
            try:
                import tables  # noqa
            except ImportError:
                raise ImportError(
                    "PyTables is required to load HDF5 files. "
                    "Install it with: pip install tables"
                )
            
            # Load entire file (HDF5 chunking is complex)
            df = pd.read_hdf(self.filepath)
            
            # Split into chunks if requested
            if chunk_size < len(df):
                chunk_list = [df.iloc[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
                return pd.concat(chunk_list, ignore_index=True)
            else:
                return df
            
        except Exception as e:
            raise LoaderError(f"Error loading HDF5 file in chunks: {str(e)}") from e

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in HDF5 file
        """
        try:
            df = pd.read_hdf(self.filepath, stop=1000)
            return len(df)
        except Exception:
            return super()._estimate_rows()