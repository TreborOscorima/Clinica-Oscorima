"""Almacenamiento de archivos adjuntos (A2).

Abstracción fina sobre el sistema de archivos local. Hoy escribe en disco bajo
`UPLOAD_DIR/clinica_<id>/`; el día que se quiera S3/Backblaze basta reimplementar
`guardar`, `ruta_absoluta` y `eliminar` sin tocar el resto del sistema (el modelo
`Adjunto` guarda solo `stored_name`, no una ruta absoluta acoplada).

No depende de Reflex ni de la sesión de BD: recibe bytes y devuelve metadatos.
"""
from __future__ import annotations

import os
import re
import uuid

from clinica_app.config import UPLOAD_ALLOWED_EXT, UPLOAD_DIR, UPLOAD_MAX_MB
from clinica_app.services.exceptions import ValidationError

_SAFE_EXT_RE = re.compile(r"^[a-z0-9]{1,8}$")


def _extension(nombre: str) -> str:
    ext = os.path.splitext(nombre or "")[1].lstrip(".").lower()
    return ext


def _clinica_dir(clinica_id: int) -> str:
    return os.path.join(UPLOAD_DIR, f"clinica_{int(clinica_id)}")


def validar(nombre: str, tamano: int) -> str:
    """Valida extensión y tamaño. Devuelve la extensión normalizada o lanza.

    Se llama ANTES de escribir a disco para rechazar temprano.
    """
    ext = _extension(nombre)
    if not ext or not _SAFE_EXT_RE.match(ext):
        raise ValidationError("Archivo sin extensión válida")
    if ext not in UPLOAD_ALLOWED_EXT:
        raise ValidationError(f"Tipo de archivo no permitido: .{ext}")
    if tamano <= 0:
        raise ValidationError("El archivo está vacío")
    if tamano > UPLOAD_MAX_MB * 1024 * 1024:
        raise ValidationError(f"El archivo supera el máximo de {UPLOAD_MAX_MB} MB")
    return ext


def guardar(clinica_id: int, nombre_original: str, data: bytes) -> str:
    """Escribe los bytes a disco y devuelve el `stored_name` (uuid.ext).

    Valida de nuevo el tamaño real de los bytes (defensa ante un `size` mentido
    por el cliente).
    """
    ext = validar(nombre_original, len(data))
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    destino_dir = _clinica_dir(clinica_id)
    os.makedirs(destino_dir, exist_ok=True)
    with open(os.path.join(destino_dir, stored_name), "wb") as fh:
        fh.write(data)
    return stored_name


def ruta_absoluta(clinica_id: int, stored_name: str) -> str:
    """Ruta en disco para servir un adjunto. Blinda contra path traversal."""
    base = os.path.abspath(_clinica_dir(clinica_id))
    # `stored_name` es un uuid.ext generado por nosotros, pero nunca confiamos:
    safe = os.path.basename(stored_name or "")
    path = os.path.abspath(os.path.join(base, safe))
    if not path.startswith(base + os.sep):
        raise ValidationError("Ruta de archivo inválida")
    return path


def eliminar(clinica_id: int, stored_name: str) -> None:
    """Borra el archivo físico si existe (idempotente)."""
    try:
        path = ruta_absoluta(clinica_id, stored_name)
    except ValidationError:
        return
    if os.path.isfile(path):
        os.remove(path)
