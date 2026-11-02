"""
XML File Loader
Handles eXtensible Markup Language format
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class XmlLoader(FileLoader):
    """
    File loader for XML format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.xml']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load XML file into DataFrame
        
        Args:
            skip_rows: Number of rows to skip at the beginning (not applicable for XML, kept for interface compatibility)
            column_names: Dictionary for renaming columns
            
        Returns:
            DataFrame with loaded data
        """
        opts = options or LoadOptions()
        skip_rows = opts.skip_rows
        column_names = opts.column_names
        try:
            # Try using pandas read_xml first (pandas 1.3.0+)
            try:
                df = pd.read_xml(self.filepath)
                
                # Apply skip_rows if specified
                if 0 < skip_rows < len(df):
                    df = df.iloc[skip_rows:].reset_index(drop=True)
                    
            except AttributeError:
                # Fallback to lxml for older pandas versions
                from lxml import etree
                tree = etree.parse(self.filepath)
                root = tree.getroot()
                
                data = []
                for child in root:
                    row = {}
                    for subchild in child:
                        row[subchild.tag] = subchild.text
                    data.append(row)
                
                df = pd.DataFrame(data)
                
                # Apply skip_rows if specified
                if 0 < skip_rows < len(df):
                    df = df.iloc[skip_rows:].reset_index(drop=True)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading XML file {self.filepath}: {str(e)}") from e

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the XML file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get basic XML structure information
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # Read first 1KB
                    root_tag = None
                    for line in content.split('\n'):
                        if line.strip().startswith('<') and not line.strip().startswith('<?'):
                            root_tag = line.strip().split()[0][1:]
                            break
                            
            except Exception:
                root_tag = 'unknown'
            
            # Count elements (rough estimate)
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    element_count = content.count('<') // 2  # Rough estimate
            except Exception:
                element_count = 0
            
            return {
                'format': 'XML',
                'root_tag': root_tag,
                'estimated_elements': element_count,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            }
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        XML files do not support chunk loading
        """
        return False

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in XML file
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Count root children (rough estimate)
                return content.count('<') // 2
        except Exception:
            return super()._estimate_rows()