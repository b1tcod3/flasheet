"""
Parquet File Loader
Handles Apache Parquet format (requires pyarrow)
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class ParquetLoader(FileLoader):
    """
    File loader for Parquet format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.parquet']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load Parquet file into DataFrame
        
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
                    "PyArrow is required to load Parquet files. "
                    "Install it with: pip install pyarrow"
                )
            
            # Load Parquet file
            df = pd.read_parquet(self.filepath)
            
            # Apply skip_rows if specified
            if 0 < skip_rows < len(df):
                df = df.iloc[skip_rows:].reset_index(drop=True)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading Parquet file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the Parquet file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get Parquet metadata
            try:
                import pyarrow.parquet as pq
                parquet_file = pq.ParquetFile(self.filepath)
                
                # Get schema information
                schema = parquet_file.schema_arrow
                
                return {
                    'format': 'Parquet',
                    'columns': [field.name for field in schema],
                    'column_count': len(schema),
                    'row_groups': parquet_file.num_row_groups,
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'pyarrow_version': pq.__version__
                }
            except ImportError:
                return {
                    'format': 'Parquet',
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'note': 'PyArrow not available for detailed metadata'
                }
                
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        Parquet files support chunk loading
        """
        return True

    def load_in_chunks(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load Parquet file in chunks
        """
        opts = options or LoadOptions()
        chunk_size = opts.chunk_size
        try:
            # Check if pyarrow is available
            try:
                import pyarrow.parquet as pq
            except ImportError:
                raise ImportError(
                    "PyArrow is required to load Parquet files. "
                    "Install it with: pip install pyarrow"
                )
            
            parquet_file = pq.ParquetFile(self.filepath)
            chunk_list = []
            
            for i in range(parquet_file.num_row_groups):
                # Read one row group as a chunk
                table = parquet_file.read_row_group(i)
                chunk_df = table.to_pandas()
                chunk_list.append(chunk_df)
            
            return pd.concat(chunk_list, ignore_index=True)
            
        except Exception as e:
            raise LoaderError(f"Error loading Parquet file in chunks: {str(e)}") from e

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in Parquet file
        """
        try:
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(self.filepath)
            
            total_rows = 0
            for i in range(parquet_file.num_row_groups):
                total_rows += parquet_file.metadata.row_group(i).num_rows
            
            return total_rows
        except Exception:
            return super()._estimate_rows()