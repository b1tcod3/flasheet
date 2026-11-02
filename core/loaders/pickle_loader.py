"""
Pickle File Loader
Handles Python Pickle format
"""

import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class RestrictedUnpickler(pickle.Unpickler):
    """
    Unpickler que solo permite deserializar clases conocidas y seguras.

    Deserializar pickle arbitrario puede ejecutar código. Este unpickler
    restringe la deserialización a las clases necesarias para reconstruir
    DataFrames de pandas y primitivas de Python, rechazando el resto.
    """

    _ALLOWED_GLOBALS: frozenset[tuple[str, str]] = frozenset({
        # Primitivas y contenedores de Python
        ('builtins', 'slice'),
        ('builtins', 'dict'),
        ('builtins', 'list'),
        ('builtins', 'tuple'),
        ('builtins', 'set'),
        ('builtins', 'frozenset'),
        ('builtins', 'int'),
        ('builtins', 'float'),
        ('builtins', 'bool'),
        ('builtins', 'str'),
        ('builtins', 'bytes'),
        ('builtins', 'bytearray'),
        ('builtins', 'complex'),
        ('builtins', 'object'),
        ('builtins', 'range'),
        ('builtins', 'map'),
        ('builtins', 'filter'),
        ('builtins', 'zip'),
        ('builtins', 'enumerate'),
        ('builtins', 'property'),
        ('builtins', 'classmethod'),
        ('builtins', 'staticmethod'),
        ('builtins', 'super'),
        ('builtins', 'type'),
        # numpy (compatibilidad numpy 1.x y 2.x)
        ('numpy', 'dtype'),
        ('numpy', 'ndarray'),
        ('numpy._core.multiarray', '_reconstruct'),
        ('numpy._core.numeric', '_frombuffer'),
        ('numpy.core.multiarray', '_reconstruct'),
        ('numpy.core.numeric', '_frombuffer'),
        # pandas
        ('pandas.core.frame', 'DataFrame'),
        ('pandas.core.internals.managers', 'BlockManager'),
        ('pandas._libs.internals', '_unpickle_block'),
        ('pandas._libs.arrays', '__pyx_unpickle_NDArrayBacked'),
        ('pandas.core.indexes.base', 'Index'),
        ('pandas.core.indexes.base', '_new_Index'),
        ('pandas.core.indexes.range', 'RangeIndex'),
        ('pandas.core.indexes.multi', 'MultiIndex'),
        ('pandas.core.arrays.datetimes', 'DatetimeArray'),
        ('pandas.core.arrays.timedeltas', 'TimedeltaArray'),
        ('pandas.core.arrays.categorical', 'Categorical'),
        ('pandas.core.arrays.integer', 'IntegerArray'),
        ('pandas.core.arrays.integer', 'Int64Dtype'),
        ('pandas.core.dtypes.dtypes', 'CategoricalDtype'),
        # Tipos estándar para columnas de objetos
        ('datetime', 'datetime'),
        ('datetime', 'date'),
        ('datetime', 'time'),
        ('datetime', 'timedelta'),
        ('decimal', 'Decimal'),
    })

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) not in self._ALLOWED_GLOBALS:
            raise pickle.UnpicklingError(
                f"Referencia no permitida al deserializar pickle: {module}.{name}"
            )
        return super().find_class(module, name)

class PickleLoader(FileLoader):
    """
    File loader for Pickle format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.pkl', '.pickle']

    def _safe_load_pickle(self) -> pd.DataFrame:
        """
        Load pickle file with restricted deserialization.

        Returns:
            DataFrame with loaded data

        Raises:
            ValueError: If the pickle does not contain a DataFrame
            pickle.UnpicklingError: If the pickle references disallowed classes
        """
        with open(self.filepath, 'rb') as f:
            obj = RestrictedUnpickler(f).load()

        if not isinstance(obj, pd.DataFrame):
            raise ValueError("Pickle file does not contain a DataFrame")

        return obj

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load Pickle file into DataFrame
        
        Args:
            skip_rows: Number of rows to skip at the beginning (not applicable for pickle, kept for interface compatibility)
            column_names: Dictionary for renaming columns
            
        Returns:
            DataFrame with loaded data
        """
        opts = options or LoadOptions()
        skip_rows = opts.skip_rows
        column_names = opts.column_names
        try:
            # Load Pickle file
            df = self._safe_load_pickle()
            
            # Apply skip_rows if specified
            if 0 < skip_rows < len(df):
                df = df.iloc[skip_rows:].reset_index(drop=True)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading Pickle file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the Pickle file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            extension = Path(self.filepath).suffix.lower()
            
            return {
                'format': 'Pickle',
                'extension': extension,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'note': 'Binary Python format - use with trusted sources only'
            }
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        Pickle files do not support chunk loading
        """
        return False

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in Pickle file
        """
        try:
            # Load a sample to count rows
            df_sample = self._safe_load_pickle()
            return len(df_sample)
        except Exception:
            return super()._estimate_rows()