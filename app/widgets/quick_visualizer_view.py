"""
QuickVisualizerView - Vista de exploración gráfica rápida y minimalista.

Permite generar histogramas, diagramas de dispersión, barras de
frecuencia y boxplots de forma inmediata con un alto data-ink ratio.
La vista solo gestiona la selección de configuración y la renderización
de la figura; la generación se delega al AppCoordinator mediante la
señal generate_requested.
"""


import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.theme import current_theme
from app.theme.palette import ThemePalette, get_palette


def _palette() -> ThemePalette:
    """Paleta activa: se relee en cada repintado para seguir al tema."""
    return get_palette(current_theme())


_CHART_TYPES: list[tuple[str, str]] = [
    ("Histograma (Distribución)", "histogram"),
    ("Dispersión (Scatter)", "scatter"),
    ("Barras (Frecuencia)", "bar"),
    ("Boxplot (Cajas)", "boxplot"),
]


class QuickVisualizerView(QWidget):
    """Vista de exploración gráfica rápida con interfaz minimalista."""

    generate_requested = Signal(str, str, str)  # (chart_type, x_col, y_col)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._df: pd.DataFrame | None = None
        self._placeholder_message = 'Carga un archivo para explorar sus datos gráficamente.'
        self._fig: Figure
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self._header = QLabel("Visualizador Rápido")
        self._header.setStyleSheet(
            f"color: {_palette().text}; font-size: 14px; font-weight: bold;"
        )
        layout.addWidget(self._header)

        # --- PANEL DE CONTROLES ---
        self._controls_frame = QFrame()
        controls_frame = self._controls_frame
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(12, 8, 12, 8)
        controls_layout.setSpacing(8)

        controls_layout.addWidget(QLabel("Tipo:"))
        self._chart_type_combo = QComboBox()
        self._chart_type_combo.addItems([label for label, _ in _CHART_TYPES])
        self._chart_type_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        controls_layout.addWidget(self._chart_type_combo)

        controls_layout.addWidget(QLabel("Eje X:"))
        self._combo_x = QComboBox()
        self._combo_x.currentIndexChanged.connect(self._on_columns_changed)
        controls_layout.addWidget(self._combo_x, 1)

        self._lbl_y = QLabel("Eje Y:")
        controls_layout.addWidget(self._lbl_y)
        self._combo_y = QComboBox()
        self._combo_y.currentIndexChanged.connect(self._on_columns_changed)
        controls_layout.addWidget(self._combo_y, 1)

        controls_layout.addStretch()
        layout.addWidget(controls_frame)

        # --- CANVAS DE MATPLOTLIB ---
        self._fig = Figure(figsize=(6, 4), facecolor=_palette().app_bg, dpi=100)
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas, 1)

        self._status_label = QLabel("Selecciona un tipo de gráfico y columnas para visualizar.")
        layout.addWidget(self._status_label)

        self._apply_styles()
        self.show_placeholder("Carga un archivo para explorar sus datos gráficamente.")

    # ==================== TEMA ====================

    def _apply_styles(self) -> None:
        """Repintar el chrome de la vista con la paleta activa."""
        tokens = _palette()
        self.setStyleSheet(f"background-color: {tokens.app_bg};")
        self._header.setStyleSheet(
            f"color: {tokens.text}; font-size: 14px; font-weight: bold;"
        )
        self._controls_frame.setStyleSheet(
            f"QFrame {{ background-color: {tokens.surface}; border: 1px solid {tokens.border}; "
            f"border-radius: 8px; }}"
            f"QLabel {{ color: {tokens.text_muted}; font-size: 12px; border: none; }}"
            f"QComboBox {{ border: 1px solid {tokens.border}; border-radius: 4px; "
            f"padding: 4px 8px; background: {tokens.app_bg}; font-size: 12px; "
            f"color: {tokens.text}; }}"
        )
        self._canvas.setStyleSheet("background-color: transparent;")
        self._status_label.setStyleSheet(
            f"color: {tokens.text_muted}; font-size: 12px;"
        )
        self._fig.set_facecolor(tokens.app_bg)
        self._canvas.draw_idle()

    def refresh_theme(self) -> None:
        """Aplicar el tema nuevo y redibujar el canvas."""
        self._apply_styles()
        if self._df is not None:
            self._on_columns_changed()
        else:
            self.show_placeholder(getattr(self, '_placeholder_message', ''))

    # ==================== DATOS Y CONFIGURACIÓN ====================

    def set_dataframe(self, df: pd.DataFrame | None) -> None:
        """Carga el DataFrame y actualiza los combos de columnas."""
        self._df = df if (df is not None and not df.empty) else None

        self._combo_x.blockSignals(True)
        self._combo_y.blockSignals(True)
        self._combo_x.clear()
        self._combo_y.clear()

        if self._df is not None:
            cols = [str(col) for col in self._df.columns]
            self._combo_x.addItems(cols)
            self._combo_y.addItems(cols)

        self._combo_x.blockSignals(False)
        self._combo_y.blockSignals(False)

        if self._df is None:
            self.show_placeholder("Carga un archivo para explorar sus datos gráficamente.")
            return
        self._on_chart_config_changed()

    def set_selected_column(self, column: str) -> None:
        """Preselecciona una columna en el combo Eje X (si existe)."""
        if self._df is not None and column in [str(c) for c in self._df.columns]:
            self._combo_x.setCurrentText(column)

    def current_chart_type(self) -> str:
        """Devolver la clave del tipo de gráfico seleccionado."""
        index = self._chart_type_combo.currentIndex()
        if 0 <= index < len(_CHART_TYPES):
            return _CHART_TYPES[index][1]
        return "histogram"

    # ==================== RENDERIZADO ====================

    def show_figure(self, fig: Figure) -> None:
        """Mostrar una figura de Matplotlib en el canvas."""
        self._fig.clear()
        self._fig = fig
        self._canvas.figure = fig
        self._status_label.setText("")
        self._canvas.draw()

    def show_placeholder(self, message: str) -> None:
        """Mostrar un mensaje central en lugar del gráfico."""
        self._placeholder_message = message
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        ax.axis('off')
        ax.text(0.5, 0.5, message, ha='center', va='center',
                color=_palette().text_muted, fontsize=11)
        self._fig.tight_layout()
        self._status_label.setText("")
        self._canvas.draw()

    def show_error(self, message: str) -> None:
        """Mostrar un error de generación en el canvas."""
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        ax.axis('off')
        ax.text(0.5, 0.5, f"No se pudo graficar:\n{message}", ha='center', va='center',
                color="#b45309", fontsize=10)
        self._fig.tight_layout()
        self._status_label.setText("")
        self._canvas.draw()

    # ==================== SLOTS INTERNOS ====================

    def _on_chart_config_changed(self) -> None:
        """Ajusta la visibilidad del combo Y según el tipo de gráfico."""
        is_scatter = self.current_chart_type() == "scatter"
        self._lbl_y.setVisible(is_scatter)
        self._combo_y.setVisible(is_scatter)
        self._on_columns_changed()

    def _on_columns_changed(self) -> None:
        """Emite generate_requested cuando hay configuración válida."""
        if self._df is None:
            return
        x_col = self._combo_x.currentText()
        chart_type = self.current_chart_type()
        if not x_col:
            return
        y_col = self._combo_y.currentText() if chart_type == "scatter" else ""
        self.generate_requested.emit(chart_type, x_col, y_col)

    # ==================== UTILIDADES ====================

    def get_df(self) -> pd.DataFrame | None:
        """Devolver el DataFrame actualmente cargado."""
        return self._df
