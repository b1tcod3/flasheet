"""
ProfilingView - Widget para mostrar el perfil de datos del dataset.

Muestra un resumen general del dataset y una tarjeta por cada columna
con tipo, nulos, cardinalidad, estadísticas numéricas y valores más
frecuentes. Diseño plano y minimalista, alto ratio tinta-datos.
"""

from typing import Any

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from app.resources import get_asset_path
from app.theme import current_theme
from app.theme.palette import ThemePalette, get_palette
from app.widgets.widget_utils import dispose_widget


def _palette() -> ThemePalette:
    """Paleta activa: se relee en cada repintado para seguir al tema."""
    return get_palette(current_theme())


_MAX_VALUE_LENGTH = 40


class _PercentBar(QWidget):
    """Barra horizontal plana con etiqueta de porcentaje."""

    def __init__(self, percent: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(16)
        self._percent = max(0.0, min(percent, 100.0))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._bar = QFrame()
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet(
            f"QFrame {{ background-color: {_palette().border}; border: none; "
            f"border-radius: 3px; }}"
        )
        layout.addWidget(self._bar, 1)

        self._label = QLabel(f"{percent:.1f}%")
        self._label.setFixedWidth(52)
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._label.setStyleSheet(f"color: {_palette().text}; font-size: 11px;")
        layout.addWidget(self._label)

        self._fill = QFrame(self._bar)
        self._fill.setFixedHeight(6)
        self._fill.setStyleSheet(
            f"QFrame {{ background-color: {_palette().accent}; border: none; "
            f"border-radius: 3px; }}"
        )
        self._fill.setGeometry(0, 0, 0, 6)

    def _update_fill(self) -> None:
        fill_width = max(0, int(self._bar.width() * self._percent / 100))
        self._fill.setGeometry(0, 0, fill_width, 6)

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self._update_fill()


class ProfilingView(QWidget):
    """Vista de perfil de datos del dataset cargado."""

    visualize_requested = Signal(str)  # (column) — pedir gráfico de la columna

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile: dict[str, Any] | None = None
        self._loading = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        self._header = QLabel("Perfil de Datos")
        self._header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        main_layout.addWidget(self._header)

        self._summary_label = QLabel("")
        main_layout.addWidget(self._summary_label)

        self._status_label = QLabel("Carga un archivo para ver su perfil de datos.")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self._status_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()
        self._scroll.setWidget(self._cards_widget)
        main_layout.addWidget(self._scroll, 1)

        self._scroll.setVisible(False)
        self._apply_styles()

    # ==================== TEMA ====================

    def _apply_styles(self) -> None:
        """Repintar el chrome de la vista con la paleta activa."""
        tokens = _palette()
        self.setStyleSheet(f"background-color: {tokens.app_bg};")
        self._header.setStyleSheet(f"color: {tokens.text};")
        self._summary_label.setStyleSheet(f"color: {tokens.text_muted}; font-size: 12px;")
        self._status_label.setStyleSheet(f"color: {tokens.text_muted}; font-size: 13px;")
        self._scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
            f"QScrollArea > QWidget > QWidget {{ background: {tokens.app_bg}; }}"
        )

    def refresh_theme(self) -> None:
        """Aplicar el tema nuevo y reconstruir las tarjetas si hay perfil."""
        self._apply_styles()
        if self._profile:
            self.set_profile(self._profile)

    # ==================== ESTADOS ====================

    def show_loading(self) -> None:
        """Mostrar estado de cálculo en curso."""
        self._loading = True
        self._clear_cards()
        self._summary_label.setText("")
        self._status_label.setText("Calculando perfil...")
        self._status_label.setVisible(True)
        self._scroll.setVisible(False)

    def set_progress(self, percent: int) -> None:
        """Actualizar el porcentaje mostrado mientras se calcula."""
        if self._loading:
            self._status_label.setText(f"Calculando perfil... {percent}%")

    def clear_profile(self) -> None:
        """Limpiar el perfil mostrado."""
        self._loading = False
        self._profile = None
        self._clear_cards()
        self._summary_label.setText("")
        self._status_label.setText("Carga un archivo para ver su perfil de datos.")
        self._status_label.setVisible(True)
        self._scroll.setVisible(False)

    # ==================== POBLADO ====================

    def set_profile(self, profile: dict[str, Any]) -> None:
        """Construir las tarjetas de columnas a partir del perfil."""
        self._loading = False
        self._profile = profile
        self._clear_cards()

        if profile is None:
            self.clear_profile()
            return

        total_rows = profile.get('total_rows', 0)
        if total_rows == 0:
            self.clear_profile()
            return

        columns = profile.get('columns', {})
        memory = profile.get('memory_usage_mb', 0.0)
        duplicated = profile.get('duplicated_rows', 0)
        quality = profile.get('data_quality_summary') or {}
        quality_score = quality.get('overall_quality_score')

        summary = (
            f"{total_rows:,} filas · {len(columns)} columnas · "
            f"{memory:.2f} MB · {duplicated:,} filas duplicadas"
        )
        if quality_score is not None:
            summary += f" · Calidad {quality_score:.1f}%"
        self._summary_label.setText(summary)
        self._status_label.setVisible(False)
        self._scroll.setVisible(True)

        for name, col_profile in columns.items():
            self._cards_layout.insertWidget(
                self._cards_layout.count() - 1, self._create_column_card(name, col_profile)
            )

    def _clear_cards(self) -> None:
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            dispose_widget(item.widget())

    @staticmethod
    def _create_separator() -> QFrame:
        """Línea divisoria sutil para organizar el contenido de la tarjeta."""
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {_palette().border}; border: none;")
        return line

    def _create_column_card(self, name: str, profile: dict[str, Any]) -> QFrame:
        if profile.get('error'):
            return self._create_error_card(name, profile.get('error_msg', 'Error desconocido'))

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {_palette().surface}; border: 1px solid {_palette().border}; "
            f"border-radius: 8px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {_palette().text}; border: none;")
        header.addWidget(name_label)
        header.addStretch()
        self._add_visualize_button(header, name)
        dtype_label = QLabel(profile.get('dtype', ''))
        dtype_label.setStyleSheet(
            f"color: {_palette().text_muted}; font-size: 11px; background: {_palette().app_bg}; "
            f"border: 1px solid {_palette().border}; border-radius: 4px; padding: 2px 8px;"
        )
        header.addWidget(dtype_label)
        layout.addLayout(header)

        rows = QGridLayout()
        rows.setHorizontalSpacing(16)
        rows.setVerticalSpacing(6)

        null_count = profile.get('null_count', 0)
        null_percent = profile.get('null_percent', 0.0)
        rows.addWidget(self._metric_label("Nulos"), 0, 0)
        rows.addWidget(_PercentBar(null_percent), 0, 1)
        rows.addWidget(self._metric_label(f"{null_count:,}"), 0, 2,
                       alignment=Qt.AlignmentFlag.AlignRight)

        unique_count = profile.get('unique_count', 0)
        unique_percent = profile.get('unique_percent', 0.0)
        rows.addWidget(self._metric_label("Únicos"), 1, 0)
        rows.addWidget(_PercentBar(unique_percent), 1, 1)
        rows.addWidget(self._metric_label(f"{unique_count:,}"), 1, 2,
                       alignment=Qt.AlignmentFlag.AlignRight)

        rows.setColumnStretch(0, 0)
        rows.setColumnStretch(1, 1)
        rows.setColumnStretch(2, 0)
        layout.addLayout(rows)

        numeric_stats = profile.get('numeric_stats')
        if numeric_stats:
            layout.addWidget(self._create_separator())
            layout.addWidget(self._numeric_stats_grid(numeric_stats))

        date_range = profile.get('date_range')
        if date_range:
            layout.addWidget(self._create_separator())
            layout.addWidget(self._metric_label(
                f"Rango: {date_range.get('min', '')} → {date_range.get('max', '')} "
                f"({date_range.get('days_span', 0):,} días)"
            ))

        top_values = profile.get('top_values')
        if top_values:
            layout.addWidget(self._create_separator())
            layout.addWidget(self._values_list_widget("Valores más frecuentes", top_values))

        distribution = profile.get('value_distribution')
        if distribution:
            layout.addWidget(self._create_separator())
            layout.addWidget(self._values_list_widget("Distribución", distribution))

        return card

    def _add_visualize_button(self, header: QHBoxLayout, name: str) -> None:
        """Botón minimalista que pide graficar la columna de la tarjeta."""
        chart_path = get_asset_path("chart.svg")
        btn = QPushButton()
        if chart_path.exists():
            btn.setIcon(QIcon(str(chart_path)))
            btn.setIconSize(QSize(14, 14))
        else:
            btn.setText("+")
        btn.setToolTip("Graficar esta columna")
        btn.setFixedSize(22, 22)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid transparent; "
            f"border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {_palette().app_bg}; border-color: {_palette().border}; }}"
            f"QPushButton:pressed {{ background: {_palette().border}; }}"
        )
        btn.clicked.connect(lambda: self.visualize_requested.emit(name))
        header.addWidget(btn)
        header.addSpacing(4)

    @staticmethod
    def _create_error_card(name: str, error_msg: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {_palette().surface}; border: 1px solid {_palette().border}; "
            f"border-radius: 8px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {_palette().text}; border: none;")
        header.addWidget(name_label)
        header.addStretch()
        badge = QLabel("error")
        badge.setStyleSheet(
            f"color: {_palette().danger}; font-size: 11px; background: #fef3c7; "
            f"border: 1px solid #fde68a; border-radius: 4px; padding: 2px 8px;"
        )
        header.addWidget(badge)
        layout.addLayout(header)

        error_label = QLabel(error_msg)
        error_label.setWordWrap(True)
        error_label.setStyleSheet(
            f"color: {_palette().danger}; font-size: 12px; border: none; margin-top: 4px;"
        )
        layout.addWidget(error_label)

        return card

    @staticmethod
    def _metric_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {_palette().text_muted}; font-size: 12px; border: none;")
        return label

    def _numeric_stats_grid(self, stats: dict[str, Any]) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {_palette().app_bg}; border: 1px solid {_palette().border}; "
            f"border-radius: 6px; }}"
        )
        grid = QGridLayout(frame)
        grid.setContentsMargins(12, 8, 12, 8)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)

        labels = [
            ("Conteo", 'count', "{:,}"),
            ("Mínimo", 'min', "{:,.4g}"),
            ("Máximo", 'max', "{:,.4g}"),
            ("Media", 'mean', "{:,.4g}"),
            ("Mediana", 'median', "{:,.4g}"),
            ("Desv. std", 'std', "{:,.4g}"),
            ("P25", 'q25', "{:,.4g}"),
            ("P75", 'q75', "{:,.4g}"),
        ]
        columns_per_row = 4
        for i, (title, key, fmt) in enumerate(labels):
            row_offset = (i // columns_per_row) * 2
            col_index = i % columns_per_row

            value = stats.get(key)
            title_label = QLabel(title)
            title_label.setStyleSheet(
                f"color: {_palette().text_muted}; font-size: 10px; border: none;"
            )
            value_label = QLabel(self._format_value(value, fmt))
            value_label.setStyleSheet(
                f"color: {_palette().text}; font-size: 11px; font-weight: 600; border: none;"
            )
            grid.addWidget(title_label, row_offset, col_index)
            grid.addWidget(value_label, row_offset + 1, col_index)

        return frame

    @staticmethod
    def _values_list_widget(title_text: str, values: list[list[Any]]) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel(title_text)
        title.setStyleSheet(
            f"color: {_palette().text_muted}; font-size: 11px; border: none; font-weight: bold;"
        )
        layout.addWidget(title)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(4)

        for row_idx, (value, count) in enumerate(values):
            value_str = str(value) if value is not None else "(nulo)"
            if len(value_str) > _MAX_VALUE_LENGTH:
                value_str = value_str[:_MAX_VALUE_LENGTH - 3] + "..."

            value_label = QLabel(value_str)
            value_label.setStyleSheet(f"color: {_palette().text}; font-size: 11px; border: none;")

            count_label = QLabel(f"{count:,}")
            count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            count_label.setStyleSheet(
                f"color: {_palette().text_muted}; font-size: 11px; border: none; "
                f"font-family: monospace;"
            )
            grid.addWidget(value_label, row_idx, 0)
            grid.addWidget(count_label, row_idx, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        layout.addWidget(grid_widget)

        return frame

    @staticmethod
    def _format_value(value: Any, fmt: str) -> str:
        if value is None:
            return "—"
        try:
            return fmt.format(value)
        except (TypeError, ValueError):
            return str(value)

    def get_profile(self) -> dict[str, Any] | None:
        """Devolver el perfil actualmente mostrado."""
        return self._profile
