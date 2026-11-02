"""
View Registry

Registro de vistas disponibles en la aplicación.
Define constantes de índices y metadata de cada vista.
"""


class ViewRegistry:
    """Registro de vistas disponibles"""

    VIEW_MAIN = 0
    VIEW_DATA = 1
    VIEW_JOIN = 3
    VIEW_PIVOT = 4
    VIEW_PROFILING = 5
    VIEW_VISUALIZER = 6

    VIEW_NAMES = {
        VIEW_MAIN: "Principal",
        VIEW_DATA: "Datos",
        VIEW_JOIN: "Datos Cruzados",
        VIEW_PIVOT: "Pivote",
        VIEW_PROFILING: "Perfil de Datos",
        VIEW_VISUALIZER: "Visualizador Rápido",
    }

    VIEW_DESCRIPTIONS = {
        VIEW_MAIN: "Pantalla de bienvenida y carga de archivos",
        VIEW_DATA: "Visualización tabular con paginación",
        VIEW_JOIN: "Resultado de cruce de datasets",
        VIEW_PIVOT: "Tablas pivote automáticas por combinación categórica × numérica",
        VIEW_PROFILING: "Perfil de datos: tipo, nulos y cardinalidad por columna",
        VIEW_VISUALIZER: "Gráficos exploratorios rápidos: histograma, dispersión, barras y boxplot",
    }

    @classmethod
    def get_view_name(cls, index: int) -> str:
        return cls.VIEW_NAMES.get(index, f"Vista {index}")

    @classmethod
    def get_view_description(cls, index: int) -> str:
        return cls.VIEW_DESCRIPTIONS.get(index, "")

    @classmethod
    def get_all_view_indices(cls) -> list:
        return list(cls.VIEW_NAMES.keys())

    @classmethod
    def is_valid_view(cls, index: int) -> bool:
        return index in cls.VIEW_NAMES
