"""Lógica pura de expiración de sesión (TTL). Aislada del State de Reflex
para poder testearla sin instanciar el árbol de estados."""
from __future__ import annotations


def sesion_vencida(login_at: float, ttl_seconds: int, ahora: float) -> bool:
    """True si una sesión iniciada en `login_at` (epoch segundos) superó el TTL
    a la hora `ahora` (epoch segundos).

    `login_at` falsy (0.0 → sin login registrado) nunca se considera vencido:
    la decisión de si hay sesión activa vive en el caller.
    """
    if not login_at:
        return False
    return (ahora - login_at) > ttl_seconds
