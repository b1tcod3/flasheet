"""
VisualizationService: Generación de visualizaciones exploratorias rápidas.

Aplica las reglas de alto data-ink ratio de Tufte: sin spines superiores
ni derechos, rejilla tenue únicamente en el eje Y, paleta de colores
limitada y submuestreo automático para datasets grandes. La generación
es stateless y tolerante a fallos; se ejecuta en segundo plano mediante
VisualizerWorkerThread para no bloquear la interfaz.
"""

import matplotlib
import pandas as pd
from PySide6.QtCore import Signal
from app.services.task_thread import CANCELLED, TaskThread
from matplotlib.axes import Axes
from matplotlib.figure import Figure

try:
    matplotlib.use("Agg")
except Exception:
    pass

# ==================== Paleta minimalista (Tufte) ====================

_ACCENT_COLOR = "#4f46e5"    # Indigo tenue (datos principales)
_ACCENT_FILL = "#e0e7ff"     # Relleno claro del boxplot
_MEDIAN_COLOR = "#1e1b4b"    # Línea de mediana del boxplot
_SPINE_COLOR = "#cbd5e1"     # Spines left/bottom
_GRID_COLOR = "#e2e8f0"      # Rejilla del eje Y
_TICK_COLOR = "#475569"      # Etiquetas de ticks
_LABEL_COLOR = "#64748b"     # Etiquetas de ejes
_EDGE_COLOR = "#ffffff"      # Borde de barras/histogramas
_OUTLIER_COLOR = "#ef4444"   # Outliers del boxplot
_FIGURE_BG = "#f8fafc"

_MAX_POINTS = 10000
_BINS = 25
_TOP_VALUES = 10
_MAX_LABEL_LENGTH = 20
_FONT_SIZE = 9
_DISPLAYED_DPI = 100


def apply_minimal_theme(ax: Axes) -> None:
    """Aplica las reglas de alto Data-Ink Ratio al Axes de Matplotlib."""
    # 1. Eliminar spines top y right
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 2. Estilizar spines left y bottom
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(_SPINE_COLOR)
        ax.spines[spine].set_linewidth(0.8)

    # 3. Rejilla horizontal sutil
    ax.yaxis.grid(True, linestyle='--', alpha=0.6, color=_GRID_COLOR)
    ax.xaxis.grid(False)

    # 4. Ticks y etiquetas discretas
    ax.tick_params(axis='both', which='both', color=_SPINE_COLOR,
                   labelsize=_FONT_SIZE, labelcolor=_TICK_COLOR)
    ax.set_facecolor("#ffffff")


