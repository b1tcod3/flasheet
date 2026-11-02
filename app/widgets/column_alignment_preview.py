"""
Column Alignment Preview Widget
Widget for previewing and manually aligning columns from multiple Excel files
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTableWidget, QTableWidgetItem,
                                QAbstractItemView, QMenu, QLineEdit,
                                QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, QPoint, QMimeData
from PySide6.QtGui import QDrag, QPixmap, QPainter, QColor
from typing import Any

class ColumnAlignmentPreview(QWidget):
    """
    Widget for previewing column alignment and manual realignment
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_metadata: list[dict[str, Any]] = []
        self.alignment_data: list[dict[str, Any]] = []
        self.column_mappings: dict[str, str] = {}
        self.dragged_item: QTableWidgetItem | None = None
        self.drag_start_pos: QPoint | None = None
        self.included_positions: set[int] = set()

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self) -> None:
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Header with buttons
        header_layout = QHBoxLayout()

        self.title_label = QLabel("Vista Previa de Alineación de Columnas")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #dddddd;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.align_position_btn = QPushButton("Alinear por Posición")
        self.align_position_btn.clicked.connect(self.align_by_position)

        self.align_name_btn = QPushButton("Alinear por Nombre")
        self.align_name_btn.clicked.connect(self.align_by_name)

        header_layout.addWidget(self.align_position_btn)
        header_layout.addWidget(self.align_name_btn)

        layout.addLayout(header_layout)

        # Alignment table
        self.alignment_table = QTableWidget()
        self.alignment_table.setAlternatingRowColors(True)
        self.alignment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.alignment_table.setDragEnabled(True)
        self.alignment_table.setAcceptDrops(True)
        self.alignment_table.setDropIndicatorShown(True)
        self.alignment_table.viewport().setAcceptDrops(True)

        # Enable context menu
        self.alignment_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.alignment_table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.alignment_table)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #717e95; font-size: 12px;")
        layout.addWidget(self.status_label)

    def connect_signals(self) -> None:
        """Connect widget signals"""
        self.alignment_table.itemDoubleClicked.connect(self.edit_column_name)
        self.alignment_table.itemChanged.connect(self.on_item_changed)

    def set_file_metadata(self, metadata: list[dict[str, Any]]) -> None:
        """
        Set the file metadata for alignment preview

        Args:
            metadata: List of file metadata dictionaries
        """
        self.file_metadata = metadata
        self.update_preview()

    def update_preview(self) -> None:
        """Update the alignment preview table"""
        if not self.file_metadata:
            self.alignment_table.setRowCount(0)
            self.alignment_table.setColumnCount(0)
            self.status_label.setText("No hay archivos para alinear")
            return

        # Find max number of columns
        max_cols = max((m.get('num_columns', 0) for m in self.file_metadata), default=0)

        if max_cols == 0:
            self.status_label.setText("Los archivos no tienen columnas")
            return

        # Set up table
        self.alignment_table.setRowCount(max_cols)
        self.alignment_table.setColumnCount(len(self.file_metadata) + 2)

        # Set headers
        headers = ['Posición', 'Incluir']
        headers.extend([m['filename'] for m in self.file_metadata])
        self.alignment_table.setHorizontalHeaderLabels(headers)

        # Reset included positions - include all by default
        self.included_positions = set(range(max_cols))

        # Set vertical headers (positions)
        for i in range(max_cols):
            self.alignment_table.setVerticalHeaderItem(i, QTableWidgetItem(f"{i + 1}"))

        # Fill table
        for pos in range(max_cols):
            # Position column
            pos_item = QTableWidgetItem(str(pos + 1))
            pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.alignment_table.setItem(pos, 0, pos_item)

            # Include checkbox
            include_checkbox = QCheckBox()
            include_checkbox.setChecked(pos in self.included_positions)
            include_checkbox.checkStateChanged.connect(lambda state, p=pos: self.on_include_changed(p, state))
            self.alignment_table.setCellWidget(pos, 1, include_checkbox)

            # Column names from each file
            for file_idx, meta in enumerate(self.file_metadata, 2):
                columns = meta.get('columns', [])
                col_name = columns[pos] if pos < len(columns) else ""
                item = QTableWidgetItem(col_name)
                item.setToolTip(f"Archivo: {meta['filename']}\nPosición: {pos + 1}")
                self.alignment_table.setItem(pos, file_idx, item)

        self.alignment_table.resizeColumnsToContents()
        self.alignment_table.resizeRowsToContents()

        self.status_label.setText(f"{len(self.file_metadata)} archivos, {max_cols} posiciones de columna")

    def align_by_position(self) -> None:
        """Auto-align columns by position"""
        self.update_preview()
        QMessageBox.information(self, "Alineación", "Columnas alineadas por posición")

    def align_by_name(self) -> None:
        """Auto-align columns by name (attempt to match similar names)"""
        if not self.file_metadata:
            return

        # Simple name-based alignment - find common column names
        all_columns: list[str] = []
        for meta in self.file_metadata:
            all_columns.extend(meta.get('columns', []))

        # Count occurrences of each column name
        from collections import Counter
        column_counts = Counter(all_columns)

        # For now, just show a message - full implementation would be more complex
        QMessageBox.information(self, "Alineación por Nombre",
                               "Alineación por nombre no implementada aún.\n"
                               f"Columnas comunes encontradas: {dict(column_counts.most_common(5))}")

    def edit_column_name(self, item: QTableWidgetItem) -> None:
        """
        Handle double-click to edit column name

        Args:
            item: The table item that was double-clicked
        """
        if item.column() <= 1:  # Position or include columns
            return

        # Create inline editor
        editor = QLineEdit(self.alignment_table)
        editor.setText(item.text())
        editor.setGeometry(self.alignment_table.visualItemRect(item))
        editor.setFocus()
        editor.show()

        def save_edit() -> None:
            new_name = editor.text().strip()
            if new_name:
                item.setText(new_name)
                # Update mappings
                file_idx = item.column() - 1
                if file_idx < len(self.file_metadata):
                    old_name = self.file_metadata[file_idx]['columns'][item.row()] if item.row() < len(self.file_metadata[file_idx]['columns']) else ""
                    if old_name:
                        self.column_mappings[old_name] = new_name
            editor.deleteLater()

        editor.returnPressed.connect(save_edit)
        editor.editingFinished.connect(save_edit)

    def on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle item changes"""
        # Could update mappings here

    def on_include_changed(self, position: int, state: Qt.CheckState) -> None:
        """Handle include checkbox state change"""
        if state == Qt.CheckState.Checked:
            self.included_positions.add(position)
        else:  # Unchecked
            self.included_positions.discard(position)

    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu for table"""
        menu = QMenu(self)

        rename_action = menu.addAction("Renombrar Columna")
        rename_action.triggered.connect(self.rename_selected_column)

        menu.exec(self.alignment_table.mapToGlobal(position))

    def rename_selected_column(self) -> None:
        """Rename the selected column"""
        current_item = self.alignment_table.currentItem()
        if current_item:
            self.edit_column_name(current_item)

    def get_column_mappings(self) -> dict[str, str]:
        """
        Get the current column mappings

        Returns:
            Dictionary of column name mappings
        """
        return self.column_mappings.copy()

    def get_alignment_data(self) -> list[dict[str, Any]]:
        """
        Get the current alignment data

        Returns:
            List of alignment information
        """
        alignment: list[dict[str, Any]] = []
        for row in range(self.alignment_table.rowCount()):
            row_data: dict[str, Any] = {'position': row + 1, 'columns': {}}

            for col in range(2, self.alignment_table.columnCount()):  # Skip position and include columns
                item = self.alignment_table.item(row, col)
                if item:
                    filename = self.alignment_table.horizontalHeaderItem(col).text()
                    row_data['columns'][filename] = item.text()

            alignment.append(row_data)

        return alignment

    def get_included_columns(self) -> list[str]:
        """
        Get the list of column names that are included in the consolidation

        Returns:
            List of column names to include
        """
        if not self.file_metadata:
            return []

        included_columns: list[str] = []
        first_file_columns = self.file_metadata[0].get('columns', [])

        for pos in sorted(self.included_positions):
            if pos < len(first_file_columns):
                col_name = first_file_columns[pos]
                if col_name:  # Skip empty column names
                    included_columns.append(col_name)

        return included_columns

    # Drag and drop methods (basic implementation)
    def mousePressEvent(self, event: object) -> None:
        """Handle mouse press for drag start"""
        if hasattr(event, 'button') and hasattr(event, 'pos'):
            from PySide6.QtGui import QMouseEvent
            assert isinstance(event, QMouseEvent)
            if event.button() == Qt.MouseButton.LeftButton:
                item = self.alignment_table.itemAt(event.position().toPoint())
                if item and item.column() > 1:  # Not position or include columns
                    self.dragged_item = item
                    self.drag_start_pos = event.position().toPoint()

    def mouseMoveEvent(self, event: object) -> None:
        """Handle mouse move for drag"""
        if self.dragged_item and self.drag_start_pos and hasattr(event, 'pos'):
            from PySide6.QtGui import QMouseEvent
            assert isinstance(event, QMouseEvent)
            if (event.position().toPoint() - self.drag_start_pos).manhattanLength() > 10:
                # Start drag
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.dragged_item.text())
                drag.setMimeData(mime_data)

                # Create pixmap for drag
                pixmap = QPixmap(self.dragged_item.sizeHint())
                pixmap.fill(QColor('lightblue'))
                painter = QPainter(pixmap)
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.dragged_item.text())
                painter.end()
                drag.setPixmap(pixmap)

                drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event: object) -> None:
        """Handle drop event"""
        if hasattr(event, 'mimeData') and hasattr(event, 'pos'):
            from PySide6.QtGui import QDropEvent
            assert isinstance(event, QDropEvent)
            if event.mimeData().hasText():
                target_item = self.alignment_table.itemAt(event.position().toPoint())
                if target_item and target_item != self.dragged_item and self.dragged_item is not None:
                    # Swap the text
                    temp_text = target_item.text()
                    target_item.setText(self.dragged_item.text())
                    self.dragged_item.setText(temp_text)

                    # Update metadata
                    self.update_metadata_from_table()

            self.dragged_item = None
            event.accept()

    def update_metadata_from_table(self) -> None:
        """Update file metadata based on current table state"""
        # This would update the internal metadata to reflect manual changes
        # For now, just a placeholder
