"""Estado de salud del sistema para el dashboard `/salud` y el endpoint
`/api/health` (monitores externos tipo UptimeRobot/CloudWatch).

Chequea: conectividad a la BD, uso de disco, uptime del proceso y frescura del
backup de MySQL. Cada chequeo es tolerante a fallos (nunca tira: reporta `ok=False`
con el motivo) para que el dashboard siga funcionando aunque una parte esté mal.
"""
from __future__ import annotations

import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinica_app.config import (
    BACKUP_DIR, BACKUP_MAX_AGE_HOURS, DISK_WARN_PCT, UPLOAD_DIR,
)

# Instante de arranque del proceso (se fija al importar el módulo).
_INICIO = time.time()

_GB = 1024 ** 3


def _humano(segundos: float) -> str:
    s = int(segundos)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


async def estado_db(session: AsyncSession) -> dict[str, Any]:
    """Conectividad a la BD: un `SELECT 1` con latencia."""
    t0 = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        return {"ok": True, "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def estado_disco(path: str | None = None) -> dict[str, Any]:
    """Uso de disco del volumen donde viven los datos (uploads por defecto)."""
    objetivo = path or UPLOAD_DIR or "."
    if not os.path.exists(objetivo):
        objetivo = "."
    try:
        total, usado, libre = shutil.disk_usage(objetivo)
        pct = round(usado / total * 100, 1) if total else 0.0
        return {
            "ok": pct < DISK_WARN_PCT,
            "total_gb": round(total / _GB, 1),
            "usado_gb": round(usado / _GB, 1),
            "libre_gb": round(libre / _GB, 1),
            "pct_usado": pct,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def uptime() -> dict[str, Any]:
    seg = time.time() - _INICIO
    return {"segundos": int(seg), "texto": _humano(seg)}


def estado_backups() -> dict[str, Any]:
    """Frescura del backup de MySQL más reciente en `BACKUP_DIR`.

    Sin `BACKUP_DIR` configurado, reporta `configurado=False` (no es un fallo:
    los backups son un pendiente P0). Con dir, busca el archivo más nuevo y
    compara su antigüedad contra `BACKUP_MAX_AGE_HOURS`.
    """
    if not BACKUP_DIR:
        return {"ok": True, "configurado": False}
    try:
        if not os.path.isdir(BACKUP_DIR):
            return {"ok": False, "configurado": True, "error": "BACKUP_DIR no existe"}
        archivos = [
            os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
            if os.path.isfile(os.path.join(BACKUP_DIR, f))
        ]
        if not archivos:
            return {"ok": False, "configurado": True, "error": "sin backups"}
        mas_nuevo = max(archivos, key=os.path.getmtime)
        edad_h = (time.time() - os.path.getmtime(mas_nuevo)) / 3600
        return {
            "ok": edad_h <= BACKUP_MAX_AGE_HOURS,
            "configurado": True,
            "ultimo": os.path.basename(mas_nuevo),
            "edad_horas": round(edad_h, 1),
        }
    except Exception as exc:
        return {"ok": False, "configurado": True, "error": str(exc)}


async def estado_sistema(session: AsyncSession) -> dict[str, Any]:
    """Agrega todos los chequeos. `status` = 'ok' salvo que algún chequeo falle."""
    db      = await estado_db(session)
    disco   = estado_disco()
    up      = uptime()
    backups = estado_backups()

    ok = db["ok"] and disco.get("ok", True) and backups.get("ok", True)
    return {
        "status":  "ok" if ok else "degraded",
        "ts":      datetime.now(timezone.utc).isoformat(),
        "db":      db,
        "disco":   disco,
        "uptime":  up,
        "backups": backups,
    }
