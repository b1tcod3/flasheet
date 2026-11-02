"""
YAML File Loader
Handles YAML format (requires pyyaml)
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class YamlLoader(FileLoader):
    """
    File loader for YAML format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.yaml', '.yml']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load YAML file into DataFrame
        
        Args:
            skip_rows: Number of rows to skip at the beginning (not applicable for YAML, kept for interface compatibility)
            column_names: Dictionary for renaming columns
            
        Returns:
            DataFrame with loaded data
        """
        opts = options or LoadOptions()
        skip_rows = opts.skip_rows
        column_names = opts.column_names
        try:
            # Check if pyyaml is available
            try:
                import yaml  # noqa
            except ImportError:
                raise ImportError(
                    "PyYAML is required to load YAML files. "
                    "Install it with: pip install pyyaml"
                )
            
            # Load YAML file
            import yaml
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Convert YAML data to DataFrame
            if isinstance(data, list):
                # If it's a list of dictionaries, create DataFrame directly
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # If it's a dictionary, try to extract a list or create single-row DataFrame
                if 'data' in data and isinstance(data['data'], list):
                    df = pd.DataFrame(data['data'])
                else:
                    # Create single-row DataFrame from dictionary
                    df = pd.DataFrame([data])
            else:
                raise ValueError("YAML file does not contain tabular data")
            
            # Apply skip_rows if specified
            if 0 < skip_rows < len(df):
                df = df.iloc[skip_rows:].reset_index(drop=True)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading YAML file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the YAML file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get basic YAML structure information
            try:
                import yaml
                # Try to parse to get structure info
                try:
                    with open(self.filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        data_type = type(data).__name__
                        is_list = isinstance(data, list)
                except Exception:
                    data_type = 'unknown'
                    is_list = False
                    
            except ImportError:
                return {
                    'format': 'YAML',
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'note': 'PyYAML not available for detailed metadata'
                }
            
            return {
                'format': 'YAML',
                'data_type': data_type,
                'is_list': is_list,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'pyyaml_version': yaml.__version__
            }
                
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        YAML files do not support chunk loading
        """
        return False

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in YAML file
        """
        try:
            import yaml
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                return len(data['data'])
            else:
                return 1  # Single row from dictionary
        except Exception:
            return super()._estimate_rows()