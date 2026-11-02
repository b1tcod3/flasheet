"""
Base File Loader Class
Abstract base class for all file format loaders
"""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd
from pathlib import Path

from .load_options import LoadOptions

class FileLoader(ABC):
    """
    Abstract base class for file loaders
    All specific file loaders should inherit from this class
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self._validate_file()

    def _validate_file(self) -> None:
        """Validate that the file exists and has the correct format"""
        p = Path(self.filepath)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")

        extension = p.suffix.lower()
        if extension not in self.get_supported_extensions():
            raise ValueError(
                f"File format '{extension}' not supported by {self.__class__.__name__}. "
                f"Supported formats: {self.get_supported_extensions()}"
            )

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """
        Get list of supported file extensions

        Returns:
            List of file extensions (e.g., ['.csv', '.tsv'])
        """

    @abstractmethod
    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load the file into a pandas DataFrame

        Args:
            options: Load options (skip rows, column renaming, separator...).
                Each loader applies the ones it understands and ignores the rest.

        Returns:
            DataFrame with the loaded data
        """

    @abstractmethod
    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the file

        Returns:
            Dictionary with file information (size, format, etc.)
        """

    @staticmethod
    def can_load_chunks() -> bool:
        """
        Check if the loader supports loading in chunks for large files

        Returns:
            True if chunk loading is supported
        """
        return False

    def load_in_chunks(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load file in chunks for better memory management

        Args:
            options: Load options; `chunk_size` controls the chunk size.

        Returns:
            DataFrame with all chunks concatenated
        """
        raise NotImplementedError(
            f"Chunk loading not supported by {self.__class__.__name__}"
        )

    def get_memory_usage_info(self) -> dict[str, Any]:
        """
        Get memory usage information for the file

        Returns:
            Dictionary with memory usage details
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            return {
                'file_size_bytes': file_size,
                'file_size_mb': file_size / (1024 * 1024),
                'estimated_data_rows': self._estimate_rows(),
                'supports_chunked_loading': self.can_load_chunks()
            }
        except Exception as e:
            return {'error': str(e)}

    def _estimate_rows(self) -> int:
        """
        Estimate the number of rows in the file (for text-based formats)

        Returns:
            Estimated number of rows
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            line_length = 100  # Rough estimate
            return file_size // line_length
        except Exception:
            return 0