class VisualizationService:
    """Servicio stateless para generar figuras minimalistas.

    Cada método recibe el DataFrame como parámetro y devuelve una
    Figure de Matplotlib lista para embeber en un FigureCanvasQTAgg.
    """

    @staticmethod
    def prepare_scatter_data(
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        max_points: int = _MAX_POINTS,
    ) -> tuple[pd.Series, pd.Series]:
        """Submuestreo aleatorio si el dataset es masivo para preservar la fluidez."""
        data = df[[x_col, y_col]].dropna()
        if len(data) > max_points:
            data = data.sample(n=max_points, random_state=42)
        return data[x_col], data[y_col]

    @staticmethod
    def generate_histogram(df: pd.DataFrame, column: str, bins: int = _BINS) -> Figure:
        """Histograma de distribución de una columna numérica."""
        fig = Figure(figsize=(6, 4), facecolor=_FIGURE_BG, dpi=_DISPLAYED_DPI)
        ax = fig.add_subplot(111)
        apply_minimal_theme(ax)

        data = df[column].dropna()
        ax.hist(data, bins=bins, color=_ACCENT_COLOR, edgecolor=_EDGE_COLOR,
                linewidth=0.5, alpha=0.85)
        ax.set_xlabel(str(column), fontsize=_FONT_SIZE, color=_LABEL_COLOR)
        ax.set_ylabel("Frecuencia", fontsize=_FONT_SIZE, color=_LABEL_COLOR)
        fig.tight_layout()
        return fig

    @staticmethod
    def generate_scatter(
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        max_points: int = _MAX_POINTS,
    ) -> Figure:
        """Diagrama de dispersión con transparencia para evidenciar densidad."""
        fig = Figure(figsize=(6, 4), facecolor=_FIGURE_BG, dpi=_DISPLAYED_DPI)
        ax = fig.add_subplot(111)
        apply_minimal_theme(ax)

        x_data, y_data = VisualizationService.prepare_scatter_data(df, x_col, y_col, max_points)
        ax.scatter(x_data, y_data, color=_ACCENT_COLOR, alpha=0.35, s=20, edgecolors='none')
        ax.set_xlabel(str(x_col), fontsize=_FONT_SIZE, color=_LABEL_COLOR)
        ax.set_ylabel(str(y_col), fontsize=_FONT_SIZE, color=_LABEL_COLOR)
        fig.tight_layout()
        return fig

    @staticmethod
    def generate_bar_counts(df: pd.DataFrame, column: str, top: int = _TOP_VALUES) -> Figure:
        """Barras horizontales del Top-N de categorías más frecuentes."""
        fig = Figure(figsize=(6, 4), facecolor=_FIGURE_BG, dpi=_DISPLAYED_DPI)
        ax = fig.add_subplot(111)
        apply_minimal_theme(ax)

        counts = df[column].dropna().value_counts().head(top)
        if counts.empty:
            ax.text(0.5, 0.5, "Sin valores en esta columna", ha='center', va='center',
                    color=_LABEL_COLOR, fontsize=10)
            fig.tight_layout()
            return fig

        y_pos = list(range(len(counts)))
        ax.barh(y_pos, counts.values, color=_ACCENT_COLOR, height=0.6, alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([str(idx)[:_MAX_LABEL_LENGTH] for idx in counts.index])
        ax.invert_yaxis()
        ax.set_xlabel("Conteo", fontsize=_FONT_SIZE, color=_LABEL_COLOR)
        fig.tight_layout()
        return fig

    @staticmethod
    def generate_boxplot(df: pd.DataFrame, column: str) -> Figure:
        """Diagrama de cajas horizontal con outliers resaltados."""
        fig = Figure(figsize=(6, 4), facecolor=_FIGURE_BG, dpi=_DISPLAYED_DPI)
        ax = fig.add_subplot(111)
        apply_minimal_theme(ax)

        data = df[column].dropna()
        ax.boxplot(
            data, vert=False, patch_artist=True,
            boxprops=dict(facecolor=_ACCENT_FILL, color=_ACCENT_COLOR, linewidth=1),
            whiskerprops=dict(color=_ACCENT_COLOR, linewidth=1),
            capprops=dict(color=_ACCENT_COLOR, linewidth=1),
            medianprops=dict(color=_MEDIAN_COLOR, linewidth=1.5),
            flierprops=dict(marker='o', markerfacecolor=_OUTLIER_COLOR,
                            markeredgecolor='none', markersize=4, alpha=0.5),
        )
        ax.set_yticks([])
        ax.set_xlabel(str(column), fontsize=_FONT_SIZE, color=_LABEL_COLOR)
        fig.tight_layout()
        return fig

    @staticmethod
    def generate_figure(df: pd.DataFrame, chart_type: str, x_col: str, y_col: str) -> Figure:
        """Despachar la generación según el tipo de gráfico solicitado."""
        if chart_type == "histogram":
            return VisualizationService.generate_histogram(df, x_col)
        if chart_type == "scatter":
            return VisualizationService.generate_scatter(df, x_col, y_col)
        if chart_type == "bar":
            return VisualizationService.generate_bar_counts(df, x_col)
        if chart_type == "boxplot":
            return VisualizationService.generate_boxplot(df, x_col)
        raise ValueError(f"Tipo de gráfico no soportado: {chart_type}")


class VisualizerWorkerThread(TaskThread):
    """Hilo para generar la visualización sin bloquear la interfaz.

    Señales:
        finished(object): Figure de Matplotlib lista para mostrar.
        error(str): Mensaje de error si falla la generación.
    """

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, df: pd.DataFrame, chart_type: str, x_col: str, y_col: str) -> None:
        super().__init__()
        self.df = df
        self.chart_type = chart_type
        self.x_col = x_col
        self.y_col = y_col

    def execute(self) -> object:
        """Generar la figura y liberarla si la tarea se canceló."""
        fig = VisualizationService.generate_figure(
            self.df, self.chart_type, self.x_col, self.y_col
        )
        if self.isInterruptionRequested():
            fig.clf()
            return CANCELLED
        return fig

    def _emit_result(self, result: object) -> None:
        self.finished.emit(result)

    def _emit_error(self, message: str) -> None:
        self.error.emit(message)


__all__ = ['VisualizationService', 'VisualizerWorkerThread', 'apply_minimal_theme']
