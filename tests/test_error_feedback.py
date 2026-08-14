"""Verifica estáticamente que ningún handler traga un ServiceError en silencio.

Regla (feedback de errores, P3): en clinica_app/state/*.py, un `except ServiceError`
NUNCA debe tener como único cuerpo un `pass`. El error de negocio debe surfacearse
al usuario — vía `yield rx.toast.error(...)`, seteando un campo `*_error`, etc.

Esto complementa a test_rbac_guards.py: aquel garantiza el guard de permiso; éste,
que las fallas esperadas no desaparezcan sin avisar.
"""
from __future__ import annotations

import ast
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "clinica_app" / "state"


def _menciona_service_error(handler: ast.ExceptHandler) -> bool:
    """True si el `except` captura ServiceError (solo o dentro de una tupla)."""
    exc = handler.type
    if exc is None:  # bare `except:` — fuera de alcance de esta regla
        return False
    nodos = exc.elts if isinstance(exc, ast.Tuple) else [exc]
    for n in nodos:
        if isinstance(n, ast.Name) and n.id == "ServiceError":
            return True
    return False


def _except_service_error_silenciosos() -> list[str]:
    silenciosos = []
    for f in sorted(STATE_DIR.glob("*.py")):
        src_full = f.read_text(encoding="utf-8")
        tree = ast.parse(src_full)
        for handler in [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]:
            if not _menciona_service_error(handler):
                continue
            cuerpo = handler.body
            if len(cuerpo) == 1 and isinstance(cuerpo[0], ast.Pass):
                silenciosos.append(f"{f.name} (línea {handler.lineno})")
    return silenciosos


def test_ningun_service_error_tragado_en_silencio():
    silenciosos = _except_service_error_silenciosos()
    assert not silenciosos, (
        "Hay `except ServiceError:` cuyo único cuerpo es `pass` (traga el error sin "
        "avisar al usuario). Surfacealo con `yield rx.toast.error(str(exc))` o seteando "
        "un campo *_error:\n  - " + "\n  - ".join(silenciosos)
    )
