"""
Base común para tareas ejecutadas en un hilo de Qt.

Las cinco tareas en segundo plano de la app (cargar archivo, cargar carpeta,
join, perfil y visualización) compartían el mismo esqueleto: comprobar
cancelación, ejecutar, emitir resultado y traducir la excepción a una señal.

`TaskThread` implementa ese esqueleto (Template Method). Cada subclase
conserva sus propias señales públicas y solo define qué ejecutar y cómo
publicar el resultado o el error.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Final

from PySide6.QtCore import QObject, QThread

logger = logging.getLogger(__name__)


class _Cancelled:
    """Centinela para indicar que la tarea se canceló a mitad de camino."""

    def __repr__(self) -> str:  # pragma: no cover - solo depuración
        return '<cancelled>'


CANCELLED: Final = _Cancelled()


class TaskThread(QThread):
    """Hilo con manejo uniforme de cancelación y errores."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        """Ejecutar la tarea y publicar el resultado o el error."""
        try:
            if self.isInterruptionRequested():
                return

            result = self.execute()
            if result is CANCELLED or self.isInterruptionRequested():
                return

            self._emit_result(result)
        except Exception as exc:
            # Frontera del hilo: la excepción no puede propagarse a la UI.
            if not self.isInterruptionRequested():
                self._emit_error(str(exc))

    @abstractmethod
    def execute(self) -> object:
        """Realizar el trabajo pesado y devolver su resultado."""

    @abstractmethod
    def _emit_result(self, result: object) -> None:
        """Publicar el resultado en la señal correspondiente."""

    @abstractmethod
    def _emit_error(self, message: str) -> None:
        """Publicar el error en la señal correspondiente."""


def stop_thread(thread: QThread | None, timeout_ms: int = 5000) -> bool:
    """Detener un hilo de forma cooperativa.

    Nunca se usa `QThread.terminate()`: matar un hilo a mitad de una operación
    deja recursos (ficheros, locks, objetos Qt) en estado inconsistente. Si el
    hilo no termina en `timeout_ms` se deja finalizar solo y se registra.

    Returns:
        True si el hilo terminó (o no estaba corriendo).
    """
    if thread is None or not thread.isRunning():
        return True

    thread.requestInterruption()
    thread.quit()

    if thread.wait(timeout_ms):
        return True

    logger.warning(
        "El hilo %s no terminó en %s ms; se deja finalizar sin terminate()",
        type(thread).__name__,
        timeout_ms,
    )
    return False


__all__ = ['CANCELLED', 'TaskThread', 'stop_thread']
