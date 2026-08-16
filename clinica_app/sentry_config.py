"""Integración con Sentry (observabilidad de errores en prod).

Es **no-op sin `SENTRY_DSN`**: la app arranca igual en dev/local. Con DSN,
inicializa el SDK una sola vez para capturar excepciones no manejadas (UI,
tareas, scheduler). El DSN lo crea el usuario en su proyecto de Sentry.
"""
from __future__ import annotations

import logging

from clinica_app.config import (
    SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE,
)

log = logging.getLogger(__name__)

_inicializado = False


def init_sentry() -> bool:
    """Inicializa Sentry si hay DSN. Idempotente. Devuelve True si quedó activo."""
    global _inicializado
    if _inicializado:
        return True
    if not SENTRY_DSN:
        return False
    try:
        import sentry_sdk
    except ImportError:
        log.warning("SENTRY_DSN configurado pero sentry-sdk no está instalado")
        return False

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,   # no mandar datos de pacientes a Sentry
    )
    _inicializado = True
    log.info("Sentry inicializado (env=%s)", SENTRY_ENVIRONMENT)
    return True
