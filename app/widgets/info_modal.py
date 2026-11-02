"""
Modal de Información para Flash View Sheet
Muestra detalles del archivo: nombre, filas, columnas, tipos
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QGroupBox,
                               QScrollArea, QPushButton, QWidget)
import pandas as pd

class InfoModal(QDialog):
    """
    Modal para mostrar información detallada del DataFrame
    """
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self.setWindowTitle("Información del Archivo")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()
        
    def setup_ui(self) -> None:
        """Configurar la interfaz del modal"""
        main_layout = QVBoxLayout(self)
        
        # Botón de cerrar
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #bd93f9;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        # Grupo: Información General
        general_group = QGroupBox("Información General")
        general_layout = QVBoxLayout(general_group)
        
        self.lbl_filename = QLabel("Nombre del archivo: -")
        self.lbl_filas = QLabel("Filas: -")
        self.lbl_columnas = QLabel("Columnas: -")
        
        general_layout.addWidget(self.lbl_filename)
        general_layout.addWidget(self.lbl_filas)
        general_layout.addWidget(self.lbl_columnas)
        
        # Grupo: Columnas
        columns_group = QGroupBox("Columnas")
        columns_layout = QVBoxLayout(columns_group)
        
        # Área de scroll para columnas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.columns_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        columns_layout.addWidget(scroll_area)
        
        # Grupo: Estadísticas
        stats_group = QGroupBox("Estadísticas Descriptivas")
        stats_layout = QVBoxLayout(stats_group)
        
        # Área de scroll para estadísticas
        self.stats_scroll = QScrollArea()
        self.stats_scroll.setWidgetResizable(True)
        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_widget)
        self.stats_scroll.setWidget(self.stats_widget)
        stats_layout.addWidget(self.stats_scroll)
        
        # Añadir todos los grupos al layout principal
        main_layout.addWidget(general_group)
        main_layout.addWidget(columns_group)
        main_layout.addWidget(stats_group)
        main_layout.addWidget(close_button)
        
    def update_info(self, df: pd.DataFrame, filename: str = "") -> None:
        """
        Actualizar la información mostrada con nuevos datos
        
        Args:
            df: DataFrame de Pandas
            filename: Nombre del archivo (opcional)
        """
        self.df = df
        
        # Actualizar información general
        if filename:
            self.lbl_filename.setText(f"Nombre del archivo: {filename}")
        self.lbl_filas.setText(f"Filas: {df.shape[0]}")
        self.lbl_columnas.setText(f"Columnas: {df.shape[1]}")
        
        # Limpiar layout de columnas
        for i in reversed(range(self.columns_layout.count())):
            widget = self.columns_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        # Mostrar información de columnas
        for col_name in df.columns:
            col_type = str(df.dtypes[col_name])
            col_info = QLabel(f"{col_name} ({col_type})")
            self.columns_layout.addWidget(col_info)
        
        # Actualizar estadísticas
        self.update_statistics(df)
        
    def update_statistics(self, df: pd.DataFrame) -> None:
        """
        Actualizar las estadísticas mostradas
        
        Args:
            df: DataFrame de Pandas
        """
        # Limpiar layout de estadísticas
        for i in reversed(range(self.stats_layout.count())):
            widget = self.stats_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        try:
            # Obtener estadísticas básicas
            from core.data_handler import obtener_estadisticas_basicas
            basic_stats = obtener_estadisticas_basicas(df)

            # Mostrar estadísticas básicas
            if basic_stats:
                basic_group = QGroupBox("Estadísticas Generales")
                basic_layout = QVBoxLayout(basic_group)

                basic_info = [
                    f"Total de filas: {basic_stats.get('total_filas', 'N/A'):,}",
                    f"Total de columnas: {basic_stats.get('total_columnas', 'N/A')}",
                    f"Columnas numéricas: {basic_stats.get('columnas_numericas', 'N/A')}",
                    f"Columnas de texto: {basic_stats.get('columnas_texto', 'N/A')}",
                    f"Uso de memoria: {basic_stats.get('memoria_uso_mb', 'N/A'):.2f} MB",
                    f"Total filas duplicadas: {basic_stats.get('filas_duplicadas', 'N/A'):,}",
                    f"Valores nulos totales: {basic_stats.get('valores_nulos_total', 'N/A'):,}",
                ]

                for info_text in basic_info:
                    info_label = QLabel(info_text)
                    basic_layout.addWidget(info_label)

                self.stats_layout.addWidget(basic_group)

            # Para datasets pequeños, mostrar estadísticas detalladas
            if len(df) <= 10000:
                self._mostrar_estadisticas_detalladas(df)
            else:
                # Para datasets grandes, mostrar mensaje de optimización
                perf_label = QLabel("Dataset grande optimizado - Estadísticas resumidas mostradas")
                perf_label.setStyleSheet("color: blue; font-style: italic;")
                self.stats_layout.addWidget(perf_label)

        except Exception as e:
            # Mostrar mensaje de error
            error_label = QLabel(f"Error al calcular estadísticas: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.stats_layout.addWidget(error_label)

    def _mostrar_estadisticas_detalladas(self, df: pd.DataFrame) -> None:
        """
        Mostrar estadísticas detalladas para datasets pequeños
        
        Args:
            df: DataFrame de Pandas
        """
        try:
            # Obtener estadísticas descriptivas
            from core.data_handler import obtener_estadisticas
            stats = obtener_estadisticas(df)

            # Mostrar estadísticas para cada columna numérica
            numeric_cols = df.select_dtypes(include=['number']).columns

            for col in numeric_cols:
                col_stats = stats[col] if col in stats.columns else None

                if col_stats is not None and not col_stats.empty:
                    # Crear grupo para cada columna numérica
                    col_group = QGroupBox(f"Estadísticas - {col}")
                    col_layout = QVBoxLayout(col_group)

                    # Mostrar estadísticas básicas
                    stats_info = [
                        f"Conteo: {col_stats.get('count', 'N/A'):,}",
                        f"Media: {col_stats.get('mean', 'N/A'):.4f}",
                        f"Desviación Estándar: {col_stats.get('std', 'N/A'):.4f}",
                        f"Mínimo: {col_stats.get('min', 'N/A'):.4f}",
                        f"25%: {col_stats.get('25%', 'N/A'):.4f}",
                        f"50% (Mediana): {col_stats.get('50%', 'N/A'):.4f}",
                        f"75%: {col_stats.get('75%', 'N/A'):.4f}",
                        f"Máximo: {col_stats.get('max', 'N/A'):.4f}",
                    ]

                    for stat_text in stats_info:
                        stat_label = QLabel(stat_text)
                        col_layout.addWidget(stat_label)

                    self.stats_layout.addWidget(col_group)

        except Exception as e:
            error_label = QLabel(f"Error al calcular estadísticas detalladas: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.stats_layout.addWidget(error_label)
