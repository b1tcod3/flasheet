#!/usr/bin/env python3
"""
TaskThread: contrato común de los hilos de trabajo.
"""

from PySide6.QtCore import Signal

from app.services.task_thread import CANCELLED, TaskThread


class _ResultThread(TaskThread):
    result = Signal(object)
    failure = Signal(str)

    def __init__(self, behaviour: str) -> None:
        super().__init__()
        self.behaviour = behaviour

    def execute(self) -> object:
        if self.behaviour == 'error':
            raise ValueError('fallo simulado')
        if self.behaviour == 'cancel':
            return CANCELLED
        return 'resultado'

    def _emit_result(self, result: object) -> None:
        self.result.emit(result)

    def _emit_error(self, message: str) -> None:
        self.failure.emit(message)


def test_emits_result_on_success() -> None:
    thread = _ResultThread('ok')
    received: list[object] = []
    thread.result.connect(received.append)

    thread.run()

    assert received == ['resultado']


def test_emits_error_message_on_failure() -> None:
    thread = _ResultThread('error')
    errors: list[str] = []
    results: list[object] = []
    thread.failure.connect(errors.append)
    thread.result.connect(results.append)

    thread.run()

    assert errors == ['fallo simulado']
    assert results == []


def test_cancelled_result_is_not_emitted() -> None:
    thread = _ResultThread('cancel')
    results: list[object] = []
    thread.result.connect(results.append)

    thread.run()

    assert results == []


def test_requested_interruption_skips_work() -> None:
    class _InterruptedThread(_ResultThread):
        def isInterruptionRequested(self) -> bool:  # type: ignore[override]
            return True

    thread = _InterruptedThread('ok')
    results: list[object] = []
    thread.result.connect(results.append)

    thread.run()

    assert results == []
