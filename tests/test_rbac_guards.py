"""Verifica estáticamente que todo event handler que escribe en BD valida permiso.

Regla: en clinica_app/state/*.py, todo método cuyo cuerpo abre sesión de BD
(get_async_session) debe llamar a tiene_permiso(...), salvo que sea un handler
de solo lectura (loaders, búsquedas, on_mount ya cubierto por su propio guard).
"""
from __future__ import annotations

import ast
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "clinica_app" / "state"

# Prefijos de handlers de SOLO LECTURA (no mutan; permitidos sin write-guard).
READ_ONLY_PREFIXES = (
    "on_mount", "cargar", "_cargar", "_recargar", "_precargar",
    "buscar", "abrir", "ver_", "set_pac_busqueda", "handle_login",
)

# Excepciones justificadas: handlers que mutan pero NO se gobiernan por un
# permiso de módulo. La autorización es la identidad de la propia sesión.
EXCEPCIONES = frozenset({
    # Autoservicio: el usuario cambia SU propia contraseña (opera solo sobre
    # self.user_id y verifica la contraseña actual). Debe estar disponible para
    # cualquier usuario autenticado, sin permiso de configuración.
    "cuenta.py::CuentaState.cambiar_password",
})


def _handlers_sin_guard() -> list[str]:
    faltantes = []
    for f in sorted(STATE_DIR.glob("*.py")):
        src_full = f.read_text(encoding="utf-8")
        tree = ast.parse(src_full)
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if not isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    continue
                if fn.name.startswith(READ_ONLY_PREFIXES):
                    continue
                if f"{f.name}::{cls.name}.{fn.name}" in EXCEPCIONES:
                    continue
                src = ast.get_source_segment(src_full, fn) or ""
                if "get_async_session" in src and "tiene_permiso" not in src:
                    faltantes.append(f"{f.name}::{cls.name}.{fn.name} (línea {fn.lineno})")
    return faltantes


def test_todo_handler_mutador_valida_permiso():
    faltantes = _handlers_sin_guard()
    assert not faltantes, (
        "Handlers que abren sesión de BD sin validar tiene_permiso(). "
        "Si el handler es de solo lectura, agregá su prefijo a READ_ONLY_PREFIXES; "
        "si escribe, agregá el guard tiene_permiso(módulo, write=True):\n  - "
        + "\n  - ".join(faltantes)
    )
