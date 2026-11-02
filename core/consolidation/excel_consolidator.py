"""
Excel Consolidator
Handles consolidation of multiple Excel DataFrames
"""

import logging

import pandas as pd
from pathlib import Path

from core.models.folder_load_config import ColumnAlignmentStrategy
from typing import Any, Callable

logger = logging.getLogger(__name__)

class ExcelConsolidator:
    """
    Class for consolidating multiple Excel DataFrames
    """

    def __init__(self) -> None:
        self.dataframes: list[dict[str, Any]] = []
        self.column_mappings: dict[str, str] = {}
        self.included_columns: list[str] = []  # If empty, include all
        self.excluded_columns: list[str] = []

    def add_dataframe(self, df: pd.DataFrame, source_name: str = "") -> None:
        """
        Add a DataFrame to be consolidated

        Args:
            df: DataFrame to add
            source_name: Name of the source file
        """
        self.dataframes.append({
            'dataframe': df.copy(),
            'source': source_name,
            'columns': df.columns.tolist()
        })

    def set_column_mappings(self, mappings: dict[str, str]) -> None:
        """
        Set column renaming mappings

        Args:
            mappings: Dictionary {old_name: new_name}
        """
        self.column_mappings = mappings

    def set_column_selection(self, included_columns: list[str] | None = None, excluded_columns: list[str] | None = None) -> None:
        """
        Set column selection for consolidation

        Args:
            included_columns: List of column names to include (if empty, include all except excluded)
            excluded_columns: List of column names to exclude
        """
        if included_columns is not None:
            self.included_columns = included_columns
        if excluded_columns is not None:
            self.excluded_columns = excluded_columns

    def align_by_position(self) -> pd.DataFrame:
        """
        Align DataFrames by column position

        Returns:
            Consolidated DataFrame
        """
        if not self.dataframes:
            return pd.DataFrame()

        # Find the maximum number of columns
        max_columns = max(len(df['columns']) for df in self.dataframes)

        # Create aligned DataFrames
        aligned_dfs = [self._align_dataframe(df_info, max_columns) for df_info in self.dataframes]

        # Concatenate all DataFrames
        consolidated = pd.concat(aligned_dfs, ignore_index=True)

        # Apply column renaming
        if self.column_mappings:
            consolidated = consolidated.rename(columns=self.column_mappings)

        # Remove temporary extra columns
        extra_cols = [col for col in consolidated.columns if col.startswith('__extra_col_')]
        consolidated = consolidated.drop(columns=extra_cols)

        return self._apply_column_selection(consolidated)

    def _align_dataframe(self, df_info: dict[str, Any], max_columns: int) -> pd.DataFrame:
        df = df_info['dataframe']
        columns = df_info['columns']

        # Pad with NaN columns if necessary
        if len(columns) < max_columns:
            for i in range(len(columns), max_columns):
                df[f'__extra_col_{i}__'] = pd.NA
                columns.append(f'__extra_col_{i}__')

        # Reorder columns to match positions
        df_aligned = df[columns[:max_columns]]

        # Add source column if specified
        if df_info['source']:
            df_aligned = df_aligned.copy()
            df_aligned['__source__'] = df_info['source']

        return df_aligned

    def _apply_column_selection(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.included_columns and not self.excluded_columns:
            return df

        columns_to_keep = []
        for col in df.columns:
            if col == '__source__':  # Always keep source column if present
                columns_to_keep.append(col)
            elif self.excluded_columns and col in self.excluded_columns:
                continue
            elif self.included_columns and col not in self.included_columns:
                continue
            else:
                columns_to_keep.append(col)
        return df[columns_to_keep]

    def get_column_alignment_preview(self) -> list[dict[str, Any]]:
        """
        Get preview of column alignment

        Returns:
            List of dictionaries with alignment information
        """
        if not self.dataframes:
            return []

        max_columns = max(len(df['columns']) for df in self.dataframes)

        alignment: list[dict[str, Any]] = []
        for i in range(max_columns):
            column_info = {'position': i + 1, 'sources': {}}

            for df_info in self.dataframes:
                source = df_info['source'] or f"File {len(alignment) + 1}"
                columns = df_info['columns']

                if i < len(columns):
                    column_info['sources'][source] = columns[i]
                else:
                    column_info['sources'][source] = None

            alignment.append(column_info)

        return alignment

    def align_by_name(self) -> pd.DataFrame:
        """
        Align DataFrames by column name

        Returns:
            Consolidated DataFrame with the union of all columns
        """
        if not self.dataframes:
            return pd.DataFrame()

        aligned_dfs = []
        for df_info in self.dataframes:
            df_aligned = df_info['dataframe'].copy()
            if df_info['source']:
                df_aligned['__source__'] = df_info['source']
            aligned_dfs.append(df_aligned)

        consolidated = pd.concat(aligned_dfs, ignore_index=True, sort=False)

        if self.column_mappings:
            consolidated = consolidated.rename(columns=self.column_mappings)

        return self._apply_column_selection(consolidated)

    @staticmethod
    def _normalize_strategy(
        strategy: ColumnAlignmentStrategy | str,
    ) -> ColumnAlignmentStrategy:
        if isinstance(strategy, ColumnAlignmentStrategy):
            return strategy
        try:
            return ColumnAlignmentStrategy(strategy)
        except ValueError as exc:
            raise ValueError(f"Unsupported alignment strategy: {strategy}") from exc

    def consolidate(self, alignment: ColumnAlignmentStrategy | str = ColumnAlignmentStrategy.BY_POSITION) -> pd.DataFrame:
        """
        Consolidate all DataFrames

        Args:
            alignment: Strategy to align columns (position or name)

        Returns:
            Consolidated DataFrame
        """
        strategy = self._normalize_strategy(alignment)
        aligners: dict[ColumnAlignmentStrategy, Callable[[], pd.DataFrame]] = {
            ColumnAlignmentStrategy.BY_POSITION: self.align_by_position,
            ColumnAlignmentStrategy.BY_NAME: self.align_by_name,
        }
        return aligners[strategy]()

    def consolidate_chunked(self, file_paths: list[str],
                           alignment: ColumnAlignmentStrategy | str = ColumnAlignmentStrategy.BY_POSITION,
                           chunk_size: int = 10, progress_callback: Callable[[float], None] | None = None) -> pd.DataFrame:
        """
        Consolidate DataFrames in chunks for better memory management

        Args:
            file_paths: List of file paths to process
            alignment: Strategy to align columns (position or name)
            chunk_size: Number of files to process per chunk
            progress_callback: Optional callback function for progress updates

        Returns:
            Consolidated DataFrame
        """
        if not file_paths:
            return pd.DataFrame()

        consolidated_chunks = []

        for i in range(0, len(file_paths), chunk_size):
            chunk_files = file_paths[i:i + chunk_size]

            # Clear previous dataframes to free memory
            self.clear()
            self._load_chunk(chunk_files)

            # Consolidate chunk
            if self.dataframes:
                chunk_result = self.consolidate(alignment)
                consolidated_chunks.append(chunk_result)

            # Progress callback
            if progress_callback:
                progress = min((i + len(chunk_files)) / len(file_paths) * 100, 100)
                progress_callback(progress)

        # Final consolidation of all chunks
        if not consolidated_chunks:
            return pd.DataFrame()

        final_result = pd.concat(consolidated_chunks, ignore_index=True)

        # Apply column mappings if set
        if self.column_mappings:
            final_result = final_result.rename(columns=self.column_mappings)

        return self._apply_column_selection(final_result)

    def _load_chunk(self, chunk_files: list[str]) -> None:
        for file_path in chunk_files:
            try:
                df = pd.read_excel(file_path)
                self.add_dataframe(df, Path(file_path).name)
            except Exception as e:
                # Log error but continue with other files
                logger.warning("Error loading %s: %s", file_path, e)
                continue

    def clear(self) -> None:
        """Clear all DataFrames"""
        self.dataframes = []
        self.column_mappings = {}
        self.included_columns = []
        self.excluded_columns = []