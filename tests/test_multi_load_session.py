#!/usr/bin/env python3
"""
Sesión de carga múltiple: contadores, errores y consolidación.
"""

import pandas as pd
import pytest

from app.services.multi_load_session import MultiLoadSession


def frame(rows: int) -> pd.DataFrame:
    return pd.DataFrame({'valor': list(range(rows))})


class TestMultiLoadSession:
    def test_starts_empty(self) -> None:
        session = MultiLoadSession(['a.csv', 'b.csv'])

        assert session.total == 2
        assert session.completed == 0
        assert session.errors == 0
        assert session.successful == 0
        assert session.consolidate() is None
        assert session.is_complete() is False

    def test_register_success_counts_and_keeps_frames(self) -> None:
        session = MultiLoadSession(['a.csv', 'b.csv'])

        session.register_success(frame(2))
        session.register_success(frame(3))

        assert session.completed == 2
        assert session.successful == 2
        assert session.errors == 0
        assert session.is_complete() is True

    def test_register_error_counts(self) -> None:
        session = MultiLoadSession(['a.csv', 'b.csv'])

        session.register_success(frame(2))
        session.register_error()

        assert session.completed == 2
        assert session.successful == 1
        assert session.errors == 1
        assert session.is_complete() is True

    def test_consolidate_concatenates_and_resets_index(self) -> None:
        session = MultiLoadSession(['a.csv', 'b.csv'])
        session.register_success(frame(2))
        session.register_success(frame(3))

        consolidated = session.consolidate()

        assert consolidated is not None
        assert len(consolidated) == 5
        assert consolidated.index.tolist() == list(range(5))

    def test_all_errors_consolidates_to_none(self) -> None:
        session = MultiLoadSession(['a.csv'])

        session.register_error()

        assert session.is_complete() is True
        assert session.consolidate() is None

    def test_is_complete_tolerates_more_registrations_than_paths(self) -> None:
        session = MultiLoadSession(['a.csv'])

        session.register_success(frame(1))
        session.register_success(frame(1))

        assert session.completed == 2
        assert session.is_complete() is True


class TestExportFormatRegistry:
    def test_labels_are_unique(self) -> None:
        from app.widgets.export_dialog import ExportFormat

        labels = [export_format.label for export_format in ExportFormat]
        assert len(labels) == len(set(labels))

    def test_from_label_round_trip(self) -> None:
        from app.widgets.export_dialog import ExportFormat

        for export_format in ExportFormat:
            assert ExportFormat.from_label(export_format.label) is export_format

    def test_only_sqlite_needs_table_name(self) -> None:
        from app.widgets.export_dialog import ExportFormat

        needs_table = [
            export_format
            for export_format in ExportFormat
            if export_format.needs_table_name
        ]
        assert needs_table == [ExportFormat.SQLITE]

    def test_unknown_label_raises(self) -> None:
        from app.widgets.export_dialog import ExportFormat

        with pytest.raises(ValueError):
            ExportFormat.from_label('YAML (.yml)')
