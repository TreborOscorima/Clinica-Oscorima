"""Configuración central de logging (observabilidad).

Un único `setup_logging()` idempotente que configura el root logger para toda la
app (UI, tareas, scheduler). En prod emite **JSON estructurado** (una línea por
evento, apto para agregadores tipo Loki/CloudWatch); en dev, texto legible.

Los servicios NO configuran logging: solo obtienen su logger con
`logging.getLogger(__name__)` y adjuntan contexto estructurado con `extra`:

    log.info("compra anulada", extra={"clinica_id": cid, "entidad": "compra",
                                      "entidad_id": compra_id})

El formateador JSON serializa esos campos `extra` como claves de primer nivel.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os

# Atributos estándar de un LogRecord — todo lo que NO esté acá se considera
# contexto `extra` del que loguea y se incluye en el JSON.
_RESERVADOS = frozenset(vars(logging.makeLogRecord({})).keys()) | {
    "message", "asctime", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Formatea cada registro como una línea JSON con el contexto `extra`."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts":     _dt.datetime.fromtimestamp(record.created, _dt.timezone.utc).isoformat(),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        for clave, valor in record.__dict__.items():
            if clave not in _RESERVADOS and not clave.startswith("_"):
                payload[clave] = valor
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _quiere_json() -> bool:
    valor = os.getenv("LOG_JSON")
    if valor is not None:
        return valor.strip().lower() in ("1", "true", "yes", "on")
    # Sin override explícito: JSON en prod, texto en dev.
    return os.getenv("ENV", "").strip().lower() == "prod"


def setup_logging(*, force: bool = False) -> None:
    """Configura el root logger una sola vez (idempotente).

    - Nivel desde `LOG_LEVEL` (default INFO).
    - Formato JSON si `LOG_JSON` es truthy, o si `ENV=prod` sin override.
    - `force=True` reemplaza los handlers existentes (útil en tests).
    """
    root = logging.getLogger()
    if getattr(root, "_clinica_configurado", False) and not force:
        return

    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler()
    if _quiere_json():
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
    root.addHandler(handler)

    nivel = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    root.setLevel(getattr(logging, nivel, logging.INFO))

    root._clinica_configurado = True  # type: ignore[attr-defined]
