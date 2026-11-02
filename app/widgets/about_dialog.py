"""
Diálogo Acerca de - AboutDialog

Diálogo modal que muestra información sobre la aplicación.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from pathlib import Path

class AboutDialog(QDialog):
    """Diálogo modal para mostrar información Acerca de"""
    
    VERSION = "1.1.0"
    AUTHOR = "b1tcod3"
    GITHUB_URL = "https://github.com/b1tcod3"
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Configurar la interfaz del diálogo"""
        self.setWindowTitle("Acerca de Flash View Sheet")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Header con logo y título
        self._create_header(layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Descripción
        self._create_description(layout)
        
        # Creador
        self._create_creator(layout)
        
        # Botón OK
        self._create_buttons(layout)
    
    def _create_header(self, layout: QVBoxLayout) -> None:
        """Crear header con logo y título"""
        header_layout = QHBoxLayout()
        
        # Logo
        logo_label = self._create_logo()
        header_layout.addWidget(logo_label)
        
        # Título y versión
        title_layout = QVBoxLayout()
        
        title_label = QLabel("Flash View Sheet")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E86AB;")
        title_layout.addWidget(title_label)
        
        version_label = QLabel(f"Versión {self.VERSION}")
        version_label.setStyleSheet("font-size: 12px; color: #666;")
        title_layout.addWidget(version_label)
        
        header_layout.addLayout(title_layout)
        layout.addLayout(header_layout)
    
    def _create_logo(self) -> QLabel:
        """Crear etiqueta con logo"""
        logo_label = QLabel()
        
        logo_path = self._get_logo_path()
        if logo_path and Path(logo_path).exists():
            pixmap = QPixmap(logo_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return logo_label
    
    def _get_logo_path(self) -> str | None:
        """Obtener ruta del logo"""
        if self.parent_window:
            import sys
            main_dir = Path(sys.modules.get('__main__', type(sys)).__file__ or '.').parent
            logo_path = main_dir / "assets" / "logo.png"
            if logo_path.exists():
                return str(logo_path)
        
        # Fallback to app/assets
        current_dir = Path(__file__).resolve().parent.parent.parent
        logo_path = current_dir / "assets" / "logo.png"
        if logo_path.exists():
            return str(logo_path)
        
        return None
    
    @staticmethod
    def _create_description(layout: QVBoxLayout) -> None:
        """Crear sección de descripción"""
        desc_text = """
        <p><b>Flash View Sheet</b> es una aplicación ligera para visualizar 
        y analizar datos de archivos Excel y CSV.</p>
        
        <p><b>Características:</b></p>
        <ul>
        <li>📊 Visualización interactiva de datos</li>
        <li>📈 Análisis estadístico</li>
        <li>🔍 Filtrado y búsqueda avanzada</li>
        <li>📤 Exportación múltiple (PDF, XLSX, CSV, SQL)</li>
        <li>⚡ Optimizaciones de rendimiento</li>
        </ul>
        <p><b>Desarrollado con:</b> Python 3.10+ y PySide6</p>
        """
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(desc_label)
    
    def _create_creator(self, layout: QVBoxLayout) -> None:
        """Crear sección de creador"""
        creator_text = f"""
        <p><b>Creador:</b> {self.AUTHOR}</p>
        <p><b>GitHub:</b> <a href="{self.GITHUB_URL}">{self.GITHUB_URL}</a></p>
        """
        creator_label = QLabel(creator_text)
        creator_label.setWordWrap(True)
        creator_label.setTextFormat(Qt.TextFormat.RichText)
        creator_label.setStyleSheet("background-color: #f0f0f0; color: #333333; padding: 10px; border-radius: 5px;")
        layout.addWidget(creator_label)
    
    def _create_buttons(self, layout: QVBoxLayout) -> None:
        """Crear botones de acción"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("Aceptar")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
    
    @classmethod
    def show_about(cls, parent: QWidget | None = None) -> None:
        """Método estático para mostrar el diálogo"""
        dialog = cls(parent)
        dialog.exec()

# Constantes exportadas
__all__ = ['AboutDialog']
