"""
Excepciones del sistema de loaders.

Permiten distinguir un fallo de lectura (recuperable por el llamante) de un
error de programación, en lugar de lanzar `Exception` genérica.
"""


class LoaderError(RuntimeError):
    """Error al leer o interpretar un archivo de datos."""


__all__ = ['LoaderError']
