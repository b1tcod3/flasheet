"""
SQLite File Loader
Handles SQLite database files
"""

import pandas as pd
from pathlib import Path
from typing import Any
from .base_loader import FileLoader
from .exceptions import LoaderError
from .load_options import LoadOptions

class SqliteLoader(FileLoader):
    """
    File loader for SQLite database format
    """

    def get_supported_extensions(self) -> list[str]:
        return ['.db', '.sqlite', '.sqlite3']

    def load(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load SQLite database into DataFrame
        
        Args:
            skip_rows: Number of rows to skip at the beginning
            column_names: Dictionary for renaming columns
            table_name: Name of the table to load (if None, load first table)
            
        Returns:
            DataFrame with loaded data
        """
        opts = options or LoadOptions()
        skip_rows = opts.skip_rows
        column_names = opts.column_names
        table_name = opts.table_name
        try:
            # If no table name provided, get the first table
            if table_name is None:
                table_name = self._get_first_table()
            
            if table_name is None:
                raise ValueError("No tables found in the database")
            
            # Load from SQLite using SQLAlchemy
            import sqlalchemy as sa
            engine = sa.create_engine(f'sqlite:///{self.filepath}')
            
            db_table = sa.Table(table_name, sa.MetaData(), autoload_with=engine)
            stmt = sa.select(db_table)
            if skip_rows > 0:
                stmt = stmt.offset(skip_rows)
            
            df = pd.read_sql(stmt, engine)
            
            # Apply column renaming if specified
            if column_names:
                df = df.rename(columns=column_names)
            
            return df
            
        except Exception as e:
            raise LoaderError(f"Error loading SQLite file {self.filepath}: {str(e)}") from e

    def _get_first_table(self) -> str | None:
        """
        Get the name of the first table in the database
        
        Returns:
            Name of the first table, or None if no tables found
        """
        try:
            import sqlalchemy as sa
            engine = sa.create_engine(f'sqlite:///{self.filepath}')
            
            # Get table names
            inspector = sa.inspect(engine)
            table_names = inspector.get_table_names()
            
            return table_names[0] if table_names else None
        except Exception:
            return None

    def get_file_info(self) -> dict[str, Any]:
        """
        Get information about the SQLite file
        """
        try:
            file_size = Path(self.filepath).stat().st_size
            
            # Get database metadata
            try:
                import sqlalchemy as sa
                engine = sa.create_engine(f'sqlite:///{self.filepath}')
                
                inspector = sa.inspect(engine)
                table_names = inspector.get_table_names()
                
                # Get info about first table
                table_info = {}
                if table_names:
                    first_table = table_names[0]
                    columns = inspector.get_columns(first_table)
                    table_info = {
                        'first_table': first_table,
                        'column_count': len(columns),
                        'columns': [col['name'] for col in columns]
                    }
                
                return {
                    'format': 'SQLite',
                    'tables': table_names,
                    'table_count': len(table_names),
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'sqlalchemy_version': sa.__version__,
                    **table_info
                }
            except ImportError:
                return {
                    'format': 'SQLite',
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'note': 'SQLAlchemy not available for detailed metadata'
                }
                
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def can_load_chunks() -> bool:
        """
        SQLite files support chunk loading
        """
        return True

    def load_in_chunks(self, options: LoadOptions | None = None) -> pd.DataFrame:
        """
        Load SQLite file in chunks
        """
        opts = options or LoadOptions()
        chunk_size = opts.chunk_size
        try:
            import sqlalchemy as sa
            engine = sa.create_engine(f'sqlite:///{self.filepath}')
            
            # Get first table
            table_name = self._get_first_table()
            if table_name is None:
                raise ValueError("No tables found in the database")
            
            chunk_list = []
            offset = 0
            
            db_table = sa.Table(table_name, sa.MetaData(), autoload_with=engine)
            
            while True:
                stmt = sa.select(db_table).limit(chunk_size).offset(offset)
                chunk_df = pd.read_sql(stmt, engine)
                
                if chunk_df.empty:
                    break
                
                chunk_list.append(chunk_df)
                offset += chunk_size
            
            return pd.concat(chunk_list, ignore_index=True)
            
        except Exception as e:
            raise LoaderError(f"Error loading SQLite file in chunks: {str(e)}") from e

    def get_table_names(self) -> list[str]:
        """
        Get list of table names in the database
        
        Returns:
            List of table names
        """
        try:
            import sqlalchemy as sa
            engine = sa.create_engine(f'sqlite:///{self.filepath}')
            inspector = sa.inspect(engine)
            return inspector.get_table_names()
        except Exception:
            return []

    def _estimate_rows(self) -> int:
        """
        Estimate number of rows in SQLite file
        """
        try:
            import sqlalchemy as sa
            engine = sa.create_engine(f'sqlite:///{self.filepath}')
            
            # Get first table
            table_name = self._get_first_table()
            if table_name is None:
                return 0
            
            # Count rows
            db_table = sa.Table(table_name, sa.MetaData(), autoload_with=engine)
            stmt = sa.select(sa.func.count().label('count')).select_from(db_table)  # pylint: disable=not-callable
            result = pd.read_sql(stmt, engine)
            return result['count'].iloc[0]
        except Exception:
            return super()._estimate_rows()