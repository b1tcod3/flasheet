#!/usr/bin/env python3
"""
Higiene del código Qt: reglas que no deben volver a colarse.

Se comprueba sobre el código fuente porque son patrones que compilan y
funcionan en pruebas, pero fallan en producción (ver skill pyside6-desktop).
"""

import ast
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / 'app'
SOURCES = sorted(APP_DIR.rglob('*.py')) + [APP_DIR.parent / 'main.py']


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _method_calls(path: Path) -> list[tuple[str, int]]:
    """(nombre_de_método, línea) de cada llamada del módulo."""
    tree = ast.parse(_read(path))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.append((node.func.attr, node.lineno))
    return calls


def test_no_qthread_terminate() -> None:
    """Matar un QThread deja recursos inconsistentes: solo cancelación cooperativa."""
    offenders = [
        f"{path}:{line}"
        for path in SOURCES
        for name, line in _method_calls(path)
        if name == 'terminate'
    ]
    assert offenders == [], f"Uso de QThread.terminate(): {offenders}"


def test_no_process_events() -> None:
    """processEvents() reentra el event loop y permite dobles ejecuciones."""
    offenders = [
        f"{path}:{line}"
        for path in SOURCES
        for name, line in _method_calls(path)
        if name == 'processEvents'
    ]
    assert offenders == [], f"Uso de processEvents(): {offenders}"


def test_inline_stylesheets_declare_color() -> None:
    """Un setStyleSheet con tipografía o padding sin color deja texto invisible."""
    pattern = re.compile(
        r'setStyleSheet\(\s*(?:"""|\'\'\'|"|\')(.*?)(?:"""|\'\'\'|"|\')\s*\)',
        re.S,
    )
    offenders: list[str] = []
    for path in SOURCES:
        source = _read(path)
        for match in pattern.finditer(source):
            qss = match.group(1)
            has_typography = bool(
                re.search(r'(font-size|font-weight|font-family|padding)\s*:', qss)
            )
            has_color = bool(re.search(r'(^|[;{\s])color\s*:', qss))
            if has_typography and not has_color:
                line = source[:match.start()].count('\n') + 1
                offenders.append(f"{path}:{line}")

    assert offenders == [], f"QSS inline sin color: {offenders}"


def test_no_deprecated_qt_enum_shortcuts() -> None:
    r"""Los alias cortos de Qt5 están deprecados en Qt6 (se usan enums con scope).

    `(?![\w.])` evita marcar los equivalentes modernos, p. ej.
    `Qt.AlignmentFlag.AlignCenter` no debe coincidir con `Qt.Align`.
    """
    deprecated = [
        'Qt.Align', 'Qt.DisplayRole', 'Qt.EditRole', 'Qt.UserRole',
        'Qt.ItemIs', 'Qt.AscendingOrder', 'Qt.DescendingOrder',
        'Qt.WindowModal', 'Qt.LeftButton', 'Qt.RichText', 'Qt.Horizontal',
        'Qt.Vertical', 'QMessageBox.Yes', 'QMessageBox.No', 'QMessageBox.Ok',
        'QDialog.Accepted', 'QFont.Bold', 'QFrame.VLine', 'QFrame.HLine',
        'QHeaderView.Interactive', 'QHeaderView.ResizeToContents',
        'QSizePolicy.Expanding', 'QTableView.SelectRows', 'QStyle.SP_',
        'QDialogButtonBox.Ok', 'QDialogButtonBox.Cancel',
        'Qt.green', 'Qt.red', 'Qt.yellow', 'Qt.white', 'Qt.black',
        'Qt.PointingHandCursor', 'Qt.CustomContextMenu', 'Qt.KeepAspectRatio',
        'Qt.SmoothTransformation', 'Qt.ItemFlags',
    ]
    offenders: list[str] = []
    for path in SOURCES:
        for number, line in enumerate(_read(path).splitlines(), 1):
            if line.strip().startswith('#'):
                continue
            for token in deprecated:
                if re.search(rf'\b{re.escape(token)}(?![\w.])', line):
                    offenders.append(f"{path}:{number} {token}")
    assert offenders == [], f"Enums obsoletos de Qt5: {offenders}"
