"""
File Loader Factory
Factory pattern for creating appropriate file loaders based on file extension
"""

from dataclasses import dataclass
from typing import Any, Type
from pathlib import Path

from .base_loader import FileLoader
from .csv_loader import CsvLoader
from .excel_loader import ExcelLoader
from .json_loader import JsonLoader
from .xml_loader import XmlLoader
from .parquet_loader import ParquetLoader
from .feather_loader import FeatherLoader
from .hdf5_loader import Hdf5Loader
from .pickle_loader import PickleLoader
from .sqlite_loader import SqliteLoader
from .yaml_loader import YamlLoader


@dataclass(frozen=True)
class FormatSpec:
    """Metadatos de un formato soportado y el loader que lo implementa."""

    extension: str
    description: str
    loader_class: Type[FileLoader]


DEFAULT_FORMATS: tuple[FormatSpec, ...] = (
    FormatSpec('.csv', 'Archivos CSV', CsvLoader),
    FormatSpec('.tsv', 'Archivos TSV', CsvLoader),
    FormatSpec('.xlsx', 'Archivos de Excel', ExcelLoader),
    FormatSpec('.xls', 'Archivos de Excel Legacy', ExcelLoader),
    FormatSpec('.json', 'Archivos JSON', JsonLoader),
    FormatSpec('.xml', 'Archivos XML', XmlLoader),
    FormatSpec('.parquet', 'Archivos Parquet', ParquetLoader),
    FormatSpec('.feather', 'Archivos Feather', FeatherLoader),
    FormatSpec('.hdf5', 'Archivos HDF5', Hdf5Loader),
    FormatSpec('.h5', 'Archivos HDF5', Hdf5Loader),
    FormatSpec('.pkl', 'Archivos Pickle', PickleLoader),
    FormatSpec('.pickle', 'Archivos Pickle', PickleLoader),
    FormatSpec('.db', 'Bases de Datos SQLite', SqliteLoader),
    FormatSpec('.sqlite', 'Bases de Datos SQLite', SqliteLoader),
    FormatSpec('.sqlite3', 'Bases de Datos SQLite', SqliteLoader),
    FormatSpec('.yaml', 'Archivos YAML', YamlLoader),
    FormatSpec('.yml', 'Archivos YAML', YamlLoader),
)


class FileLoaderFactory:
    """
    Factory class for creating file loaders

    Única fuente de verdad de los formatos soportados: extensión,
    descripción para la UI y clase que lo carga.
    """

    def __init__(self) -> None:
        self._specs: dict[str, FormatSpec] = {spec.extension: spec for spec in DEFAULT_FORMATS}

    def get_loader(self, filepath: str) -> FileLoader:
        """
        Get the appropriate file loader for a given file path

        Args:
            filepath: Path to the file

        Returns:
            FileLoader instance for the file type

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file format is not supported
        """
        if not Path(filepath).exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        extension = Path(filepath).suffix.lower()
        spec = self._specs.get(extension)
        if spec is None:
            raise ValueError(
                f"Unsupported file format: '{extension}'. "
                f"Supported formats: {self.get_supported_extensions()}"
            )

        return spec.loader_class(filepath)

    def is_supported(self, filepath: str) -> bool:
        """
        Check if a file format is supported

        Args:
            filepath: Path to the file

        Returns:
            True if the file format is supported
        """
        return Path(filepath).suffix.lower() in self._specs

    def get_supported_extensions(self) -> list[str]:
        """
        Get list of all supported file extensions

        Returns:
            List of supported file extensions
        """
        return list(self._specs)

    def get_format_descriptions(self) -> dict[str, str]:
        """Map of extension -> human readable description."""
        return {extension: spec.description for extension, spec in self._specs.items()}

    @staticmethod
    def get_format_description(extension: str) -> str:
        """
        Get description of a file format

        Args:
            extension: File extension (e.g., '.csv')

        Returns:
            Description of the format
        """
        spec = _global_factory._specs.get(extension.lower())
        if spec is None:
            return f"Unknown format: {extension}"
        return spec.description

    def get_loader_info(self, filepath: str) -> dict[str, Any]:
        """
        Get information about the loader for a given file

        Args:
            filepath: Path to the file

        Returns:
            Dictionary with loader information
        """
        if not self.is_supported(filepath):
            return {"error": "Unsupported file format"}

        extension = Path(filepath).suffix.lower()
        loader = self.get_loader(filepath)

        return {
            "extension": extension,
            "loader_class": type(loader).__name__,
            "supports_chunks": loader.can_load_chunks(),
            "file_info": loader.get_file_info(),
            "memory_info": loader.get_memory_usage_info()
        }

    def register_loader(
        self,
        extension: str,
        loader_class: Type[FileLoader],
        description: str | None = None,
    ) -> None:
        """
        Register a new loader for a file extension (for extensibility)

        Args:
            extension: File extension (e.g., '.custom')
            loader_class: Class that inherits from FileLoader
            description: Optional description shown in file dialogs
        """
        if not issubclass(loader_class, FileLoader):
            raise ValueError("Loader class must inherit from FileLoader")

        normalized = extension.lower()
        self._specs[normalized] = FormatSpec(
            extension=normalized,
            description=description or f"Archivos {normalized.lstrip('.').upper()}",
            loader_class=loader_class,
        )


# Global factory instance
_global_factory = FileLoaderFactory()


def get_file_loader(filepath: str) -> FileLoader:
    """
    Get file loader for a given file path (convenience function)

    Args:
        filepath: Path to the file

    Returns:
        FileLoader instance for the file type
    """
    return _global_factory.get_loader(filepath)


def is_file_supported(filepath: str) -> bool:
    """
    Check if a file format is supported (convenience function)

    Args:
        filepath: Path to the file

    Returns:
        True if the file format is supported
    """
    return _global_factory.is_supported(filepath)


def get_supported_formats() -> list[str]:
    """
    Get list of all supported file formats (convenience function)

    Returns:
        List of supported file extensions
    """
    return _global_factory.get_supported_extensions()


def get_format_descriptions() -> dict[str, str]:
    """Get extension -> description map (single source of truth for the UI)."""
    return _global_factory.get_format_descriptions()
