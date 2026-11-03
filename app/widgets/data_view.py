"""
DataView - Widget principal para vista de datos con paginación y filtros integrados.
Diseño moderno con botones segmentados dinámicos y barra de búsqueda minimalista.
"""

import logging

import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView,
                               QLineEdit, QPushButton, QLabel, QFrame,
                               QMessageBox, QSpinBox, QSizePolicy, QButtonGroup,
                               QComboBox, QHeaderView, QStyle, QAbstractItemView)
from PySide6.QtCore import Signal

from app.services.filter_service import ColumnNotFoundError, FilterError
from app.services.pagination_manager import PaginationManager
from app.models.pandas_model import VirtualizedPandasModel
from app.widgets.widget_utils import dispose_widget
from typing import Any, Optional


logger = logging.getLogger(__name__)

_MAX_QUICK_FILTER_VALUES = 5


def _sorted_values(values: list[Any]) -> list[Any]:
    """Ordenar valores de una columna tolerando tipos mixtos (int + str).

    Un Excel real puede tener `[10, 'A-2', 50]` en la misma columna: comparar
    directamente lanza TypeError. En ese caso se ordena por texto.
    """
    try:
        return sorted(values)
    except TypeError:
        return sorted(values, key=str)


class DataView(QWidget):
    """
    Widget principal que integra filtros dinámicos, tabla y paginación en una sola vista.
    """

    filter_applied = Signal(str, str)
    filter_cleared = Signal()
    data_updated = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.pagination_manager: Optional[PaginationManager] = None
        self.pandas_model: Optional[VirtualizedPandasModel] = None
        self._applying_sort: bool = False
        self._quick_filter_groups: dict[str, QButtonGroup] = {}

        self.search_column_combo: QComboBox
        self.search_input: QLineEdit
        self.filter_btn: QPushButton
        self.clear_search_btn: QPushButton
        self.table_view: QTableView
        self.page_info_label: QLabel
        self.page_number_label: QLabel
        self.page_size_spin: QSpinBox
        self.first_page_btn: QPushButton
        self.prev_page_btn: QPushButton
        self.next_page_btn: QPushButton
        self.last_page_btn: QPushButton

        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 16, 20, 16)

        self._quick_filters_container = QWidget()
        self._quick_filters_layout = QVBoxLayout(self._quick_filters_container)
        self._quick_filters_layout.setContentsMargins(0, 0, 0, 0)
        self._quick_filters_layout.setSpacing(4)
        main_layout.addWidget(self._quick_filters_container)
        self._quick_filters_container.setVisible(False)

        self._create_search_section(main_layout)
        self._create_table_section(main_layout)
        self._create_pagination_section(main_layout)

    def _create_search_section(self, parent_layout: QVBoxLayout) -> None:
        search_frame = QFrame()
        search_frame.setObjectName("searchFrame")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(4, 4, 4, 4)
        search_layout.setSpacing(0)

        self.search_column_combo = QComboBox()
        self.search_column_combo.setObjectName("searchCombo")
        search_layout.addWidget(self.search_column_combo)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setObjectName("vDivider")
        search_layout.addWidget(sep1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar...")
        self.search_input.setMinimumWidth(220)
        self.search_input.setObjectName("searchInput")
        self.search_input.returnPressed.connect(self._apply_text_filter)
        search_layout.addWidget(self.search_input, 1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setObjectName("vDivider")
        search_layout.addWidget(sep2)

        self.filter_btn = QPushButton("Filtrar")
        self.filter_btn.setObjectName("primaryBtn")
        self.filter_btn.clicked.connect(self._apply_text_filter)
        search_layout.addWidget(self.filter_btn)

        self.clear_search_btn = QPushButton("Limpiar")
        self.clear_search_btn.setObjectName("secondaryBtn")
        self.clear_search_btn.clicked.connect(self.clear_filter)
        search_layout.addWidget(self.clear_search_btn)

        parent_layout.addWidget(search_frame)

    def _create_table_section(self, parent_layout: QVBoxLayout) -> None:
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSortingEnabled(True)
        self.table_view.setShowGrid(False)
        self.table_view.setWordWrap(False)
        self.table_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setHighlightSections(True)
        header.setMinimumSectionSize(80)

        vertical = self.table_view.verticalHeader()
        vertical.setDefaultSectionSize(28)
        vertical.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)


        parent_layout.addWidget(self.table_view, 1)

    def _create_pagination_section(self, parent_layout: QVBoxLayout) -> None:
        pagination_frame = QFrame()
        pagination_frame.setObjectName("paginationFrame")

        pagination_layout = QHBoxLayout(pagination_frame)
        pagination_layout.setContentsMargins(0, 0, 0, 0)

        self.page_info_label = QLabel("0 registros")
        self.page_info_label.setObjectName("mutedLabel")
        pagination_layout.addWidget(self.page_info_label)

        self.page_number_label = QLabel("Página 1 de 1")
        self.page_number_label.setObjectName("mutedLabel")
        pagination_layout.addWidget(self.page_number_label)

        pagination_layout.addStretch()

        pagination_layout.addWidget(QLabel("Filas por página:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(10, 1000)
        self.page_size_spin.setValue(10)
        self.page_size_spin.valueChanged.connect(self._change_page_size)
        pagination_layout.addWidget(self.page_size_spin)

        pagination_layout.addSpacing(12)

        self.first_page_btn = QPushButton()
        self.first_page_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_page_btn = QPushButton()
        self.prev_page_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        self.next_page_btn = QPushButton()
        self.next_page_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        self.last_page_btn = QPushButton()
        self.last_page_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))

        for btn in (self.first_page_btn, self.prev_page_btn,
                    self.next_page_btn, self.last_page_btn):
            btn.setObjectName("pageBtn")
            btn.setFixedSize(32, 28)
            pagination_layout.addWidget(btn)

        self.first_page_btn.clicked.connect(self.first_page)
        self.prev_page_btn.clicked.connect(self.previous_page)
        self.next_page_btn.clicked.connect(self.next_page)
        self.last_page_btn.clicked.connect(self.last_page)

        parent_layout.addWidget(pagination_frame)

    # ------------------------------------------------------------------
    # Dynamic quick filters
    # ------------------------------------------------------------------

    def _populate_quick_filters(self, df: pd.DataFrame) -> None:
        self._quick_filters_container.setUpdatesEnabled(False)
        try:
            self._rebuild_quick_filters(df)
        finally:
            self._quick_filters_container.setUpdatesEnabled(True)

    def _rebuild_quick_filters(self, df: pd.DataFrame) -> None:
        while self._quick_filters_layout.count():
            child = self._quick_filters_layout.takeAt(0)
            if child.widget():
                dispose_widget(child.widget())
            elif child.layout():
                self._clear_sub_layout(child.layout())

        self._quick_filter_groups.clear()

        candidates: list[str] = []
        for col in df.columns:
            nunique = df[col].nunique(dropna=True)
            if 1 < nunique <= _MAX_QUICK_FILTER_VALUES:
                candidates.append(col)

        if not candidates:
            self._quick_filters_container.setVisible(False)
            return

        self._quick_filters_container.setVisible(True)

        for col in candidates:
            row = self._create_quick_filter_row(col, df)
            self._quick_filters_layout.addWidget(row)

    def _create_quick_filter_row(self, col: str, df: pd.DataFrame) -> QWidget:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)

        label = QLabel(col)
        label.setObjectName("mutedLabel")
        layout.addWidget(label)

        btn_group = QButtonGroup(frame)
        btn_group.setExclusive(True)
        self._quick_filter_groups[col] = btn_group

        values = _sorted_values(df[col].dropna().unique().tolist())

        all_btn = QPushButton("Todos")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.setObjectName("segmentButton")
        btn_group.addButton(all_btn, 0)
        all_btn.clicked.connect(lambda: self._apply_quick_filter_clear(col))
        layout.addWidget(all_btn)

        for i, val in enumerate(values):
            btn = QPushButton(str(val))
            btn.setCheckable(True)
            btn.setObjectName("segmentButton")
            btn_group.addButton(btn, i + 1)
            btn.clicked.connect(lambda checked, c=col, v=str(val): self._apply_quick_filter(c, v))
            layout.addWidget(btn)

        layout.addStretch()
        return frame


    def _apply_quick_filter(self, column: str, value: str) -> None:
        if self.pagination_manager is None:
            return
        try:
            self.pagination_manager.apply_filter(column, value)
            self.filter_applied.emit(column, value)
        except FilterError as e:
            QMessageBox.critical(self, "Error", f"Error al filtrar: {e}")

    def _apply_quick_filter_clear(self, column: str) -> None:
        if self.pagination_manager is None:
            return
        self.pagination_manager.clear_filter()
        for col, group in self._quick_filter_groups.items():
            if col != column:
                continue
            for btn in group.buttons():
                if btn.text() == "Todos":
                    btn.setChecked(True)
                    break
        self.filter_cleared.emit()

    @staticmethod
    def _clear_sub_layout(layout) -> None:  # type: ignore[no-untyped-def]
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                DataView._clear_sub_layout(child.layout())

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def set_data(self, df: pd.DataFrame) -> None:
        if self.pagination_manager is None:
            self.pagination_manager = PaginationManager(df, self.page_size_spin.value())
            self._connect_pagination_signals()
        else:
            self.pagination_manager.set_data(df)

        if not df.empty:
            self.search_column_combo.clear()
            self.search_column_combo.addItems(df.columns.tolist())

        try:
            self._populate_quick_filters(df)
        except Exception:
            # Un fallo decorando los filtros no debe impedir cargar la tabla
            logger.exception("No se pudieron construir los filtros rápidos")

        self.update_view()

        # Ajustar anchos una sola vez por dataset (usa solo la página visible)
        if len(df.columns) <= 50:
            self.table_view.resizeColumnsToContents()

    @property
    def original_df(self) -> Optional[pd.DataFrame]:
        """Dataset base de la vista (propiedad del PaginationManager)."""
        if self.pagination_manager is None:
            return None
        return self.pagination_manager.original_df

    def _connect_pagination_signals(self) -> None:
        assert self.pagination_manager is not None
        self.pagination_manager.page_changed.connect(self._on_page_changed)
        self.pagination_manager.page_size_changed.connect(self._on_page_size_changed)
        self.pagination_manager.data_changed.connect(self._on_data_changed)
        self.pagination_manager.total_pages_changed.connect(self._on_total_pages_changed)

    def _connect_model_signals(self) -> None:
        if self.pandas_model is not None:
            self.pandas_model.sort_requested.connect(self._on_sort_requested)

    def _on_sort_requested(self, column_name: str, ascending: bool) -> None:
        """Delegar el ordenamiento en el dueño del estado (PaginationManager)."""
        if self.pagination_manager is None or self._applying_sort:
            return

        self._applying_sort = True
        try:
            self.pagination_manager.sort_by(column_name, ascending=ascending)
        except ColumnNotFoundError:
            return
        finally:
            self._applying_sort = False

    def update_view(self) -> None:
        if self.pagination_manager is None:
            return

        current_page_data = self.pagination_manager.get_page_data()

        if self.pandas_model is None:
            self.pandas_model = VirtualizedPandasModel(current_page_data)
            self.table_view.setModel(self.pandas_model)
            self._connect_model_signals()
        else:
            self.pandas_model.update_data(current_page_data)

        self._update_page_info()
        self._update_pagination_buttons()
        self.data_updated.emit(self.pagination_manager.filtered_df)

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def _apply_text_filter(self) -> None:
        if self.pagination_manager is None:
            return

        column = self.search_column_combo.currentText()
        term = self.search_input.text().strip()

        if not column or not term:
            return

        try:
            self.pagination_manager.apply_filter(column, term)
            self.filter_applied.emit(column, term)
        except FilterError as e:
            QMessageBox.critical(self, "Error", f"Error de búsqueda: {e}")

    def clear_filter(self) -> None:
        if self.pagination_manager:
            self.pagination_manager.clear_filter()
            self.search_input.clear()

            for group in self._quick_filter_groups.values():
                for btn in group.buttons():
                    if btn.text() == "Todos":
                        btn.setChecked(True)
                        break

            self.filter_cleared.emit()

    # ------------------------------------------------------------------
    # Pagination UI
    # ------------------------------------------------------------------

    def _update_page_info(self) -> None:
        if self.pagination_manager is None:
            self.page_info_label.setText("Sin datos")
            self.page_number_label.setText("Página 1 de 1")
            return

        info = self.pagination_manager.get_page_info()
        if info['total_rows'] == 0:
            self.page_info_label.setText("No hay registros")
            self.page_number_label.setText("Página 1 de 1")
        else:
            self.page_info_label.setText(
                f"Mostrando {info['start_row']}–{info['end_row']} de "
                f"{info['total_rows']} registros"
            )
            self.page_number_label.setText(
                f"Página {info['current_page']} de {info['total_pages']}"
            )

    def _update_pagination_buttons(self) -> None:
        if self.pagination_manager is None:
            for btn in (self.first_page_btn, self.prev_page_btn,
                        self.next_page_btn, self.last_page_btn):
                btn.setEnabled(False)
            return

        can_prev = self.pagination_manager.can_go_previous()
        can_next = self.pagination_manager.can_go_next()
        curr = self.pagination_manager.get_current_page()
        total = self.pagination_manager.get_total_pages()

        self.first_page_btn.setEnabled(can_prev and curr > 1)
        self.prev_page_btn.setEnabled(can_prev)
        self.next_page_btn.setEnabled(can_next)
        self.last_page_btn.setEnabled(can_next and curr < total)

    # ------------------------------------------------------------------
    # Pagination actions
    # ------------------------------------------------------------------

    def first_page(self) -> None:
        if self.pagination_manager:
            self.pagination_manager.first_page()

    def previous_page(self) -> None:
        if self.pagination_manager:
            self.pagination_manager.previous_page()

    def next_page(self) -> None:
        if self.pagination_manager:
            self.pagination_manager.next_page()

    def last_page(self) -> None:
        if self.pagination_manager:
            self.pagination_manager.last_page()

    def set_page_size(self, size: int) -> None:
        """Cambiar las filas por página (sincroniza el control y el gestor)."""
        if size != self.page_size_spin.value():
            self.page_size_spin.setValue(size)
        elif self.pagination_manager is not None:
            self.pagination_manager.set_page_size(size)

    def _change_page_size(self, size: int) -> None:
        if self.pagination_manager:
            self.pagination_manager.set_page_size(size)

    # ------------------------------------------------------------------
    # PaginationManager slots
    # ------------------------------------------------------------------

    def _on_page_changed(self, _page: int) -> None:
        self.update_view()

    def _on_page_size_changed(self, size: int) -> None:
        self.page_size_spin.setValue(size)
        self.update_view()

    def _on_data_changed(self) -> None:
        self.update_view()

    def _on_total_pages_changed(self, _total: int) -> None:
        self._update_pagination_buttons()
        self._update_page_info()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_current_filter_info(self) -> dict:
        if self.pagination_manager:
            return self.pagination_manager.get_filter_info()
        return {}

    def export_current_page(self) -> pd.DataFrame:
        if self.pagination_manager:
            return self.pagination_manager.get_page_data()
        return pd.DataFrame()

    def set_column_visibility_enabled(self, _enabled: bool) -> None:
        """API de visibilidad de columnas.

        Intencionalmente sin implementación: la visibilidad de columnas se
        gestiona a nivel de modelo/vista sin requerir acción en este widget.
        """
