"""Política de contraseñas (auditoría: reglas de complejidad).

Validador puro y reutilizable: la contraseña debe tener un mínimo de longitud y
combinar letras y números. No es una fortaleza de nivel bancario —el sistema lo
usa personal de clínica— pero eleva el piso previo (solo `len >= 6`) a algo que
frena las contraseñas triviales. Se aplica al crear usuario, al cambiarla desde
la administración y en el autoservicio (ver services/auth.cambiar_mi_password).
"""
from __future__ import annotations

import re

from clinica_app.services.exceptions import ValidationError

LONGITUD_MINIMA = 8

_TIENE_LETRA = re.compile(r"[A-Za-z]")
_TIENE_NUMERO = re.compile(r"\d")


def validar_password(password: str) -> None:
    """Valida la política. Lanza ValidationError con un mensaje claro si no cumple."""
    p = password or ""
    if len(p) < LONGITUD_MINIMA:
        raise ValidationError(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres"
        )
    if not _TIENE_LETRA.search(p):
        raise ValidationError("La contraseña debe incluir al menos una letra")
    if not _TIENE_NUMERO.search(p):
        raise ValidationError("La contraseña debe incluir al menos un número")
